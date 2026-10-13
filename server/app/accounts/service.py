import hmac
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import mailer
from app.accounts.models import AccountSession, EmailChallenge, User
from app.accounts.ratelimit import limiter
from app.accounts.security import (
    SESSION_PREFIX,
    burn_password_check,
    code_matches,
    hash_code,
    hash_password,
    hash_session_token,
    needs_rehash,
    new_code,
    new_session_token,
    verify_password,
)
from app.core.auth import Principal
from app.core.config import settings
from app.db.models import Connection, IdempotencyRecord, OAuthClientConfig, OAuthState, RunLog, RuntimeToken

logger = logging.getLogger("connector.accounts")

OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN = timedelta(seconds=60)
SHORT_SESSION = timedelta(hours=12)
LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = 15 * 60
MIN_PASSWORD = 10
MAX_PASSWORD = 128


class AccountError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# --- time helpers ----------------------------------------------------------

def _now() -> datetime:
    return datetime.utcnow()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="microseconds") + "Z"


def _parse(ts: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(ts.rstrip("Z")) if ts else None


# --- validation ------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"^[a-z0-9._%+\-]+@[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?)+$"
)
_RESERVED_SUFFIXES = (".invalid", ".test", ".localhost", ".local", ".example")
_RESERVED_DOMAINS = {"example.com", "example.org", "example.net", "localhost"}
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "1234567890", "12345678910", "qwertyuiop", "qwerty12345",
    "iloveyou123", "letmein1234", "admin12345", "welcome123", "abc1234567", "1q2w3e4r5t", "passw0rd123",
}


def _blocked_domains() -> set:
    return {d.strip().lower() for d in settings.ACCOUNTS_BLOCKED_EMAIL_DOMAINS.split(",") if d.strip()}


def normalize_email(raw: Optional[str]) -> str:
    email = (raw or "").strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AccountError(400, "INVALID_EMAIL", "Please enter a valid email address.")
    domain = email.rsplit("@", 1)[1]
    if domain in _RESERVED_DOMAINS or domain.endswith(_RESERVED_SUFFIXES) or domain in _blocked_domains():
        raise AccountError(400, "INVALID_EMAIL", "Please use a valid email address.")
    return email


def validate_password(password: Optional[str], email: str = "") -> None:
    if not isinstance(password, str) or not (MIN_PASSWORD <= len(password) <= MAX_PASSWORD):
        raise AccountError(400, "WEAK_PASSWORD", f"Password must be {MIN_PASSWORD}-{MAX_PASSWORD} characters long.")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS or lowered == email or (email and lowered == email.split("@")[0]):
        raise AccountError(400, "WEAK_PASSWORD", "That password is too easy to guess.")


# --- signup policy ---------------------------------------------------------

def _invite_codes() -> list:
    return [c.strip() for c in settings.ACCOUNTS_INVITE_CODES.split(",") if c.strip()]


def effective_signup_mode() -> str:
    """The configured mode, downgraded to 'disabled' when it is unsafe to honour."""
    mode = (settings.ACCOUNTS_SIGNUP_MODE or "disabled").strip().lower()
    if mode == "open" and not mailer.email_enabled():
        logger.error("ACCOUNTS_SIGNUP_MODE=open needs an email backend; signups are disabled.")
        return "disabled"
    if mode == "invite" and not _invite_codes():
        logger.error("ACCOUNTS_SIGNUP_MODE=invite needs ACCOUNTS_INVITE_CODES; signups are disabled.")
        return "disabled"
    return mode if mode in ("invite", "open") else "disabled"


def _invite_valid(code: Optional[str]) -> bool:
    supplied = (code or "").strip().encode("utf-8")
    ok = False
    for candidate in _invite_codes():  # compare against all codes, no early exit
        ok |= hmac.compare_digest(supplied, candidate.encode("utf-8"))
    return ok


# --- users -----------------------------------------------------------------

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


def _rate_limit(key: str, limit: int, window: float, message: str = "Too many attempts. Please try again later.") -> None:
    if not limiter.allow(key, limit, window):
        raise AccountError(429, "RATE_LIMITED", message)


def _verification_email(code: str, purpose: str) -> Tuple[str, str]:
    if purpose == "verify_email":
        subject = f"Your {settings.PROJECT_NAME} verification code"
        lead = "Use this code to verify your email address"
    else:
        subject = f"Your {settings.PROJECT_NAME} password reset code"
        lead = "Use this code to reset your password"
    body = (
        f"{lead}: {code}\n\nThe code expires in 10 minutes. "
        "If you did not request it, you can safely ignore this email."
    )
    return subject, body


async def issue_challenge(db: AsyncSession, user: User, purpose: str) -> Optional[str]:
    """Create a fresh one-time code, or None when one was issued less than a minute ago."""
    now = _now()
    latest = (await db.execute(
        select(EmailChallenge)
        .where(EmailChallenge.user_id == user.id, EmailChallenge.purpose == purpose)
        .order_by(EmailChallenge.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if latest and latest.consumed_at is None and now - _parse(latest.created_at) < OTP_COOLDOWN:
        return None
    await db.execute(
        update(EmailChallenge)
        .where(EmailChallenge.user_id == user.id, EmailChallenge.purpose == purpose,
               EmailChallenge.consumed_at.is_(None))
        .values(consumed_at=_iso(now))
    )
    code = new_code()
    challenge_id = str(uuid.uuid4())
    db.add(EmailChallenge(
        id=challenge_id, user_id=user.id, purpose=purpose, code_hash=hash_code(challenge_id, code),
        created_at=_iso(now), expires_at=_iso(now + OTP_TTL),
    ))
    await db.commit()
    return code


async def consume_challenge(db: AsyncSession, user: User, purpose: str, code: Optional[str]) -> None:
    """Validate and burn a code. Raises 401 for wrong, expired, or exhausted codes."""
    invalid = AccountError(401, "INVALID_OR_EXPIRED_CODE", "That code is invalid or has expired.")
    now = _now()
    ch = (await db.execute(
        select(EmailChallenge)
        .where(EmailChallenge.user_id == user.id, EmailChallenge.purpose == purpose,
               EmailChallenge.consumed_at.is_(None))
        .order_by(EmailChallenge.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not ch or _parse(ch.expires_at) < now or not isinstance(code, str):
        raise invalid
    if not code_matches(ch.id, code, ch.code_hash):
        ch.attempts += 1
        if ch.attempts >= OTP_MAX_ATTEMPTS:
            ch.consumed_at = _iso(now)  # too many guesses: the code is dead even if guessed later
        await db.commit()
        raise invalid
    ch.consumed_at = _iso(now)


# --- sessions --------------------------------------------------------------

async def create_session(db: AsyncSession, user: User, ip: Optional[str], user_agent: Optional[str],
                         remember: bool = True) -> Tuple[str, int]:
    token = new_session_token()
    ttl = timedelta(days=settings.ACCOUNTS_SESSION_DAYS) if remember else SHORT_SESSION
    now = _now()
    db.add(AccountSession(
        token_hash=hash_session_token(token), user_id=user.id, created_at=_iso(now),
        expires_at=_iso(now + ttl), last_used_at=_iso(now),
        user_agent=(user_agent or "")[:512] or None, ip=ip,
    ))
    user.last_login_at = _iso(now)
    await db.commit()
    return token, int(ttl.total_seconds())


async def get_session_user(db: AsyncSession, raw_token: Optional[str]) -> Optional[Tuple[AccountSession, User]]:
    if not raw_token or not raw_token.startswith(SESSION_PREFIX):
        return None
    row = (await db.execute(
        select(AccountSession).where(AccountSession.token_hash == hash_session_token(raw_token))
    )).scalar_one_or_none()
    now = _now()
    if not row or row.revoked or _parse(row.expires_at) <= now:
        return None
    user = await db.get(User, row.user_id)
    if not user or not user.is_active or not user.is_email_verified:
        return None
    if not row.last_used_at or now - _parse(row.last_used_at) > timedelta(minutes=5):
        row.last_used_at = _iso(now)
        await db.commit()
    return row, user


async def session_principal_resolver(raw_token: str, db: AsyncSession) -> Optional[Principal]:
    """Plug into the core: a valid session cookie becomes a tenant admin for the user's own tenant."""
    found = await get_session_user(db, raw_token)
    if not found:
        return None
    _, user = found
    return Principal(kind="tenant_admin", id=f"user:{user.id}", name=user.email, tenant_id=user.tenant_id)


async def revoke_session(db: AsyncSession, raw_token: Optional[str]) -> None:
    if raw_token:
        await db.execute(update(AccountSession)
                         .where(AccountSession.token_hash == hash_session_token(raw_token))
                         .values(revoked=True))
        await db.commit()


async def revoke_user_sessions(db: AsyncSession, user_id: str, keep_token: Optional[str] = None) -> None:
    stmt = update(AccountSession).where(AccountSession.user_id == user_id, AccountSession.revoked.is_(False))
    if keep_token:
        stmt = stmt.where(AccountSession.token_hash != hash_session_token(keep_token))
    await db.execute(stmt.values(revoked=True))


# --- flows -----------------------------------------------------------------

async def signup(db: AsyncSession, email: Optional[str], password: Optional[str], invite_code: Optional[str],
                 ip: str) -> Tuple[str, Optional[Tuple[User, str]]]:
    """Returns (status, (user, code)) where code is set when a verification email must be sent."""
    mode = effective_signup_mode()
    if mode == "disabled":
        raise AccountError(403, "SIGNUP_CLOSED", "Sign-ups are currently closed.")
    _rate_limit(f"signup:ip:{ip}", 10, 3600)
    email = normalize_email(email)
    validate_password(password, email)
    if mode == "invite" and not _invite_valid(invite_code):
        raise AccountError(403, "INVALID_INVITE", "That invite code is not valid.")

    verification = mailer.email_enabled()
    existing = await get_user_by_email(db, email)
    if existing:
        if not verification:
            raise AccountError(409, "EMAIL_REGISTERED", "An account with this email already exists.")
        burn_password_check(password)  # same cost as a real signup, and the same response
        if not existing.is_email_verified:
            code = await issue_challenge(db, existing, "verify_email")
            return "verification_required", ((existing, code) if code else None)
        return "verification_required", None

    user = User(
        email=email, password_hash=hash_password(password), tenant_id=f"u_{uuid.uuid4().hex}",
        is_email_verified=not verification, is_active=True, password_changed_at=_iso(_now()),
    )
    db.add(user)
    await db.commit()
    if not verification:
        return "created", None
    code = await issue_challenge(db, user, "verify_email")
    return "verification_required", ((user, code) if code else None)


async def verify_email(db: AsyncSession, email: Optional[str], code: Optional[str], ip: str) -> User:
    _rate_limit(f"verify:ip:{ip}", 30, 900)
    invalid = AccountError(401, "INVALID_OR_EXPIRED_CODE", "That code is invalid or has expired.")
    try:
        user = await get_user_by_email(db, normalize_email(email))
    except AccountError:
        raise invalid
    if not user:
        raise invalid
    await consume_challenge(db, user, "verify_email", code)
    user.is_email_verified = True
    await db.commit()
    return user


async def login(db: AsyncSession, email: Optional[str], password: Optional[str], ip: str) -> User:
    _rate_limit(f"login:ip:{ip}", 30, LOGIN_FAILURE_WINDOW)
    bad = AccountError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    try:
        normalized = normalize_email(email)
    except AccountError:
        burn_password_check(password or "")
        raise bad
    fail_key = f"login:fail:{normalized}"
    if limiter.count(fail_key, LOGIN_FAILURE_WINDOW) >= LOGIN_FAILURE_LIMIT:
        raise AccountError(429, "RATE_LIMITED", "Too many failed attempts. Please try again in a few minutes.")
    user = await get_user_by_email(db, normalized)
    if not user or not isinstance(password, str) or not verify_password(user.password_hash, password):
        if not user:
            burn_password_check(password if isinstance(password, str) else "")
        limiter.record(fail_key, LOGIN_FAILURE_WINDOW)
        raise bad
    if not user.is_email_verified:
        raise AccountError(403, "EMAIL_NOT_VERIFIED", "Please verify your email address first.")
    if not user.is_active:
        raise AccountError(403, "ACCOUNT_DISABLED", "This account has been disabled. Contact support.")
    limiter.reset(fail_key)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


async def forgot_password(db: AsyncSession, email: Optional[str], ip: str) -> Optional[Tuple[User, str]]:
    if not mailer.email_enabled():
        raise AccountError(503, "EMAIL_UNAVAILABLE", "Password reset by email is not available. Contact the operator.")
    _rate_limit(f"forgot:ip:{ip}", 20, 3600)
    try:
        normalized = normalize_email(email)
    except AccountError:
        return None
    _rate_limit(f"forgot:email:{normalized}", 3, 3600)
    user = await get_user_by_email(db, normalized)
    if not user or not user.is_email_verified or not user.is_active:
        return None
    code = await issue_challenge(db, user, "reset_password")
    return (user, code) if code else None


async def resend_verification(db: AsyncSession, email: Optional[str], ip: str) -> Optional[Tuple[User, str]]:
    if not mailer.email_enabled():
        raise AccountError(503, "EMAIL_UNAVAILABLE", "Email verification is not available. Contact the operator.")
    _rate_limit(f"resend:ip:{ip}", 20, 3600)
    try:
        normalized = normalize_email(email)
    except AccountError:
        return None
    _rate_limit(f"resend:email:{normalized}", 3, 3600)
    user = await get_user_by_email(db, normalized)
    if not user or user.is_email_verified:
        return None
    code = await issue_challenge(db, user, "verify_email")
    return (user, code) if code else None


async def reset_password(db: AsyncSession, email: Optional[str], code: Optional[str],
                         new_password: Optional[str], ip: str) -> None:
    _rate_limit(f"reset:ip:{ip}", 30, 900)
    invalid = AccountError(401, "INVALID_OR_EXPIRED_CODE", "That code is invalid or has expired.")
    try:
        normalized = normalize_email(email)
    except AccountError:
        raise invalid
    user = await get_user_by_email(db, normalized)
    if not user:
        raise invalid
    validate_password(new_password, normalized)
    await consume_challenge(db, user, "reset_password", code)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = _iso(_now())
    await revoke_user_sessions(db, user.id)  # every device must sign in again
    await db.commit()


async def change_password(db: AsyncSession, user: User, current: Optional[str], new: Optional[str],
                          keep_token: Optional[str]) -> None:
    _rate_limit(f"chpw:user:{user.id}", 10, 900)
    if not isinstance(current, str) or not verify_password(user.password_hash, current):
        raise AccountError(401, "INVALID_CREDENTIALS", "Current password is incorrect.")
    validate_password(new, user.email)
    user.password_hash = hash_password(new)
    user.password_changed_at = _iso(_now())
    await revoke_user_sessions(db, user.id, keep_token=keep_token)
    await db.commit()


async def purge_tenant_data(db: AsyncSession, tenant_id: str) -> None:
    for model in (Connection, OAuthState, RuntimeToken, RunLog, IdempotencyRecord):
        await db.execute(delete(model).where(model.tenant_id == tenant_id))
    await db.execute(delete(OAuthClientConfig).where(OAuthClientConfig.service.like(f"tenant:{tenant_id}:%")))


async def delete_account(db: AsyncSession, user: User, password: Optional[str]) -> None:
    _rate_limit(f"delete:user:{user.id}", 5, 900)
    if not isinstance(password, str) or not verify_password(user.password_hash, password):
        raise AccountError(401, "INVALID_CREDENTIALS", "Password is incorrect.")
    await purge_tenant_data(db, user.tenant_id)
    await db.execute(delete(AccountSession).where(AccountSession.user_id == user.id))
    await db.execute(delete(EmailChallenge).where(EmailChallenge.user_id == user.id))
    await db.delete(user)
    await db.commit()


async def queue_email(user: User, code: Optional[str], purpose: str) -> None:
    if code:
        subject, body = _verification_email(code, purpose)
        await mailer.send_email(user.email, subject, body)


def client_ip(request: Request) -> str:
    """Peer address, or X-Real-IP when the peer is the local reverse proxy."""
    peer = request.client.host if request.client else "unknown"
    if peer in ("127.0.0.1", "::1", "testclient") or peer.startswith(("10.", "172.", "192.168.")):
        forwarded = request.headers.get("x-real-ip")
        if forwarded:
            return forwarded.strip()[:64]
    return peer

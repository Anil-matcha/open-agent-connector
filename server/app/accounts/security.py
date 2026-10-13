import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

SESSION_PREFIX = "cs_"

_hasher = PasswordHasher()  # argon2id with the library's recommended parameters
# Verified against when an email is unknown, so "no such user" costs the same as "wrong password".
_DUMMY_HASH = _hasher.hash("not-a-real-password-used-only-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def burn_password_check(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def new_session_token() -> str:
    return SESSION_PREFIX + secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _otp_key() -> bytes:
    return hmac.new(settings.ENCRYPTION_KEY.encode("utf-8"), b"accounts-otp-v1", hashlib.sha256).digest()


def hash_code(challenge_id: str, code: str) -> str:
    """Keyed hash: a leaked database cannot be brute-forced offline without the server key."""
    return hmac.new(_otp_key(), f"{challenge_id}:{code}".encode("utf-8"), hashlib.sha256).hexdigest()


def code_matches(challenge_id: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(challenge_id, code.strip()), stored_hash)

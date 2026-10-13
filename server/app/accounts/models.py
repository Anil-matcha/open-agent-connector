import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Index, Integer, String

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(254), nullable=False, unique=True, index=True)  # stored lower-cased
    password_hash = Column(String(255), nullable=False)
    tenant_id = Column(String(64), nullable=False, unique=True)  # the tenant this user owns
    is_email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(32), default=_now)
    last_login_at = Column(String(32), nullable=True)
    password_changed_at = Column(String(32), nullable=True)


class AccountSession(Base):
    __tablename__ = "account_sessions"

    # SHA-256 of the cookie value; the raw token exists only in the user's browser.
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    created_at = Column(String(32), default=_now)
    expires_at = Column(String(32), nullable=False)
    last_used_at = Column(String(32), nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    user_agent = Column(String(512), nullable=True)
    ip = Column(String(64), nullable=True)


class EmailChallenge(Base):
    """One-time 6-digit code for email verification or password reset (stored only as a keyed hash)."""

    __tablename__ = "email_challenges"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False)
    purpose = Column(String(32), nullable=False)  # "verify_email" | "reset_password"
    code_hash = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(String(32), default=_now)
    expires_at = Column(String(32), nullable=False)
    consumed_at = Column(String(32), nullable=True)

    __table_args__ = (Index("idx_challenge_user_purpose", "user_id", "purpose"),)

import json
import secrets
from typing import Optional, List, Dict, Any, Union
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_token
from app.core.policy import match_pattern
from app.db.session import get_db
from app.db.models import RuntimeToken, utcnow_str

security_scheme = HTTPBearer(auto_error=False)

class Principal:
    def __init__(
        self,
        kind: str, # "admin" or "runtime"
        id: str,
        name: str,
        allowed_actions: Optional[List[str]] = None,
        blocked_actions: Optional[List[str]] = None,
        allowed_connections: Optional[List[str]] = None,
        allowed_proxies: Optional[List[str]] = None,
    ):
        self.kind = kind
        self.id = id
        self.name = name
        self.allowed_actions = allowed_actions or []
        self.blocked_actions = blocked_actions or []
        self.allowed_connections = allowed_connections or []
        self.allowed_proxies = allowed_proxies or []

    @property
    def is_admin(self) -> bool:
        return self.kind == "admin"

    def can_access_action(self, action_id: str) -> bool:
        """Deny-by-default action access evaluation."""
        if self.is_admin:
            return True

        # 1. Any matching blocked rule immediately denies
        for pattern in self.blocked_actions:
            if match_pattern(pattern, action_id):
                return False

        # 2. Deny-by-default: must match an explicitly allowed action
        if not self.allowed_actions:
            return False

        for pattern in self.allowed_actions:
            if match_pattern(pattern, action_id):
                return True

        return False

    def can_access_connection(self, connection_name: str) -> bool:
        """Connection access evaluation."""
        if self.is_admin:
            return True
        if not self.allowed_connections:
            # If not explicitly restricted, default connection access is allowed
            return True
        return connection_name in self.allowed_connections

    def can_access_proxy(self, service: str) -> bool:
        """Deny-by-default proxy access evaluation."""
        if self.is_admin:
            return True
        if not self.allowed_proxies:
            return False
        for pattern in self.allowed_proxies:
            if match_pattern(pattern, service):
                return True
        return False


def _extract_token(request: Request, auth_creds: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    # 1. Standard Bearer Authorization header
    if auth_creds and auth_creds.credentials:
        return auth_creds.credentials.strip()

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    # 2. Dedicated x-admin-token or x-runtime-token headers
    admin_header = request.headers.get("x-admin-token")
    if admin_header and admin_header.strip():
        return admin_header.strip()

    runtime_header = request.headers.get("x-runtime-token")
    if runtime_header and runtime_header.strip():
        return runtime_header.strip()

    return None


async def resolve_principal(raw_token: str, db: AsyncSession) -> Optional[Principal]:
    if not raw_token:
        return None

    # 1. Check against Admin token (constant time comparison)
    admin_secret = settings.ADMIN_TOKEN.strip()
    if admin_secret and secrets.compare_digest(raw_token, admin_secret):
        return Principal(
            kind="admin",
            id="admin-operator",
            name="Operator Admin",
            allowed_actions=["*"],
            allowed_connections=["*"],
            allowed_proxies=["*"]
        )

    # 2. Check against persistent RuntimeToken in database
    token_hashed = hash_token(raw_token)
    stmt = select(RuntimeToken).where(
        RuntimeToken.token_hash == token_hashed,
        RuntimeToken.is_active == True
    )
    result = await db.execute(stmt)
    token_row = result.scalar_one_or_none()
    if token_row:
        # Update last used timestamp
        token_row.last_used_at = utcnow_str()
        try:
            await db.commit()
        except Exception:
            pass

        return Principal(
            kind="runtime",
            id=token_row.id,
            name=token_row.name,
            allowed_actions=json.loads(token_row.allowed_actions or "[]"),
            blocked_actions=json.loads(token_row.blocked_actions or "[]"),
            allowed_connections=json.loads(token_row.allowed_connections or "[]"),
            allowed_proxies=json.loads(token_row.allowed_proxies or "[]")
        )

    # 3. Check optional static RUNTIME_TOKEN setting
    static_runtime = settings.RUNTIME_TOKEN.strip()
    if static_runtime and secrets.compare_digest(raw_token, static_runtime):
        return Principal(
            kind="runtime",
            id="static-runtime",
            name="Static Runtime Token",
            allowed_actions=["*"],
            allowed_connections=["*"],
            allowed_proxies=["*"]
        )

    return None


async def require_admin(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Principal:
    """Enforces that the caller is an authenticated administrator."""
    token = _extract_token(request, auth_creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authorization required: missing bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    principal = await resolve_principal(token, db)
    if not principal or not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized admin token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return principal


async def require_runtime_or_admin(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Principal:
    """Enforces that the caller has either a valid runtime token or admin token."""
    token = _extract_token(request, auth_creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: missing bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    principal = await resolve_principal(token, db)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return principal


def check_action_permission(principal: Principal, action_id: str, connection_name: str = "default"):
    """Validates that the principal is permitted to call the specific action and connection."""
    if not principal.can_access_action(action_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: action '{action_id}' is not authorized for this token"
        )

    if not principal.can_access_connection(connection_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: connection '{connection_name}' is not authorized for this token"
        )

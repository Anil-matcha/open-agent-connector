import secrets
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import RuntimeToken, utcnow_str
from app.core.security import hash_token
from app.core.auth import require_admin, Principal

router = APIRouter(prefix="/runtime-tokens", tags=["Admin Tokens"])

class CreateTokenInput(BaseModel):
    name: str
    allowedActions: Optional[List[str]] = []
    blockedActions: Optional[List[str]] = []
    allowedProxies: Optional[List[str]] = []
    allowedConnections: Optional[List[str]] = []

@router.get("")
async def list_tokens(
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RuntimeToken)
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "allowedActions": json.loads(t.allowed_actions or "[]"),
                "blockedActions": json.loads(t.blocked_actions or "[]"),
                "allowedProxies": json.loads(t.allowed_proxies or "[]"),
                "allowedConnections": json.loads(t.allowed_connections or "[]"),
                "isActive": getattr(t, "is_active", True),
                "revokedAt": getattr(t, "revoked_at", None),
                "createdAt": t.created_at,
                "lastUsedAt": t.last_used_at
            }
            for t in tokens
        ]
    }

@router.post("")
async def create_token(
    payload: CreateTokenInput,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    raw_token = f"ch_live_{secrets.token_urlsafe(32)}"
    token_hashed = hash_token(raw_token)
    
    token = RuntimeToken(
        name=payload.name,
        token_hash=token_hashed,
        allowed_actions=json.dumps(payload.allowedActions or []),
        blocked_actions=json.dumps(payload.blockedActions or []),
        allowed_proxies=json.dumps(payload.allowedProxies or []),
        allowed_connections=json.dumps(payload.allowedConnections or []),
        is_active=True
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return {
        "success": True,
        "data": {
            "id": token.id,
            "name": token.name,
            "rawToken": raw_token, # Only returned once upon creation!
            "allowedActions": payload.allowedActions or [],
            "allowedConnections": payload.allowedConnections or [],
            "createdAt": token.created_at
        }
    }

@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RuntimeToken).where(RuntimeToken.id == token_id)
    token = (await db.execute(stmt)).scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Mark as revoked and delete
    token.is_active = False
    token.revoked_at = utcnow_str()
    await db.delete(token)
    await db.commit()
    return {"success": True, "message": "Token revoked successfully"}

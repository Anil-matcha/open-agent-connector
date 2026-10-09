import secrets
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

class VerifyTokenInput(BaseModel):
    token: str

@router.get("/status")
async def get_auth_status(request: Request):
    """
    Returns authentication state for the web console.
    When accessed on local loopback, provides the local admin token to the UI.
    On non-loopback addresses, requires explicit operator login.
    """
    client_host = request.client.host if request.client else ""
    is_loopback = client_host in ("127.0.0.1", "::1", "localhost", "testclient")

    return {
        "status": "ready",
        "isLoopback": is_loopback,
        "localToken": settings.ADMIN_TOKEN if is_loopback else None
    }

@router.post("/verify")
async def verify_token(payload: VerifyTokenInput):
    """Verifies whether a provided bearer token matches the admin secret."""
    admin_secret = settings.ADMIN_TOKEN.strip()
    is_valid = bool(admin_secret and secrets.compare_digest(payload.token.strip(), admin_secret))
    return {
        "valid": is_valid
    }

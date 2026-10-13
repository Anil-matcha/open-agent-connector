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
    # A reverse proxy on the same host also appears as loopback, so any proxy
    # header means the caller is not genuinely local.
    proxied = any(
        h in request.headers
        for h in ("x-forwarded-for", "x-real-ip", "forwarded", "x-forwarded-host")
    )
    expose = settings.EXPOSE_LOCAL_TOKEN and is_loopback and not proxied

    return {
        "status": "ready",
        "isLoopback": is_loopback and not proxied,
        "localToken": settings.ADMIN_TOKEN if expose else None
    }

@router.post("/verify")
async def verify_token(payload: VerifyTokenInput):
    """Verifies whether a provided bearer token matches the admin secret."""
    admin_secret = settings.ADMIN_TOKEN.strip()
    is_valid = bool(admin_secret and secrets.compare_digest(payload.token.strip(), admin_secret))
    return {
        "valid": is_valid
    }

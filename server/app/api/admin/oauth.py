from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.services.oauth_service import OAuthService, OAUTH_PROVIDERS
from app.core.auth import require_admin, Principal

router = APIRouter(prefix="/oauth", tags=["Admin OAuth"])

class OAuthConfigInput(BaseModel):
    clientId: str
    clientSecret: str

@router.get("/providers")
async def list_oauth_providers(
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List providers supporting OAuth2 and indicate if client credentials are configured."""
    results = []
    for service, meta in OAUTH_PROVIDERS.items():
        config = await OAuthService.get_client_config(db, service)
        results.append({
            "service": service,
            "displayName": meta["display_name"],
            "configured": config is not None and bool(config.get("client_id")),
            "defaultScopes": meta["default_scopes"]
        })
    return {"success": True, "data": results}

@router.get("/{service}/config")
async def get_oauth_config(
    service: str,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Check if OAuth is configured for a service. Never exposes client_secret."""
    config = await OAuthService.get_client_config(db, service)
    if not config:
        return {"success": True, "configured": False, "clientId": None}
    return {
        "success": True,
        "configured": True,
        "clientId": config.get("client_id")
    }

@router.post("/{service}/config")
async def set_oauth_config(
    service: str,
    payload: OAuthConfigInput,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Configure or update OAuth client ID and client secret (stored AES-256-GCM encrypted)."""
    if service not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"OAuth is not supported for service '{service}'.")
    
    await OAuthService.set_client_config(
        session=db,
        service=service,
        client_id=payload.clientId.strip(),
        client_secret=payload.clientSecret.strip()
    )
    return {"success": True, "message": f"OAuth client configuration saved securely for {service}."}

@router.get("/{service}/authorize")
async def initiate_oauth(
    service: str,
    connectionName: Optional[str] = "default",
    redirectUri: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate PKCE state, record expiring transaction state, and return authorization URL."""
    try:
        res = await OAuthService.create_authorization_url(
            session=db,
            service=service,
            connection_name=connectionName or "default",
            redirect_uri=redirectUri
        )
        return {"success": True, "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth authorization: {str(e)}")

@router.get("/{service}/callback")
async def handle_oauth_callback(
    service: str,
    code: str = Query(...),
    state: str = Query(...),
    returnUri: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth redirect callback, atomically consume state, exchange code, and persist connection."""
    try:
        conn = await OAuthService.exchange_code(
            session=db,
            service=service,
            code=code,
            state=state
        )
        dest = returnUri or conn.get("returnUri")
        if dest:
            sep = "&" if "?" in dest else "?"
            return RedirectResponse(url=f"{dest}{sep}status=connected&service={service}&connectionName={conn.get('connectionName')}")
        return {"success": True, "data": conn}
    except ValueError as e:
        if returnUri:
            sep = "&" if "?" in returnUri else "?"
            from urllib.parse import quote
            return RedirectResponse(url=f"{returnUri}{sep}status=error&error={quote(str(e))}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if returnUri:
            sep = "&" if "?" in returnUri else "?"
            from urllib.parse import quote
            return RedirectResponse(url=f"{returnUri}{sep}status=error&error={quote('OAuth token exchange failed')}")
        raise HTTPException(status_code=500, detail=f"OAuth callback exchange failed: {str(e)}")

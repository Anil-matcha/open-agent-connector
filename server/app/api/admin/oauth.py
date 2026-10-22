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
    subdomain: Optional[str] = None
    mode: Optional[str] = "custom"

@router.get("/providers")
async def list_oauth_providers(
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List providers supporting OAuth2 and indicate if client credentials are configured."""
    results = []
    for service, meta in OAUTH_PROVIDERS.items():
        status = await OAuthService.get_oauth_status(db, admin.tenant_id, service)
        results.append({
            "service": service,
            "displayName": meta["display_name"],
            "configured": status["configured"],
            "hostedAvailable": status["hostedAvailable"],
            "customConfigured": status["customConfigured"],
            "activeMode": status["activeMode"],
            "callbackUrl": status["callbackUrl"],
            "defaultScopes": meta["default_scopes"]
        })
    return {"success": True, "data": results}

@router.get("/{service}/config")
async def get_oauth_config(
    service: str,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Check if OAuth is configured for a service. Exposes hosted and custom status."""
    status = await OAuthService.get_oauth_status(db, admin.tenant_id, service)
    config = await OAuthService.get_client_config(db, admin.tenant_id, service)
    return {
        "success": True,
        "service": service,
        "configured": status["configured"],
        "hostedAvailable": status["hostedAvailable"],
        "customConfigured": status["customConfigured"],
        "activeMode": status["activeMode"],
        "clientId": config.get("client_id") if config else None,
        "subdomain": config.get("subdomain") if config else None,
        "callbackUrl": status["callbackUrl"],
        "hostedDomain": status["hostedDomain"],
        "publicOrigin": status["publicOrigin"],
        "defaultScopes": status["defaultScopes"]
    }

@router.post("/{service}/config")
async def set_oauth_config(
    service: str,
    payload: OAuthConfigInput,
    mode: Optional[str] = Query(None, description="'hosted' or 'custom'"),
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Configure or update OAuth client ID and client secret (stored AES-256-GCM encrypted)."""
    if service not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"OAuth is not supported for service '{service}'.")
    
    target_mode = mode or payload.mode or "custom"
    if target_mode == "hosted" and not admin.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Configuring server-wide hosted OAuth credentials requires master admin privileges."
        )
    await OAuthService.set_client_config(
        session=db,
        tenant_id=admin.tenant_id,
        service=service,
        client_id=payload.clientId.strip(),
        client_secret=payload.clientSecret.strip(),
        mode=target_mode,
        subdomain=payload.subdomain.strip() if payload.subdomain else None
    )
    return {
        "success": True,
        "mode": target_mode,
        "message": f"OAuth client configuration ({target_mode}) saved securely for {service}."
    }

@router.get("/{service}/authorize")
async def initiate_oauth(
    service: str,
    connectionName: Optional[str] = "default",
    redirectUri: Optional[str] = None,
    subdomain: Optional[str] = Query(None, description="Subdomain for multi-tenant services like Zendesk/Shopify"),
    mode: Optional[str] = Query(None, description="'hosted' or 'custom' (defaults to active mode)"),
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate PKCE state, record expiring transaction state, and return authorization URL."""
    try:
        res = await OAuthService.create_authorization_url(
            session=db,
            tenant_id=admin.tenant_id,
            service=service,
            connection_name=connectionName or "default",
            redirect_uri=redirectUri,
            subdomain=subdomain,
            mode=mode
        )
        return {"success": True, "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth authorization: {str(e)}")

@router.get("/{service}/callback")
async def handle_oauth_callback(
    service: str,
    state: str = Query(...),
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth redirect callback, atomically consume state, exchange code, and persist connection.

    The only redirect destination is the return URL stored (and origin-checked) when the flow
    started. Nothing in the callback request can choose where the browser is sent next.
    """
    from urllib.parse import quote

    dest = await OAuthService.peek_return_uri(db, service, state)

    def back(**params):
        sep = "&" if "?" in dest else "?"
        query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
        return RedirectResponse(url=f"{dest}{sep}{query}")

    if error:
        err_msg = error_description or error
        if dest:
            return back(status="error", error=err_msg)
        raise HTTPException(status_code=400, detail=f"Provider OAuth error: {err_msg}")

    if not code:
        if dest:
            return back(status="error", error="Missing authorization code")
        raise HTTPException(status_code=400, detail="Missing authorization code from provider callback.")

    try:
        conn = await OAuthService.exchange_code(
            session=db,
            service=service,
            code=code,
            state=state
        )
        if dest:
            return back(status="connected", service=service, connectionName=conn.get("connectionName"))
        return {"success": True, "data": conn}
    except ValueError as e:
        if dest:
            return back(status="error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if dest:
            return back(status="error", error="OAuth token exchange failed")
        raise HTTPException(status_code=500, detail=f"OAuth callback exchange failed: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.providers.registry import registry
from app.services.connection_service import ConnectionService
from app.core.ssrf import create_guarded_client
from app.core.auth import require_runtime_or_admin, Principal

router = APIRouter(prefix="/proxy", tags=["Proxy"])

class ProxyRequestBody(BaseModel):
    endpoint: str
    method: Optional[str] = "GET"
    body: Optional[Any] = None
    headers: Optional[Dict[str, str]] = {}
    connectionName: Optional[str] = "default"

@router.post("/{service}")
async def proxy_request(
    service: str,
    payload: ProxyRequestBody,
    alias_header: Optional[str] = Header(None, alias="x-connector-alias"),
    principal: Principal = Depends(require_runtime_or_admin),
    db: AsyncSession = Depends(get_db)
):
    provider = registry.get_provider(service)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{service}' not found")
        
    conn_name = alias_header or payload.connectionName or "default"

    # Enforce proxy and connection access control
    if not principal.can_access_proxy(service):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: proxy access to service '{service}' is not authorized for this token"
        )
    if not principal.can_access_connection(conn_name):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: connection '{conn_name}' is not authorized for this token"
        )

    credential = await ConnectionService.resolve_credentials(db, service, conn_name)
    if credential is None and "no_auth" not in provider.auth_types:
        raise HTTPException(status_code=400, detail=f"No configured connection for service '{service}' (alias: '{conn_name}')")

    client = await create_guarded_client()
    try:
        result = await provider.proxy(
            endpoint=payload.endpoint,
            method=payload.method or "GET",
            credential=credential,
            body=payload.body,
            headers=payload.headers or {},
            client=client
        )
        return {"success": True, "data": result}
    except NotImplementedError:
        raise HTTPException(status_code=501, detail=f"Proxy not supported for provider '{service}'")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy upstream request failed: {str(e)}")
    finally:
        await client.aclose()

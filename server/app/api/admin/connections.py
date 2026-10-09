from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.services.connection_service import ConnectionService
from app.core.auth import require_admin, Principal

router = APIRouter(prefix="/connections", tags=["Admin Connections"])

class ConnectionUpsertInput(BaseModel):
    authType: str # "api_key", "oauth2", "custom"
    values: Dict[str, Any]
    connectionName: Optional[str] = "default"

class ConnectionReconnectInput(BaseModel):
    values: Dict[str, Any]
    connectionName: Optional[str] = None

@router.get("")
async def list_connections(
    service: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    conns = await ConnectionService.list_connections(db, service)
    return {"success": True, "data": conns}

@router.get("/{id_or_service}")
async def get_connection(
    id_or_service: str,
    connectionName: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    conn = await ConnectionService.resolve_connection(db, id_or_service, connectionName)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    import json
    scopes = []
    try:
        scopes = json.loads(conn.granted_scopes or "[]")
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "id": conn.id,
            "service": conn.service,
            "connectionName": conn.connection_name,
            "authType": conn.auth_type,
            "accountId": conn.account_id,
            "displayName": conn.display_name,
            "grantedScopes": scopes,
            "status": conn.status or "active",
            "statusMessage": conn.status_message,
            "lastValidatedAt": conn.last_validated_at,
            "expiresAt": conn.expires_at,
            "createdAt": conn.created_at,
            "updatedAt": conn.updated_at
        }
    }

@router.put("/{service}")
async def upsert_connection(
    service: str,
    payload: ConnectionUpsertInput,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        conn = await ConnectionService.upsert_connection(
            session=db,
            service=service,
            auth_type=payload.authType,
            values=payload.values,
            connection_name=payload.connectionName or "default"
        )
        return {"success": True, "data": conn}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save connection: {str(e)}")

@router.post("/{id_or_service}/test")
async def test_connection(
    id_or_service: str,
    connectionName: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Test stored credentials in real-time against the upstream provider."""
    try:
        res = await ConnectionService.test_connection(db, id_or_service, connectionName)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.post("/{id_or_service}/disconnect")
async def disconnect_connection(
    id_or_service: str,
    connectionName: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a connection without permanently deleting the record."""
    try:
        res = await ConnectionService.disconnect_connection(db, id_or_service, connectionName)
        return {"success": True, "data": res}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect connection: {str(e)}")

@router.post("/{id_or_service}/reconnect")
async def reconnect_connection(
    id_or_service: str,
    payload: ConnectionReconnectInput,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Rotate credentials for an existing connection and re-validate live."""
    try:
        res = await ConnectionService.reconnect_connection(
            session=db,
            id_or_service=id_or_service,
            values=payload.values,
            connection_name=payload.connectionName
        )
        return {"success": True, "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reconnect connection: {str(e)}")

@router.delete("/{id_or_service}")
async def delete_connection(
    id_or_service: str,
    connectionName: Optional[str] = None,
    admin: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    removed = await ConnectionService.delete_connection(db, id_or_service, connectionName)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"success": True, "message": "Connection deleted successfully"}

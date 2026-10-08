from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["Admin Connections"])

class ConnectionUpsertInput(BaseModel):
    authType: str # "api_key", "oauth2", "custom"
    values: Dict[str, Any]
    connectionName: Optional[str] = "default"

@router.get("")
async def list_connections(
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    conns = await ConnectionService.list_connections(db, service)
    return {"success": True, "data": conns}

@router.put("/{service}")
async def upsert_connection(
    service: str,
    payload: ConnectionUpsertInput,
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

@router.delete("/{service}")
async def delete_connection(
    service: str,
    connectionName: Optional[str] = "default",
    db: AsyncSession = Depends(get_db)
):
    removed = await ConnectionService.delete_connection(db, service, connectionName)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"success": True, "message": "Connection deleted successfully"}

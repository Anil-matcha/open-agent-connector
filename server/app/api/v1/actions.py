from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.providers.registry import registry
from app.services.action_runner import ActionRunner

router = APIRouter(prefix="/actions", tags=["Actions"])

class ActionExecutionInput(BaseModel):
    input: Dict[str, Any] = {}
    connectionName: Optional[str] = "default"

@router.get("")
async def list_actions(
    query: Optional[str] = None,
    service: Optional[str] = None
):
    actions = registry.search_actions(query or "", service)
    data = []
    for a in actions:
        provider = registry.get_action_provider(a.id)
        action_dict = a.to_dict()
        action_dict["service"] = provider.service if provider else ""
        action_dict["providerName"] = provider.display_name if provider else ""
        data.append(action_dict)
    return {
        "success": True,
        "data": data
    }

@router.get("/{action_id}")
async def get_action(action_id: str):
    action = registry.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")
    provider = registry.get_action_provider(action_id)
    action_dict = action.to_dict()
    action_dict["service"] = provider.service if provider else ""
    action_dict["providerName"] = provider.display_name if provider else ""
    return {
        "success": True,
        "data": action_dict
    }

@router.post("/{action_id}")
async def execute_action(
    action_id: str,
    payload: ActionExecutionInput,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    alias_header: Optional[str] = Header(None, alias="x-connector-alias"),
    db: AsyncSession = Depends(get_db)
):
    conn_name = alias_header or payload.connectionName or "default"
    try:
        result = await ActionRunner.run(
            session=db,
            action_id=action_id,
            input_data=payload.input,
            connection_name=conn_name,
            caller="http",
            idempotency_key=idempotency_key
        )
        if not result.get("success"):
            status_code = result.get("status_code", 400)
            raise HTTPException(status_code=status_code, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action execution error: {str(e)}")

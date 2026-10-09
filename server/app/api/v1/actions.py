from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.providers.registry import registry
from app.services.action_runner import ActionRunner
from app.core.auth import (
    require_runtime_or_admin,
    check_action_permission,
    resolve_principal,
    _extract_token,
    Principal
)

router = APIRouter(prefix="/actions", tags=["Actions"])

class ActionExecutionInput(BaseModel):
    input: Dict[str, Any] = {}
    connectionName: Optional[str] = "default"

@router.get("")
async def list_actions(
    request: Request,
    query: Optional[str] = None,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List actions matching search criteria.
    If caller authenticates with a runtime token, results are scoped to authorized actions only.
    """
    token = _extract_token(request)
    principal: Optional[Principal] = await resolve_principal(token, db) if token else None

    actions = registry.search_actions(query or "", service)
    data = []
    for a in actions:
        # Enforce deny-by-default scope filtering for runtime callers
        if principal and not principal.can_access_action(a.id):
            continue

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
async def get_action(
    action_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    action = registry.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")

    token = _extract_token(request)
    if token:
        principal = await resolve_principal(token, db)
        if principal and not principal.can_access_action(action_id):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: action '{action_id}' is not authorized for this token"
            )

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
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    alias_header: Optional[str] = Header(None, alias="x-connector-alias"),
    request_id_header: Optional[str] = Header(None, alias="X-Request-ID"),
    principal: Principal = Depends(require_runtime_or_admin),
    db: AsyncSession = Depends(get_db)
):
    conn_name = alias_header or payload.connectionName or "default"

    # Enforce permission check before touching provider or network
    check_action_permission(principal, action_id, conn_name)

    try:
        result = await ActionRunner.run(
            session=db,
            action_id=action_id,
            input_data=payload.input,
            connection_name=conn_name,
            caller="http",
            idempotency_key=idempotency_key,
            principal_id=principal.id
        )
        exec_id = result.get("meta", {}).get("executionId") or request_id_header
        if exec_id:
            response.headers["X-Request-ID"] = exec_id
            response.headers["X-Correlation-ID"] = exec_id

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

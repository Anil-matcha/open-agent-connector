from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional

from app.db.session import get_db
from app.db.models import RunLog, Connection
from app.providers.registry import registry

router = APIRouter(prefix="", tags=["Admin Audit & Runs"])

@router.get("/runs")
async def list_runs(
    service: Optional[str] = None,
    actionId: Optional[str] = None,
    ok: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RunLog).order_by(desc(RunLog.started_at)).limit(limit)
    if service:
        stmt = stmt.where(RunLog.service == service)
    if actionId:
        stmt = stmt.where(RunLog.action_id == actionId)
    if ok is not None:
        stmt = stmt.where(RunLog.ok == ok)

    result = await db.execute(stmt)
    runs = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "actionId": r.action_id,
                "service": r.service,
                "caller": r.caller,
                "ok": r.ok,
                "statusCode": r.status_code,
                "durationMs": r.duration_ms,
                "inputSummary": r.input_summary,
                "outputSummary": r.output_summary,
                "errorMessage": r.error_message,
                "startedAt": r.started_at,
                "completedAt": r.completed_at
            }
            for r in runs
        ]
    }

@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RunLog).where(RunLog.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "success": True,
        "data": {
            "id": run.id,
            "actionId": run.action_id,
            "service": run.service,
            "caller": run.caller,
            "ok": run.ok,
            "statusCode": run.status_code,
            "durationMs": run.duration_ms,
            "inputSummary": run.input_summary,
            "outputSummary": run.output_summary,
            "errorMessage": run.error_message,
            "startedAt": run.started_at,
            "completedAt": run.completed_at
        }
    }

@router.get("/stats")
async def get_overview_stats(db: AsyncSession = Depends(get_db)):
    total_runs = (await db.execute(select(func.count(RunLog.id)))).scalar_one() or 0
    successful_runs = (await db.execute(select(func.count(RunLog.id)).where(RunLog.ok == True))).scalar_one() or 0
    total_connections = (await db.execute(select(func.count(Connection.id)))).scalar_one() or 0
    total_providers = len(registry.list_providers())
    total_actions = len(registry.list_actions())

    success_rate = round((successful_runs / total_runs * 100), 1) if total_runs > 0 else 0.0

    return {
        "success": True,
        "data": {
            "totalRuns": total_runs,
            "successfulRuns": successful_runs,
            "successRate": success_rate,
            "totalConnections": total_connections,
            "totalProviders": total_providers,
            "totalActions": total_actions
        }
    }

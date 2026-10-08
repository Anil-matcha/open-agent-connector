import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.providers.registry import registry
from app.db.models import RunLog, IdempotencyRecord, utcnow_str
from app.services.connection_service import ConnectionService
from app.core.ssrf import create_guarded_client
from app.core.idempotency import compute_request_hash
from app.core.security import encrypt_secret, decrypt_secret

class ActionRunner:
    @staticmethod
    async def run(
        session: AsyncSession,
        action_id: str,
        input_data: Dict[str, Any],
        connection_name: str = "default",
        caller: str = "http",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        action = registry.get_action(action_id)
        if not action:
            raise ValueError(f"Unknown action: '{action_id}'")
        
        provider = registry.get_action_provider(action_id)
        if not provider:
            raise ValueError(f"Provider not found for action '{action_id}'")

        # 1. Idempotency Check
        key_hash = None
        if idempotency_key:
            key_hash = compute_request_hash(action_id, connection_name, input_data)
            stmt = select(IdempotencyRecord).where(IdempotencyRecord.key_hash == key_hash)
            existing_record = (await session.execute(stmt)).scalar_one_or_none()
            if existing_record:
                if existing_record.status == "in_progress":
                    return {
                        "success": False,
                        "error": {"code": "idempotency_conflict", "message": "An identical request is currently in progress."},
                        "status_code": 409
                    }
                if existing_record.status == "completed" and existing_record.response_payload:
                    replayed_data = json.loads(decrypt_secret(existing_record.response_payload))
                    return {
                        "success": True,
                        "data": replayed_data,
                        "meta": {"actionId": action_id, "replayed": True}
                    }

            # Register in-progress record
            in_progress = IdempotencyRecord(
                key_hash=key_hash,
                action_id=action_id,
                status="in_progress",
                expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
            )
            session.add(in_progress)
            await session.commit()

        # 2. Resolve credentials
        credential = await ConnectionService.resolve_credentials(session, provider.service, connection_name)
        if credential is None and "no_auth" not in provider.auth_types:
            raise ValueError(f"No configured connection found for service '{provider.service}' (alias: '{connection_name}'). Please connect account first.")

        # 3. Execute
        execution_id = str(uuid.uuid4())
        started_at = utcnow_str()
        start_time = time.perf_counter()
        
        client = await create_guarded_client()
        ok = True
        status_code = 200
        error_msg = None
        result_data = {}

        try:
            result_data = await action.execute(input_data or {}, credential, client)
        except Exception as e:
            ok = False
            status_code = 500
            error_msg = str(e)
        finally:
            await client.aclose()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            completed_at = utcnow_str()

        # 4. Save RunLog
        run_log = RunLog(
            id=execution_id,
            action_id=action_id,
            service=provider.service,
            caller=caller,
            ok=ok,
            status_code=status_code,
            duration_ms=duration_ms,
            input_summary=json.dumps(input_data)[:2000] if input_data else None,
            output_summary=json.dumps(result_data)[:2000] if ok else None,
            error_message=error_msg,
            started_at=started_at,
            completed_at=completed_at
        )
        session.add(run_log)

        # 5. Update Idempotency
        if key_hash:
            stmt = select(IdempotencyRecord).where(IdempotencyRecord.key_hash == key_hash)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                if ok:
                    record.status = "completed"
                    record.response_status = 200
                    record.response_payload = encrypt_secret(json.dumps(result_data))
                else:
                    record.status = "failed"
                    record.response_status = 500

        await session.commit()

        if not ok:
            return {
                "success": False,
                "error": {"code": "execution_failed", "message": error_msg},
                "meta": {
                    "executionId": execution_id,
                    "actionId": action_id,
                    "durationMs": duration_ms
                },
                "status_code": status_code
            }

        return {
            "success": True,
            "data": result_data,
            "meta": {
                "executionId": execution_id,
                "actionId": action_id,
                "durationMs": duration_ms,
                "replayed": False
            }
        }

import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jsonschema

from app.providers.registry import registry
from app.db.models import RunLog, IdempotencyRecord, utcnow_str
from app.services.connection_service import ConnectionService
from app.core.ssrf import create_guarded_client, SSRFViolationError
from app.core.idempotency import compute_idempotency_scope_key, compute_payload_hash
from app.core.security import encrypt_secret, decrypt_secret, redact_sensitive_data, safe_error_message

class ActionRunner:
    @staticmethod
    async def run(
        session: AsyncSession,
        action_id: str,
        input_data: Dict[str, Any],
        connection_name: str = "default",
        caller: str = "http",
        idempotency_key: Optional[str] = None,
        principal_id: Optional[str] = None
    ) -> Dict[str, Any]:
        action = registry.get_action(action_id)
        if not action:
            raise ValueError(f"Unknown action: '{action_id}'")
        
        provider = registry.get_action_provider(action_id)
        if not provider:
            raise ValueError(f"Provider not found for action '{action_id}'")

        # Clean input: ignore routing param if present
        clean_input = dict(input_data or {})
        clean_input.pop("connectionName", None)

        # 1. JSON Schema Validation before side effects
        if action.input_schema and isinstance(action.input_schema, dict):
            # If schema requires properties, validate
            try:
                # We validate against a copy without connectionName if schema has it
                validator = jsonschema.Draft7Validator(action.input_schema)
                errors = list(validator.iter_errors(clean_input))
                if errors:
                    first_err = errors[0]
                    field_path = ".".join(str(p) for p in first_err.path) if first_err.path else "root"
                    return {
                        "success": False,
                        "error": {
                            "code": "invalid_input",
                            "message": f"Input validation failed on '{field_path}': {first_err.message}"
                        },
                        "status_code": 400
                    }
            except Exception as schema_err:
                # If schema validation engine fails unexpectedly, log safely
                pass

        # 2. Strict Scoped Idempotency Check
        scope_key = None
        payload_hash = None
        if idempotency_key and idempotency_key.strip():
            scope_key = compute_idempotency_scope_key(
                idempotency_key=idempotency_key,
                principal_id=principal_id,
                action_id=action_id,
                connection_name=connection_name
            )
            payload_hash = compute_payload_hash(clean_input)

            stmt = select(IdempotencyRecord).where(IdempotencyRecord.key_hash == scope_key)
            existing_record = (await session.execute(stmt)).scalar_one_or_none()
            if existing_record:
                # Payload mismatch with identical key returns 409 Conflict
                if existing_record.payload_hash and existing_record.payload_hash != payload_hash:
                    return {
                        "success": False,
                        "error": {
                            "code": "idempotency_conflict",
                            "message": "Idempotency key was previously used with a different request payload."
                        },
                        "status_code": 409
                    }

                # In progress claims return 409 Conflict
                if existing_record.status == "in_progress":
                    return {
                        "success": False,
                        "error": {
                            "code": "idempotency_in_progress",
                            "message": "A request with this idempotency key is currently in progress."
                        },
                        "status_code": 409
                    }

                # Completed claims replay encrypted stored response
                if existing_record.status == "completed" and existing_record.response_payload:
                    replayed_data = json.loads(decrypt_secret(existing_record.response_payload))
                    return {
                        "success": True,
                        "data": replayed_data,
                        "meta": {
                            "actionId": action_id,
                            "replayed": True,
                            "connectionName": connection_name
                        }
                    }

            # Register in-progress claim record
            in_progress = IdempotencyRecord(
                key_hash=scope_key,
                payload_hash=payload_hash,
                action_id=action_id,
                status="in_progress",
                expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
            )
            session.add(in_progress)
            await session.commit()

        # 3. Resolve credentials
        credential = await ConnectionService.resolve_credentials(session, provider.service, connection_name)
        if credential is None and "no_auth" not in provider.auth_types:
            raise ValueError(
                f"No configured connection found for service '{provider.service}' (alias: '{connection_name}'). Please connect your credentials first."
            )

        # 4. Execute
        execution_id = str(uuid.uuid4())
        started_at = utcnow_str()
        start_time = time.perf_counter()
        
        client = await create_guarded_client()
        ok = True
        status_code = 200
        error_msg = None
        result_data = {}

        try:
            result_data = await action.execute(clean_input, credential, client)
        except SSRFViolationError as e:
            ok = False
            status_code = 400
            error_msg = f"SSRF Security Violation: {str(e)}"
        except Exception as e:
            ok = False
            status_code = 500
            error_msg = safe_error_message(e)
        finally:
            await client.aclose()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            completed_at = utcnow_str()

        # 5. Save RunLog with systematic secret and header redaction
        redacted_input = redact_sensitive_data(clean_input) if clean_input else None
        redacted_output = redact_sensitive_data(result_data) if (ok and result_data) else None

        run_log = RunLog(
            id=execution_id,
            action_id=action_id,
            service=provider.service,
            caller=caller,
            ok=ok,
            status_code=status_code,
            duration_ms=duration_ms,
            input_summary=json.dumps(redacted_input)[:2000] if redacted_input else None,
            output_summary=json.dumps(redacted_output)[:2000] if redacted_output else None,
            error_message=error_msg,
            started_at=started_at,
            completed_at=completed_at
        )
        session.add(run_log)

        # 6. Update Idempotency
        if scope_key:
            stmt = select(IdempotencyRecord).where(IdempotencyRecord.key_hash == scope_key)
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record:
                if ok:
                    record.status = "completed"
                    record.response_status = 200
                    record.response_payload = encrypt_secret(json.dumps(result_data))
                else:
                    record.status = "failed"
                    record.response_status = status_code

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

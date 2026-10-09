import hashlib
import json
from typing import Any, Dict, Optional

def normalize_payload(payload: Any) -> Any:
    """Recursively normalizes dictionaries and lists for canonical hash computation."""
    if isinstance(payload, dict):
        return {k: normalize_payload(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        return [normalize_payload(item) for item in payload]
    return payload

def compute_payload_hash(input_data: Dict[str, Any]) -> str:
    """Computes a canonical SHA-256 hash of the normalized request input."""
    normalized = normalize_payload(input_data or {})
    raw = json.dumps(normalized, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def compute_idempotency_scope_key(
    idempotency_key: str,
    principal_id: Optional[str],
    action_id: str,
    connection_name: Optional[str]
) -> str:
    """
    Computes the unique scope key binding the idempotency key, principal,
    target action, and connection name together.
    """
    raw = f"{idempotency_key.strip()}:{principal_id or 'anon'}:{action_id}:{connection_name or 'default'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def compute_request_hash(action_id: str, connection_id: Optional[str], input_data: Dict[str, Any]) -> str:
    """Legacy helper maintained for backward compatibility."""
    normalized = normalize_payload(input_data or {})
    raw = f"{action_id}:{connection_id or 'default'}:{json.dumps(normalized, separators=(',', ':'))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

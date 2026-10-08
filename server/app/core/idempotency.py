import hashlib
import json
from typing import Any, Dict, Optional

def normalize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {k: normalize_payload(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        return [normalize_payload(item) for item in payload]
    return payload

def compute_request_hash(action_id: str, connection_id: Optional[str], input_data: Dict[str, Any]) -> str:
    normalized = normalize_payload(input_data or {})
    raw = f"{action_id}:{connection_id or 'default'}:{json.dumps(normalized, separators=(',', ':'))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

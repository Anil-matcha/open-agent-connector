import fnmatch
import json
from typing import List, Optional

def match_pattern(pattern: str, value: str) -> bool:
    if pattern == "*":
        return True
    return fnmatch.fnmatchcase(value, pattern)

def evaluate_action_policy(action_id: str, allowed_rules_json: str, blocked_rules_json: str) -> bool:
    """Evaluates whether an action is permitted based on allow and block rules."""
    try:
        allowed = json.loads(allowed_rules_json or "[]")
        blocked = json.loads(blocked_rules_json or "[]")
    except Exception:
        allowed, blocked = [], []

    # Any matching block rule immediately rejects
    for b in blocked:
        if match_pattern(b, action_id):
            return False

    # If allowed is empty, it means unrestricted by default
    if not allowed or allowed == ["*"]:
        return True

    # Must match at least one allowed rule
    for a in allowed:
        if match_pattern(a, action_id):
            return True

    return False

def evaluate_proxy_policy(service: str, allowed_proxies_json: str) -> bool:
    try:
        allowed = json.loads(allowed_proxies_json or "[]")
    except Exception:
        allowed = []
        
    if not allowed:
        return False # Proxies are deny-by-default for persistent tokens
    for a in allowed:
        if match_pattern(a, service):
            return True
    return False

def evaluate_connection_policy(connection_id: Optional[str], allowed_connections_json: str) -> bool:
    if not connection_id:
        return True
    try:
        allowed = json.loads(allowed_connections_json or "[]")
    except Exception:
        allowed = []
    if not allowed:
        return True # Empty means unrestricted
    return connection_id in allowed

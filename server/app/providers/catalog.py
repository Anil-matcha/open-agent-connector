"""
Unified Actions Catalog Manager for ConnectorHub.
Maintains all provider actions in a single centralized actions_catalog.json file,
partitioned by provider service ID.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

CATALOG_PATH = Path(__file__).parent / "actions_catalog.json"

_cached_catalog: Optional[Dict[str, List[Dict[str, Any]]]] = None

def _normalize_action(act: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure both snake_case and camelCase keys exist for all schema fields."""
    in_schema = act.get("inputSchema") or act.get("input_schema") or {"type": "object", "properties": {}}
    out_schema = act.get("outputSchema") or act.get("output_schema") or {"type": "object"}
    req_scopes = act.get("requiredScopes") or act.get("required_scopes") or []

    act["input_schema"] = in_schema
    act["inputSchema"] = in_schema
    act["output_schema"] = out_schema
    act["outputSchema"] = out_schema
    act["required_scopes"] = req_scopes
    act["requiredScopes"] = req_scopes
    return act

def get_actions_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Load, normalize, and cache the complete actions catalog."""
    global _cached_catalog
    if _cached_catalog is None:
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            _cached_catalog = {
                svc: [_normalize_action(a) for a in acts]
                for svc, acts in raw.items()
            }
        else:
            _cached_catalog = {}
    return _cached_catalog

def get_provider_actions(service: str) -> List[Dict[str, Any]]:
    """Retrieve all normalized actions for a specific provider service ID."""
    catalog = get_actions_catalog()
    return catalog.get(service.lower().strip(), [])

def list_catalog_services() -> List[str]:
    """List all provider services defined in the actions catalog."""
    catalog = get_actions_catalog()
    return list(catalog.keys())

def reload_actions_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Force reload and re-normalize the actions catalog from disk."""
    global _cached_catalog
    _cached_catalog = None
    return get_actions_catalog()

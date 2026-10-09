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

def get_actions_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Load and cache the complete actions catalog."""
    global _cached_catalog
    if _cached_catalog is None:
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                _cached_catalog = json.load(f)
        else:
            _cached_catalog = {}
    return _cached_catalog

def get_provider_actions(service: str) -> List[Dict[str, Any]]:
    """Retrieve all actions for a specific provider service ID."""
    catalog = get_actions_catalog()
    return catalog.get(service.lower().strip(), [])

def list_catalog_services() -> List[str]:
    """List all provider services defined in the actions catalog."""
    catalog = get_actions_catalog()
    return list(catalog.keys())

def reload_actions_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Force reload the actions catalog from disk."""
    global _cached_catalog
    _cached_catalog = None
    return get_actions_catalog()

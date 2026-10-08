from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.providers.registry import registry

router = APIRouter(prefix="/providers", tags=["Providers"])

@router.get("")
async def list_providers(category: Optional[str] = None):
    providers = registry.list_providers()
    if category and category.lower() != "all":
        providers = [p for p in providers if p.category.lower() == category.lower()]
    return {
        "success": True,
        "data": [p.to_dict() for p in providers]
    }

@router.get("/{service}")
async def get_provider(service: str):
    p = registry.get_provider(service)
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{service}' not found")
    data = p.to_dict()
    data["actions"] = [a.to_dict() for a in p.actions.values()]
    return {
        "success": True,
        "data": data
    }

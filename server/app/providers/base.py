from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx

class Action(ABC):
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        required_scopes: Optional[List[str]] = None,
        category: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {"type": "object"}
        self.required_scopes = required_scopes or []
        self.category = category or "General"

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        credential: Optional[Dict[str, Any]],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Execute the action against upstream API."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "requiredScopes": self.required_scopes,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema
        }

class Provider(ABC):
    def __init__(
        self,
        service: str,
        display_name: str,
        category: str,
        auth_types: List[str],
        description: str = "",
        homepage_url: str = "",
        icon_url: str = "",
        base_url: str = "",
        auth_configs: Optional[List[Dict[str, Any]]] = None
    ):
        self.service = service
        self.display_name = display_name
        self.category = category
        self.auth_types = auth_types
        self.description = description
        self.homepage_url = homepage_url
        self.icon_url = icon_url
        self.base_url = base_url
        self.auth_configs = auth_configs or []
        self.actions: Dict[str, Action] = {}

    def register_action(self, action: Action):
        self.actions[action.id] = action

    async def validate_credentials(
        self,
        credential: Dict[str, Any],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Validate credentials against provider API and return profile {account_id, display_name, granted_scopes, avatar_url}"""
        return {
            "account_id": "verified",
            "display_name": f"{self.display_name} Account",
            "granted_scopes": [],
            "avatar_url": None
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Default proxy forwarder."""
        raise NotImplementedError(f"Proxy not implemented for {self.service}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "displayName": self.display_name,
            "category": self.category,
            "authTypes": self.auth_types,
            "authConfigs": self.auth_configs,
            "description": self.description,
            "homepageUrl": self.homepage_url,
            "actionCount": len(self.actions)
        }

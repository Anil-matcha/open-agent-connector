"""
Notion Provider for ConnectorHub.
Loads and registers 28 actions from 'actions_catalog.json'.
Full support for pages, databases, blocks, comments, and data sources via Notion API v1.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def _notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Notion Integration Secret or OAuth Access Token required. Please connect your Notion account first.")
    return str(token).strip()

class NotionDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/users/me")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _notion_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["pageId", "databaseId", "blockId", "userId", "dataSourceId", "propertyId", "page_id", "database_id", "block_id", "user_id", "data_source_id", "property_id", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{NOTION_API_BASE}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = None
        params = None

        if req_method in ["POST", "PATCH", "PUT"]:
            json_body = inputs
        elif req_method == "GET":
            params = {k: v for k, v in inputs.items() if v is not None}

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            msg = data.get("message") if isinstance(data, dict) else str(data)
            raise ValueError(f"Notion API error ({resp.status_code}): {msg}")

        return {"status": resp.status_code, "data": data}

class NotionProvider(Provider):
    def __init__(self):
        super().__init__(
            service="notion",
            display_name="Notion",
            category="Project Management",
            auth_types=["oauth2", "api_key"],
            description="All-in-one workspace for notes, docs, databases, and project management.",
            homepage_url="https://notion.so",
            base_url=NOTION_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Notion OAuth 2.0",
                    "placeholder": "secret_... or ntn_...",
                    "description": "Connect securely via Notion OAuth 2.0 authorization code grant.",
                    "docs_url": "https://developers.notion.com/docs/authorization",
                    "docs_label": "Notion OAuth Guide",
                    "setup_guide": {
                        "title": "Notion OAuth Integration Guide",
                        "docs_url": "https://www.notion.so/profile/integrations",
                        "docs_label": "Notion Integrations Portal",
                        "instructions": [
                            "1. Go to Notion Integrations Portal (notion.so/profile/integrations).",
                            "2. Create a new Public Integration and configure OAuth redirect URIs.",
                            "3. Add your Integration Client ID and Secret to ConnectorHub.",
                            "4. Authorize access to select workspaces and pages."
                        ],
                        "scopes": ["read_content", "update_content", "insert_content"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "secret_... or ntn_...",
                            "description": "Notion OAuth access token."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Internal Integration Secret",
                    "placeholder": "secret_... or ntn_...",
                    "description": "Direct internal integration secret created in your Notion workspace.",
                    "docs_url": "https://developers.notion.com/docs/create-a-notion-integration",
                    "docs_label": "Notion Integration Docs",
                    "setup_guide": {
                        "title": "Notion Integration Secret Setup",
                        "docs_url": "https://www.notion.so/profile/integrations",
                        "docs_label": "Notion Integrations Portal",
                        "instructions": [
                            "1. Navigate to Notion My Integrations (notion.so/profile/integrations).",
                            "2. Click '+ New integration', select your associated workspace, and submit.",
                            "3. Copy the 'Internal Integration Secret' and paste below.",
                            "4. Important: Open your Notion pages or databases, click '...' > 'Connect to' and choose your integration."
                        ],
                        "scopes": ["read_content", "update_content", "insert_content"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Internal Integration Secret",
                            "type": "password",
                            "required": True,
                            "placeholder": "secret_...",
                            "description": "Notion internal integration secret token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("notion"):
            self.register_action(NotionDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Notion credentials against GET https://api.notion.com/v1/users/me."""
        token = _extract_token(credential)
        headers = _notion_headers(token)
        url = f"{NOTION_API_BASE}/users/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Notion API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Notion Integration Secret. Notion returned 401 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Notion credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = data.get("id") or "notion-user"
        name = data.get("name") or "Notion Workspace"
        bot_meta = data.get("bot", {})
        owner = bot_meta.get("owner", {})
        workspace_name = bot_meta.get("workspace_name")

        display_name = f"Notion ({workspace_name or name})"
        avatar_url = data.get("avatar_url")

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["read_content", "update_content", "insert_content"],
            "avatar_url": avatar_url
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
        """SSRF-guarded proxy forwarder for Notion API v1."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{NOTION_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_notion_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }

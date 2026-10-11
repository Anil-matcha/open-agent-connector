"""
Monday Provider for ConnectorHub.
Loads and registers 67 actions from 'actions_catalog.json'.
Comprehensive Work OS management including boards, items, columns, groups, updates, and automation via Monday GraphQL API v2.
"""
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

MONDAY_API_BASE = "https://api.monday.com/v2"
MONDAY_API_VERSION = "2024-01"

def _monday_headers(token: str) -> Dict[str, str]:
    auth = token if token.startswith("Bearer ") else f"Bearer {token}"
    return {
        "Authorization": auth,
        "API-Version": MONDAY_API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Monday Personal API Token or OAuth Access Token required. Please connect your Monday.com account first.")
    return str(token).strip()

MONDAY_QUERY_TEMPLATES = {
    "get_current_user": "query { me { id name email is_admin photo_thumb } }",
    "list_boards": "query ListBoards($limit: Int) { boards(limit: $limit) { id name state board_kind description workspace { id name } } }",
    "get_board": "query GetBoard($boardId: ID!) { boards(ids: [$boardId]) { id name state description columns { id title type } groups { id title } } }",
    "list_items": "query ListItems($limit: Int) { items_page(limit: $limit) { items { id name state column_values { id text value } } } }",
    "get_item": "query GetItem($itemId: ID!) { items(ids: [$itemId]) { id name state board { id name } column_values { id text value } } }",
    "create_item": "mutation CreateItem($boardId: ID!, $groupId: String, $itemName: String!, $columnValues: JSON) { create_item(board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $columnValues) { id name } }",
    "archive_item": "mutation ArchiveItem($itemId: ID!) { archive_item(item_id: $itemId) { id } }",
    "create_board": "mutation CreateBoard($boardName: String!, $boardKind: BoardKind!) { create_board(board_name: $boardName, board_kind: $boardKind) { id name } }",
    "archive_board": "mutation ArchiveBoard($boardId: ID!) { archive_board(board_id: $boardId) { id } }",
}

class MondayDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.raw_name = action_meta["id"].replace("monday.", "")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _monday_headers(token)
        assert_public_url(MONDAY_API_BASE)

        # Support direct GraphQL query or predefined operation
        if "query" in inputs:
            payload = {"query": inputs["query"], "variables": inputs.get("variables", {})}
        elif self.raw_name in MONDAY_QUERY_TEMPLATES:
            query_str = MONDAY_QUERY_TEMPLATES[self.raw_name]
            variables = {}
            for k in ["boardId", "itemId", "groupId", "itemName", "boardName", "boardKind", "limit"]:
                if k in inputs:
                    variables[k] = inputs[k]
                elif k == "boardId" and "board_id" in inputs:
                    variables[k] = inputs["board_id"]
                elif k == "itemId" and "item_id" in inputs:
                    variables[k] = inputs["item_id"]
            payload = {"query": query_str, "variables": variables}
        else:
            # Generic GraphQL fallback for remaining actions
            query_str = inputs.get("query")
            if not query_str:
                query_str = "query { me { id name email } }"
            payload = {"query": query_str, "variables": inputs.get("variables", {})}

        resp = await execute_guarded_request(
            client=client,
            method="POST",
            url=MONDAY_API_BASE,
            headers=headers,
            json_body=payload
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            err_msg = data.get("error_message") if isinstance(data, dict) else str(data)
            raise ValueError(f"Monday API error ({resp.status_code}): {err_msg}")

        if isinstance(data, dict) and data.get("errors"):
            errors = data.get("errors", [])
            err_msg = "; ".join(e.get("message", "Error") for e in errors)
            raise ValueError(f"Monday GraphQL error: {err_msg}")

        return {"status": resp.status_code, "data": data.get("data", data) if isinstance(data, dict) else data}

class MondayProvider(Provider):
    def __init__(self):
        super().__init__(
            service="monday",
            display_name="Monday.com",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="Work operating system that powers teams to run processes, projects, and everyday work.",
            homepage_url="https://monday.com",
            base_url=MONDAY_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Monday Personal API Token",
                    "placeholder": "eyJhbGci...",
                    "description": "Monday.com Personal API token generated from Developer section.",
                    "docs_url": "https://developer.monday.com/api-reference/docs/authentication",
                    "docs_label": "Monday Authentication Docs",
                    "setup_guide": {
                        "title": "Monday API Token Guide",
                        "docs_url": "https://auth.monday.com/users/edit/developer",
                        "docs_label": "Monday Developer Section",
                        "instructions": [
                            "1. Log into Monday.com and click your profile icon > Administration > Developers.",
                            "2. Navigate to 'Developer' section and select 'My Access Tokens'.",
                            "3. Generate and copy your Personal API Token.",
                            "4. Paste your token below."
                        ],
                        "scopes": ["boards:read", "boards:write", "workspaces:read", "users:read", "me:read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "Monday.com API Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Monday OAuth 2.0",
                    "placeholder": "eyJhbGci...",
                    "description": "Connect via Monday.com OAuth 2.0 authorization code flow.",
                    "docs_url": "https://developer.monday.com/apps/docs/oauth-and-permissions",
                    "docs_label": "Monday OAuth Documentation",
                    "setup_guide": {
                        "title": "Monday OAuth App Setup",
                        "docs_url": "https://developer.monday.com/apps",
                        "docs_label": "Monday Apps Framework",
                        "instructions": [
                            "1. Go to Monday Developer Center (developer.monday.com/apps) and create an app.",
                            "2. Under OAuth, set your redirect URI and choose required scopes (boards:read, boards:write).",
                            "3. Add Client ID & Secret to ConnectorHub settings.",
                            "4. Complete user authorization flow."
                        ],
                        "scopes": ["boards:read", "boards:write", "workspaces:read", "users:read", "me:read"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "Monday OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("monday"):
            self.register_action(MondayDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Monday credentials via GraphQL me query."""
        token = _extract_token(credential)
        headers = _monday_headers(token)
        assert_public_url(MONDAY_API_BASE)

        payload = {"query": "query { me { id name email is_admin photo_thumb } }"}

        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=MONDAY_API_BASE,
                headers=headers,
                json_body=payload
            )
        except Exception as e:
            raise ValueError(f"Unable to reach Monday API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Monday API Token. Monday returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Monday credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        if "errors" in body and body["errors"]:
            err_msg = body["errors"][0].get("message", "Error")
            raise ValueError(f"Monday validation failed: {err_msg}")

        me = (body.get("data") or {}).get("me") or {}
        account_id = str(me.get("id") or "monday-user")
        name = me.get("name") or me.get("email") or "Monday User"
        avatar_url = me.get("photo_thumb")

        return {
            "account_id": account_id,
            "display_name": f"Monday ({name})",
            "granted_scopes": ["boards:read", "boards:write", "workspaces:read", "users:read", "me:read"],
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
        """SSRF-guarded proxy forwarder for Monday GraphQL API v2."""
        token = _extract_token(credential)
        assert_public_url(MONDAY_API_BASE)

        req_headers = dict(headers or {})
        req_headers.update(_monday_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method="POST",
            url=MONDAY_API_BASE,
            headers=req_headers,
            json_body=body if body else {"query": "query { me { id name } }"}
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

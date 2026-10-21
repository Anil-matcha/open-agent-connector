"""
Shortcut Provider for ConnectorHub.
Loads and registers 15 actions for stories, epics, workflows, projects, and members.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.app.shortcut.com/api/v3"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "personalAccessToken", "api_key", "access_token"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    token = _extract_token(credential)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    if token:
        headers["Shortcut-Token"] = token
    return headers

ROUTES: Dict[str, List[Any]] = {
    "list_members": ["GET", "/members", [], ["orgId"]],
    "get_member": ["GET", "/members/{memberId}", ["memberId"], ["orgId"]],
    "list_projects": ["GET", "/projects", [], []],
    "get_project": ["GET", "/projects/{projectId}", ["projectId"], []],
    "list_epics": ["GET", "/epics", [], ["includesDescription"]],
    "get_epic": ["GET", "/epics/{epicId}", ["epicId"], []],
    "create_epic": ["POST", "/epics", [], []],
    "update_epic": ["PUT", "/epics/{epicId}", ["epicId"], []],
    "list_stories": ["GET", "/projects/{projectId}/stories", ["projectId"], ["includesDescription"]],
    "get_story": ["GET", "/stories/{storyId}", ["storyId"], []],
    "create_story": ["POST", "/stories", [], []],
    "update_story": ["PUT", "/stories/{storyId}", ["storyId"], []],
    "search_stories": ["GET", "/search/stories", [], ["query", "next", "detail", "pageSize"]],
    "list_workflows": ["GET", "/workflows", [], []],
    "get_workflow": ["GET", "/workflows/{workflowId}", ["workflowId"], []],
}

class ShortcutDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Productivity"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        headers = _build_headers(cred)
        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        target_url = f"{DEFAULT_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or req_method == "GET":
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("error") or err_msg
            except Exception:
                pass
            raise ValueError(f"Shortcut API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class ShortcutProvider(Provider):
    def __init__(self):
        super().__init__(
            service="shortcut",
            display_name="Shortcut",
            category="Productivity",
            auth_types=["api_key"],
            description="Agile project management, stories, epics, workflows, and iterations with 15 actions.",
            homepage_url="https://shortcut.com",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Shortcut API Token",
                    "placeholder": "61b1...-....",
                    "description": "Your Shortcut API token from User Settings > API Tokens.",
                    "docs_url": "https://developer.shortcut.com/api/rest/v3",
                    "docs_label": "Shortcut API Documentation",
                    "setup_guide": {
                        "title": "Shortcut API Token Setup Guide",
                        "docs_url": "https://app.shortcut.com/settings/account/api-tokens",
                        "docs_label": "Shortcut API Tokens",
                        "instructions": [
                            "1. Sign in to Shortcut (formerly Clubhouse).",
                            "2. Navigate to User Profile Settings > API Tokens.",
                            "3. Generate a new API Token and give it a label.",
                            "4. Copy the token and paste it below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "Paste Shortcut API token..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("shortcut"):
            self.register_action(ShortcutDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Shortcut API token is required.")

        val_url = f"{DEFAULT_API_BASE}/member"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Shortcut connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Shortcut credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Shortcut validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        profile = data.get("profile") or {}
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": profile.get("name") or profile.get("mention_name") or profile.get("email") or "Shortcut Member"
        }

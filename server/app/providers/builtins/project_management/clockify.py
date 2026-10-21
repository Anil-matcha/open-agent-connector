"""
Clockify Provider for ConnectorHub.
Loads and registers 12 actions for time tracking, workspaces, projects, tasks, and time entries.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.clockify.me/api/v1"

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
        headers["x-api-key"] = token
    return headers

ROUTES: Dict[str, List[Any]] = {
    "get_current_user": ["GET", "/user", [], []],
    "list_workspaces": ["GET", "/workspaces", [], ["roles"]],
    "get_workspace": ["GET", "/workspaces/{workspaceId}", ["workspaceId"], []],
    "list_projects": ["GET", "/workspaces/{workspaceId}/projects", ["workspaceId"], ["name", "page", "page-size", "archived", "billable"]],
    "get_project": ["GET", "/workspaces/{workspaceId}/projects/{projectId}", ["workspaceId", "projectId"], ["hydrated"]],
    "create_project": ["POST", "/workspaces/{workspaceId}/projects", ["workspaceId"], []],
    "update_project": ["PUT", "/workspaces/{workspaceId}/projects/{projectId}", ["workspaceId", "projectId"], []],
    "delete_project": ["DELETE", "/workspaces/{workspaceId}/projects/{projectId}", ["workspaceId", "projectId"], []],
    "list_tasks": ["GET", "/workspaces/{workspaceId}/projects/{projectId}/tasks", ["workspaceId", "projectId"], ["name", "page", "page-size", "is-active"]],
    "create_task": ["POST", "/workspaces/{workspaceId}/projects/{projectId}/tasks", ["workspaceId", "projectId"], []],
    "list_time_entries": ["GET", "/workspaces/{workspaceId}/user/{userId}/time-entries", ["workspaceId", "userId"], ["start", "end", "page", "page-size", "description", "in-progress"]],
    "create_time_entry": ["POST", "/workspaces/{workspaceId}/time-entries", ["workspaceId"], []],
}

class ClockifyDynamicAction(Action):
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
            raise ValueError(f"Clockify API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class ClockifyProvider(Provider):
    def __init__(self):
        super().__init__(
            service="clockify",
            display_name="Clockify",
            category="Productivity",
            auth_types=["api_key"],
            description="Time tracking, workspaces, projects, tasks, and time entries with 12 actions.",
            homepage_url="https://clockify.me",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Clockify API Key",
                    "placeholder": "XyZ123...",
                    "description": "Your personal Clockify API key from User Preferences.",
                    "docs_url": "https://clockify.me/developers-api",
                    "docs_label": "Clockify API Documentation",
                    "setup_guide": {
                        "title": "Clockify API Key Setup Guide",
                        "docs_url": "https://app.clockify.me/user/preferences#advanced",
                        "docs_label": "Clockify Preferences",
                        "instructions": [
                            "1. Log in to Clockify and open Profile Settings > Preferences.",
                            "2. Scroll down to the Advanced section at the bottom.",
                            "3. Click 'Generate' to create a personal API key.",
                            "4. Copy the API key and paste it below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "Paste Clockify API key..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("clockify"):
            self.register_action(ClockifyDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Clockify API key is required.")

        val_url = f"{DEFAULT_API_BASE}/user"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Clockify connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Clockify credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Clockify validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": data.get("name") or data.get("email") or "Clockify User"
        }

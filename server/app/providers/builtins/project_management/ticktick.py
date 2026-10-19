"""
TickTick Provider for ConnectorHub.
Loads and registers 21 actions for tasks, habits, and checklists.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.ticktick.com/open/v1"

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
        headers["Authorization"] = f"Bearer {token}"
    return headers

ROUTES: Dict[str, List[Any]] = {
    "batch_add_tasks": ["POST", "/batch/task", [], ["add"]],
    "complete_task": ["POST", "/project/{projectId}/task/{taskId}/complete", ["projectId", "taskId"], []],
    "create_or_update_habit_checkin": ["POST", "/habit/{habitId}/checkin", ["habitId"], ["status", "goal"]],
    "create_project": ["POST", "/project", [], ["name", "color", "viewMode"]],
    "create_task": ["POST", "/task", [], ["title", "content", "projectId", "dueDate", "priority"]],
    "create_task2": ["POST", "/task", [], ["title", "content", "projectId"]],
    "delete_project": ["DELETE", "/project/{projectId}", ["projectId"], []],
    "delete_task": ["DELETE", "/project/{projectId}/task/{taskId}", ["projectId", "taskId"], []],
    "filter_tasks": ["GET", "/task/filter", [], ["projectId", "status"]],
    "get_habit": ["GET", "/habit/{habitId}", ["habitId"], []],
    "get_project_by_id": ["GET", "/project/{projectId}", ["projectId"], []],
    "get_project_with_data": ["GET", "/project/{projectId}/data", ["projectId"], []],
    "get_task_by_project_and_id": ["GET", "/project/{projectId}/task/{taskId}", ["projectId", "taskId"], []],
    "get_user_project": ["GET", "/project", [], []],
    "list_all_tasks": ["GET", "/task", [], []],
    "list_completed_tasks": ["GET", "/task/completed", [], []],
    "list_habit_checkins": ["GET", "/habit/{habitId}/checkin", ["habitId"], []],
    "list_habits": ["GET", "/habit", [], []],
    "move_tasks": ["POST", "/task/move", [], []],
    "update_project": ["POST", "/project/{projectId}", ["projectId"], ["name", "color"]],
    "update_task": ["POST", "/task/{taskId}", ["taskId"], ["title", "content", "dueDate", "priority"]],
}

class TickTickDynamicAction(Action):
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
                err_msg = err_json.get("errorMessage") or err_json.get("error") or err_msg
            except Exception:
                pass
            raise ValueError(f"TickTick API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class TickTickProvider(Provider):
    def __init__(self):
        super().__init__(
            service="ticktick",
            display_name="TickTick",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="TickTick task lists, habits, check-ins, projects, and reminders with 21 actions.",
            homepage_url="https://ticktick.com",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "TickTick OAuth Access Token",
                    "placeholder": "tt_...",
                    "description": "Authenticate via official TickTick OAuth 2.0 flow.",
                    "docs_url": "https://developer.ticktick.com/docs#/openapi",
                    "docs_label": "TickTick OpenAPI Guide",
                    "setup_guide": {
                        "title": "TickTick OAuth Setup Guide",
                        "docs_url": "https://developer.ticktick.com/manage",
                        "docs_label": "TickTick Developer Portal",
                        "instructions": [
                            "1. Go to TickTick Developer Center (developer.ticktick.com) and register an Application.",
                            "2. Set Redirect URI to: https://connector.suparagent.ai/api/oauth/ticktick/callback",
                            "3. Request scopes: tasks:read and tasks:write.",
                            "4. Connect seamlessly via Hosted OAuth."
                        ],
                        "scopes": ["tasks:read", "tasks:write"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "tt_..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("ticktick"):
            self.register_action(TickTickDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("TickTick access token is required.")

        val_url = f"{DEFAULT_API_BASE}/user/profile"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"TickTick connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid TickTick credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"TickTick validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("username") or data.get("id") or token[:8] + "..."),
            "display_name": data.get("username") or data.get("email") or "TickTick Account"
        }

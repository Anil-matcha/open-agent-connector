"""
Zoom Provider for ConnectorHub.
Loads and registers 4 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ZOOM_API_BASE = "https://api.zoom.us/v2"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["accessToken", "token", "access_token", "apiKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Zoom OAuth access token required. Please connect your Zoom account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "create_meeting": [
        "POST",
        "/users/{userId}/meetings",
        [
            "userId"
        ],
        []
    ],
    "get_user": [
        "GET",
        "/users/{userId}",
        [
            "userId"
        ],
        []
    ],
    "list_meetings": [
        "GET",
        "/users/{userId}/meetings",
        [
            "userId"
        ],
        [
            "type",
            "page_size",
            "page_number"
        ]
    ],
    "update_meeting": [
        "PATCH",
        "/meetings/{meetingId}",
        [
            "meetingId"
        ],
        []
    ]
}

class ZoomDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _headers(token)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        user_id = input_data.get("userId") or input_data.get("user_id") or "me"
        path = path.replace("{userId}", urllib.parse.quote(str(user_id), safe=""))
        path = path.replace("{user_id}", urllib.parse.quote(str(user_id), safe=""))

        for var in path_vars:
            if var in ["userId", "user_id"]:
                continue
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{ZOOM_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in ["userId", "user_id"] or k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or resp.text
            raise ValueError(f"Zoom API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ZoomProvider(Provider):
    def __init__(self):
        super().__init__(
            service="zoom",
            display_name="Zoom",
            category="Communication",
            auth_types=["oauth2"],
            description="Zoom meetings and user management integration suite with 4 actions."
        )
        for act in get_provider_actions("zoom"):
            self.register_action(ZoomDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{ZOOM_API_BASE}/users/me"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Zoom credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Zoom validation failed: {resp.status_code} {resp.text}")

        try:
            user = resp.json()
            u_id = str(user.get("id", "verified"))
            u_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email") or u_id
        except Exception:
            u_id = "verified"
            u_name = "Zoom User"

        return {
            "account_id": u_id,
            "display_name": f"Zoom ({u_name})"
        }

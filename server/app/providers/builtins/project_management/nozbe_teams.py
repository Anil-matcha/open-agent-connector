"""
Nozbe Teams Provider for ConnectorHub.
Loads and registers 16 actions with exact route definitions and parameters.
"""
import base64
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api4.nozbe.com/v1/api"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "nozbe_teams" == "sanity":
        project_id = str(cred.get("projectId") or "default").strip()
        return base.replace("{projectId}", project_id).rstrip("/")

    if "nozbe_teams" == "make":
        zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
        if not zone.endswith("/api/v2"):
            zone = f"{zone}/api/v2"
        return zone

    if "nozbe_teams" in ["home_assistant", "homebox", "kobotoolbox"]:
        val = str(cred.get("baseUrl") or base).strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        if "nozbe_teams" == "homebox" and not val.endswith("/api/v1"):
            val = f"{val.rstrip('/')}/api/v1"
        return val.rstrip("/")

    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base.rstrip("/")

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "nozbe"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "toggl":
        if token:
            pair = f"{token}:api_token"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "clickmeeting":
        if token:
            headers["X-Api-Key"] = token
    elif auth_mode == "nozbe":
        if token:
            headers["Authorization"] = f"apikey {token}"
    elif auth_mode == "kobotoolbox":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode == "dropbox_sign":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "systeme_io":
        if token:
            headers["X-API-Key"] = token
    elif auth_mode == "make":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode in ["storyblok", "ipdata", "mapbox"]:
        # Query param auth, no special auth header required
        pass

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_comment": [
        "POST",
        "/comments",
        [],
        [
            "body",
            "task_id",
            "is_pinned",
            "is_team",
            "extra"
        ]
    ],
    "create_project": [
        "POST",
        "/projects",
        [],
        [
            "name",
            "team_id",
            "is_open",
            "is_favorite",
            "is_single_actions",
            "is_template",
            "color",
            "description",
            "extra",
            "preferences",
            "sidebar_position"
        ]
    ],
    "create_task": [
        "POST",
        "/tasks",
        [],
        [
            "name",
            "project_id",
            "project_section_id",
            "responsible_id",
            "due_at",
            "is_followed",
            "is_all_day",
            "priority_position",
            "time_needed",
            "extra"
        ]
    ],
    "delete_comment": [
        "DELETE",
        "/comments/{id}",
        [
            "id"
        ],
        []
    ],
    "delete_project": [
        "DELETE",
        "/projects/{id}",
        [
            "id"
        ],
        []
    ],
    "delete_task": [
        "DELETE",
        "/tasks/{id}",
        [
            "id"
        ],
        []
    ],
    "get_comment": [
        "GET",
        "/comments/{id}",
        [
            "id"
        ],
        []
    ],
    "get_project": [
        "GET",
        "/projects/{id}",
        [
            "id"
        ],
        []
    ],
    "get_task": [
        "GET",
        "/tasks/{id}",
        [
            "id"
        ],
        []
    ],
    "list_comments": [
        "GET",
        "/comments",
        [],
        [
            "limit",
            "offset",
            "sortBy",
            "task_id"
        ]
    ],
    "list_projects": [
        "GET",
        "/projects",
        [],
        [
            "limit",
            "offset",
            "sortBy",
            "team_id",
            "is_single_actions"
        ]
    ],
    "list_tasks": [
        "GET",
        "/tasks",
        [],
        [
            "limit",
            "offset",
            "sortBy",
            "project_id"
        ]
    ],
    "list_teams": [
        "GET",
        "/teams",
        [],
        [
            "limit",
            "offset",
            "sortBy"
        ]
    ],
    "update_comment": [
        "PUT",
        "/comments/{id}",
        [
            "id"
        ],
        [
            "body",
            "is_pinned",
            "is_deleted",
            "extra"
        ]
    ],
    "update_project": [
        "PUT",
        "/projects/{id}",
        [
            "id"
        ],
        [
            "name",
            "team_id",
            "ended_at",
            "last_seen_event_at",
            "is_open",
            "is_favorite",
            "is_single_actions",
            "is_template",
            "color",
            "description",
            "extra",
            "preferences",
            "sidebar_position"
        ]
    ],
    "update_task": [
        "PUT",
        "/tasks/{id}",
        [
            "id"
        ],
        [
            "name",
            "project_id",
            "project_section_id",
            "responsible_id",
            "due_at",
            "ended_at",
            "is_followed",
            "is_abandoned",
            "is_all_day",
            "priority_position",
            "time_needed",
            "time_spent",
            "extra"
        ]
    ]
}

class NozbeTeamsDynamicAction(Action):
    def __init__(self, action_dict: Dict[str, Any]):
        super().__init__(
            id=action_dict["id"],
            name=action_dict["name"],
            description=action_dict.get("description", ""),
            input_schema=action_dict.get("inputSchema") or action_dict.get("input_schema") or {"type": "object", "properties": {}},
            output_schema=action_dict.get("outputSchema") or action_dict.get("output_schema") or {"type": "object", "properties": {}},
            required_scopes=action_dict.get("requiredScopes") or action_dict.get("required_scopes") or []
        )
        self.raw_dict = action_dict

    async def execute(self, credential: Dict[str, Any], params: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        action_name = self.name
        route_meta = ROUTES.get(action_name, ["GET", f"/{action_name}", [], []])
        method = route_meta[0]
        path_template = route_meta[1]
        path_param_names = route_meta[2]
        body_param_names = route_meta[3]

        base_url = _resolve_base_url(cred)
        path = path_template

        # Fill path parameters
        for p_name in path_param_names:
            val = params.get(p_name)
            if val is not None:
                path = path.replace("{" + p_name + "}", urllib.parse.quote(str(val), safe=""))
            else:
                path = path.replace("{" + p_name + "}", "")

        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        assert_public_url(full_url)

        headers = _build_headers(cred)
        req_params = {}
        req_json = None

        auth_mode = "nozbe"
        token = _extract_token(cred)
        if auth_mode == "storyblok" and token:
            req_params["token"] = token
        elif auth_mode == "ipdata" and token:
            req_params["api-key"] = token
        elif auth_mode == "mapbox" and token:
            req_params["access_token"] = token

        if method in ["GET", "DELETE"]:
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_params[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_params:
                    req_params[k] = v
        else:
            req_json = {}
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_json[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_json:
                    req_json[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=full_url,
            headers=headers,
            params=req_params if req_params else None,
            json=req_json if req_json else None
        )

        if resp.status_code >= 400:
            raise ValueError(f"Nozbe Teams API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class NozbeTeamsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="nozbe_teams",
            display_name="Nozbe Teams",
            category="Project Management",
            auth_types=['api_key'],
            description="Nozbe Teams collaborative task, project, and team management provider with 16 actions."
        )
        for act in get_provider_actions("nozbe_teams"):
            self.register_action(NozbeTeamsDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "nozbe_teams" not in ["sanity"]:
            raise ValueError("API token or key is required for Nozbe Teams.")

        if "nozbe_teams" == "sanity":
            project_id = str(cred.get("projectId") or "").strip()
            if not project_id:
                raise ValueError("Sanity projectId is required in credentials.")
            if not token:
                raise ValueError("API token is required for Sanity.")
            val_url = f"https://api.sanity.io/v2021-06-07/projects/{project_id}/datasets"
        elif "nozbe_teams" == "home_assistant":
            base_url = str(cred.get("baseUrl") or "http://homeassistant.local:8123").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/config"
        elif "nozbe_teams" == "homebox":
            base_url = str(cred.get("baseUrl") or "http://homebox.local:7745").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            if not base_url.endswith("/api/v1"):
                base_url = f"{base_url.rstrip('/')}/api/v1"
            val_url = f"{base_url.rstrip('/')}/status"
        elif "nozbe_teams" == "kobotoolbox":
            base_url = str(cred.get("baseUrl") or "https://kf.kobotoolbox.org").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/assets/?limit=1"
        elif "nozbe_teams" == "make":
            zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
            if not zone.endswith("/api/v2"):
                zone = f"{zone}/api/v2"
            val_url = f"{zone}/users/me"
        else:
            base_url = _resolve_base_url(cred)
            val_url = f"{base_url.rstrip('/')}/teams".replace("//", "/")

        req_params = {}
        auth_mode = "nozbe"
        if auth_mode == "storyblok" and token:
            req_params["token"] = token
        elif auth_mode == "ipdata" and token:
            req_params["api-key"] = token
        elif auth_mode == "mapbox" and token:
            req_params["access_token"] = token

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"Nozbe Teams connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Nozbe Teams credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Nozbe Teams validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": "verified",
            "display_name": f"Nozbe Teams Account"
        }

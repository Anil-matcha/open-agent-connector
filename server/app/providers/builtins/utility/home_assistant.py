"""
Home Assistant Provider for ConnectorHub.
Loads and registers 28 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "http://homeassistant.local:8123"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "home_assistant" == "sanity":
        project_id = str(cred.get("projectId") or "default").strip()
        return base.replace("{projectId}", project_id).rstrip("/")

    if "home_assistant" == "make":
        zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
        if not zone.endswith("/api/v2"):
            zone = f"{zone}/api/v2"
        return zone

    if "home_assistant" in ["home_assistant", "homebox", "kobotoolbox"]:
        val = str(cred.get("baseUrl") or base).strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        if "home_assistant" == "homebox" and not val.endswith("/api/v1"):
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

    auth_mode = "Bearer"
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
    "call_service": [
        "POST",
        "/api/services/{domain}/{service}",
        [
            "domain",
            "service"
        ],
        [
            "serviceData",
            "returnResponse"
        ]
    ],
    "check_config": [
        "POST",
        "/api/config/core/check_config",
        [],
        []
    ],
    "delete_automation_config": [
        "DELETE",
        "/api/config/automation/config/{automationId}",
        [
            "automationId"
        ],
        []
    ],
    "delete_scene_config": [
        "DELETE",
        "/api/config/scene/config/{sceneId}",
        [
            "sceneId"
        ],
        []
    ],
    "delete_script_config": [
        "DELETE",
        "/api/config/script/config/{scriptKey}",
        [
            "scriptKey"
        ],
        []
    ],
    "execute_script": [
        "POST",
        "/api/services/script/{scriptId}",
        [
            "scriptId"
        ],
        [
            "sequence",
            "variables"
        ]
    ],
    "fire_event": [
        "POST",
        "/api/events/{eventType}",
        [
            "eventType"
        ],
        [
            "eventData"
        ]
    ],
    "get_automation_config": [
        "GET",
        "/api/config/automation/config/{automationId}",
        [
            "automationId"
        ],
        []
    ],
    "get_config": [
        "GET",
        "/api/config",
        [],
        []
    ],
    "get_error_log": [
        "GET",
        "/api/error_log",
        [],
        []
    ],
    "get_history": [
        "GET",
        "/api/history/period",
        [],
        [
            "entityIds",
            "startTime",
            "endTime",
            "minimalResponse",
            "noAttributes",
            "skipInitialState",
            "significantChangesOnly"
        ]
    ],
    "get_logbook": [
        "GET",
        "/api/logbook",
        [],
        [
            "startTime",
            "endTime",
            "entityIds",
            "period",
            "contextId"
        ]
    ],
    "get_registries": [
        "POST",
        "/api/websocket/registries",
        [],
        [
            "include"
        ]
    ],
    "get_scene_config": [
        "GET",
        "/api/config/scene/config/{sceneId}",
        [
            "sceneId"
        ],
        []
    ],
    "get_script_config": [
        "GET",
        "/api/config/script/config/{scriptKey}",
        [
            "scriptKey"
        ],
        []
    ],
    "get_state": [
        "GET",
        "/api/states/{entityId}",
        [
            "entityId"
        ],
        []
    ],
    "list_calendar_events": [
        "GET",
        "/api/calendars/{entityId}",
        [
            "entityId"
        ],
        [
            "start",
            "end"
        ]
    ],
    "list_calendars": [
        "GET",
        "/api/calendars",
        [],
        []
    ],
    "list_device_automations": [
        "POST",
        "/api/websocket/device_automations",
        [],
        [
            "deviceId"
        ]
    ],
    "list_events": [
        "GET",
        "/api/events",
        [],
        []
    ],
    "list_services": [
        "GET",
        "/api/services",
        [],
        []
    ],
    "list_states": [
        "GET",
        "/api/states",
        [],
        []
    ],
    "render_template": [
        "POST",
        "/api/template",
        [],
        [
            "template",
            "variables"
        ]
    ],
    "save_automation_config": [
        "POST",
        "/api/config/automation/config/{automationId}",
        [
            "automationId"
        ],
        [
            "config"
        ]
    ],
    "save_scene_config": [
        "POST",
        "/api/config/scene/config/{sceneId}",
        [
            "sceneId"
        ],
        [
            "config"
        ]
    ],
    "save_script_config": [
        "POST",
        "/api/config/script/config/{scriptKey}",
        [
            "scriptKey"
        ],
        [
            "config"
        ]
    ],
    "search_related": [
        "POST",
        "/api/websocket/search/related",
        [],
        [
            "itemType",
            "itemId"
        ]
    ],
    "validate_config": [
        "POST",
        "/api/config/core/check_config",
        [],
        [
            "triggers",
            "conditions",
            "actions"
        ]
    ]
}

class HomeAssistantDynamicAction(Action):
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

        auth_mode = "Bearer"
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
            raise ValueError(f"Home Assistant API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class HomeAssistantProvider(Provider):
    def __init__(self):
        super().__init__(
            service="home_assistant",
            display_name="Home Assistant",
            category="Utilities & Tools",
            auth_types=['api_key'],
            description="Home Assistant smart home automation platform for entity states, services, events, templates, config, and calendars with 28 actions."
        )
        for act in get_provider_actions("home_assistant"):
            self.register_action(HomeAssistantDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "home_assistant" not in ["sanity"]:
            raise ValueError("API token or key is required for Home Assistant.")

        if "home_assistant" == "sanity":
            project_id = str(cred.get("projectId") or "").strip()
            if not project_id:
                raise ValueError("Sanity projectId is required in credentials.")
            if not token:
                raise ValueError("API token is required for Sanity.")
            val_url = f"https://api.sanity.io/v2021-06-07/projects/{project_id}/datasets"
        elif "home_assistant" == "home_assistant":
            base_url = str(cred.get("baseUrl") or "http://homeassistant.local:8123").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/config"
        elif "home_assistant" == "homebox":
            base_url = str(cred.get("baseUrl") or "http://homebox.local:7745").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            if not base_url.endswith("/api/v1"):
                base_url = f"{base_url.rstrip('/')}/api/v1"
            val_url = f"{base_url.rstrip('/')}/status"
        elif "home_assistant" == "kobotoolbox":
            base_url = str(cred.get("baseUrl") or "https://kf.kobotoolbox.org").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/assets/?limit=1"
        elif "home_assistant" == "make":
            zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
            if not zone.endswith("/api/v2"):
                zone = f"{zone}/api/v2"
            val_url = f"{zone}/users/me"
        else:
            base_url = _resolve_base_url(cred)
            val_url = f"{base_url.rstrip('/')}/api/config".replace("//", "/")

        req_params = {}
        auth_mode = "Bearer"
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
            raise ValueError(f"Home Assistant connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Home Assistant credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Home Assistant validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": "verified",
            "display_name": f"Home Assistant Account"
        }

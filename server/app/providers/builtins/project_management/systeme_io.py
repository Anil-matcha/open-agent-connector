"""
Systeme.io Provider for ConnectorHub.
Loads and registers 24 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.systeme.io"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "systeme_io" == "sanity":
        project_id = str(cred.get("projectId") or "default").strip()
        return base.replace("{projectId}", project_id).rstrip("/")

    if "systeme_io" == "make":
        zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
        if not zone.endswith("/api/v2"):
            zone = f"{zone}/api/v2"
        return zone

    if "systeme_io" in ["home_assistant", "homebox", "kobotoolbox"]:
        val = str(cred.get("baseUrl") or base).strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        if "systeme_io" == "homebox" and not val.endswith("/api/v1"):
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

    auth_mode = "systeme_io"
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
    "attach_contact_tag": [
        "POST",
        "/api/contacts/{contactId}/tags",
        [
            "contactId"
        ],
        []
    ],
    "cancel_subscription": [
        "POST",
        "/api/payment/subscriptions/{subscriptionId}/cancel",
        [
            "subscriptionId"
        ],
        []
    ],
    "create_contact": [
        "POST",
        "/api/contacts",
        [],
        []
    ],
    "create_enrollment": [
        "POST",
        "/api/school/courses/{courseId}/enrollments",
        [
            "courseId"
        ],
        []
    ],
    "create_tag": [
        "POST",
        "/api/tags",
        [],
        []
    ],
    "create_webhook": [
        "POST",
        "/api/webhooks",
        [],
        []
    ],
    "delete_contact": [
        "DELETE",
        "/api/contacts/{contactId}",
        [
            "contactId"
        ],
        []
    ],
    "delete_enrollment": [
        "DELETE",
        "/api/school/courses/{courseId}/enrollments/{enrollmentId}",
        [
            "courseId",
            "enrollmentId"
        ],
        []
    ],
    "delete_tag": [
        "DELETE",
        "/api/tags/{tagId}",
        [
            "tagId"
        ],
        []
    ],
    "delete_webhook": [
        "DELETE",
        "/api/webhooks/{webhookId}",
        [
            "webhookId"
        ],
        []
    ],
    "detach_contact_tag": [
        "DELETE",
        "/api/contacts/{contactId}/tags/{tagId}",
        [
            "contactId",
            "tagId"
        ],
        []
    ],
    "get_contact": [
        "GET",
        "/api/contacts/{contactId}",
        [
            "contactId"
        ],
        []
    ],
    "get_tag": [
        "GET",
        "/api/tags/{tagId}",
        [
            "tagId"
        ],
        []
    ],
    "get_webhook": [
        "GET",
        "/api/webhooks/{webhookId}",
        [
            "webhookId"
        ],
        []
    ],
    "list_contact_fields": [
        "GET",
        "/api/contact_fields",
        [],
        []
    ],
    "list_contacts": [
        "GET",
        "/api/contacts",
        [],
        []
    ],
    "list_courses": [
        "GET",
        "/api/school/courses",
        [],
        []
    ],
    "list_enrollments": [
        "GET",
        "/api/school/courses/{courseId}/enrollments",
        [
            "courseId"
        ],
        []
    ],
    "list_subscriptions": [
        "GET",
        "/api/payment/subscriptions",
        [],
        []
    ],
    "list_tags": [
        "GET",
        "/api/tags",
        [],
        []
    ],
    "list_webhooks": [
        "GET",
        "/api/webhooks",
        [],
        []
    ],
    "update_contact": [
        "PATCH",
        "/api/contacts/{contactId}",
        [
            "contactId"
        ],
        []
    ],
    "update_tag": [
        "PUT",
        "/api/tags/{tagId}",
        [
            "tagId"
        ],
        []
    ],
    "update_webhook": [
        "PATCH",
        "/api/webhooks/{webhookId}",
        [
            "webhookId"
        ],
        []
    ]
}

class SystemeIoDynamicAction(Action):
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

        auth_mode = "systeme_io"
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
            raise ValueError(f"Systeme.io API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class SystemeIoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="systeme_io",
            display_name="Systeme.io",
            category="Project Management",
            auth_types=['api_key'],
            description="Systeme.io all-in-one marketing platform for contacts, tags, courses, enrollments, webhooks, and subscriptions with 24 actions."
        )
        for act in get_provider_actions("systeme_io"):
            self.register_action(SystemeIoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "systeme_io" not in ["sanity"]:
            raise ValueError("API token or key is required for Systeme.io.")

        if "systeme_io" == "sanity":
            project_id = str(cred.get("projectId") or "").strip()
            if not project_id:
                raise ValueError("Sanity projectId is required in credentials.")
            if not token:
                raise ValueError("API token is required for Sanity.")
            val_url = f"https://api.sanity.io/v2021-06-07/projects/{project_id}/datasets"
        elif "systeme_io" == "home_assistant":
            base_url = str(cred.get("baseUrl") or "http://homeassistant.local:8123").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/config"
        elif "systeme_io" == "homebox":
            base_url = str(cred.get("baseUrl") or "http://homebox.local:7745").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            if not base_url.endswith("/api/v1"):
                base_url = f"{base_url.rstrip('/')}/api/v1"
            val_url = f"{base_url.rstrip('/')}/status"
        elif "systeme_io" == "kobotoolbox":
            base_url = str(cred.get("baseUrl") or "https://kf.kobotoolbox.org").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/assets/?limit=1"
        elif "systeme_io" == "make":
            zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
            if not zone.endswith("/api/v2"):
                zone = f"{zone}/api/v2"
            val_url = f"{zone}/users/me"
        else:
            base_url = _resolve_base_url(cred)
            val_url = f"{base_url.rstrip('/')}/api/tags?limit=1".replace("//", "/")

        req_params = {}
        auth_mode = "systeme_io"
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
            raise ValueError(f"Systeme.io connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Systeme.io credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Systeme.io validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": "verified",
            "display_name": f"Systeme.io Account"
        }

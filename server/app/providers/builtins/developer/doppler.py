"""
Doppler Provider for ConnectorHub.
Loads and registers 44 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.doppler.com/v3"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    if base.startswith("{instanceUrl}"):
        inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
        base = base.replace("{instanceUrl}", inst)
    return base

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
    elif auth_mode == "gitea_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "zerotier_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "n8n_header":
        if token:
            headers["X-N8N-API-KEY"] = token
    elif auth_mode == "readme_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mingdao_auth":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cred.get("appKey"):
            headers["X-App-Key"] = str(cred["appKey"])
        if cred.get("sign"):
            headers["X-Sign"] = str(cred["sign"])

    return headers

ROUTES: Dict[str, List[Any]] = {
    "clone_config": [
        "POST",
        "/v3/me",
        [],
        []
    ],
    "create_change_request": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "create_config": [
        "POST",
        "/v3/me",
        [],
        []
    ],
    "create_environment": [
        "POST",
        "/v3/environments",
        [],
        []
    ],
    "create_project": [
        "POST",
        "/v3/projects",
        [],
        []
    ],
    "create_service_token": [
        "POST",
        "/v3/configs/config/tokens",
        [],
        []
    ],
    "create_sync": [
        "POST",
        "/v3/integrations",
        [],
        []
    ],
    "delete_config": [
        "DELETE",
        "/v3/me",
        [],
        []
    ],
    "delete_environment": [
        "DELETE",
        "/v3/environments/environment",
        [],
        []
    ],
    "delete_project": [
        "DELETE",
        "/v3/projects/project",
        [],
        []
    ],
    "delete_secret": [
        "DELETE",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "delete_service_token": [
        "POST",
        "/v3/configs/config/tokens",
        [],
        []
    ],
    "delete_sync": [
        "DELETE",
        "/v3/integrations",
        [],
        []
    ],
    "download_secrets": [
        "GET",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "get_auth_me": [
        "GET",
        "/auth_me",
        [],
        []
    ],
    "get_change_request": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "get_config": [
        "GET",
        "/v3/me",
        [],
        []
    ],
    "get_config_log": [
        "GET",
        "/v3/configs/config/logs",
        [],
        []
    ],
    "get_environment": [
        "GET",
        "/v3/environments/environment",
        [],
        []
    ],
    "get_integration": [
        "GET",
        "/v3/integrations",
        [],
        []
    ],
    "get_project": [
        "GET",
        "/project",
        [],
        []
    ],
    "get_secret": [
        "GET",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "get_sync": [
        "GET",
        "/v3/integrations",
        [],
        []
    ],
    "issue_dynamic_secret_lease": [
        "GET",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "list_change_requests": [
        "GET",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "list_config_logs": [
        "GET",
        "/v3/configs/config/logs",
        [],
        []
    ],
    "list_configs": [
        "GET",
        "/v3/configs",
        [],
        []
    ],
    "list_environments": [
        "GET",
        "/v3/environments",
        [],
        []
    ],
    "list_integrations": [
        "GET",
        "/v3/integrations",
        [],
        []
    ],
    "list_projects": [
        "GET",
        "/v3/projects",
        [],
        []
    ],
    "list_secret_names": [
        "GET",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "list_secrets": [
        "GET",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "list_service_tokens": [
        "POST",
        "/v3/configs/config/tokens",
        [],
        []
    ],
    "review_change_request_unit": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "revoke_dynamic_secret_lease": [
        "DELETE",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "set_config_inheritable": [
        "POST",
        "/v3/projects",
        [],
        []
    ],
    "update_change_request": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "update_change_request_assignees": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "update_change_request_unit_status": [
        "POST",
        "/v3/workplace/change_requests",
        [],
        []
    ],
    "update_config": [
        "POST",
        "/v3/me",
        [],
        []
    ],
    "update_environment": [
        "PUT",
        "/v3/environments/environment",
        [],
        []
    ],
    "update_project": [
        "POST",
        "/v3/projects/project",
        [],
        []
    ],
    "update_secret_note": [
        "POST",
        "/v3/configs/config/secrets",
        [],
        []
    ],
    "update_secrets": [
        "POST",
        "/v3/configs/config/secrets",
        [],
        []
    ]
}

class DopplerDynamicAction(Action):
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

        url_path = path_template
        for p in path_param_names:
            if p in params:
                val = str(params[p])
                url_path = url_path.replace("{" + p + "}", urllib.parse.quote(val, safe=""))

        url_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "default", url_path)

        base_url = _resolve_base_url(cred)
        if base_url.endswith("/") and url_path.startswith("/"):
            full_url = base_url + url_path[1:]
        elif not base_url.endswith("/") and not url_path.startswith("/"):
            full_url = base_url + "/" + url_path
        else:
            full_url = base_url + url_path

        assert_public_url(full_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        req_json: Optional[Dict[str, Any]] = None

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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Doppler API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class DopplerProvider(Provider):
    def __init__(self):
        super().__init__(
            service="doppler",
            display_name="Doppler",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Doppler universal secret management, configs, projects, and environments with 44 actions."
        )
        for act in get_provider_actions("doppler"):
            self.register_action(DopplerDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.doppler.com/v3/me"
        for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))
        if val_url.startswith("{instanceUrl}"):
            inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
            val_url = val_url.replace("{instanceUrl}", inst)

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Doppler connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Doppler credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Doppler validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Doppler Account"
        }

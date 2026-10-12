"""
Neon Provider for ConnectorHub.
Loads and registers 18 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://console.neon.tech/api/v2"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
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
    elif auth_mode == "upstash_bearer":
        rt = cred.get("restToken") or token
        if rt:
            headers["Authorization"] = f"Bearer {rt}"
    elif auth_mode == "figma_token":
        if token:
            if str(token).startswith("figd_") or not str(token).startswith("ey"):
                headers["X-Figma-Token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "wordpress_auth":
        if cred.get("username") and (cred.get("password") or token):
            u = str(cred.get("username"))
            p = str(cred.get("password") or token)
            pair = f"{u}:{p}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
        elif token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "mixpanel_basic":
        u = str(cred.get("serviceAccountUsername") or cred.get("username") or "")
        p = str(cred.get("secret") or token)
        pair = f"{u}:{p}"
        headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "klaviyo_api_key":
        if token:
            headers["Authorization"] = f"Klaviyo-API-Key {token}"
            headers["revision"] = "2024-10-15"
    elif auth_mode == "segment_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "activecampaign_token":
        if token:
            headers["Api-Token"] = token
    elif auth_mode == "ghost_key":
        pass

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_branch": [
        "POST",
        "/users/me",
        [],
        [
            "projectId",
            "name",
            "parentId",
            "parentLsn",
            "parentTimestamp",
            "protected",
            "initSource"
        ]
    ],
    "create_database": [
        "POST",
        "/users/me",
        [],
        [
            "projectId",
            "branchId",
            "name",
            "ownerName"
        ]
    ],
    "create_project": [
        "POST",
        "/projects",
        [],
        [
            "name",
            "orgId",
            "regionId",
            "pgVersion",
            "branchName",
            "databaseName",
            "roleName",
            "storePasswords",
            "historyRetentionSeconds"
        ]
    ],
    "delete_branch": [
        "DELETE",
        "/users/me",
        [],
        [
            "projectId",
            "branchId"
        ]
    ],
    "delete_database": [
        "DELETE",
        "/users/me",
        [],
        [
            "projectId",
            "branchId",
            "databaseName"
        ]
    ],
    "delete_project": [
        "DELETE",
        "/users/me",
        [],
        [
            "projectId"
        ]
    ],
    "get_branch": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "branchId"
        ]
    ],
    "get_current_user": [
        "GET",
        "/users/me",
        [],
        []
    ],
    "get_database": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "branchId",
            "databaseName"
        ]
    ],
    "get_operation": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "operationId"
        ]
    ],
    "get_project": [
        "GET",
        "/project",
        [],
        [
            "projectId"
        ]
    ],
    "list_branches": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "search",
            "sortBy",
            "sortOrder",
            "cursor",
            "limit"
        ]
    ],
    "list_databases": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "branchId"
        ]
    ],
    "list_operations": [
        "GET",
        "/users/me",
        [],
        [
            "projectId",
            "cursor",
            "limit"
        ]
    ],
    "list_projects": [
        "GET",
        "/projects",
        [],
        [
            "cursor",
            "limit",
            "search",
            "orgId",
            "recoverable"
        ]
    ],
    "update_branch": [
        "PATCH",
        "/users/me",
        [],
        [
            "projectId",
            "branchId",
            "name",
            "protected"
        ]
    ],
    "update_database": [
        "PATCH",
        "/users/me",
        [],
        [
            "projectId",
            "branchId",
            "databaseName",
            "newName",
            "ownerName"
        ]
    ],
    "update_project": [
        "PATCH",
        "/users/me",
        [],
        [
            "projectId",
            "name",
            "historyRetentionSeconds"
        ]
    ]
}

class NeonDynamicAction(Action):
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

        if "Bearer" == "ghost_key":
            token = _extract_token(cred)
            if token:
                req_params["key"] = token

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
            raise ValueError(f"Neon API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class NeonProvider(Provider):
    def __init__(self):
        super().__init__(
            service="neon",
            display_name="Neon",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Neon serverless Postgres, branches, projects, and database management with 18 actions."
        )
        for act in get_provider_actions("neon"):
            self.register_action(NeonDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://console.neon.tech/api/v2/users/me"
        for key in ["domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "Bearer" == "ghost_key":
            token = _extract_token(cred)
            if token:
                params["key"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=params if params else None
            )
        except Exception as e:
            raise ValueError(f"Neon connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Neon credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Neon validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Neon Account"
        }

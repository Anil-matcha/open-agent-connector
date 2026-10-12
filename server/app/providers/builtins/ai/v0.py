"""
v0 Provider for ConnectorHub.
Loads and registers 45 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://api.v0.dev"

def _headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "userKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("v0 credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "v0" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "get_user": [
        "GET",
        "/v1/user",
        [],
        []
    ],
    "find_projects": [
        "GET",
        "/v1/projects",
        [],
        [
            "limit"
        ]
    ],
    "create_project": [
        "POST",
        "/v1/projects",
        [],
        []
    ],
    "get_project": [
        "GET",
        "/v1/projects/{projectId}",
        [
            "projectId"
        ],
        []
    ],
    "update_project": [
        "PATCH",
        "/v1/projects/{projectId}",
        [
            "projectId"
        ],
        []
    ],
    "get_project_by_chat": [
        "GET",
        "/v1/chats/{chatId}/project",
        [
            "chatId"
        ],
        []
    ],
    "assign_project_to_chat": [
        "POST",
        "/v1/projects/{projectId}/assign",
        [
            "projectId"
        ],
        []
    ],
    "delete_project": [
        "DELETE",
        "/v1/projects/{projectId}",
        [
            "projectId"
        ],
        []
    ],
    "find_env_vars": [
        "GET",
        "/v1/projects/{projectId}/env-vars",
        [
            "projectId"
        ],
        []
    ],
    "get_env_var": [
        "GET",
        "/v1/projects/{projectId}/env-vars/{environmentVariableId}",
        [
            "projectId",
            "environmentVariableId"
        ],
        []
    ],
    "create_env_vars": [
        "POST",
        "/v1/projects/{projectId}/env-vars",
        [
            "projectId"
        ],
        []
    ],
    "update_env_vars": [
        "PATCH",
        "/v1/projects/{projectId}/env-vars",
        [
            "projectId"
        ],
        []
    ],
    "delete_env_vars": [
        "POST",
        "/v1/projects/{projectId}/env-vars/delete",
        [
            "projectId"
        ],
        []
    ],
    "create_chat": [
        "POST",
        "/v1/chats",
        [],
        []
    ],
    "init_chat": [
        "POST",
        "/v1/chats/init",
        [],
        []
    ],
    "send_message": [
        "POST",
        "/v1/chats/{chatId}/messages",
        [
            "chatId"
        ],
        []
    ],
    "find_chats": [
        "GET",
        "/v1/chats",
        [],
        [
            "limit"
        ]
    ],
    "get_chat": [
        "GET",
        "/v1/chats/{chatId}",
        [
            "chatId"
        ],
        []
    ],
    "update_chat": [
        "PATCH",
        "/v1/chats/{chatId}",
        [
            "chatId"
        ],
        []
    ],
    "favorite_chat": [
        "PUT",
        "/v1/chats/{chatId}/favorite",
        [
            "chatId"
        ],
        []
    ],
    "fork_chat": [
        "POST",
        "/v1/chats/{chatId}/fork",
        [
            "chatId"
        ],
        []
    ],
    "delete_chat": [
        "DELETE",
        "/v1/chats/{chatId}",
        [
            "chatId"
        ],
        []
    ],
    "find_messages": [
        "GET",
        "/v1/chats/{chatId}/messages",
        [
            "chatId"
        ],
        []
    ],
    "get_message": [
        "GET",
        "/v1/chats/{chatId}/messages/{messageId}",
        [
            "chatId",
            "messageId"
        ],
        []
    ],
    "resume_message": [
        "POST",
        "/v1/chats/{chatId}/messages/{messageId}/resume",
        [
            "chatId",
            "messageId"
        ],
        []
    ],
    "find_versions": [
        "GET",
        "/v1/chats/{chatId}/versions",
        [
            "chatId"
        ],
        []
    ],
    "get_version": [
        "GET",
        "/v1/chats/{chatId}/versions/{versionId}",
        [
            "chatId",
            "versionId"
        ],
        []
    ],
    "update_version": [
        "PATCH",
        "/v1/chats/{chatId}/versions/{versionId}",
        [
            "chatId",
            "versionId"
        ],
        []
    ],
    "create_deployment": [
        "POST",
        "/v1/deployments",
        [],
        []
    ],
    "find_deployments": [
        "GET",
        "/v1/deployments",
        [],
        [
            "limit",
            "projectId",
            "chatId"
        ]
    ],
    "get_deployment": [
        "GET",
        "/v1/deployments/{deploymentId}",
        [
            "deploymentId"
        ],
        []
    ],
    "find_deployment_logs": [
        "GET",
        "/v1/deployments/{deploymentId}/logs",
        [
            "deploymentId"
        ],
        []
    ],
    "find_deployment_errors": [
        "GET",
        "/v1/deployments/{deploymentId}/errors",
        [
            "deploymentId"
        ],
        []
    ],
    "find_hooks": [
        "GET",
        "/v1/hooks",
        [],
        []
    ],
    "create_hook": [
        "POST",
        "/v1/hooks",
        [],
        []
    ],
    "get_hook": [
        "GET",
        "/v1/hooks/{hookId}",
        [
            "hookId"
        ],
        []
    ],
    "update_hook": [
        "PATCH",
        "/v1/hooks/{hookId}",
        [
            "hookId"
        ],
        []
    ],
    "delete_hook": [
        "DELETE",
        "/v1/hooks/{hookId}",
        [
            "hookId"
        ],
        []
    ],
    "find_rate_limit": [
        "GET",
        "/v1/rate-limits",
        [],
        []
    ],
    "get_billing": [
        "GET",
        "/v1/user/billing",
        [],
        []
    ],
    "get_plan": [
        "GET",
        "/v1/user/plan",
        [],
        []
    ],
    "get_user_scopes": [
        "GET",
        "/v1/user/scopes",
        [],
        []
    ],
    "get_usage_report": [
        "GET",
        "/v1/reports/usage",
        [],
        []
    ],
    "create_vercel_project": [
        "POST",
        "/v1/integrations/vercel/projects",
        [],
        []
    ],
    "find_vercel_projects": [
        "GET",
        "/v1/integrations/vercel/projects",
        [],
        []
    ]
}

class V0DynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Modern AI & Vector DBs"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        self.action_meta = action_meta
        act_name = action_meta["name"]
        route_info = ROUTES.get(act_name) or [
            action_meta.get("method", "GET"),
            action_meta.get("endpoint", ""),
            action_meta.get("pathParams", []),
            action_meta.get("queryParams", [])
        ]
        self.method = route_info[0]
        self.endpoint_template = route_info[1]
        self.path_params = route_info[2]
        self.query_params = set(route_info[3])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        inputs = dict(input_data or {})
        headers = _headers(token, credential)

        path = self.endpoint_template
        # Replace path variables (supporting camelCase, snake_case, and kebab-case)
        path_matches = re.findall(r"\{([^\}]+)\}", path)
        for var in path_matches:
            val = None
            candidates = [
                var,
                "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_"),
                var.replace("-", "_"),
                "id",
                "name"
            ]
            for cand in candidates:
                if cand in inputs:
                    val = inputs.pop(cand)
                    break
            if val is not None:
                path = path.replace(chr(123) + var + chr(125), urllib.parse.quote(str(val), safe=""))

        # Special endpoints overriding base URL
        if "v0" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "v0" == "new_relic" and path.startswith("/graphql"):
            base_url = "https://api.newrelic.com"

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        params = {}
        body = {}

        for k, v in inputs.items():
            if v is None or v == "":
                continue
            if req_method in ["GET", "DELETE"] or k in self.query_params or k in ["limit", "offset", "cursor", "page", "per_page"]:
                params[k] = v
            else:
                body[k] = v

        # Payload wraps / transforms if required
        if "v0" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "v0" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "v0" == "pagerduty" and self.name == "resolve_incident":
            body = {"incident": {"type": "incident_reference", "status": "resolved"}}

        json_body = body if (req_method in ["POST", "PUT", "PATCH"] and body) else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=json_body
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("detail") or resp.text
            raise ValueError(f"v0 API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class V0Provider(Provider):
    def __init__(self):
        super().__init__(
            service="v0",
            display_name="v0",
            category="Modern AI & Vector DBs",
            auth_types=["api_key"] if "v0" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="v0 integration suite for ConnectorHub."
        )
        for act in get_provider_actions("v0"):
            self.register_action(V0DynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/v1/user"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid v0 credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"v0 validation failed: {resp.status_code} {resp.text}")

        try:
            res_data = resp.json()
        except Exception:
            res_data = {}

        acc_id = None
        disp_name = None
        for key in ["id", "user_id", "userId", "username", "login", "email", "name", "account_id"]:
            if isinstance(res_data, dict):
                if key in res_data:
                    acc_id = str(res_data[key])
                    break
                user_obj = res_data.get("user") or res_data.get("data")
                if isinstance(user_obj, dict) and key in user_obj:
                    acc_id = str(user_obj[key])
                    disp_name = str(user_obj.get("name") or user_obj.get("username") or acc_id)
                    break

        return {
            "account_id": acc_id or "connected_account",
            "display_name": disp_name or f"v0 ({acc_id or 'verified'})"
        }

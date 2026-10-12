"""
Keygen Provider for ConnectorHub.
Loads and registers 76 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.keygen.sh/v1"

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
    "activate_machine": [
        "GET",
        "/activate_machine",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "attach_license_entitlements": [
        "POST",
        "/attach_license_entitlements",
        [],
        [
            "id",
            "entitlementIds"
        ]
    ],
    "attach_license_users": [
        "POST",
        "/attach_license_users",
        [],
        [
            "id",
            "userIds"
        ]
    ],
    "attach_policy_entitlements": [
        "POST",
        "/attach_policy_entitlements",
        [],
        [
            "id",
            "entitlementIds"
        ]
    ],
    "ban_user": [
        "GET",
        "/ban_user",
        [],
        [
            "id"
        ]
    ],
    "change_license_group": [
        "GET",
        "/change_license_group",
        [],
        [
            "id",
            "groupId"
        ]
    ],
    "change_license_owner": [
        "GET",
        "/change_license_owner",
        [],
        [
            "id",
            "userId"
        ]
    ],
    "change_license_policy": [
        "GET",
        "/change_license_policy",
        [],
        [
            "id",
            "policyId"
        ]
    ],
    "change_machine_group": [
        "GET",
        "/change_machine_group",
        [],
        [
            "id",
            "groupId"
        ]
    ],
    "change_machine_owner": [
        "GET",
        "/change_machine_owner",
        [],
        [
            "id",
            "userId"
        ]
    ],
    "change_user_group": [
        "GET",
        "/change_user_group",
        [],
        [
            "id",
            "groupId"
        ]
    ],
    "check_in_license": [
        "POST",
        "/check_in_license",
        [],
        [
            "id"
        ]
    ],
    "create_component": [
        "POST",
        "/component",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_entitlement": [
        "POST",
        "/entitlement",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_group": [
        "POST",
        "/group",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_license": [
        "POST",
        "/license",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_policy": [
        "POST",
        "/policy",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_process": [
        "POST",
        "/process",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_product": [
        "POST",
        "/product",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "create_user": [
        "POST",
        "/user",
        [],
        [
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "deactivate_machine": [
        "GET",
        "/deactivate_machine",
        [],
        [
            "id"
        ]
    ],
    "decrement_license_usage": [
        "POST",
        "/decrement_license_usage",
        [],
        [
            "id",
            "decrement"
        ]
    ],
    "delete_component": [
        "DELETE",
        "/component",
        [],
        [
            "id"
        ]
    ],
    "delete_entitlement": [
        "POST",
        "/entitlement",
        [],
        [
            "id"
        ]
    ],
    "delete_group": [
        "POST",
        "/group",
        [],
        [
            "id"
        ]
    ],
    "delete_license": [
        "DELETE",
        "/license",
        [],
        [
            "id"
        ]
    ],
    "delete_policy": [
        "POST",
        "/policy",
        [],
        [
            "id"
        ]
    ],
    "delete_process": [
        "DELETE",
        "/process",
        [],
        [
            "id"
        ]
    ],
    "delete_product": [
        "DELETE",
        "/product",
        [],
        [
            "id"
        ]
    ],
    "delete_user": [
        "DELETE",
        "/user",
        [],
        [
            "id"
        ]
    ],
    "detach_license_entitlements": [
        "DELETE",
        "/detach_license_entitlements",
        [],
        [
            "id",
            "entitlementIds"
        ]
    ],
    "detach_license_users": [
        "DELETE",
        "/detach_license_users",
        [],
        [
            "id",
            "userIds"
        ]
    ],
    "detach_policy_entitlements": [
        "DELETE",
        "/detach_policy_entitlements",
        [],
        [
            "id",
            "entitlementIds"
        ]
    ],
    "increment_license_usage": [
        "POST",
        "/increment_license_usage",
        [],
        [
            "id",
            "increment"
        ]
    ],
    "list_components": [
        "GET",
        "/components",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_entitlements": [
        "GET",
        "/entitlements",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_groups": [
        "POST",
        "/groups",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_license_entitlements": [
        "POST",
        "/license_entitlements",
        [],
        [
            "id",
            "limit",
            "pageSize",
            "pageCursor"
        ]
    ],
    "list_license_users": [
        "POST",
        "/license_users",
        [],
        [
            "id",
            "limit",
            "pageSize",
            "pageCursor"
        ]
    ],
    "list_licenses": [
        "GET",
        "/licenses",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_machines": [
        "GET",
        "/machines",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_policies": [
        "POST",
        "/policies",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_policy_entitlements": [
        "POST",
        "/policy_entitlements",
        [],
        [
            "id",
            "limit",
            "pageSize",
            "pageCursor"
        ]
    ],
    "list_processes": [
        "GET",
        "/processes",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_products": [
        "GET",
        "/products",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "list_users": [
        "GET",
        "/users",
        [],
        [
            "pageNumber",
            "pageSize",
            "include",
            "filter"
        ]
    ],
    "ping_machine": [
        "GET",
        "/ping_machine",
        [],
        [
            "id"
        ]
    ],
    "ping_process": [
        "GET",
        "/ping_process",
        [],
        [
            "id"
        ]
    ],
    "reinstate_license": [
        "GET",
        "/reinstate_license",
        [],
        [
            "id"
        ]
    ],
    "renew_license": [
        "GET",
        "/renew_license",
        [],
        [
            "id"
        ]
    ],
    "reset_license_usage": [
        "POST",
        "/reset_license_usage",
        [],
        [
            "id"
        ]
    ],
    "reset_machine_heartbeat": [
        "POST",
        "/reset_machine_heartbeat",
        [],
        [
            "id"
        ]
    ],
    "retrieve_component": [
        "GET",
        "/retrieve_component",
        [],
        [
            "id"
        ]
    ],
    "retrieve_entitlement": [
        "GET",
        "/retrieve_entitlement",
        [],
        [
            "id"
        ]
    ],
    "retrieve_group": [
        "POST",
        "/retrieve_group",
        [],
        [
            "id"
        ]
    ],
    "retrieve_license": [
        "GET",
        "/retrieve_license",
        [],
        [
            "id"
        ]
    ],
    "retrieve_machine": [
        "GET",
        "/retrieve_machine",
        [],
        [
            "id"
        ]
    ],
    "retrieve_policy": [
        "POST",
        "/retrieve_policy",
        [],
        [
            "id"
        ]
    ],
    "retrieve_process": [
        "GET",
        "/retrieve_process",
        [],
        [
            "id"
        ]
    ],
    "retrieve_product": [
        "GET",
        "/retrieve_product",
        [],
        [
            "id"
        ]
    ],
    "retrieve_user": [
        "GET",
        "/retrieve_user",
        [],
        [
            "id"
        ]
    ],
    "revoke_license": [
        "POST",
        "/license",
        [],
        [
            "id"
        ]
    ],
    "suspend_license": [
        "GET",
        "/suspend_license",
        [],
        [
            "id"
        ]
    ],
    "unban_user": [
        "GET",
        "/unban_user",
        [],
        [
            "id"
        ]
    ],
    "update_component": [
        "PATCH",
        "/component",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_entitlement": [
        "PATCH",
        "/entitlement",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_group": [
        "POST",
        "/group",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_license": [
        "PATCH",
        "/license",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_machine": [
        "PATCH",
        "/machine",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_policy": [
        "POST",
        "/policy",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_process": [
        "PATCH",
        "/process",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_product": [
        "PATCH",
        "/product",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "update_user": [
        "PATCH",
        "/user",
        [],
        [
            "id",
            "attributes",
            "relationships",
            "meta"
        ]
    ],
    "validate_license_by_id": [
        "POST",
        "/validate_license_by_id",
        [],
        [
            "id",
            "nonce",
            "scope"
        ]
    ],
    "validate_license_key": [
        "POST",
        "/validate_license_key",
        [],
        [
            "key",
            "nonce",
            "scope"
        ]
    ],
    "whoami": [
        "GET",
        "/whoami",
        [],
        []
    ]
}

class KeygenDynamicAction(Action):
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
            raise ValueError(f"Keygen API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class KeygenProvider(Provider):
    def __init__(self):
        super().__init__(
            service="keygen",
            display_name="Keygen",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Keygen software licensing, entitlements, and machine activation with 76 actions."
        )
        for act in get_provider_actions("keygen"):
            self.register_action(KeygenDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.keygen.sh/v1/me"
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
            raise ValueError(f"Keygen connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Keygen credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Keygen validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Keygen Account"
        }

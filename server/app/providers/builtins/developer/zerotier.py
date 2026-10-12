"""
ZeroTier Provider for ConnectorHub.
Loads and registers 68 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.zerotier.com/api/v1"

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

    auth_mode = "zerotier_token"
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
    "accept_invitation": [
        "POST",
        "/org-invitation/${id(input, ",
        [],
        [
            "invitationId"
        ]
    ],
    "add_iam": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "resourceType",
            "resourceId",
            "principal",
            "roles"
        ]
    ],
    "add_members": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "members"
        ]
    ],
    "add_user_token": [
        "POST",
        "/user/${id(input, ",
        [],
        [
            "userId",
            "tokenName",
            "token"
        ]
    ],
    "authorize_member": [
        "POST",
        "{path}/authorize",
        [
            "path"
        ],
        [
            "networkId",
            "memberId"
        ]
    ],
    "authorize_members": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "deviceIds"
        ]
    ],
    "check_permissions": [
        "POST",
        "/user/check-permissions",
        [],
        [
            "checks"
        ]
    ],
    "create_api_key": [
        "POST",
        "/service-account/${id(input, ",
        [],
        [
            "serviceAccountId",
            "expires",
            "description"
        ]
    ],
    "create_invitation": [
        "POST",
        "/org-invitation",
        [],
        [
            "email"
        ]
    ],
    "create_network": [
        "POST",
        "/network-group/${zerotierPathSegment(groupId, ",
        [],
        [
            "networkGroupId",
            "name",
            "description",
            "config"
        ]
    ],
    "create_network_group": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId",
            "name",
            "description"
        ]
    ],
    "create_service_account": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId",
            "id",
            "name",
            "description"
        ]
    ],
    "create_webhook": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId",
            "url",
            "eventList",
            "description"
        ]
    ],
    "deauthorize_member": [
        "POST",
        "{path}/de-authorize",
        [
            "path"
        ],
        [
            "networkId",
            "memberId"
        ]
    ],
    "deauthorize_members": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "deviceIds"
        ]
    ],
    "decline_invitation": [
        "DELETE",
        "/org-invitation/${id(input, ",
        [],
        [
            "invitationId"
        ]
    ],
    "delete_api_key": [
        "DELETE",
        "/api-key/${id(input, ",
        [],
        [
            "apiKeyId"
        ]
    ],
    "delete_current_user": [
        "DELETE",
        "/user",
        [],
        []
    ],
    "delete_member": [
        "DELETE",
        "/network/{networkId}/member",
        [
            "networkId"
        ],
        [
            "memberId"
        ]
    ],
    "delete_network": [
        "DELETE",
        "/network/${id(input, ",
        [],
        [
            "networkId"
        ]
    ],
    "delete_network_group": [
        "DELETE",
        "/network-group/${id(input, ",
        [],
        [
            "networkGroupId"
        ]
    ],
    "delete_service_account": [
        "DELETE",
        "/service-account/${id(input, ",
        [],
        [
            "serviceAccountId"
        ]
    ],
    "delete_user": [
        "DELETE",
        "/user/${id(input, ",
        [],
        [
            "userId"
        ]
    ],
    "delete_user_token": [
        "DELETE",
        "/user/${id(input, ",
        [],
        [
            "userId",
            "tokenName"
        ]
    ],
    "delete_webhook": [
        "DELETE",
        "/webhook/${id(input, ",
        [],
        [
            "webhookId"
        ]
    ],
    "delete_webhook_secret": [
        "DELETE",
        "/webhook-secret/${id(input, ",
        [],
        [
            "webhookSecretId"
        ]
    ],
    "get_api_key": [
        "POST",
        "/api-key/${id(input, ",
        [],
        [
            "apiKeyId"
        ]
    ],
    "get_flow_rules": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId"
        ]
    ],
    "get_iam": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "resourceType",
            "resourceId"
        ]
    ],
    "get_invitation": [
        "POST",
        "/org-invitation/${id(input, ",
        [],
        [
            "invitationId"
        ]
    ],
    "get_member": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "memberId"
        ]
    ],
    "get_network": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId"
        ]
    ],
    "get_network_group": [
        "POST",
        "/network-group/${id(input, ",
        [],
        [
            "networkGroupId"
        ]
    ],
    "get_org": [
        "GET",
        "/org/${zerotierPathSegment(orgId, ",
        [],
        [
            "orgId"
        ]
    ],
    "get_org_iam_tree": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId"
        ]
    ],
    "get_org_subscription": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId"
        ]
    ],
    "get_random_token": [
        "POST",
        "/randomToken",
        [],
        []
    ],
    "get_service_account": [
        "POST",
        "/service-account/${id(input, ",
        [],
        [
            "serviceAccountId"
        ]
    ],
    "get_status": [
        "POST",
        "/status",
        [],
        []
    ],
    "get_user": [
        "POST",
        "/user/${id(input, ",
        [],
        [
            "userId"
        ]
    ],
    "get_webhook": [
        "POST",
        "/webhook/${id(input, ",
        [],
        [
            "webhookId"
        ]
    ],
    "invite_users": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId",
            "emails"
        ]
    ],
    "list_invitations": [
        "POST",
        "/org-invitation",
        [],
        []
    ],
    "list_members": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId"
        ]
    ],
    "list_network_group_networks": [
        "POST",
        "/network-group/${id(input, ",
        [],
        [
            "networkGroupId",
            "stats",
            "permissionCheck"
        ]
    ],
    "list_network_groups": [
        "POST",
        "/network-group",
        [],
        [
            "orgId",
            "stats",
            "permissionCheck"
        ]
    ],
    "list_networks": [
        "GET",
        "/network",
        [],
        [
            "orgId",
            "stats",
            "permissionCheck"
        ]
    ],
    "list_org_members": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId"
        ]
    ],
    "list_orgs": [
        "POST",
        "/org",
        [],
        [
            "permissionCheck",
            "latest",
            "stats"
        ]
    ],
    "list_service_accounts": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId"
        ]
    ],
    "list_webhooks": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId"
        ]
    ],
    "reject_member": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "memberId"
        ]
    ],
    "reject_members": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "deviceIds"
        ]
    ],
    "remove_iam": [
        "DELETE",
        "/org/${id(input, ",
        [],
        [
            "resourceType",
            "resourceId",
            "principal",
            "roles"
        ]
    ],
    "remove_members": [
        "DELETE",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "deviceIds"
        ]
    ],
    "replace_iam": [
        "PUT",
        "/org/${id(input, ",
        [],
        [
            "resourceType",
            "resourceId",
            "assignments"
        ]
    ],
    "rotate_webhook_secret": [
        "POST",
        "/webhook/${id(input, ",
        [],
        [
            "webhookId",
            "overlapHours"
        ]
    ],
    "search_principals": [
        "POST",
        "/org/${id(input, ",
        [],
        [
            "orgId",
            "search",
            "principalType"
        ]
    ],
    "set_network_user_permissions": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "userId",
            "read",
            "authorize",
            "modify",
            "delete"
        ]
    ],
    "update_api_key": [
        "POST",
        "/api-key/${id(input, ",
        [],
        [
            "apiKeyId",
            "description"
        ]
    ],
    "update_current_user": [
        "POST",
        "/user",
        [],
        [
            "firstName",
            "lastName"
        ]
    ],
    "update_flow_rules": [
        "POST",
        "/network/${id(input, ",
        [],
        [
            "networkId",
            "kind",
            "config"
        ]
    ],
    "update_member": [
        "POST",
        "/member",
        [],
        [
            "networkId",
            "memberId",
            "name",
            "description",
            "authorized",
            "activeBridge",
            "noAutoAssignIps",
            "ipAssignments",
            "ipv4Assignments",
            "ipv6Assignments"
        ]
    ],
    "update_network": [
        "POST",
        "/network/{networkId}",
        [
            "networkId"
        ],
        [
            "name",
            "description",
            "config"
        ]
    ],
    "update_network_group": [
        "POST",
        "/network-group/${id(input, ",
        [],
        [
            "networkGroupId",
            "name",
            "description"
        ]
    ],
    "update_service_account": [
        "POST",
        "/service-account/${id(input, ",
        [],
        [
            "serviceAccountId",
            "name",
            "description"
        ]
    ],
    "update_user": [
        "POST",
        "/user/${id(input, ",
        [],
        [
            "userId",
            "displayName",
            "smsNumber"
        ]
    ],
    "update_webhook": [
        "POST",
        "/webhook/${id(input, ",
        [],
        [
            "webhookId",
            "url",
            "eventList",
            "description"
        ]
    ]
}

class ZeroTierDynamicAction(Action):
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
            raise ValueError(f"ZeroTier API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ZeroTierProvider(Provider):
    def __init__(self):
        super().__init__(
            service="zerotier",
            display_name="ZeroTier",
            category="Developer Tools",
            auth_types=["api_key", "custom_credential"],
            description="ZeroTier global virtual network management, members, and controller API with 68 actions."
        )
        for act in get_provider_actions("zerotier"):
            self.register_action(ZeroTierDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.zerotier.com/api/v1/user"
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
            raise ValueError(f"ZeroTier connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid ZeroTier credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"ZeroTier validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"ZeroTier Account"
        }

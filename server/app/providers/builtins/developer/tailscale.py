"""
Tailscale Provider for ConnectorHub.
Loads and registers 82 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://api.tailscale.com/api/v2"

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
    raise ValueError("Tailscale credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "tailscale" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "list_devices": [
        "GET",
        "/tailnet/-/devices",
        [],
        []
    ],
    "get_device": [
        "GET",
        "/device/{deviceId}",
        [
            "deviceId"
        ],
        []
    ],
    "list_device_routes": [
        "GET",
        "/device/{deviceId}/routes",
        [
            "deviceId"
        ],
        []
    ],
    "get_device_posture_attributes": [
        "GET",
        "/device/{deviceId}/attributes",
        [
            "deviceId"
        ],
        []
    ],
    "list_configuration_audit_logs": [
        "GET",
        "/tailnet/-/logging/configuration",
        [],
        [
            "start",
            "end",
            "actor",
            "target",
            "event"
        ]
    ],
    "get_log_streaming_status": [
        "GET",
        "/tailnet/-/logging/{logType}/stream/status",
        [
            "logType"
        ],
        []
    ],
    "list_dns_nameservers": [
        "GET",
        "/tailnet/-/dns/nameservers",
        [],
        []
    ],
    "get_dns_preferences": [
        "GET",
        "/tailnet/-/dns/preferences",
        [],
        []
    ],
    "list_dns_search_paths": [
        "GET",
        "/tailnet/-/dns/searchpaths",
        [],
        []
    ],
    "get_split_dns": [
        "GET",
        "/tailnet/-/dns/split-dns",
        [],
        []
    ],
    "get_dns_configuration": [
        "GET",
        "/tailnet/-/dns/configuration",
        [],
        []
    ],
    "list_users": [
        "GET",
        "/tailnet/-/users",
        [],
        [
            "type",
            "role"
        ]
    ],
    "get_user": [
        "GET",
        "/users/{userId}",
        [
            "userId"
        ],
        []
    ],
    "get_contacts": [
        "GET",
        "/tailnet/-/contacts",
        [],
        []
    ],
    "get_tailnet_settings": [
        "GET",
        "/tailnet/-/settings",
        [],
        []
    ],
    "list_services": [
        "GET",
        "/tailnet/-/services",
        [],
        []
    ],
    "get_service": [
        "GET",
        "/tailnet/-/services/{serviceName}",
        [
            "serviceName"
        ],
        []
    ],
    "set_device_routes": [
        "POST",
        "/device/{deviceId}/routes",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_authorized": [
        "POST",
        "/device/{deviceId}/authorized",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_name": [
        "POST",
        "/device/{deviceId}/name",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_tags": [
        "POST",
        "/device/{deviceId}/tags",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_ip": [
        "POST",
        "/device/{deviceId}/ip",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_posture_attribute": [
        "POST",
        "/device/{deviceId}/attributes/{attributeKey}",
        [
            "deviceId",
            "attributeKey"
        ],
        []
    ],
    "set_dns_nameservers": [
        "POST",
        "/tailnet/-/dns/nameservers",
        [],
        []
    ],
    "set_dns_preferences": [
        "POST",
        "/tailnet/-/dns/preferences",
        [],
        []
    ],
    "set_dns_search_paths": [
        "POST",
        "/tailnet/-/dns/searchpaths",
        [],
        []
    ],
    "update_split_dns": [
        "PATCH",
        "/tailnet/-/dns/split-dns",
        [],
        []
    ],
    "set_split_dns": [
        "PUT",
        "/tailnet/-/dns/split-dns",
        [],
        []
    ],
    "set_dns_configuration": [
        "POST",
        "/tailnet/-/dns/configuration",
        [],
        []
    ],
    "update_tailnet_settings": [
        "PATCH",
        "/tailnet/-/settings",
        [],
        []
    ],
    "update_service": [
        "PUT",
        "/tailnet/-/services/{serviceName}",
        [
            "serviceName"
        ],
        []
    ],
    "list_service_hosts": [
        "GET",
        "/tailnet/-/services/{serviceName}/devices",
        [
            "serviceName"
        ],
        []
    ],
    "get_service_device_approval": [
        "GET",
        "/tailnet/-/services/{serviceName}/device/{deviceId}/approved",
        [
            "serviceName",
            "deviceId"
        ],
        []
    ],
    "update_service_device_approval": [
        "POST",
        "/tailnet/-/services/{serviceName}/device/{deviceId}/approved",
        [
            "serviceName",
            "deviceId"
        ],
        []
    ],
    "batch_update_device_posture_attributes": [
        "PATCH",
        "/tailnet/-/device-attributes",
        [],
        []
    ],
    "delete_device": [
        "DELETE",
        "/device/{deviceId}",
        [
            "deviceId"
        ],
        []
    ],
    "expire_device_key": [
        "POST",
        "/device/{deviceId}/expire",
        [
            "deviceId"
        ],
        []
    ],
    "set_device_key_expiry": [
        "POST",
        "/device/{deviceId}/key",
        [
            "deviceId"
        ],
        []
    ],
    "delete_device_posture_attribute": [
        "DELETE",
        "/device/{deviceId}/attributes/{attributeKey}",
        [
            "deviceId",
            "attributeKey"
        ],
        []
    ],
    "get_log_streaming_configuration": [
        "GET",
        "/tailnet/-/logging/{logType}/stream",
        [
            "logType"
        ],
        []
    ],
    "set_log_streaming_configuration": [
        "PUT",
        "/tailnet/-/logging/{logType}/stream",
        [
            "logType"
        ],
        []
    ],
    "disable_log_streaming": [
        "DELETE",
        "/tailnet/-/logging/{logType}/stream",
        [
            "logType"
        ],
        []
    ],
    "get_aws_external_id": [
        "POST",
        "/tailnet/-/aws-external-id",
        [],
        []
    ],
    "validate_aws_external_id": [
        "POST",
        "/tailnet/-/aws-external-id/{externalId}/validate-aws-trust-policy",
        [
            "externalId"
        ],
        []
    ],
    "list_keys": [
        "GET",
        "/tailnet/-/keys",
        [],
        [
            "all"
        ]
    ],
    "create_key": [
        "POST",
        "/tailnet/-/keys",
        [],
        []
    ],
    "get_key": [
        "GET",
        "/tailnet/-/keys/{keyId}",
        [
            "keyId"
        ],
        []
    ],
    "delete_key": [
        "DELETE",
        "/tailnet/-/keys/{keyId}",
        [
            "keyId"
        ],
        []
    ],
    "update_key": [
        "PUT",
        "/tailnet/-/keys/{keyId}",
        [
            "keyId"
        ],
        []
    ],
    "get_policy_file": [
        "GET",
        "/tailnet/-/acl",
        [],
        [
            "details"
        ]
    ],
    "set_policy_file": [
        "POST",
        "/tailnet/-/acl",
        [],
        []
    ],
    "update_user_role": [
        "POST",
        "/users/{userId}/role",
        [
            "userId"
        ],
        []
    ],
    "approve_user": [
        "POST",
        "/users/{userId}/approve",
        [
            "userId"
        ],
        []
    ],
    "suspend_user": [
        "POST",
        "/users/{userId}/suspend",
        [
            "userId"
        ],
        []
    ],
    "restore_user": [
        "POST",
        "/users/{userId}/restore",
        [
            "userId"
        ],
        []
    ],
    "delete_user": [
        "POST",
        "/users/{userId}/delete",
        [
            "userId"
        ],
        []
    ],
    "update_contact": [
        "PATCH",
        "/tailnet/-/contacts/{contactType}",
        [
            "contactType"
        ],
        []
    ],
    "resend_contact_verification_email": [
        "POST",
        "/tailnet/-/contacts/{contactType}/resend-verification-email",
        [
            "contactType"
        ],
        []
    ],
    "list_webhooks": [
        "GET",
        "/tailnet/-/webhooks",
        [],
        []
    ],
    "create_webhook": [
        "POST",
        "/tailnet/-/webhooks",
        [],
        []
    ],
    "get_webhook": [
        "GET",
        "/webhooks/{endpointId}",
        [
            "endpointId"
        ],
        []
    ],
    "update_webhook": [
        "PATCH",
        "/webhooks/{endpointId}",
        [
            "endpointId"
        ],
        []
    ],
    "delete_webhook": [
        "DELETE",
        "/webhooks/{endpointId}",
        [
            "endpointId"
        ],
        []
    ],
    "test_webhook": [
        "POST",
        "/webhooks/{endpointId}/test",
        [
            "endpointId"
        ],
        []
    ],
    "rotate_webhook_secret": [
        "POST",
        "/webhooks/{endpointId}/rotate",
        [
            "endpointId"
        ],
        []
    ],
    "delete_service": [
        "DELETE",
        "/tailnet/-/services/{serviceName}",
        [
            "serviceName"
        ],
        []
    ],
    "list_oauth_apps": [
        "GET",
        "/tailnet/-/oauth-apps",
        [],
        []
    ],
    "create_oauth_app": [
        "POST",
        "/tailnet/-/oauth-apps",
        [],
        []
    ],
    "get_oauth_app": [
        "GET",
        "/tailnet/-/oauth-apps/{appId}",
        [
            "appId"
        ],
        []
    ],
    "update_oauth_app": [
        "PUT",
        "/tailnet/-/oauth-apps/{appId}",
        [
            "appId"
        ],
        []
    ],
    "delete_oauth_app": [
        "DELETE",
        "/tailnet/-/oauth-apps/{appId}",
        [
            "appId"
        ],
        []
    ],
    "list_device_invites": [
        "GET",
        "/device/{deviceId}/device-invites",
        [
            "deviceId"
        ],
        []
    ],
    "get_device_invite": [
        "GET",
        "/device-invites/{deviceInviteId}",
        [
            "deviceInviteId"
        ],
        []
    ],
    "delete_device_invite": [
        "DELETE",
        "/device-invites/{deviceInviteId}",
        [
            "deviceInviteId"
        ],
        []
    ],
    "list_network_flow_logs": [
        "GET",
        "/tailnet/-/logging/network",
        [],
        [
            "start",
            "end"
        ]
    ],
    "preview_policy_rule_matches": [
        "POST",
        "/tailnet/-/acl/preview",
        [],
        [
            "type",
            "previewFor"
        ]
    ],
    "validate_policy_file": [
        "POST",
        "/tailnet/-/acl/validate",
        [],
        []
    ],
    "list_posture_integrations": [
        "GET",
        "/tailnet/-/posture/integrations",
        [],
        []
    ],
    "create_posture_integration": [
        "POST",
        "/tailnet/-/posture/integrations",
        [],
        []
    ],
    "get_posture_integration": [
        "GET",
        "/posture/integrations/{integrationId}",
        [
            "integrationId"
        ],
        []
    ],
    "update_posture_integration": [
        "PATCH",
        "/posture/integrations/{integrationId}",
        [
            "integrationId"
        ],
        []
    ],
    "delete_posture_integration": [
        "DELETE",
        "/posture/integrations/{integrationId}",
        [
            "integrationId"
        ],
        []
    ]
}

class TailscaleDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Developer Tools"),
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
        if "tailscale" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "tailscale" == "new_relic" and path.startswith("/graphql"):
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
        if "tailscale" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "tailscale" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "tailscale" == "pagerduty" and self.name == "resolve_incident":
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
            raise ValueError(f"Tailscale API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class TailscaleProvider(Provider):
    def __init__(self):
        super().__init__(
            service="tailscale",
            display_name="Tailscale",
            category="Developer Tools",
            auth_types=["api_key"] if "tailscale" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="Tailscale integration suite for ConnectorHub."
        )
        for act in get_provider_actions("tailscale"):
            self.register_action(TailscaleDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/tailnet/-/devices"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Tailscale credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Tailscale validation failed: {resp.status_code} {resp.text}")

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
            "display_name": disp_name or f"Tailscale ({acc_id or 'verified'})"
        }

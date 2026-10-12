"""
Pi-hole Provider for ConnectorHub.
Loads and registers 40 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "{instanceUrl}/api"

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
    "add_domain": [
        "POST",
        "domains/{type}/{kind}",
        [
            "type",
            "kind"
        ],
        [
            "domain",
            "comment",
            "groups",
            "enabled"
        ]
    ],
    "add_list": [
        "POST",
        "lists",
        [],
        [
            "address",
            "type",
            "comment",
            "groups",
            "enabled"
        ]
    ],
    "batch_delete_clients": [
        "GET",
        "dhcp/leases",
        [],
        [
            "items"
        ]
    ],
    "batch_delete_domains": [
        "GET",
        "dhcp/leases",
        [],
        [
            "items"
        ]
    ],
    "batch_delete_groups": [
        "DELETE",
        "/batch_delete_groups",
        [],
        [
            "items"
        ]
    ],
    "batch_delete_lists": [
        "DELETE",
        "/batch_delete_lists",
        [],
        [
            "items"
        ]
    ],
    "create_client": [
        "POST",
        "clients",
        [],
        [
            "client",
            "comment",
            "groups"
        ]
    ],
    "create_group": [
        "POST",
        "groups",
        [],
        [
            "name",
            "comment",
            "enabled"
        ]
    ],
    "delete_client": [
        "DELETE",
        "clients/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "client"
        ]
    ],
    "delete_domain": [
        "GET",
        "domains/{type}/{kind}/{encodeURIComponent}",
        [
            "type",
            "kind",
            "encodeURIComponent"
        ],
        [
            "domain"
        ]
    ],
    "delete_group": [
        "GET",
        "groups/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "name"
        ]
    ],
    "delete_list": [
        "GET",
        "lists/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "address",
            "type"
        ]
    ],
    "export_backup": [
        "GET",
        "teleporter",
        [],
        []
    ],
    "flush_dns_logs": [
        "POST",
        "action/flush/logs",
        [],
        []
    ],
    "get_config": [
        "GET",
        "config",
        [],
        []
    ],
    "get_dhcp_leases": [
        "GET",
        "dhcp/leases",
        [],
        []
    ],
    "get_dns_blocking_status": [
        "GET",
        "dns/blocking",
        [],
        []
    ],
    "get_history": [
        "GET",
        "history",
        [],
        []
    ],
    "get_network_devices": [
        "GET",
        "network/devices",
        [],
        []
    ],
    "get_overview": [
        "GET",
        "stats/summary",
        [],
        []
    ],
    "get_queries": [
        "GET",
        "queries",
        [],
        [
            "from",
            "until",
            "length",
            "start",
            "cursor",
            "domain",
            "clientIp",
            "clientName",
            "upstream",
            "type",
            "status",
            "reply",
            "dnssec",
            "disk"
        ]
    ],
    "get_query_types": [
        "GET",
        "stats/query_types",
        [],
        []
    ],
    "get_recent_blocked": [
        "GET",
        "stats/recent_blocked",
        [],
        [
            "count"
        ]
    ],
    "get_top_clients": [
        "GET",
        "stats/top_clients",
        [],
        [
            "count",
            "blocked"
        ]
    ],
    "get_top_domains": [
        "GET",
        "stats/top_domains",
        [],
        [
            "count",
            "blocked"
        ]
    ],
    "get_upstreams": [
        "GET",
        "stats/upstreams",
        [],
        []
    ],
    "import_backup": [
        "POST",
        "teleporter",
        [],
        [
            "file"
        ]
    ],
    "list_clients": [
        "GET",
        "clients",
        [],
        []
    ],
    "list_domains": [
        "GET",
        "domains/{type}/{kind}",
        [
            "type",
            "kind"
        ],
        []
    ],
    "list_groups": [
        "GET",
        "groups",
        [],
        []
    ],
    "list_lists": [
        "GET",
        "lists",
        [],
        [
            "type"
        ]
    ],
    "restart_dns": [
        "POST",
        "action/restartdns",
        [],
        []
    ],
    "run_gravity": [
        "POST",
        "action/gravity",
        [],
        []
    ],
    "search_domain": [
        "GET",
        "search/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "domain",
            "partial",
            "maxResults"
        ]
    ],
    "set_dns_blocking": [
        "POST",
        "dns/blocking",
        [],
        [
            "blocking",
            "timer"
        ]
    ],
    "update_client": [
        "PUT",
        "clients/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "client",
            "comment",
            "groups"
        ]
    ],
    "update_config": [
        "PATCH",
        "config",
        [],
        [
            "config",
            "restart"
        ]
    ],
    "update_domain": [
        "PUT",
        "domains/{type}/{kind}/{encodeURIComponent}",
        [
            "type",
            "kind",
            "encodeURIComponent"
        ],
        [
            "domain",
            "comment",
            "groups",
            "enabled"
        ]
    ],
    "update_group": [
        "PUT",
        "groups/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "name",
            "newName",
            "comment",
            "enabled"
        ]
    ],
    "update_list": [
        "PUT",
        "lists/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "address",
            "type",
            "comment",
            "groups",
            "enabled"
        ]
    ]
}

class PiHoleDynamicAction(Action):
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
            raise ValueError(f"Pi-hole API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PiHoleProvider(Provider):
    def __init__(self):
        super().__init__(
            service="pi_hole",
            display_name="Pi-hole",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Pi-hole network-wide ad blocking and DNS sinkhole management with 40 actions."
        )
        for act in get_provider_actions("pi_hole"):
            self.register_action(PiHoleDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "{instanceUrl}/api/info/version"
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
            raise ValueError(f"Pi-hole connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Pi-hole credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Pi-hole validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Pi-hole Account"
        }

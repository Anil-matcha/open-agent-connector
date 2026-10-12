"""
Oracle Cloud Infrastructure Provider for ConnectorHub.
Loads and registers 34 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://iaas.{region}.oraclecloud.com/20160918"

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
    "create_subnet": [
        "POST",
        "/subnet",
        [],
        [
            "vcnId",
            "compartmentId",
            "cidrBlock",
            "displayName"
        ]
    ],
    "create_vcn": [
        "POST",
        "/vcn",
        [],
        [
            "compartmentId",
            "cidrBlock",
            "displayName"
        ]
    ],
    "delete_vcn": [
        "DELETE",
        "/vcn",
        [],
        [
            "vcnId"
        ]
    ],
    "get_compartment_by_name": [
        "GET",
        "/compartment_by_name",
        [],
        [
            "name",
            "parentCompartmentId"
        ]
    ],
    "get_current_tenancy": [
        "GET",
        "/current_tenancy",
        [],
        []
    ],
    "get_current_user": [
        "GET",
        "/current_user",
        [],
        []
    ],
    "get_image": [
        "GET",
        "/image",
        [],
        [
            "imageId"
        ]
    ],
    "get_instance": [
        "GET",
        "/instance",
        [],
        [
            "instanceId"
        ]
    ],
    "get_metrics_data": [
        "GET",
        "/metrics_data",
        [],
        [
            "compartmentId",
            "query",
            "namespace",
            "startTime",
            "endTime",
            "resourceGroup",
            "resolution",
            "compartmentIdInSubtree"
        ]
    ],
    "get_network_security_group": [
        "GET",
        "/network_security_group",
        [],
        [
            "networkSecurityGroupId"
        ]
    ],
    "get_security_list": [
        "GET",
        "/security_list",
        [],
        [
            "securityListId"
        ]
    ],
    "get_subnet": [
        "GET",
        "/subnet",
        [],
        [
            "subnetId"
        ]
    ],
    "get_tenancy": [
        "GET",
        "/tenancy",
        [],
        [
            "tenancyId"
        ]
    ],
    "get_vcn": [
        "GET",
        "/vcn",
        [],
        [
            "vcnId"
        ]
    ],
    "get_vnic": [
        "GET",
        "/vnic",
        [],
        [
            "vnicId"
        ]
    ],
    "get_vnic_attachment": [
        "GET",
        "/vnic_attachment",
        [],
        [
            "vnicAttachmentId"
        ]
    ],
    "instance_action": [
        "GET",
        "/instance_action",
        [],
        [
            "instanceId",
            "action"
        ]
    ],
    "launch_instance": [
        "GET",
        "/launch_instance",
        [],
        [
            "compartmentId",
            "displayName",
            "availabilityDomain",
            "subnetId",
            "imageId",
            "shape",
            "ocpus",
            "memoryInGBs"
        ]
    ],
    "list_alarms": [
        "GET",
        "/alarms",
        [],
        [
            "compartmentId",
            "limit",
            "page"
        ]
    ],
    "list_availability_domains": [
        "GET",
        "/availability_domains",
        [],
        [
            "compartmentId"
        ]
    ],
    "list_compartments": [
        "GET",
        "/compartments",
        [],
        [
            "compartmentId",
            "compartmentIdInSubtree",
            "accessLevel",
            "includeRoot",
            "limit",
            "page"
        ]
    ],
    "list_images": [
        "GET",
        "/images",
        [],
        [
            "compartmentId",
            "operatingSystem",
            "limit",
            "page"
        ]
    ],
    "list_instance_agent_command_executions": [
        "GET",
        "/instance_agent_command_executions",
        [],
        [
            "compartmentId",
            "instanceId",
            "limit",
            "page"
        ]
    ],
    "list_instances": [
        "GET",
        "/instances",
        [],
        [
            "compartmentId",
            "lifecycleState",
            "limit",
            "page"
        ]
    ],
    "list_metric_definitions": [
        "GET",
        "/metric_definitions",
        [],
        [
            "compartmentId",
            "groupBy",
            "metricName",
            "namespace",
            "resourceGroup",
            "compartmentIdInSubtree",
            "limit",
            "page"
        ]
    ],
    "list_network_security_groups": [
        "GET",
        "/network_security_groups",
        [],
        [
            "compartmentId",
            "vcnId",
            "vlanId",
            "limit",
            "page"
        ]
    ],
    "list_security_lists": [
        "GET",
        "/security_lists",
        [],
        [
            "compartmentId",
            "vcnId",
            "limit",
            "page"
        ]
    ],
    "list_subnets": [
        "GET",
        "/subnets",
        [],
        [
            "compartmentId",
            "vcnId",
            "limit",
            "page"
        ]
    ],
    "list_subscribed_regions": [
        "GET",
        "/subscribed_regions",
        [],
        [
            "tenancyId"
        ]
    ],
    "list_vcns": [
        "GET",
        "/vcns",
        [],
        [
            "compartmentId",
            "limit",
            "page"
        ]
    ],
    "list_vnic_attachments": [
        "GET",
        "/vnic_attachments",
        [],
        [
            "compartmentId",
            "instanceId",
            "limit",
            "page"
        ]
    ],
    "run_instance_agent_command": [
        "POST",
        "/run_instance_agent_command",
        [],
        [
            "compartmentId",
            "instanceId",
            "displayName",
            "script",
            "executionTimeoutInSeconds"
        ]
    ],
    "terminate_instance": [
        "GET",
        "/terminate_instance",
        [],
        [
            "instanceId"
        ]
    ],
    "update_instance": [
        "PATCH",
        "/instance",
        [],
        [
            "instanceId",
            "ocpus",
            "memoryInGBs"
        ]
    ]
}

class OracleCloudDynamicAction(Action):
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
            raise ValueError(f"Oracle Cloud Infrastructure API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class OracleCloudProvider(Provider):
    def __init__(self):
        super().__init__(
            service="oracle_cloud",
            display_name="Oracle Cloud Infrastructure",
            category="Developer Tools",
            auth_types=["custom_credential", "api_key"],
            description="Oracle Cloud Infrastructure compute instances, VCN networking, and IAM with 34 actions."
        )
        for act in get_provider_actions("oracle_cloud"):
            self.register_action(OracleCloudDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://iaas.{region}.oraclecloud.com/20160918/instances?limit=1"
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
            raise ValueError(f"Oracle Cloud Infrastructure connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Oracle Cloud Infrastructure credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Oracle Cloud Infrastructure validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Oracle Cloud Infrastructure Account"
        }

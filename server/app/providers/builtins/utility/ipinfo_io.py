"""
IPinfo Provider for ConnectorHub.
Loads and registers 27 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://ipinfo.io"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "ipinfo_io" == "sanity":
        project_id = str(cred.get("projectId") or "default").strip()
        return base.replace("{projectId}", project_id).rstrip("/")

    if "ipinfo_io" == "make":
        zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
        if not zone.endswith("/api/v2"):
            zone = f"{zone}/api/v2"
        return zone

    if "ipinfo_io" in ["home_assistant", "homebox", "kobotoolbox"]:
        val = str(cred.get("baseUrl") or base).strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        if "ipinfo_io" == "homebox" and not val.endswith("/api/v1"):
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
    "batch_lite_lookup": [
        "POST",
        "/batch",
        [],
        [
            "queries"
        ]
    ],
    "batch_lookup": [
        "POST",
        "/batch",
        [],
        [
            "ips",
            "filter"
        ]
    ],
    "get_abuse_contact": [
        "GET",
        "/{ip}/abuse",
        [
            "ip"
        ],
        []
    ],
    "get_carrier_info": [
        "GET",
        "/{ip}/carrier",
        [
            "ip"
        ],
        []
    ],
    "get_city_by_ip": [
        "GET",
        "/{ip}/city",
        [
            "ip"
        ],
        []
    ],
    "get_company_info": [
        "GET",
        "/{ip}/company",
        [
            "ip"
        ],
        []
    ],
    "get_core_field_by_me": [
        "GET",
        "/lookup/me/{field}",
        [
            "field"
        ],
        []
    ],
    "get_country_by_ip": [
        "GET",
        "/{ip}/country",
        [
            "ip"
        ],
        []
    ],
    "get_current_ip": [
        "GET",
        "/ip",
        [],
        []
    ],
    "get_current_ip_info": [
        "GET",
        "/json",
        [],
        []
    ],
    "get_current_loc": [
        "GET",
        "/loc",
        [],
        []
    ],
    "get_current_region": [
        "GET",
        "/region",
        [],
        []
    ],
    "get_geo_by_ip": [
        "GET",
        "/{ip}/geo",
        [
            "ip"
        ],
        []
    ],
    "get_hostname_by_ip": [
        "GET",
        "/{ip}/hostname",
        [
            "ip"
        ],
        []
    ],
    "get_ip_by_ip": [
        "GET",
        "/{ip}/ip",
        [
            "ip"
        ],
        []
    ],
    "get_ip_info": [
        "GET",
        "/{ip}",
        [
            "ip"
        ],
        []
    ],
    "get_ip_info_by_ip": [
        "GET",
        "/{ip}/json",
        [
            "ip"
        ],
        []
    ],
    "get_lite_field_by_ip": [
        "GET",
        "/lookup/{ip}/{field}",
        [
            "ip",
            "field"
        ],
        []
    ],
    "get_location_by_ip": [
        "GET",
        "/{ip}/loc",
        [
            "ip"
        ],
        []
    ],
    "get_org_by_ip": [
        "GET",
        "/{ip}/org",
        [
            "ip"
        ],
        []
    ],
    "get_plus_field_by_me": [
        "GET",
        "/lookup/me/{field}",
        [
            "field"
        ],
        []
    ],
    "get_postal_by_ip": [
        "GET",
        "/{ip}/postal",
        [
            "ip"
        ],
        []
    ],
    "get_privacy_details": [
        "GET",
        "/{ip}/privacy",
        [
            "ip"
        ],
        []
    ],
    "get_region_by_ip": [
        "GET",
        "/{ip}/region",
        [
            "ip"
        ],
        []
    ],
    "get_timezone_by_ip": [
        "GET",
        "/{ip}/timezone",
        [
            "ip"
        ],
        []
    ],
    "get_token_info": [
        "GET",
        "/me",
        [],
        []
    ],
    "map_ips": [
        "POST",
        "/tools/map",
        [],
        [
            "ipAddresses",
            "cli"
        ]
    ]
}

class IpinfoIoDynamicAction(Action):
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
            raise ValueError(f"IPinfo API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class IpinfoIoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="ipinfo_io",
            display_name="IPinfo",
            category="Utilities & Tools",
            auth_types=['api_key'],
            description="IPinfo IP geolocation, ASN, company, carrier, abuse contact, and batch lookup intelligence API with 27 actions."
        )
        for act in get_provider_actions("ipinfo_io"):
            self.register_action(IpinfoIoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "ipinfo_io" not in ["sanity"]:
            raise ValueError("API token or key is required for IPinfo.")

        if "ipinfo_io" == "sanity":
            project_id = str(cred.get("projectId") or "").strip()
            if not project_id:
                raise ValueError("Sanity projectId is required in credentials.")
            if not token:
                raise ValueError("API token is required for Sanity.")
            val_url = f"https://api.sanity.io/v2021-06-07/projects/{project_id}/datasets"
        elif "ipinfo_io" == "home_assistant":
            base_url = str(cred.get("baseUrl") or "http://homeassistant.local:8123").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/config"
        elif "ipinfo_io" == "homebox":
            base_url = str(cred.get("baseUrl") or "http://homebox.local:7745").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            if not base_url.endswith("/api/v1"):
                base_url = f"{base_url.rstrip('/')}/api/v1"
            val_url = f"{base_url.rstrip('/')}/status"
        elif "ipinfo_io" == "kobotoolbox":
            base_url = str(cred.get("baseUrl") or "https://kf.kobotoolbox.org").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/assets/?limit=1"
        elif "ipinfo_io" == "make":
            zone = str(cred.get("zoneUrl") or "https://eu1.make.com").strip().rstrip("/")
            if not zone.endswith("/api/v2"):
                zone = f"{zone}/api/v2"
            val_url = f"{zone}/users/me"
        else:
            base_url = _resolve_base_url(cred)
            val_url = f"{base_url.rstrip('/')}/json".replace("//", "/")

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
            raise ValueError(f"IPinfo connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid IPinfo credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"IPinfo validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": "verified",
            "display_name": f"IPinfo Account"
        }

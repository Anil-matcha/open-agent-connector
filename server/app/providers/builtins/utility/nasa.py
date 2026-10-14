"""
NASA Provider for ConnectorHub.
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

DEFAULT_API_BASE = "https://api.nasa.gov"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    if "nasa" == "braze":
        rest_endpoint = str(cred.get("restEndpoint") or cred.get("baseUrl") or base).strip().rstrip("/")
        if not rest_endpoint.startswith("http://") and not rest_endpoint.startswith("https://"):
            rest_endpoint = f"https://{rest_endpoint}"
        return rest_endpoint
    if "nasa" == "getresponse":
        max_url = str(cred.get("maxApiBaseUrl") or base).strip().rstrip("/")
        return max_url

    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "siteId"]:
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

    auth_mode = "nasa_query"
    if auth_mode == "bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "jotform":
        if token:
            headers["APIKEY"] = token
    elif auth_mode == "getresponse":
        if token:
            headers["X-Auth-Token"] = f"api-key {token}"
            domain = str(cred.get("domain") or "").strip()
            if domain:
                headers["X-Domain"] = domain
    elif auth_mode == "tiktok":
        if token:
            headers["Access-Token"] = token
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "nasa_query":
        pass

    return headers

ROUTES: Dict[str, List[Any]] = {
    "get_apod": [
        "GET",
        "/planetary/apod",
        [],
        [
            "date",
            "concept_tags",
            "hd",
            "count",
            "start_date",
            "end_date",
            "thumbs"
        ]
    ],
    "browse_neo": [
        "GET",
        "/neo/rest/v1/neo/browse",
        [],
        [
            "page",
            "size"
        ]
    ],
    "get_neo_lookup": [
        "GET",
        "/neo/rest/v1/neo/{asteroidId}",
        [
            "asteroidId"
        ],
        []
    ],
    "search_near_earth_objects": [
        "GET",
        "/neo/rest/v1/feed",
        [],
        [
            "start_date",
            "end_date",
            "detailed"
        ]
    ],
    "get_donki_cme": [
        "GET",
        "/DONKI/CME",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_cme_analysis": [
        "GET",
        "/DONKI/CMEAnalysis",
        [],
        [
            "startDate",
            "endDate",
            "mostAccurateOnly",
            "speed",
            "halfAngle",
            "catalog"
        ]
    ],
    "get_donki_gst": [
        "GET",
        "/DONKI/GST",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_ips": [
        "GET",
        "/DONKI/IPS",
        [],
        [
            "startDate",
            "endDate",
            "location",
            "catalog"
        ]
    ],
    "get_donki_solar_flares": [
        "GET",
        "/DONKI/FLR",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_sep": [
        "GET",
        "/DONKI/SEP",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_mpc": [
        "GET",
        "/DONKI/MPC",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_rbe": [
        "GET",
        "/DONKI/RBE",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_hss": [
        "GET",
        "/DONKI/HSS",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_wsa_enlil": [
        "GET",
        "/DONKI/WSAEnlilSimulations",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_donki_notifications": [
        "GET",
        "/DONKI/notifications",
        [],
        [
            "startDate",
            "endDate",
            "type"
        ]
    ],
    "get_epic_natural": [
        "GET",
        "/EPIC/api/natural",
        [],
        []
    ],
    "get_epic_natural_date": [
        "GET",
        "/EPIC/api/natural/date/{date}",
        [
            "date"
        ],
        []
    ],
    "list_epic_natural_dates": [
        "GET",
        "/EPIC/api/natural/all",
        [],
        []
    ],
    "get_epic_enhanced": [
        "GET",
        "/EPIC/api/enhanced",
        [],
        []
    ],
    "get_epic_enhanced_date": [
        "GET",
        "/EPIC/api/enhanced/date/{date}",
        [
            "date"
        ],
        []
    ],
    "list_epic_enhanced_dates": [
        "GET",
        "/EPIC/api/enhanced/all",
        [],
        []
    ],
    "get_epic_aerosol": [
        "GET",
        "/EPIC/api/aerosol",
        [],
        []
    ],
    "get_epic_aerosol_date": [
        "GET",
        "/EPIC/api/aerosol/date/{date}",
        [
            "date"
        ],
        []
    ],
    "list_epic_aerosol_dates": [
        "GET",
        "/EPIC/api/aerosol/all",
        [],
        []
    ],
    "get_epic_cloud": [
        "GET",
        "/EPIC/api/cloud",
        [],
        []
    ],
    "get_epic_cloud_date": [
        "GET",
        "/EPIC/api/cloud/date/{date}",
        [
            "date"
        ],
        []
    ],
    "list_epic_cloud_dates": [
        "GET",
        "/EPIC/api/cloud/all",
        [],
        []
    ]
}

class NasaDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Utilities & Tools"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        base_url = _resolve_base_url(cred)
        headers = _build_headers(cred)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{base_url}{path}" if not path.startswith("http") else path
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        if "nasa_query" == "nasa_query" and token:
            params["api_key"] = token

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("error") or err_json.get("error_description") or err_msg
            except Exception:
                pass
            raise ValueError(f"NASA API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class NasaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="nasa",
            display_name="NASA",
            category="Utilities & Tools",
            auth_types=['api_key'],
            description="NASA Open APIs for Astronomy Picture of the Day, near-Earth objects, space weather DONKI, and EPIC satellite imagery with 27 actions."
        )
        for act in get_provider_actions("nasa"):
            self.register_action(NasaDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token:
            raise ValueError("API key or token is required for NASA.")

        val_url = "https://api.nasa.gov/planetary/apod"
        if "nasa" == "braze":
            rest_endpoint = str(cred.get("restEndpoint") or cred.get("baseUrl") or "https://rest.iad-01.braze.com").strip().rstrip("/")
            if not rest_endpoint.startswith("http://") and not rest_endpoint.startswith("https://"):
                rest_endpoint = f"https://{rest_endpoint}"
            val_url = f"{rest_endpoint}/campaigns/list?page=1"
        elif "nasa" == "hotjar":
            site_id = str(cred.get("siteId") or cred.get("site_id") or "1").strip()
            val_url = f"https://api.hotjar.io/v1/sites/{site_id}/surveys"
        elif "nasa" == "getresponse":
            max_url = str(cred.get("maxApiBaseUrl") or "https://api.getresponse.com/v3").strip().rstrip("/")
            val_url = f"{max_url}/accounts"

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "nasa_query" == "nasa_query" and token:
            req_params["api_key"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"NASA connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid NASA credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"NASA validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": token[:8] + "..." if len(token) > 8 else "verified",
            "display_name": f"NASA Account"
        }

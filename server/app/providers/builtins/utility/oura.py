"""
Oura Provider for ConnectorHub.
Loads and registers 35 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.ouraring.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
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
    elif auth_mode == "token_auth":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode == "unsplash_client_id":
        if token:
            headers["Authorization"] = f"Client-ID {token}"
    elif auth_mode == "amplitude_basic":
        if token:
            secret = str(cred.get("secretKey") or cred.get("apiKeyId") or "X").strip()
            pair = f"{token}:{secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "get_daily_activity": [
        "GET",
        "/daily_activity",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_cardiovascular_age": [
        "GET",
        "/daily_cardiovascular_age",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_readiness": [
        "GET",
        "/daily_readiness",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_resilience": [
        "GET",
        "/daily_resilience",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_sleep": [
        "GET",
        "/daily_sleep",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_spo2": [
        "GET",
        "/daily_spo2",
        [],
        [
            "documentId"
        ]
    ],
    "get_daily_stress": [
        "GET",
        "/daily_stress",
        [],
        [
            "documentId"
        ]
    ],
    "get_enhanced_tag": [
        "GET",
        "/enhanced_tag",
        [],
        [
            "documentId"
        ]
    ],
    "get_personal_info": [
        "GET",
        "{ouraUserCollectionPath}/{collection}",
        [
            "ouraUserCollectionPath",
            "collection"
        ],
        []
    ],
    "get_rest_mode_period": [
        "GET",
        "/rest_mode_period",
        [],
        [
            "documentId"
        ]
    ],
    "get_ring_configuration": [
        "GET",
        "/ring_configuration",
        [],
        [
            "documentId"
        ]
    ],
    "get_session": [
        "GET",
        "/session",
        [],
        [
            "documentId"
        ]
    ],
    "get_sleep": [
        "GET",
        "/sleep",
        [],
        [
            "documentId"
        ]
    ],
    "get_sleep_time": [
        "GET",
        "/sleep_time",
        [],
        [
            "documentId"
        ]
    ],
    "get_tag": [
        "GET",
        "/tag",
        [],
        [
            "documentId"
        ]
    ],
    "get_vo2_max": [
        "GET",
        "/vo2_max",
        [],
        [
            "documentId"
        ]
    ],
    "get_workout": [
        "GET",
        "/workout",
        [],
        [
            "documentId"
        ]
    ],
    "list_daily_activity": [
        "GET",
        "/daily_activity",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_cardiovascular_age": [
        "GET",
        "/daily_cardiovascular_age",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_readiness": [
        "GET",
        "/daily_readiness",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_resilience": [
        "GET",
        "/daily_resilience",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_sleep": [
        "GET",
        "/daily_sleep",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_spo2": [
        "GET",
        "/daily_spo2",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_daily_stress": [
        "GET",
        "/daily_stress",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_enhanced_tag": [
        "GET",
        "/enhanced_tag",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_heartrate": [
        "GET",
        "/heartrate",
        [],
        [
            "startDatetime",
            "endDatetime",
            "latest",
            "nextToken",
            "fields"
        ]
    ],
    "list_rest_mode_period": [
        "GET",
        "/rest_mode_period",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_ring_battery_level": [
        "GET",
        "/ring_battery_level",
        [],
        [
            "startDatetime",
            "endDatetime",
            "latest",
            "nextToken",
            "fields"
        ]
    ],
    "list_ring_configuration": [
        "GET",
        "/ring_configuration",
        [],
        [
            "nextToken",
            "fields"
        ]
    ],
    "list_session": [
        "GET",
        "/session",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_sleep": [
        "GET",
        "/sleep",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_sleep_time": [
        "GET",
        "/sleep_time",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_tag": [
        "GET",
        "/tag",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_vo2_max": [
        "GET",
        "/vo2_max",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ],
    "list_workout": [
        "GET",
        "/workout",
        [],
        [
            "startDate",
            "endDate",
            "nextToken",
            "fields"
        ]
    ]
}

class OuraDynamicAction(Action):
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

        if resp.status_code >= 400:
            raise ValueError(f"Oura API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class OuraProvider(Provider):
    def __init__(self):
        super().__init__(
            service="oura",
            display_name="Oura",
            category="Health & Fitness",
            auth_types=["oauth2"],
            description="Oura Ring health, sleep, readiness, and resilience platform with 35 actions."
        )
        for act in get_provider_actions("oura"):
            self.register_action(OuraDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.ouraring.com/v2/usercollection/personal_info"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

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
            raise ValueError(f"Oura connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Oura credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Oura validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "oura" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Oura credentials: {body.get('errmsg') or resp.text}")
                elif "oura" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid Oura credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Oura Account"
        }

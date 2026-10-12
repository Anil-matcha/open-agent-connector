"""
Chargebee Provider for ConnectorHub.
Loads and registers 9 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://{site}.chargebee.com/api/v2"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
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

    auth_mode = "chargebee_basic"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode in ["recurly_basic", "chargebee_basic"]:
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "voiceflow_key":
        if token:
            headers["Authorization"] = token
    elif auth_mode in ["alpha_vantage", "fmp"]:
        if token:
            headers["apikey"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_customer": [
        "POST",
        "/customers",
        [],
        []
    ],
    "get_customer": [
        "POST",
        "/customers",
        [],
        [
            "customerId"
        ]
    ],
    "get_invoice": [
        "GET",
        "/invoice",
        [],
        [
            "invoiceId"
        ]
    ],
    "get_item_price": [
        "GET",
        "/item_price",
        [],
        [
            "itemPriceId"
        ]
    ],
    "get_subscription": [
        "GET",
        "/subscription",
        [],
        [
            "subscriptionId"
        ]
    ],
    "list_customers": [
        "POST",
        "/customers",
        [],
        [
            "limit",
            "offset",
            "id",
            "customerId",
            "subscriptionId",
            "email",
            "status",
            "itemId",
            "sortBy",
            "sortOrder"
        ]
    ],
    "list_invoices": [
        "GET",
        "/invoices",
        [],
        [
            "limit",
            "offset",
            "id",
            "customerId",
            "subscriptionId",
            "email",
            "status",
            "itemId",
            "sortBy",
            "sortOrder"
        ]
    ],
    "list_item_prices": [
        "GET",
        "/item_prices",
        [],
        [
            "limit",
            "offset",
            "id",
            "customerId",
            "subscriptionId",
            "email",
            "status",
            "itemId",
            "sortBy",
            "sortOrder"
        ]
    ],
    "list_subscriptions": [
        "GET",
        "/subscriptions",
        [],
        [
            "limit",
            "offset",
            "id",
            "customerId",
            "subscriptionId",
            "email",
            "status",
            "itemId",
            "sortBy",
            "sortOrder"
        ]
    ]
}

class ChargebeeDynamicAction(Action):
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

        token = _extract_token(cred)
        if "chargebee_basic" in ["alpha_vantage", "fmp"] and token:
            req_params["apikey"] = token

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
            raise ValueError(f"Chargebee API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ChargebeeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="chargebee",
            display_name="Chargebee",
            category="Finance & Accounting",
            auth_types=["api_key"],
            description="Chargebee subscription billing and revenue management platform with 9 actions."
        )
        for act in get_provider_actions("chargebee"):
            self.register_action(ChargebeeDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://{site}.chargebee.com/api/v2/customers?limit=1"
        for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        token = _extract_token(cred)
        if "chargebee_basic" in ["alpha_vantage", "fmp"] and token:
            req_params["apikey"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"Chargebee connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Chargebee credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Chargebee validation failed: {resp.status_code} {resp.text}")

        # For Alpha Vantage, invalid API key returns 200 with 'Information' or 'Error Message'
        if "chargebee_basic" == "alpha_vantage":
            try:
                j = resp.json()
                if "Error Message" in j or "Information" in j:
                    raise ValueError(f"Invalid Alpha Vantage credentials: {resp.text}")
            except Exception as e:
                if "Invalid Alpha Vantage" in str(e):
                    raise

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Chargebee Account"
        }

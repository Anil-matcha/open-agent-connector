"""
Shopee Provider for ConnectorHub.
Loads and registers 24 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://partner.shopeemobile.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "shopee" in ["shopify_admin", "shopify_storefront"]:
        shop = str(cred.get("shopDomain") or cred.get("shop") or "default.myshopify.com").strip()
        shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
        return base.replace("{shopDomain}", shop).rstrip("/")

    if "shopee" == "shopify_partner":
        org_id = str(cred.get("organizationId") or cred.get("orgId") or "1").strip()
        return base.replace("{organizationId}", org_id).rstrip("/")

    if "shopee" == "sendbird":
        app_id = str(cred.get("applicationId") or cred.get("appId") or "default").strip()
        return base.replace("{applicationId}", app_id).rstrip("/")

    if "shopee" == "listmonk":
        val = str(cred.get("baseUrl") or "https://listmonk.example.com").strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
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
    elif auth_mode == "shopify_admin":
        if token:
            headers["X-Shopify-Access-Token"] = token
    elif auth_mode == "shopify_storefront":
        if token:
            headers["X-Shopify-Storefront-Access-Token"] = token
    elif auth_mode == "coingecko":
        if token:
            is_pro = str(cred.get("plan") or "").lower() == "pro"
            header_name = "x-cg-pro-api-key" if is_pro else "x-cg-demo-api-key"
            headers[header_name] = token
    elif auth_mode == "sendbird":
        if token:
            headers["Api-Token"] = token
    elif auth_mode == "listmonk":
        user = str(cred.get("apiUser") or cred.get("username") or "").strip()
        if user and token:
            pair = f"{user}:{token}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mailgun":
        if token:
            pair = f"api:{token}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "flexmail":
        acc_id = str(cred.get("accountId") or "").strip()
        pat = token or str(cred.get("personalAccessToken") or "").strip()
        if acc_id and pat:
            pair = f"{acc_id}:{pat}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "crisp":
        token_id = str(cred.get("tokenIdentifier") or "").strip()
        token_key = token or str(cred.get("tokenKey") or "").strip()
        if token_id and token_key:
            pair = f"{token_id}:{token_key}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
        if cred.get("tokenTier"):
            headers["X-Crisp-Tier"] = str(cred["tokenTier"]).strip()
    elif auth_mode == "vonage":
        api_key = str(cred.get("apiKey") or token or "").strip()
        api_secret = str(cred.get("apiSecret") or "").strip()
        if api_key and api_secret:
            pair = f"{api_key}:{api_secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "onesignal":
        if token:
            headers["Authorization"] = f"Key {token}"

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_global_item": [
        "POST",
        "/api/v2/global_product/add_global_item",
        [],
        [
            "merchantId",
            "categoryId",
            "name",
            "description",
            "sku",
            "imageIds",
            "originalPrice",
            "stock",
            "weight",
            "packageLength",
            "packageWidth",
            "packageHeight",
            "daysToShip",
            "condition",
            "brandId",
            "brandName",
            "attributes",
            "sellerStock"
        ]
    ],
    "get_global_attribute_tree": [
        "GET",
        "/api/v2/global_product/get_attribute_tree",
        [],
        [
            "merchantId",
            "categoryIds",
            "language"
        ]
    ],
    "get_global_items": [
        "GET",
        "/api/v2/global_product/get_global_item_info",
        [],
        [
            "merchantId",
            "globalItemIds"
        ]
    ],
    "get_item_models": [
        "GET",
        "/api/v2/product/get_model_list",
        [],
        [
            "shopId",
            "itemId"
        ]
    ],
    "get_merchant_info": [
        "GET",
        "/api/v2/merchant/get_merchant_info",
        [],
        [
            "merchantId"
        ]
    ],
    "get_order_escrow": [
        "GET",
        "/api/v2/payment/get_escrow_detail",
        [],
        [
            "shopId",
            "orderSerialNumber"
        ]
    ],
    "get_orders": [
        "GET",
        "/api/v2/order/get_order_detail",
        [],
        [
            "shopId",
            "orderSerialNumbers",
            "optionalFields"
        ]
    ],
    "get_return": [
        "GET",
        "/api/v2/returns/get_return_detail",
        [],
        [
            "shopId",
            "returnSerialNumber"
        ]
    ],
    "get_shipping_parameters": [
        "GET",
        "/api/v2/logistics/get_shipping_parameter",
        [],
        [
            "shopId",
            "orderSerialNumber",
            "packageNumber"
        ]
    ],
    "get_shop_info": [
        "GET",
        "/api/v2/shop/get_shop_info",
        [],
        [
            "shopId"
        ]
    ],
    "get_shop_items": [
        "GET",
        "/api/v2/product/get_item_base_info",
        [],
        [
            "shopId",
            "itemIds",
            "includeTaxInfo",
            "includeComplaintPolicy"
        ]
    ],
    "get_tracking_info": [
        "POST",
        "/api/v2/logistics/get_tracking_info",
        [],
        [
            "shopId",
            "orderSerialNumber",
            "packageNumber"
        ]
    ],
    "get_tracking_number": [
        "POST",
        "/api/v2/logistics/get_tracking_number",
        [],
        [
            "shopId",
            "orderSerialNumber",
            "packageNumber",
            "optionalFields"
        ]
    ],
    "list_global_brands": [
        "GET",
        "/api/v2/global_product/get_brand_list",
        [],
        [
            "merchantId",
            "categoryId",
            "offset",
            "pageSize",
            "status"
        ]
    ],
    "list_global_categories": [
        "GET",
        "/api/v2/global_product/get_category",
        [],
        [
            "merchantId",
            "language"
        ]
    ],
    "list_global_items": [
        "GET",
        "/api/v2/global_product/get_global_item_list",
        [],
        [
            "merchantId",
            "cursor",
            "pageSize",
            "updatedFrom",
            "updatedTo"
        ]
    ],
    "list_merchant_shops": [
        "GET",
        "/api/v2/merchant/get_shop_list_by_merchant",
        [],
        [
            "merchantId",
            "page",
            "pageSize"
        ]
    ],
    "list_orders": [
        "GET",
        "/api/v2/order/get_order_list",
        [],
        [
            "shopId",
            "timeRangeField",
            "timeFrom",
            "timeTo",
            "pageSize",
            "cursor",
            "orderStatus"
        ]
    ],
    "list_returns": [
        "GET",
        "/api/v2/returns/get_return_list",
        [],
        [
            "shopId",
            "page",
            "pageSize",
            "createdFrom",
            "createdTo",
            "updatedFrom",
            "updatedTo",
            "status",
            "negotiationStatus",
            "sellerProofStatus",
            "sellerCompensationStatus"
        ]
    ],
    "list_shop_items": [
        "GET",
        "/api/v2/product/get_item_list",
        [],
        [
            "shopId",
            "offset",
            "pageSize",
            "statuses",
            "updatedFrom",
            "updatedTo"
        ]
    ],
    "ship_order": [
        "GET",
        "/api/v2/logistics/ship_order",
        [],
        [
            "shopId",
            "orderSerialNumber",
            "packageNumber",
            "pickup",
            "dropoff",
            "nonIntegrated"
        ]
    ],
    "update_item_prices": [
        "PATCH",
        "/api/v2/product/update_price",
        [],
        [
            "shopId",
            "itemId",
            "prices"
        ]
    ],
    "update_item_stocks": [
        "PATCH",
        "/api/v2/product/update_stock",
        [],
        [
            "shopId",
            "itemId",
            "stocks"
        ]
    ],
    "upload_product_image": [
        "POST",
        "/api/v2/global_product/add_global_item",
        [],
        [
            "shopId",
            "imageUrl",
            "scene",
            "ratio"
        ]
    ]
}

class ShopeeDynamicAction(Action):
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
                path = path.replace(" + p_name + ", urllib.parse.quote(str(val), safe=""))
            else:
                path = path.replace(" + p_name + ", "")

        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        assert_public_url(full_url)

        headers = _build_headers(cred)
        req_params = {}
        req_json = None

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
            raise ValueError(f"Shopee API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class ShopeeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="shopee",
            display_name="Shopee",
            category="E-Commerce & Retail",
            auth_types=['oauth2'],
            description="Shopee Open Platform with 24 actions for merchant orders, global items, logistics, and returns."
        )
        for act in get_provider_actions("shopee"):
            self.register_action(ShopeeDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)

        if "shopee" in ["shopify_admin", "shopify_storefront"]:
            shop = str(cred.get("shopDomain") or cred.get("shop") or "").strip()
            if not shop:
                raise ValueError("Shopify shopDomain is required in credentials.")
            shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info".replace("{shopDomain}", shop)
        elif "shopee" == "shopify_partner":
            org_id = str(cred.get("organizationId") or cred.get("orgId") or "").strip()
            if not org_id:
                raise ValueError("Shopify Partner organizationId is required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info".replace("{organizationId}", org_id)
        elif "shopee" == "sendbird":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Sendbird applicationId is required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info".replace("{applicationId}", app_id)
        elif "shopee" == "listmonk":
            base_url = str(cred.get("baseUrl") or "").strip()
            user = str(cred.get("apiUser") or cred.get("username") or "").strip()
            if not base_url:
                raise ValueError("Listmonk baseUrl is required in credentials.")
            if not user:
                raise ValueError("Listmonk apiUser is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/subscribers?per_page=1"
        elif "shopee" == "flexmail":
            acc_id = str(cred.get("accountId") or "").strip()
            pat = token or str(cred.get("personalAccessToken") or "").strip()
            if not acc_id or not pat:
                raise ValueError("Flexmail accountId and personalAccessToken are required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info"
        elif "shopee" == "crisp":
            token_id = str(cred.get("tokenIdentifier") or "").strip()
            token_key = token or str(cred.get("tokenKey") or "").strip()
            if not token_id or not token_key:
                raise ValueError("Crisp tokenIdentifier and tokenKey are required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info"
        elif "shopee" == "vonage":
            api_key = str(cred.get("apiKey") or token or "").strip()
            api_secret = str(cred.get("apiSecret") or "").strip()
            if not api_key or not api_secret:
                raise ValueError("Vonage apiKey and apiSecret are required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info"
        elif "shopee" == "onesignal_rest_api":
            app_id = str(cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("OneSignal appId is required in credentials.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info"
        else:
            if not token:
                raise ValueError("API token or key is required for Shopee.")
            val_url = "https://partner.shopeemobile.com/api/v2/shop/get_shop_info"
            for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
                if "{" + key + "}" in val_url:
                    val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))
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
            raise ValueError(f"Shopee connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Shopee credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Shopee validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "shopee" == "shopee" and body.get("error"):
                    raise ValueError(f"Invalid Shopee credentials: {body.get('message') or resp.text}")
                elif "shopee" == "coingecko" and body.get("error"):
                    raise ValueError(f"Invalid Shopee credentials: {body.get('error')}")
                elif "shopee" == "sendbird" and body.get("error") is True:
                    raise ValueError(f"Invalid Shopee credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Shopee Account"
        }

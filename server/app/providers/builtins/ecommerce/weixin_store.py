"""
WeChat Store Provider for ConnectorHub.
Loads and registers 32 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.weixin.qq.com"

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
    "accept_aftersale": [
        "POST",
        "/channels/ec/aftersale/acceptapply",
        [],
        [
            "afterSaleOrderId",
            "addressId",
            "acceptType"
        ]
    ],
    "add_product": [
        "POST",
        "/channels/ec/product/add",
        [],
        [
            "title",
            "headImgs",
            "catsV2",
            "deliverMethod",
            "deliverAcctType",
            "extraService",
            "skus",
            "outProductId",
            "descInfo",
            "attrs",
            "brandId",
            "expressInfo",
            "listing",
            "aftersaleDesc",
            "limitedInfo",
            "sizeChart"
        ]
    ],
    "apply_category": [
        "POST",
        "/channels/ec/category/add",
        [],
        [
            "categoryInfo"
        ]
    ],
    "delete_product": [
        "POST",
        "/channels/ec/product/delete",
        [],
        [
            "productId"
        ]
    ],
    "delisting_product": [
        "POST",
        "/channels/ec/product/delisting",
        [],
        [
            "productId"
        ]
    ],
    "get_address": [
        "POST",
        "/channels/ec/merchant/address/get",
        [],
        [
            "addressId"
        ]
    ],
    "get_aftersale_order": [
        "POST",
        "/channels/ec/aftersale/getaftersaleorder",
        [],
        [
            "afterSaleOrderId"
        ]
    ],
    "get_category": [
        "POST",
        "/shop/ec/category/detail",
        [],
        [
            "catId"
        ]
    ],
    "get_category_application": [
        "POST",
        "/shop/ec/category/getbizcatflowdetail",
        [],
        [
            "auditId"
        ]
    ],
    "get_category_product_rule": [
        "POST",
        "/shop/ec/category/getcategoryproductrule",
        [],
        [
            "catId",
            "releaseMode",
            "brandId"
        ]
    ],
    "get_freight_template": [
        "POST",
        "/channels/ec/merchant/getfreighttemplatedetail",
        [],
        [
            "templateId"
        ]
    ],
    "get_order": [
        "POST",
        "/channels/ec/order/get",
        [],
        [
            "orderId"
        ]
    ],
    "get_product": [
        "POST",
        "/channels/ec/product/get",
        [],
        [
            "productId",
            "dataType"
        ]
    ],
    "get_shop_info": [
        "GET",
        "/channels/ec/basics/info/get",
        [],
        []
    ],
    "list_addresses": [
        "POST",
        "/channels/ec/merchant/address/list",
        [],
        [
            "offset",
            "limit"
        ]
    ],
    "list_aftersale_orders": [
        "POST",
        "/channels/ec/aftersale/getaftersalelist",
        [],
        [
            "createTimeStart",
            "createTimeEnd",
            "updateTimeStart",
            "updateTimeEnd",
            "nextKey"
        ]
    ],
    "list_categories": [
        "POST",
        "/shop/ec/category/all",
        [],
        []
    ],
    "list_category_permissions": [
        "POST",
        "/shop/ec/category/get_category_relation_list",
        [],
        [
            "status"
        ]
    ],
    "list_delivery_companies": [
        "POST",
        "/channels/ec/order/deliverycompanylist/new/get",
        [],
        [
            "ewaybillOnly"
        ]
    ],
    "list_freight_templates": [
        "POST",
        "/channels/ec/merchant/getfreighttemplatelist",
        [],
        [
            "offset",
            "limit"
        ]
    ],
    "list_orders": [
        "POST",
        "/channels/ec/order/list/get",
        [],
        [
            "createTimeStart",
            "createTimeEnd",
            "updateTimeStart",
            "updateTimeEnd",
            "status",
            "openid",
            "pageSize",
            "nextKey"
        ]
    ],
    "list_products": [
        "POST",
        "/channels/ec/product/list/get",
        [],
        [
            "status",
            "pageSize",
            "nextKey"
        ]
    ],
    "list_valid_brands": [
        "POST",
        "/channels/ec/brand/valid/list/get",
        [],
        [
            "pageSize",
            "nextKey"
        ]
    ],
    "listing_product": [
        "POST",
        "/channels/ec/product/listing",
        [],
        [
            "productId"
        ]
    ],
    "precheck_product_category": [
        "POST",
        "/channels/ec/product/categoryprecheck",
        [],
        [
            "catId"
        ]
    ],
    "reject_aftersale": [
        "POST",
        "/channels/ec/aftersale/rejectapply",
        [],
        [
            "afterSaleOrderId",
            "rejectReasonType",
            "rejectReason"
        ]
    ],
    "send_delivery": [
        "POST",
        "/channels/ec/order/delivery/send",
        [],
        [
            "orderId",
            "deliveries"
        ]
    ],
    "update_order_merchant_notes": [
        "POST",
        "/channels/ec/order/merchantnotes/update",
        [],
        [
            "orderId",
            "merchantNotes",
            "tagColor"
        ]
    ],
    "update_product": [
        "POST",
        "/channels/ec/product/update",
        [],
        [
            "productId",
            "title",
            "headImgs",
            "catsV2",
            "deliverMethod",
            "deliverAcctType",
            "extraService",
            "skus",
            "outProductId",
            "descInfo",
            "attrs",
            "brandId",
            "expressInfo",
            "listing",
            "aftersaleDesc",
            "limitedInfo",
            "sizeChart"
        ]
    ],
    "update_product_stock": [
        "POST",
        "/channels/ec/product/stock/update",
        [],
        [
            "productId",
            "skus"
        ]
    ],
    "upload_image": [
        "POST",
        "/shop/ec/basics/img/upload",
        [],
        [
            "imageUrl",
            "file",
            "width",
            "height"
        ]
    ],
    "upload_qualification_image": [
        "POST",
        "/shop/ec/basics/qualification/upload",
        [],
        [
            "file"
        ]
    ]
}

class WeixinStoreDynamicAction(Action):
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
            raise ValueError(f"WeChat Store API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class WeixinStoreProvider(Provider):
    def __init__(self):
        super().__init__(
            service="weixin_store",
            display_name="WeChat Store",
            category="E-Commerce & Retail",
            auth_types=["api_key"],
            description="WeChat Video Account Store (Channels EC) with 32 actions for product management, orders, categories, and aftersale."
        )
        for act in get_provider_actions("weixin_store"):
            self.register_action(WeixinStoreDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.weixin.qq.com/channels/ec/basics/address/get?access_token={{token}}"
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
            raise ValueError(f"WeChat Store connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid WeChat Store credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"WeChat Store validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "weixin_store" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid WeChat Store credentials: {body.get('errmsg') or resp.text}")
                elif "weixin_store" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid WeChat Store credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"WeChat Store Account"
        }

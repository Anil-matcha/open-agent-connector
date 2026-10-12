"""
Xiaohongshu Store Provider for ConnectorHub.
Loads and registers 36 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://ark.xiaohongshu.com"

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
    "adjust_sku_stock": [
        "GET",
        "/adjust_sku_stock",
        [],
        [
            "skuId",
            "qty"
        ]
    ],
    "audit_after_sale": [
        "GET",
        "/audit_after_sale",
        [],
        [
            "returnsId",
            "action",
            "reason",
            "description",
            "message",
            "sellerAddressRecordId",
            "droneSnCodes"
        ]
    ],
    "confirm_after_sale_receive": [
        "GET",
        "/confirm_after_sale_receive",
        [],
        [
            "returnsId",
            "action",
            "reason",
            "description",
            "droneSnCodes"
        ]
    ],
    "create_item": [
        "POST",
        "/item",
        [],
        [
            "name",
            "categoryId",
            "shippingTemplateId",
            "shippingGrossWeight",
            "images",
            "createSkuList",
            "brandId",
            "attributes",
            "variantIds",
            "articleNo",
            "description",
            "itemShortTitle",
            "deliveryMode",
            "freeReturn",
            "videos",
            "imageDescriptions"
        ]
    ],
    "deliver_order": [
        "GET",
        "/deliver_order",
        [],
        [
            "orderId",
            "expressNo",
            "expressCompanyCode",
            "expressCompanyName",
            "deliveringTime",
            "unpack",
            "skuIdList",
            "returnAddressId",
            "skuIdentifyCodeInfo"
        ]
    ],
    "get_after_sale": [
        "GET",
        "/after_sale",
        [],
        [
            "returnsId",
            "needNegotiateRecord"
        ]
    ],
    "get_category_attributes": [
        "GET",
        "/category_attributes",
        [],
        [
            "categoryId"
        ]
    ],
    "get_item": [
        "GET",
        "/item",
        [],
        [
            "itemId",
            "pageNo",
            "pageSize"
        ]
    ],
    "get_order": [
        "GET",
        "/order",
        [],
        [
            "orderId"
        ]
    ],
    "get_order_declare_info": [
        "GET",
        "/order_declare_info",
        [],
        [
            "orderId"
        ]
    ],
    "get_order_receiver_info": [
        "GET",
        "/order_receiver_info",
        [],
        [
            "receiverQueries",
            "isReturn"
        ]
    ],
    "get_order_tracking": [
        "POST",
        "/order_tracking",
        [],
        [
            "orderId"
        ]
    ],
    "get_sku_stock": [
        "GET",
        "/sku_stock",
        [],
        [
            "skuId"
        ]
    ],
    "list_address_records": [
        "POST",
        "/address_records",
        [],
        [
            "pageIndex",
            "pageSize"
        ]
    ],
    "list_after_sale_reject_reasons": [
        "GET",
        "/after_sale_reject_reasons",
        [],
        [
            "returnsId",
            "rejectReasonType"
        ]
    ],
    "list_after_sales": [
        "GET",
        "/after_sales",
        [],
        [
            "orderId",
            "timeType",
            "startTime",
            "endTime",
            "statuses",
            "returnTypes",
            "pageNo",
            "pageSize"
        ]
    ],
    "list_carriage_templates": [
        "GET",
        "/carriage_templates",
        [],
        [
            "pageIndex",
            "pageSize"
        ]
    ],
    "list_categories": [
        "GET",
        "/categories",
        [],
        [
            "categoryId"
        ]
    ],
    "list_express_companies": [
        "GET",
        "/express_companies",
        [],
        []
    ],
    "list_item_skus": [
        "GET",
        "/item_skus",
        [],
        [
            "id",
            "createTimeFrom",
            "createTimeTo",
            "updateTimeFrom",
            "updateTimeTo",
            "buyable",
            "stockGte",
            "stockLte",
            "barcode",
            "scSkucode",
            "singlePackOnly",
            "lastId",
            "isChannel",
            "pageNo",
            "pageSize"
        ]
    ],
    "list_items": [
        "GET",
        "/items",
        [],
        [
            "id",
            "createTimeFrom",
            "createTimeTo",
            "updateTimeFrom",
            "updateTimeTo",
            "buyable",
            "stockGte",
            "stockLte",
            "barcode",
            "skucode",
            "freeze",
            "singlePackOnly",
            "lastId",
            "isChannel",
            "pageNo",
            "pageSize"
        ]
    ],
    "list_logistics_plans": [
        "GET",
        "/logistics_plans",
        [],
        []
    ],
    "list_materials": [
        "GET",
        "/materials",
        [],
        [
            "materialId",
            "name",
            "type",
            "status",
            "createTimeFrom",
            "createTimeTo",
            "ascByCreateTime",
            "pageNo",
            "pageSize"
        ]
    ],
    "list_orders": [
        "GET",
        "/orders",
        [],
        [
            "timeType",
            "startTime",
            "endTime",
            "orderType",
            "orderStatus",
            "pageNo",
            "pageSize"
        ]
    ],
    "list_supported_ports": [
        "GET",
        "/supported_ports",
        [],
        []
    ],
    "modify_order_express": [
        "PATCH",
        "/modify_order_express",
        [],
        [
            "orderId",
            "expressNo",
            "expressCompanyCode",
            "expressCompanyName",
            "deliveryOrderIndex",
            "oldExpressNo",
            "expressUrlProofList"
        ]
    ],
    "modify_order_remark": [
        "PATCH",
        "/modify_order_remark",
        [],
        [
            "orderId",
            "sellerMarkNote",
            "operator",
            "sellerMarkPriority"
        ]
    ],
    "refresh_token": [
        "GET",
        "/refresh_token",
        [],
        []
    ],
    "resend_payment_record": [
        "POST",
        "/resend_payment_record",
        [],
        [
            "orderId",
            "customsType"
        ]
    ],
    "search_brands": [
        "GET",
        "/search_brands",
        [],
        [
            "categoryId",
            "keyword",
            "pageNo",
            "pageSize"
        ]
    ],
    "search_items": [
        "GET",
        "/search_items",
        [],
        [
            "keyword",
            "keywords",
            "buyable",
            "createTimeFrom",
            "createTimeTo",
            "lastId",
            "pageNo",
            "pageSize"
        ]
    ],
    "set_sku_availability": [
        "POST",
        "/set_sku_availability",
        [],
        [
            "skuId",
            "available"
        ]
    ],
    "ship_after_sale_exchange": [
        "GET",
        "/ship_after_sale_exchange",
        [],
        [
            "returnsId",
            "expressCompanyCode",
            "expressNo"
        ]
    ],
    "sync_sku_stock": [
        "GET",
        "/sync_sku_stock",
        [],
        [
            "skuId",
            "qty"
        ]
    ],
    "update_item": [
        "PATCH",
        "/item",
        [],
        [
            "itemId",
            "name",
            "categoryId",
            "shippingTemplateId",
            "shippingGrossWeight",
            "images",
            "updateSkuList",
            "createSkuList",
            "deleteSkuIdList",
            "brandId",
            "attributes",
            "variantIds",
            "articleNo",
            "description",
            "itemShortTitle",
            "deliveryMode",
            "freeReturn",
            "videos",
            "imageDescriptions"
        ]
    ],
    "upload_material": [
        "POST",
        "/upload_material",
        [],
        [
            "name",
            "type",
            "contentBase64"
        ]
    ]
}

class XiaohongshuStoreDynamicAction(Action):
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
            raise ValueError(f"Xiaohongshu Store API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class XiaohongshuStoreProvider(Provider):
    def __init__(self):
        super().__init__(
            service="xiaohongshu_store",
            display_name="Xiaohongshu Store",
            category="E-Commerce & Retail",
            auth_types=["api_key"],
            description="Xiaohongshu Store OpenAPI with 36 actions for product inventory, order logistics, and after-sale audits."
        )
        for act in get_provider_actions("xiaohongshu_store"):
            self.register_action(XiaohongshuStoreDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://ark.xiaohongshu.com/ark/open_api/v3/common/express/list"
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
            raise ValueError(f"Xiaohongshu Store connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Xiaohongshu Store credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Xiaohongshu Store validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "xiaohongshu_store" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Xiaohongshu Store credentials: {body.get('errmsg') or resp.text}")
                elif "xiaohongshu_store" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid Xiaohongshu Store credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Xiaohongshu Store Account"
        }

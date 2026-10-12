"""
WooCommerce Provider for ConnectorHub.
Loads and registers 26 actions with exact route definitions and parameters.
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

def _extract_creds(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    store_url = cred.get("storeUrl") or cred.get("store_url") or cred.get("url") or ""
    consumer_key = cred.get("consumerKey") or cred.get("consumer_key") or cred.get("key") or ""
    consumer_secret = cred.get("consumerSecret") or cred.get("consumer_secret") or cred.get("secret") or ""

    if not store_url or not consumer_key or not consumer_secret:
        raise ValueError("WooCommerce requires storeUrl, consumerKey, and consumerSecret.")

    clean_url = str(store_url).strip().rstrip("/")
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = f"https://{clean_url}"

    return {
        "store_url": clean_url,
        "consumer_key": str(consumer_key).strip(),
        "consumer_secret": str(consumer_secret).strip()
    }

def _headers(consumer_key: str, consumer_secret: str) -> Dict[str, str]:
    auth_pair = f"{consumer_key}:{consumer_secret}"
    b64_auth = base64.b64encode(auth_pair.encode()).decode()
    return {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "add_order_note": [
        "POST",
        "/orders/{orderId}/notes",
        [
            "orderId"
        ],
        []
    ],
    "create_coupon": [
        "POST",
        "/coupons",
        [],
        []
    ],
    "create_order": [
        "POST",
        "/orders",
        [],
        []
    ],
    "create_product": [
        "POST",
        "/products",
        [],
        []
    ],
    "create_product_variation": [
        "POST",
        "/products/{productId}/variations",
        [
            "productId"
        ],
        []
    ],
    "get_coupon": [
        "GET",
        "/coupons/{couponId}",
        [
            "couponId"
        ],
        []
    ],
    "get_customer": [
        "GET",
        "/customers/{customerId}",
        [
            "customerId"
        ],
        []
    ],
    "get_order": [
        "GET",
        "/orders/{orderId}",
        [
            "orderId"
        ],
        []
    ],
    "get_product": [
        "GET",
        "/products/{productId}",
        [
            "productId"
        ],
        []
    ],
    "get_product_variation": [
        "GET",
        "/products/{productId}/variations/{variationId}",
        [
            "productId",
            "variationId"
        ],
        []
    ],
    "list_coupons": [
        "GET",
        "/coupons",
        [],
        [
            "per_page",
            "page"
        ]
    ],
    "list_customers": [
        "GET",
        "/customers",
        [],
        [
            "per_page",
            "page",
            "email"
        ]
    ],
    "list_order_notes": [
        "GET",
        "/orders/{orderId}/notes",
        [
            "orderId"
        ],
        []
    ],
    "list_orders": [
        "GET",
        "/orders",
        [],
        [
            "per_page",
            "page",
            "status",
            "customer"
        ]
    ],
    "list_product_attribute_terms": [
        "GET",
        "/products/attributes/{attributeId}/terms",
        [
            "attributeId"
        ],
        []
    ],
    "list_product_attributes": [
        "GET",
        "/products/attributes",
        [],
        []
    ],
    "list_product_categories": [
        "GET",
        "/products/categories",
        [],
        [
            "per_page",
            "page"
        ]
    ],
    "list_product_tags": [
        "GET",
        "/products/tags",
        [],
        [
            "per_page",
            "page"
        ]
    ],
    "list_product_variations": [
        "GET",
        "/products/{productId}/variations",
        [
            "productId"
        ],
        []
    ],
    "list_products": [
        "GET",
        "/products",
        [],
        [
            "per_page",
            "page",
            "search",
            "status",
            "category",
            "tag"
        ]
    ],
    "update_coupon": [
        "PUT",
        "/coupons/{couponId}",
        [
            "couponId"
        ],
        []
    ],
    "update_order": [
        "PUT",
        "/orders/{orderId}",
        [
            "orderId"
        ],
        []
    ],
    "update_order_status": [
        "PUT",
        "/orders/{orderId}",
        [
            "orderId"
        ],
        []
    ],
    "update_product": [
        "PUT",
        "/products/{productId}",
        [
            "productId"
        ],
        []
    ],
    "update_product_variation": [
        "PUT",
        "/products/{productId}/variations/{variationId}",
        [
            "productId",
            "variationId"
        ],
        []
    ],
    "upload_media": [
        "POST",
        "/wp/v2/media",
        [],
        []
    ]
}

class WooCommerceDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Ecommerce"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        creds = _extract_creds(credential)
        headers = _headers(creds["consumer_key"], creds["consumer_secret"])

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

        base_url = f"{creds['store_url']}/wp-json/wc/v3"
        if path.startswith("/wp/"):
            base_url = creds["store_url"]

        target_url = f"{base_url}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("code") or resp.text
            raise ValueError(f"WooCommerce API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class WooCommerceProvider(Provider):
    def __init__(self):
        super().__init__(
            service="woocommerce",
            display_name="WooCommerce",
            category="Ecommerce",
            auth_types=["custom_credential"],
            description="WooCommerce store REST API integration suite with 26 actions.",
            auth_configs=[
                {
                    "type": "custom_credential",
                    "fields": [
                        {
                            "key": "storeUrl",
                            "label": "Store URL",
                            "type": "text",
                            "required": True,
                            "placeholder": "https://example.com",
                            "description": "The base URL of your WooCommerce store."
                        },
                        {
                            "key": "consumerKey",
                            "label": "Consumer Key",
                            "type": "text",
                            "required": True,
                            "placeholder": "ck_...",
                            "description": "WooCommerce REST API Consumer Key generated in WooCommerce Settings > Advanced > REST API."
                        },
                        {
                            "key": "consumerSecret",
                            "label": "Consumer Secret",
                            "type": "password",
                            "required": True,
                            "placeholder": "cs_...",
                            "description": "WooCommerce REST API Consumer Secret."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("woocommerce"):
            self.register_action(WooCommerceDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        creds = _extract_creds(credential)
        headers = _headers(creds["consumer_key"], creds["consumer_secret"])

        val_url = f"{creds['store_url']}/wp-json/wc/v3/system_status"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid WooCommerce credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            # Fallback to products
            fallback_url = f"{creds['store_url']}/wp-json/wc/v3/products"
            resp2 = await execute_guarded_request(
                client=client,
                method="GET",
                url=fallback_url,
                headers=headers,
                params={"per_page": 1}
            )
            if resp2.status_code >= 400:
                raise ValueError(f"WooCommerce validation failed: {resp2.status_code} {resp2.text}")

        domain = urllib.parse.urlparse(creds["store_url"]).netloc
        return {
            "account_id": domain or creds["consumer_key"][:8],
            "display_name": f"WooCommerce ({domain})"
        }

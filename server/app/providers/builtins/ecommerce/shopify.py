"""
Shopify Provider for ConnectorHub.
Loads and registers 13 actions from 'actions_catalog.json'.
E-commerce management: Shop details, Blogs, Articles, Authors, Tags, and Pages via Shopify REST Admin API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SHOPIFY_API_VERSION = "2024-01"

SHOPIFY_ENDPOINT_MAP = {
    "shopify.count_articles": ("GET", "/articles/count.json"),
    "shopify.count_blogs": ("GET", "/blogs/count.json"),
    "shopify.count_pages": ("GET", "/pages/count.json"),
    "shopify.get_article": ("GET", "/articles/{article_id}.json"),
    "shopify.get_blog": ("GET", "/blogs/{blog_id}.json"),
    "shopify.get_page": ("GET", "/pages/{page_id}.json"),
    "shopify.get_shop": ("GET", "/shop.json"),
    "shopify.list_article_authors": ("GET", "/articles/authors.json"),
    "shopify.list_article_tags": ("GET", "/articles/tags.json"),
    "shopify.list_articles": ("GET", "/articles.json"),
    "shopify.list_blog_article_tags": ("GET", "/blogs/{blog_id}/articles/tags.json"),
    "shopify.list_blogs": ("GET", "/blogs.json"),
    "shopify.list_pages": ("GET", "/pages.json"),
}

def _resolve_shopify_base(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    domain = cred.get("shopDomain") or cred.get("shop") or cred.get("subdomain") or "test-store"
    domain = str(domain).strip().lower()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("//")[-1]
    if not domain.endswith(".myshopify.com"):
        domain = f"{domain}.myshopify.com"
    return f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}"

def _shopify_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("apiKey") or cred.get("accessToken") or cred.get("token") or ""
    if not str(token).strip():
        raise ValueError("Shopify Admin API access token required. Please connect your Shopify store first.")

    return {
        "X-Shopify-Access-Token": str(token).strip(),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class ShopifyDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "E-Commerce"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = SHOPIFY_ENDPOINT_MAP.get(action_meta["id"], ("GET", "/shop.json"))
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        base_url = _resolve_shopify_base(credential)
        inputs = dict(input_data or {})
        headers = _shopify_headers(credential)

        path = self.endpoint_template
        for var in ["article_id", "blog_id", "page_id", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method == "GET" else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                err_msg = res_data.get("errors") or res_data.get("message") or str(res_data)
            raise ValueError(f"Shopify API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class ShopifyProvider(Provider):
    def __init__(self):
        super().__init__(
            service="shopify",
            display_name="Shopify",
            category="E-Commerce",
            auth_types=["api_key", "oauth2"],
            description="Leading multi-channel commerce platform powering millions of businesses worldwide.",
            homepage_url="https://www.shopify.com",
            base_url="https://{shopDomain}.myshopify.com/admin/api/2024-01",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Shopify Admin API Access Token",
                    "placeholder": "shpat_...",
                    "description": "Custom App Admin API access token created in Shopify Admin > Settings > Apps and sales channels > Develop apps.",
                    "docs_url": "https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens",
                    "docs_label": "Shopify Access Tokens Guide",
                    "setup_guide": {
                        "title": "Shopify Custom App Token Guide",
                        "docs_url": "https://help.shopify.com/en/manual/apps/app-types/custom-apps",
                        "docs_label": "Shopify Custom Apps Help",
                        "instructions": [
                            "1. Sign in to your Shopify store admin (e.g. your-store.myshopify.com/admin).",
                            "2. Go to Settings > Apps and sales channels > Develop apps.",
                            "3. Click 'Create an app', select Admin API scopes (read_content, read_products, etc.).",
                            "4. Click 'Install app' and copy your Admin API access token (starts with 'shpat_')."
                        ],
                        "scopes": ["read_content", "read_products", "read_themes"]
                    },
                    "fields": [
                        {
                            "key": "shopDomain",
                            "label": "Shop Domain / Subdomain",
                            "type": "text",
                            "required": True,
                            "placeholder": "my-store",
                            "description": "Your store handle or domain (e.g. 'my-store' or 'my-store.myshopify.com')."
                        },
                        {
                            "key": "apiKey",
                            "label": "Admin API Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "shpat_...",
                            "description": "Shopify Custom App Admin API access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("shopify"):
            self.register_action(ShopifyDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Shopify credentials by querying GET /shop.json."""
        base_url = _resolve_shopify_base(credential)
        headers = _shopify_headers(credential)
        url = f"{base_url}/shop.json"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Shopify API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Shopify credentials. Shopify returned Unauthorized.")
        elif resp.status_code == 404:
            raise ValueError(f"Shopify store domain not found: {base_url}")
        elif resp.status_code != 200:
            raise ValueError(f"Shopify credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        shop = body.get("shop", {})
        return {
            "valid": True,
            "accountId": str(shop.get("id", "shopify_shop")),
            "displayName": shop.get("name") or "Shopify Store",
            "metadata": {
                "validationEndpoint": "/shop.json",
                "email": shop.get("email"),
                "myshopifyDomain": shop.get("myshopify_domain")
            }
        }

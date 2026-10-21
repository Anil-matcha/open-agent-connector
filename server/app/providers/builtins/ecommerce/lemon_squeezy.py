"""
Lemon Squeezy Provider for ConnectorHub.
Loads and registers 16 actions from 'actions_catalog.json'.
All-in-one platform for selling digital products and SaaS: Stores, Products, Variants, Customers, Orders, Subscriptions, and Webhooks via Lemon Squeezy API v1.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

LEMON_SQUEEZY_API_BASE = "https://api.lemonsqueezy.com/v1"

LEMON_SQUEEZY_ENDPOINT_MAP = {
    "lemon_squeezy.create_customer": ("POST", "/customers"),
    "lemon_squeezy.create_webhook": ("POST", "/webhooks"),
    "lemon_squeezy.delete_webhook": ("DELETE", "/webhooks/{id}"),
    "lemon_squeezy.list_customers": ("GET", "/customers"),
    "lemon_squeezy.list_orders": ("GET", "/orders"),
    "lemon_squeezy.list_products": ("GET", "/products"),
    "lemon_squeezy.list_stores": ("GET", "/stores"),
    "lemon_squeezy.list_subscriptions": ("GET", "/subscriptions"),
    "lemon_squeezy.list_variants": ("GET", "/variants"),
    "lemon_squeezy.list_webhooks": ("GET", "/webhooks"),
    "lemon_squeezy.retrieve_authenticated_user": ("GET", "/users/me"),
    "lemon_squeezy.retrieve_customer": ("GET", "/customers/{id}"),
    "lemon_squeezy.retrieve_store": ("GET", "/stores/{id}"),
    "lemon_squeezy.retrieve_webhook": ("GET", "/webhooks/{id}"),
    "lemon_squeezy.update_customer": ("PATCH", "/customers/{id}"),
    "lemon_squeezy.update_webhook": ("PATCH", "/webhooks/{id}"),
}

def _lemon_squeezy_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Lemon Squeezy API Key required. Please connect your Lemon Squeezy account first.")
    return str(token).strip()

class LemonSqueezyDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = LEMON_SQUEEZY_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/products")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _lemon_squeezy_headers(token)

        path = self.endpoint_template
        for var in ["customer_id", "customerId", "store_id", "storeId", "webhook_id", "webhookId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))
            if "{id}" in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace("{id}", urllib.parse.quote(str(val), safe=""))

        url = f"{LEMON_SQUEEZY_API_BASE}{path}"
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
            raise ValueError(f"Lemon Squeezy API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class LemonSqueezyProvider(Provider):
    def __init__(self):
        super().__init__(
            service="lemon_squeezy",
            display_name="Lemon Squeezy",
            category="Finance",
            auth_types=["api_key"],
            description="Merchant of record for SaaS and digital creators: Checkout, Payments, Subscriptions, Global Tax compliance, and Invoicing.",
            homepage_url="https://www.lemonsqueezy.com",
            base_url=LEMON_SQUEEZY_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Lemon Squeezy API Key",
                    "placeholder": "lsq_...",
                    "description": "API Key generated in Settings > API.",
                    "docs_url": "https://docs.lemonsqueezy.com/guides/developer-guide/getting-started",
                    "docs_label": "Lemon Squeezy Developer Guide",
                    "setup_guide": {
                        "title": "Lemon Squeezy API Key Guide",
                        "docs_url": "https://app.lemonsqueezy.com/settings/api",
                        "docs_label": "Lemon Squeezy API Settings",
                        "instructions": [
                            "1. Sign in to Lemon Squeezy at app.lemonsqueezy.com.",
                            "2. Navigate to Settings > API.",
                            "3. Click '+' to generate a new API key, name it (e.g. 'ConnectorHub').",
                            "4. Copy your key and paste it below."
                        ],
                        "scopes": ["stores:read", "products:read", "orders:read", "subscriptions:read", "customers:read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "lsq_...",
                            "description": "Lemon Squeezy API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("lemon_squeezy"):
            self.register_action(LemonSqueezyDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Lemon Squeezy API Key by querying GET /users/me."""
        token = _extract_token(credential)
        headers = _lemon_squeezy_headers(token)
        url = f"{LEMON_SQUEEZY_API_BASE}/users/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Lemon Squeezy API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Lemon Squeezy API key. Lemon Squeezy returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Lemon Squeezy credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user_data = body.get("data", {})
        attributes = user_data.get("attributes", {})
        return {
            "valid": True,
            "accountId": str(user_data.get("id", "lemon_squeezy_user")),
            "displayName": attributes.get("name") or attributes.get("email") or "Lemon Squeezy User",
            "metadata": {
                "validationEndpoint": "/users/me",
                "email": attributes.get("email")
            }
        }

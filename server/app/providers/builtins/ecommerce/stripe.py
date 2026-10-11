"""
Stripe Provider for ConnectorHub.
Loads and registers 18 actions from 'actions_catalog.json'.
Global payments and subscription infrastructure: Customers, Products, Prices, Charges, and Account details via Stripe REST API v1.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

STRIPE_API_BASE = "https://api.stripe.com/v1"

STRIPE_ENDPOINT_MAP = {
    "stripe.create_customer": ("POST", "/customers"),
    "stripe.create_price": ("POST", "/prices"),
    "stripe.create_product": ("POST", "/products"),
    "stripe.delete_customer": ("DELETE", "/customers/{id}"),
    "stripe.delete_product": ("DELETE", "/products/{id}"),
    "stripe.get_customer": ("GET", "/customers/{id}"),
    "stripe.get_price": ("GET", "/prices/{id}"),
    "stripe.get_product": ("GET", "/products/{id}"),
    "stripe.identify_account": ("GET", "/account"),
    "stripe.list_customers": ("GET", "/customers"),
    "stripe.list_prices": ("GET", "/prices"),
    "stripe.list_products": ("GET", "/products"),
    "stripe.search_customers": ("GET", "/customers/search"),
    "stripe.search_prices": ("GET", "/prices/search"),
    "stripe.search_products": ("GET", "/products/search"),
    "stripe.update_customer": ("POST", "/customers/{id}"),
    "stripe.update_price": ("POST", "/prices/{id}"),
    "stripe.update_product": ("POST", "/products/{id}"),
}

def _stripe_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Stripe Secret Key required. Please connect your Stripe account first.")
    return str(token).strip()

class StripeDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = STRIPE_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/customers")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _stripe_headers(token)

        path = self.endpoint_template
        for var in ["customer_id", "price_id", "product_id", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))
            if "{id}" in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace("{id}", urllib.parse.quote(str(val), safe=""))

        url = f"{STRIPE_API_BASE}{path}"
        assert_public_url(url)

        req_method = self.method
        # Stripe accepts form-encoded parameters for POST/PUT/PATCH
        data = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method in ["GET", "DELETE"] else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            data=data,
            params=params
        )

        try:
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                err_msg = res_data.get("error", {}).get("message") if isinstance(res_data.get("error"), dict) else res_data.get("message") or str(res_data)
            raise ValueError(f"Stripe API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class StripeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="stripe",
            display_name="Stripe",
            category="Finance",
            auth_types=["api_key", "oauth2"],
            description="Financial infrastructure platform for online business: Payments, Billing subscriptions, Invoices, and Customer accounts.",
            homepage_url="https://stripe.com",
            base_url=STRIPE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Stripe Secret Key",
                    "placeholder": "sk_live_... or rk_live_...",
                    "description": "Stripe Secret or Restricted API Key from Dashboard > Developers > API keys.",
                    "docs_url": "https://dashboard.stripe.com/apikeys",
                    "docs_label": "Stripe API Keys Dashboard",
                    "setup_guide": {
                        "title": "Stripe API Key Guide",
                        "docs_url": "https://dashboard.stripe.com/apikeys",
                        "docs_label": "Stripe Developers Dashboard",
                        "instructions": [
                            "1. Sign in to your Stripe Dashboard at dashboard.stripe.com.",
                            "2. Navigate to Developers > API keys.",
                            "3. Under 'Standard keys' or 'Restricted keys', reveal or create your secret key.",
                            "4. Copy your key (starts with 'sk_live_', 'sk_test_', or 'rk_') and paste it below."
                        ],
                        "scopes": ["customers:read", "customers:write", "prices:read", "prices:write", "products:read", "products:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Secret Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "sk_live_...",
                            "description": "Stripe Secret or Restricted API key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("stripe"):
            self.register_action(StripeDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Stripe Secret Key by querying GET /v1/account."""
        token = _extract_token(credential)
        headers = _stripe_headers(token)
        url = f"{STRIPE_API_BASE}/account"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Stripe API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Stripe secret key. Stripe returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Stripe credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        business_profile = body.get("business_profile", {})
        display_name = business_profile.get("name") or body.get("id") or "Stripe Account"
        return {
            "valid": True,
            "accountId": body.get("id", "stripe_account"),
            "displayName": display_name,
            "metadata": {
                "validationEndpoint": "/v1/account",
                "country": body.get("country"),
                "defaultCurrency": body.get("default_currency")
            }
        }

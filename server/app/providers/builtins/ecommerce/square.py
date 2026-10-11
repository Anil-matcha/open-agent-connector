"""
Square Provider for ConnectorHub.
Loads and registers 6 actions from 'actions_catalog.json'.
Point-of-sale and omni-channel commerce platform: Locations, Customers, Customer Search, and Profile Updates via Square Connect API v2.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SQUARE_API_BASE = "https://connect.squareup.com/v2"

SQUARE_ENDPOINT_MAP = {
    "square.create_customer": ("POST", "/customers"),
    "square.get_customer": ("GET", "/customers/{customer_id}"),
    "square.list_customers": ("GET", "/customers"),
    "square.list_locations": ("GET", "/locations"),
    "square.search_customers": ("POST", "/customers/search"),
    "square.update_customer": ("PUT", "/customers/{customer_id}"),
}

def _square_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Square-Version": "2024-01-18",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Square Access Token required. Please connect your Square account first.")
    return str(token).strip()

class SquareDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = SQUARE_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "search" in action_meta["name"] else "GET", "/customers")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _square_headers(token)

        path = self.endpoint_template
        for var in ["customer_id", "customerId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{SQUARE_API_BASE}{path}"
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
            raise ValueError(f"Square API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class SquareProvider(Provider):
    def __init__(self):
        super().__init__(
            service="square",
            display_name="Square",
            category="Finance",
            auth_types=["api_key", "oauth2"],
            description="Commerce and financial services ecosystem providing in-person, online, and mobile point-of-sale solutions.",
            homepage_url="https://squareup.com",
            base_url=SQUARE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Square Access Token",
                    "placeholder": "EAAA...",
                    "description": "Square Personal Access Token or OAuth Access Token from Developer Dashboard.",
                    "docs_url": "https://developer.squareup.com/docs/build-basics/access-tokens",
                    "docs_label": "Square Access Tokens Guide",
                    "setup_guide": {
                        "title": "Square Access Token Guide",
                        "docs_url": "https://developer.squareup.com/apps",
                        "docs_label": "Square Developer Console",
                        "instructions": [
                            "1. Sign in to the Square Developer Dashboard at developer.squareup.com/apps.",
                            "2. Select or create an application.",
                            "3. Navigate to 'Credentials'.",
                            "4. Copy your Production Access Token (or Sandbox Access Token) and paste it below."
                        ],
                        "scopes": ["CUSTOMERS_READ", "CUSTOMERS_WRITE", "MERCHANT_PROFILE_READ"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "EAAA...",
                            "description": "Square Access Token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("square"):
            self.register_action(SquareDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Square credentials by querying GET /v2/locations."""
        token = _extract_token(credential)
        headers = _square_headers(token)
        url = f"{SQUARE_API_BASE}/locations"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Square API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Square token. Square returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Square credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        locations = body.get("locations", [])
        primary_loc = locations[0] if locations else {}
        return {
            "valid": True,
            "accountId": str(primary_loc.get("id") or "square_merchant"),
            "displayName": primary_loc.get("name") or "Square Merchant",
            "metadata": {
                "validationEndpoint": "/v2/locations",
                "locationCount": len(locations),
                "businessName": primary_loc.get("business_name")
            }
        }

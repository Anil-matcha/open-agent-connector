"""
PayPal Provider for ConnectorHub.
Loads and registers 14 actions from 'actions_catalog.json'.
Global payments processing: Orders, Authorizations, Captures, Refunds, Balance Reporting, and Shipment Tracking via PayPal REST API v1/v2.
"""
import base64
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

PAYPAL_LIVE_BASE = "https://api-m.paypal.com"
PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"

PAYPAL_ENDPOINT_MAP = {
    "paypal.add_tracking": ("POST", "/v2/checkout/orders/{orderId}/track"),
    "paypal.authorize_order": ("POST", "/v2/checkout/orders/{orderId}/authorize"),
    "paypal.capture_authorization": ("POST", "/v2/payments/authorizations/{authorizationId}/capture"),
    "paypal.capture_order": ("POST", "/v2/checkout/orders/{orderId}/capture"),
    "paypal.create_order": ("POST", "/v2/checkout/orders"),
    "paypal.get_authorization": ("GET", "/v2/payments/authorizations/{authorizationId}"),
    "paypal.get_balances": ("GET", "/v1/reporting/balances"),
    "paypal.get_capture": ("GET", "/v2/payments/captures/{captureId}"),
    "paypal.get_order": ("GET", "/v2/checkout/orders/{orderId}"),
    "paypal.get_refund": ("GET", "/v2/payments/refunds/{refundId}"),
    "paypal.list_transactions": ("GET", "/v1/reporting/transactions"),
    "paypal.refund_capture": ("POST", "/v2/payments/captures/{captureId}/refund"),
    "paypal.update_tracking": ("PUT", "/v2/checkout/orders/{orderId}/trackers/{trackerId}"),
    "paypal.void_authorization": ("POST", "/v2/payments/authorizations/{authorizationId}/void"),
}

def _resolve_paypal_base(credential: Optional[Dict[str, Any]]) -> str:
    env = (credential or {}).get("environment") or ""
    if str(env).strip().lower() in ("sandbox", "test"):
        return PAYPAL_SANDBOX_BASE
    return PAYPAL_LIVE_BASE

async def _get_paypal_bearer_token(credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> str:
    cred = credential or {}
    # Direct access token if provided
    if cred.get("accessToken") or cred.get("token"):
        return str(cred.get("accessToken") or cred.get("token")).strip()

    client_id = cred.get("clientId") or cred.get("client_id") or cred.get("apiKey")
    client_secret = cred.get("clientSecret") or cred.get("client_secret")

    if not client_id or not client_secret:
        if cred.get("apiKey"):
            return str(cred["apiKey"]).strip()
        raise ValueError("PayPal Client ID and Client Secret required. Please connect your PayPal account first.")

    base_url = _resolve_paypal_base(credential)
    url = f"{base_url}/v1/oauth2/token"
    assert_public_url(url)

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    resp = await execute_guarded_request(
        client=client,
        method="POST",
        url=url,
        headers=headers,
        data={"grant_type": "client_credentials"}
    )

    if resp.status_code >= 400:
        raise ValueError(f"PayPal token exchange failed ({resp.status_code}): {resp.text[:200]}")

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError("PayPal did not return an access token.")
    return str(token)

class PayPalDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = PAYPAL_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "capture" in action_meta["name"] else "GET", "/v2/checkout/orders")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = await _get_paypal_bearer_token(credential, client)
        base_url = _resolve_paypal_base(credential)
        inputs = dict(input_data or {})
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }

        path = self.endpoint_template
        for var in ["orderId", "authorizationId", "captureId", "refundId", "trackerId", "id"]:
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
                err_msg = res_data.get("message") or res_data.get("error_description") or str(res_data)
            raise ValueError(f"PayPal API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class PayPalProvider(Provider):
    def __init__(self):
        super().__init__(
            service="paypal",
            display_name="PayPal",
            category="Finance",
            auth_types=["custom_credential", "api_key", "oauth2"],
            description="Online payments system supporting global money transfers, payment processing for online vendors, and auction sites.",
            homepage_url="https://www.paypal.com",
            base_url=PAYPAL_LIVE_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "PayPal REST API Credentials",
                    "placeholder": "Client ID & Secret",
                    "description": "PayPal REST App credentials from the Developer Dashboard.",
                    "docs_url": "https://developer.paypal.com/api/rest/",
                    "docs_label": "PayPal Developer Portal",
                    "setup_guide": {
                        "title": "PayPal API Credentials Guide",
                        "docs_url": "https://developer.paypal.com/dashboard/applications",
                        "docs_label": "PayPal Developer Dashboard",
                        "instructions": [
                            "1. Sign in to PayPal Developer Dashboard at developer.paypal.com.",
                            "2. Navigate to 'Apps & Credentials'.",
                            "3. Select or create a REST API app.",
                            "4. Copy your Client ID and Secret and paste them below."
                        ],
                        "scopes": ["orders:read", "orders:write", "payments:read", "payments:write"]
                    },
                    "fields": [
                        {
                            "key": "clientId",
                            "label": "Client ID",
                            "type": "text",
                            "required": True,
                            "placeholder": "A...",
                            "description": "PayPal App Client ID."
                        },
                        {
                            "key": "clientSecret",
                            "label": "Client Secret",
                            "type": "password",
                            "required": True,
                            "placeholder": "E...",
                            "description": "PayPal App Client Secret."
                        },
                        {
                            "key": "environment",
                            "label": "Environment",
                            "type": "text",
                            "required": False,
                            "placeholder": "live or sandbox",
                            "description": "PayPal environment ('live' or 'sandbox', default 'live')."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("paypal"):
            self.register_action(PayPalDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate PayPal credentials by attempting an OAuth token exchange against /v1/oauth2/token."""
        base_url = _resolve_paypal_base(credential)
        url = f"{base_url}/v1/oauth2/token"
        assert_public_url(url)

        cred = credential or {}
        client_id = cred.get("clientId") or cred.get("client_id") or cred.get("apiKey") or ""
        client_secret = cred.get("clientSecret") or cred.get("client_secret") or ""

        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=url,
                headers=headers,
                data={"grant_type": "client_credentials"}
            )
        except Exception as e:
            raise ValueError(f"Unable to reach PayPal API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid PayPal credentials. PayPal returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"PayPal credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        app_id = body.get("app_id") or client_id[:8]
        return {
            "valid": True,
            "accountId": app_id,
            "displayName": f"PayPal App ({app_id})",
            "metadata": {
                "validationEndpoint": "/v1/oauth2/token",
                "appId": body.get("app_id"),
                "tokenType": body.get("token_type")
            }
        }

"""
Customer.io Provider for ConnectorHub.
Loads and registers 7 actions from 'actions_catalog.json'.
Behavioral messaging and event tracking: Identify customers, track customer/anonymous events, delete profiles, merge customers, and manage suppression via Customer.io Track API.
"""
import base64
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CUSTOMERIO_TRACK_BASE = "https://track.customer.io"
CUSTOMERIO_TRACK_EU_BASE = "https://track-eu.customer.io"

CUSTOMERIO_ENDPOINT_MAP = {
    "customerio.delete_customer": ("DELETE", "/api/v1/customers/{identifier}"),
    "customerio.identify_customer": ("PUT", "/api/v1/customers/{identifier}"),
    "customerio.merge_customers": ("POST", "/api/v1/merge_customers"),
    "customerio.suppress_customer": ("POST", "/api/v1/customers/{identifier}/suppress"),
    "customerio.track_anonymous_event": ("POST", "/api/v1/events"),
    "customerio.track_customer_event": ("POST", "/api/v1/customers/{identifier}/events"),
    "customerio.unsuppress_customer": ("POST", "/api/v1/customers/{identifier}/unsuppress"),
}

def _resolve_customerio_base(credential: Optional[Dict[str, Any]]) -> str:
    region = (credential or {}).get("region") or ""
    if str(region).strip().lower() == "eu":
        return CUSTOMERIO_TRACK_EU_BASE
    return CUSTOMERIO_TRACK_BASE

def _customerio_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    site_id = cred.get("siteId") or cred.get("site_id") or ""
    api_key = cred.get("apiKey") or cred.get("api_key") or cred.get("token") or ""

    if site_id and api_key:
        auth_pair = f"{site_id}:{api_key}"
        encoded = base64.b64encode(auth_pair.encode("utf-8")).decode("utf-8")
        auth_header = f"Basic {encoded}"
    elif api_key:
        auth_header = f"Bearer {api_key}"
    else:
        raise ValueError("Customer.io Site ID and API Key required. Please connect your account first.")

    return {
        "Authorization": auth_header,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class CustomerIODynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Marketing"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = CUSTOMERIO_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST", "/api/v1/events")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        base_url = _resolve_customerio_base(credential)
        inputs = dict(input_data or {})
        headers = _customerio_headers(credential)

        path = self.endpoint_template
        for var in ["identifier", "id", "customer_id"]:
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
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            err_msg = str(data)
            if isinstance(data, dict):
                err_msg = data.get("meta", {}).get("error") if isinstance(data.get("meta"), dict) else data.get("error") or str(data)
            raise ValueError(f"Customer.io API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class CustomerIOProvider(Provider):
    def __init__(self):
        super().__init__(
            service="customerio",
            display_name="Customer.io",
            category="Marketing",
            auth_types=["api_key"],
            description="Automated messaging and customer engagement platform powered by real-time behavioral data.",
            homepage_url="https://customer.io",
            base_url=CUSTOMERIO_TRACK_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Customer.io Track API Credentials",
                    "placeholder": "Site ID & API Key",
                    "description": "Customer.io Track API credentials used for behavioral tracking.",
                    "docs_url": "https://customer.io/docs/api/track/",
                    "docs_label": "Customer.io Track API Docs",
                    "setup_guide": {
                        "title": "Customer.io Credentials Guide",
                        "docs_url": "https://fly.customer.io/settings/api_credentials",
                        "docs_label": "Customer.io API Credentials Page",
                        "instructions": [
                            "1. Sign in to Customer.io at fly.customer.io.",
                            "2. Navigate to Settings > Workspace Settings > API Credentials.",
                            "3. Under 'Track API Keys', copy your Site ID and API Key.",
                            "4. Enter them below."
                        ],
                        "scopes": ["track:events", "track:customers", "track:identify"]
                    },
                    "fields": [
                        {
                            "key": "siteId",
                            "label": "Site ID",
                            "type": "text",
                            "required": True,
                            "placeholder": "CUSTOMERIO_SITE_ID",
                            "description": "Customer.io Track API Site ID."
                        },
                        {
                            "key": "apiKey",
                            "label": "Track API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "CUSTOMERIO_API_KEY",
                            "description": "Customer.io Track API Key."
                        },
                        {
                            "key": "region",
                            "label": "Region (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "us or eu",
                            "description": "Workspace region ('us' or 'eu', defaults to 'us')."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("customerio"):
            self.register_action(CustomerIODynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Customer.io credentials by querying GET /api/v1/accounts/region."""
        base_url = _resolve_customerio_base(credential)
        headers = _customerio_headers(credential)
        url = f"{base_url}/api/v1/accounts/region"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Customer.io API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Customer.io credentials. Customer.io returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Customer.io credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        site_id = credential.get("siteId") or "customerio_workspace"
        return {
            "valid": True,
            "accountId": site_id,
            "displayName": f"Customer.io ({site_id})",
            "metadata": {
                "validationEndpoint": "/api/v1/accounts/region",
                "region": body.get("region") or "us"
            }
        }

"""
HubSpot Provider for ConnectorHub.
Loads and registers 26 actions from 'actions_catalog.json'.
Comprehensive CRM, Marketing, and Sales platform integration: Contacts, Companies, Deals, Custom Objects, Properties, Owners, and Campaigns via HubSpot CRM v3 API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

HUBSPOT_API_BASE = "https://api.hubapi.com"

HUBSPOT_ENDPOINT_MAP = {
    "hubspot.create_company": ("POST", "/crm/v3/objects/companies"),
    "hubspot.create_contact": ("POST", "/crm/v3/objects/contacts"),
    "hubspot.create_deal": ("POST", "/crm/v3/objects/deals"),
    "hubspot.get_company": ("GET", "/crm/v3/objects/companies/{companyId}"),
    "hubspot.get_contact": ("GET", "/crm/v3/objects/contacts/{contactId}"),
    "hubspot.get_deal": ("GET", "/crm/v3/objects/deals/{dealId}"),
    "hubspot.get_crm_objects": ("GET", "/crm/v3/objects/{objectType}"),
    "hubspot.manage_crm_objects": ("POST", "/crm/v3/objects/{objectType}"),
    "hubspot.search_companies": ("POST", "/crm/v3/objects/companies/search"),
    "hubspot.search_contacts": ("POST", "/crm/v3/objects/contacts/search"),
    "hubspot.search_deals": ("POST", "/crm/v3/objects/deals/search"),
    "hubspot.search_crm_objects": ("POST", "/crm/v3/objects/{objectType}/search"),
    "hubspot.update_company": ("PATCH", "/crm/v3/objects/companies/{companyId}"),
    "hubspot.update_contact": ("PATCH", "/crm/v3/objects/contacts/{contactId}"),
    "hubspot.update_deal": ("PATCH", "/crm/v3/objects/deals/{dealId}"),
    "hubspot.list_properties": ("GET", "/crm/v3/properties/{objectType}"),
    "hubspot.get_property": ("GET", "/crm/v3/properties/{objectType}/{propertyName}"),
    "hubspot.get_properties": ("GET", "/crm/v3/properties/{objectType}"),
    "hubspot.search_properties": ("POST", "/crm/v3/properties/{objectType}/search"),
    "hubspot.search_owners": ("GET", "/crm/v3/owners"),
    "hubspot.get_user_details": ("GET", "/crm/v3/owners/{ownerId}"),
    "hubspot.get_campaign_analytics": ("GET", "/marketing/v3/campaigns/analytics"),
    "hubspot.get_campaign_asset_metrics": ("GET", "/marketing/v3/campaigns/assets/metrics"),
    "hubspot.get_campaign_asset_types": ("GET", "/marketing/v3/campaigns/assets/types"),
    "hubspot.get_campaign_contacts_by_type": ("GET", "/marketing/v3/campaigns/contacts"),
    "hubspot.submit_feedback": ("POST", "/crm/v3/objects/feedback_submissions"),
}

def _hubspot_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("HubSpot Access Token or API Key required. Please connect your HubSpot account first.")
    return str(token).strip()

class HubSpotDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "CRM"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = HUBSPOT_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "search" in action_meta["name"] else "GET", "/crm/v3/objects/contacts")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _hubspot_headers(token)

        path = self.endpoint_template
        for var in ["companyId", "contactId", "dealId", "ownerId", "objectType", "propertyName", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{HUBSPOT_API_BASE}{path}"
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
                err_msg = data.get("message") or data.get("error") or str(data)
            raise ValueError(f"HubSpot API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class HubSpotProvider(Provider):
    def __init__(self):
        super().__init__(
            service="hubspot",
            display_name="HubSpot",
            category="CRM",
            auth_types=["oauth2", "api_key"],
            description="Industry-leading inbound CRM, sales pipeline, marketing automation, and customer service platform.",
            homepage_url="https://www.hubspot.com",
            base_url=HUBSPOT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "HubSpot Private App Token",
                    "placeholder": "pat-na1-...",
                    "description": "HubSpot Private App Access Token created in Settings > Integrations > Private Apps.",
                    "docs_url": "https://developers.hubspot.com/docs/api/private-apps",
                    "docs_label": "HubSpot Private Apps Guide",
                    "setup_guide": {
                        "title": "HubSpot Private App Token Guide",
                        "docs_url": "https://app.hubspot.com/settings/integrations/private-apps",
                        "docs_label": "HubSpot Private Apps Settings",
                        "instructions": [
                            "1. Sign in to your HubSpot portal at app.hubspot.com.",
                            "2. Navigate to Settings (gear icon) > Integrations > Private Apps.",
                            "3. Click 'Create a private app', name it (e.g. 'ConnectorHub').",
                            "4. On the Scopes tab, select CRM scopes: crm.objects.contacts.read/write, crm.objects.companies.read/write, crm.objects.deals.read/write.",
                            "5. Click 'Create app', copy the token (starts with 'pat-') and paste it below."
                        ],
                        "scopes": ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.deals.read", "crm.schemas.custom.read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Private App Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "pat-na1-...",
                            "description": "HubSpot Private App Access Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "HubSpot OAuth 2.0",
                    "description": "Connect via HubSpot OAuth 2.0 authorization code flow.",
                    "docs_url": "https://developers.hubspot.com/docs/api/working-with-oauth",
                    "docs_label": "HubSpot OAuth Guide",
                    "setup_guide": {
                        "title": "HubSpot OAuth 2.0 Setup",
                        "docs_url": "https://app.hubspot.com/developers",
                        "docs_label": "HubSpot Developer Portal",
                        "instructions": [
                            "1. Create an app in the HubSpot Developer Portal.",
                            "2. Add your redirect URI.",
                            "3. Select required CRM scopes.",
                            "4. Connect with 1-click OAuth."
                        ],
                        "scopes": ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.deals.read"]
                    }
                }
            ]
        )

        for meta in get_provider_actions("hubspot"):
            self.register_action(HubSpotDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate HubSpot credentials by querying GET /crm/v3/objects/contacts?limit=1."""
        token = _extract_token(credential)
        headers = _hubspot_headers(token)
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts?limit=1"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach HubSpot API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid HubSpot token. HubSpot returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"HubSpot credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        return {
            "valid": True,
            "account_id": "hubspot_account",
            "accountId": "hubspot_account",
            "display_name": "HubSpot Portal",
            "displayName": "HubSpot Portal",
            "metadata": {
                "validationEndpoint": "/crm/v3/objects/contacts",
                "status": resp.status_code
            }
        }

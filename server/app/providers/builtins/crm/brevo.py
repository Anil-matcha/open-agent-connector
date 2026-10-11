"""
Brevo Provider for ConnectorHub.
Loads and registers 12 actions from 'actions_catalog.json'.
Transactional email, SMS, and CRM marketing: Contacts, Lists, Folders, and Account details via Brevo REST API v3.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

BREVO_API_BASE = "https://api.brevo.com/v3"

BREVO_ENDPOINT_MAP = {
    "brevo.add_contacts_to_list": ("POST", "/contacts/lists/{listId}/contacts/add"),
    "brevo.create_contact": ("POST", "/contacts"),
    "brevo.create_contact_list": ("POST", "/contacts/lists"),
    "brevo.delete_contact": ("DELETE", "/contacts/{identifier}"),
    "brevo.get_account": ("GET", "/account"),
    "brevo.get_contact": ("GET", "/contacts/{identifier}"),
    "brevo.list_contact_folders": ("GET", "/contacts/folders"),
    "brevo.list_contact_lists": ("GET", "/contacts/lists"),
    "brevo.list_contacts": ("GET", "/contacts"),
    "brevo.list_contacts_in_list": ("GET", "/contacts/lists/{listId}/contacts"),
    "brevo.remove_contacts_from_list": ("POST", "/contacts/lists/{listId}/contacts/remove"),
    "brevo.update_contact_list": ("PUT", "/contacts/lists/{listId}"),
}

def _brevo_headers(api_key: str) -> Dict[str, str]:
    return {
        "api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Brevo API Key required. Please connect your Brevo account first.")
    return str(token).strip()

class BrevoDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Marketing"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = BREVO_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/contacts")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _brevo_headers(api_key)

        path = self.endpoint_template
        for var in ["identifier", "listId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{BREVO_API_BASE}{path}"
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
            raise ValueError(f"Brevo API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class BrevoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="brevo",
            display_name="Brevo",
            category="Marketing",
            auth_types=["api_key"],
            description="Complete CRM suite offering marketing automation, transactional email, SMS, and WhatsApp campaigns.",
            homepage_url="https://www.brevo.com",
            base_url=BREVO_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Brevo API Key",
                    "placeholder": "xkeysib_...",
                    "description": "Brevo v3 API key found in SMTP & API settings.",
                    "docs_url": "https://developers.brevo.com/docs/getting-started",
                    "docs_label": "Brevo API Getting Started",
                    "setup_guide": {
                        "title": "Brevo API Key Guide",
                        "docs_url": "https://app.brevo.com/settings/keys/api",
                        "docs_label": "Brevo API Keys Dashboard",
                        "instructions": [
                            "1. Sign in to your Brevo account at app.brevo.com.",
                            "2. Navigate to SMTP & API > API Keys.",
                            "3. Click 'Generate a new API key', name it (e.g. 'ConnectorHub').",
                            "4. Copy your key (starts with 'xkeysib-') and paste it below."
                        ],
                        "scopes": ["contacts:read", "contacts:write", "lists:read", "lists:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "xkeysib_...",
                            "description": "Brevo v3 API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("brevo"):
            self.register_action(BrevoDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Brevo credentials by querying GET /account."""
        api_key = _extract_token(credential)
        headers = _brevo_headers(api_key)
        url = f"{BREVO_API_BASE}/account"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Brevo API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Brevo API key. Brevo returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Brevo credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        return {
            "valid": True,
            "accountId": str(body.get("email") or "brevo_account"),
            "displayName": body.get("companyName") or body.get("email") or "Brevo Account",
            "metadata": {
                "validationEndpoint": "/account",
                "email": body.get("email"),
                "plan": body.get("plan", [])
            }
        }

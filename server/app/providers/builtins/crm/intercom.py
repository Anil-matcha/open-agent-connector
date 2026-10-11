"""
Intercom Provider for ConnectorHub.
Loads and registers 24 actions from 'actions_catalog.json'.
Customer communication and messaging platform: Contacts, Companies, Conversations, Tickets, Admins, Articles, and Events via Intercom REST API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

INTERCOM_API_BASE = "https://api.intercom.io"

INTERCOM_ENDPOINT_MAP = {
    "intercom.close_conversation": ("POST", "/conversations/{conversationId}/parts"),
    "intercom.create_contact": ("POST", "/contacts"),
    "intercom.get_admin": ("GET", "/admins/{adminId}"),
    "intercom.get_article": ("GET", "/articles/{articleId}"),
    "intercom.get_company": ("GET", "/companies"),
    "intercom.get_contact": ("GET", "/contacts/{contactId}"),
    "intercom.get_contact_by_external_id": ("GET", "/contacts/find_by_external_id/{externalId}"),
    "intercom.get_conversation": ("GET", "/conversations/{conversationId}"),
    "intercom.get_counts": ("GET", "/counts"),
    "intercom.get_current_admin": ("GET", "/me"),
    "intercom.get_job_status": ("GET", "/jobs/status/{jobId}"),
    "intercom.get_ticket": ("GET", "/tickets/{ticketId}"),
    "intercom.list_admins": ("GET", "/admins"),
    "intercom.list_articles": ("GET", "/articles"),
    "intercom.list_companies": ("POST", "/companies/list"),
    "intercom.list_contacts": ("GET", "/contacts"),
    "intercom.list_conversations": ("GET", "/conversations"),
    "intercom.list_events": ("GET", "/events"),
    "intercom.list_tags": ("GET", "/tags"),
    "intercom.reopen_conversation": ("POST", "/conversations/{conversationId}/parts"),
    "intercom.reply_to_conversation": ("POST", "/conversations/{conversationId}/reply"),
    "intercom.search_contacts": ("POST", "/contacts/search"),
    "intercom.search_tickets": ("POST", "/tickets/search"),
    "intercom.update_contact": ("PUT", "/contacts/{contactId}"),
}

def _intercom_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Intercom-Version": "2.11",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Intercom Access Token required. Please connect your Intercom account first.")
    return str(token).strip()

class IntercomDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = INTERCOM_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "search" in action_meta["name"] else "GET", "/contacts")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _intercom_headers(token)

        path = self.endpoint_template
        for var in ["conversationId", "contactId", "adminId", "articleId", "ticketId", "jobId", "externalId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{INTERCOM_API_BASE}{path}"
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
                err_msg = data.get("errors") or data.get("message") or str(data)
            raise ValueError(f"Intercom API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class IntercomProvider(Provider):
    def __init__(self):
        super().__init__(
            service="intercom",
            display_name="Intercom",
            category="Communication",
            auth_types=["oauth2", "api_key"],
            description="The complete AI-first customer service platform uniting customer messaging, help center, and conversational support.",
            homepage_url="https://www.intercom.com",
            base_url=INTERCOM_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Intercom Access Token",
                    "placeholder": "dG9rX...",
                    "description": "Intercom Access Token from your Intercom Developer Workspace.",
                    "docs_url": "https://developers.intercom.com/docs/build-an-integration/learn-more/authentication",
                    "docs_label": "Intercom Authentication Guide",
                    "setup_guide": {
                        "title": "Intercom Access Token Setup",
                        "docs_url": "https://app.intercom.com/a/apps/_/developer-hub",
                        "docs_label": "Intercom Developer Hub",
                        "instructions": [
                            "1. Sign in to Intercom Developer Hub (app.intercom.com/a/apps/_/developer-hub).",
                            "2. Select or create an app for your workspace.",
                            "3. Navigate to 'Configure > Authentication'.",
                            "4. Copy your Access Token and paste it below."
                        ],
                        "scopes": ["contacts:read", "contacts:write", "conversations:read", "conversations:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "dG9rX...",
                            "description": "Intercom Access Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Intercom OAuth 2.0",
                    "description": "Connect via Intercom OAuth 2.0.",
                    "docs_url": "https://developers.intercom.com/docs/build-an-integration/learn-more/authentication/#oauth",
                    "docs_label": "Intercom OAuth Guide",
                    "setup_guide": {
                        "title": "Intercom OAuth Setup",
                        "docs_url": "https://app.intercom.com/a/apps/_/developer-hub",
                        "docs_label": "Intercom Developer Hub",
                        "instructions": [
                            "1. Create an OAuth app in Intercom Developer Hub.",
                            "2. Add redirect URL.",
                            "3. Connect with 1-click OAuth."
                        ],
                        "scopes": []
                    }
                }
            ]
        )

        for meta in get_provider_actions("intercom"):
            self.register_action(IntercomDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Intercom credentials by querying GET /me."""
        token = _extract_token(credential)
        headers = _intercom_headers(token)
        url = f"{INTERCOM_API_BASE}/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Intercom API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Intercom token. Intercom returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Intercom credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        return {
            "valid": True,
            "accountId": str(body.get("id", "intercom_admin")),
            "displayName": body.get("name") or "Intercom Admin",
            "metadata": {
                "validationEndpoint": "/me",
                "email": body.get("email"),
                "app": body.get("app", {}).get("name")
            }
        }

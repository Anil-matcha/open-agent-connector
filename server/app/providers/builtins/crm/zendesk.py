"""
Zendesk Provider for ConnectorHub.
Loads and registers 11 actions from 'actions_catalog.json'.
Customer service, helpdesk ticketing, user management, and organization tracking via Zendesk Support REST API v2.
"""
import base64
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ZENDESK_ENDPOINT_MAP = {
    "zendesk.create_ticket": ("POST", "/api/v2/tickets.json"),
    "zendesk.get_current_user": ("GET", "/api/v2/users/me.json"),
    "zendesk.get_organization": ("GET", "/api/v2/organizations/{organizationId}.json"),
    "zendesk.get_ticket": ("GET", "/api/v2/tickets/{ticketId}.json"),
    "zendesk.get_user": ("GET", "/api/v2/users/{userId}.json"),
    "zendesk.list_organizations": ("GET", "/api/v2/organizations.json"),
    "zendesk.list_tickets": ("GET", "/api/v2/tickets.json"),
    "zendesk.list_users": ("GET", "/api/v2/users.json"),
    "zendesk.reply_to_ticket": ("PUT", "/api/v2/tickets/{ticketId}.json"),
    "zendesk.search_users": ("GET", "/api/v2/users/search.json"),
    "zendesk.update_ticket": ("PUT", "/api/v2/tickets/{ticketId}.json"),
}

def _resolve_zendesk_base(credential: Optional[Dict[str, Any]]) -> str:
    subdomain = (credential or {}).get("subdomain") or (credential or {}).get("instanceUrl") or "d3v-sample"
    subdomain = str(subdomain).strip().lower()
    if subdomain.startswith("http://") or subdomain.startswith("https://"):
        return subdomain.rstrip("/")
    if ".zendesk.com" in subdomain:
        return f"https://{subdomain}"
    return f"https://{subdomain}.zendesk.com"

def _zendesk_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    cred = credential or {}
    token = cred.get("apiKey") or cred.get("accessToken") or cred.get("token") or ""
    email = cred.get("email")

    if email and token:
        # Zendesk API Token Basic Auth: email/token:api_token
        auth_pair = f"{email}/token:{token}"
        encoded = base64.b64encode(auth_pair.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {encoded}"
    elif token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        raise ValueError("Zendesk credentials required (API token or OAuth access token).")

    return headers

class ZendeskDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Helpdesk"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = ZENDESK_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/api/v2/tickets.json")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        base_url = _resolve_zendesk_base(credential)
        inputs = dict(input_data or {})
        headers = _zendesk_headers(credential)

        path = self.endpoint_template
        for var in ["ticketId", "userId", "organizationId", "id"]:
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
                err_msg = data.get("error") or data.get("description") or str(data)
            raise ValueError(f"Zendesk API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class ZendeskProvider(Provider):
    def __init__(self):
        super().__init__(
            service="zendesk",
            display_name="Zendesk",
            category="Helpdesk",
            auth_types=["api_key", "oauth2"],
            description="Leading customer service software and support ticket system empowering agents to build great customer relationships.",
            homepage_url="https://www.zendesk.com",
            base_url="https://{subdomain}.zendesk.com/api/v2",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Zendesk API Token",
                    "placeholder": "zendesk_api_token...",
                    "description": "Zendesk API Token used with your admin/agent email address.",
                    "docs_url": "https://developer.zendesk.com/api-reference/ticketing/introduction/#api-token",
                    "docs_label": "Zendesk API Token Guide",
                    "setup_guide": {
                        "title": "Zendesk API Token Setup",
                        "docs_url": "https://support.zendesk.com/hc/en-us/articles/4408889114522",
                        "docs_label": "Zendesk Admin Center",
                        "instructions": [
                            "1. Sign in to your Zendesk Admin Center (yoursubdomain.zendesk.com/admin).",
                            "2. Go to Apps and integrations > Zendesk API > Settings.",
                            "3. Enable Token Access, then click 'Add API token'.",
                            "4. Copy your API token and note your Zendesk Subdomain and Agent Email."
                        ],
                        "scopes": ["tickets:read", "tickets:write", "users:read", "organizations:read"]
                    },
                    "fields": [
                        {
                            "key": "subdomain",
                            "label": "Subdomain",
                            "type": "text",
                            "required": True,
                            "placeholder": "mycompany",
                            "description": "Your Zendesk subdomain (e.g. 'mycompany' from mycompany.zendesk.com)."
                        },
                        {
                            "key": "email",
                            "label": "Agent Email",
                            "type": "text",
                            "required": True,
                            "placeholder": "agent@mycompany.com",
                            "description": "Email address of the authenticated Zendesk user."
                        },
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "zendesk_api_token...",
                            "description": "Zendesk API token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("zendesk"):
            self.register_action(ZendeskDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Zendesk API credentials by querying GET /api/v2/users/me.json."""
        base_url = _resolve_zendesk_base(credential)
        headers = _zendesk_headers(credential)
        url = f"{base_url}/api/v2/users/me.json"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Zendesk API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Zendesk credentials. Zendesk returned Unauthorized.")
        elif resp.status_code == 404:
            raise ValueError(f"Zendesk subdomain not found or invalid: {base_url}")
        elif resp.status_code != 200:
            raise ValueError(f"Zendesk credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user = body.get("user", {})
        return {
            "valid": True,
            "accountId": str(user.get("id", "zendesk_user")),
            "displayName": user.get("name") or "Zendesk User",
            "metadata": {
                "validationEndpoint": "/api/v2/users/me.json",
                "email": user.get("email"),
                "role": user.get("role")
            }
        }

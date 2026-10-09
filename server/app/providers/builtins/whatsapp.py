"""
WhatsApp Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Meta WhatsApp Cloud API specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"

def _whatsapp_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("WhatsApp System User or Access Token required. Please connect your WhatsApp account first.")
    return str(token).strip()

class WhatsAppDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "POST").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/{phoneNumberId}/messages")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _whatsapp_headers(token)
        inputs = dict(input_data or {})

        # 1. Path variables substitution
        path = self.endpoint_template
        for var in ["phoneNumberId", "wabaId", "mediaId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None and var == "phoneNumberId":
                    val = (credential or {}).get("phoneNumberId") or inputs.pop("phone_number_id", None)
                if val is None and var == "wabaId":
                    val = (credential or {}).get("wabaId") or inputs.pop("waba_id", None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{WHATSAPP_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

        # 2. Payload construction
        if self.id == "whatsapp.send_message":
            to = inputs.pop("to", "")
            text = inputs.pop("text", "") or inputs.pop("message", "")
            body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": str(to),
                "type": "text",
                "text": {"preview_url": inputs.pop("preview_url", False), "body": str(text)}
            }
        elif self.id == "whatsapp.send_template_message":
            body = {
                "messaging_product": "whatsapp",
                "to": str(inputs.pop("to", "")),
                "type": "template",
                "template": inputs.pop("template", {})
            }
        elif self.method in ["POST", "PUT", "PATCH"]:
            body = inputs
        else:
            for k, v in inputs.items():
                if v is not None:
                    params[k] = str(v)

        resp = await execute_guarded_request(
            client=client,
            method=self.method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=body if body is not None and self.method in ["POST", "PUT", "PATCH"] else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"WhatsApp Cloud API error ({resp.status_code}): {msg}")

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class WhatsAppProvider(Provider):
    def __init__(self):
        super().__init__(
            service="whatsapp",
            display_name="WhatsApp",
            category="Communication",
            auth_types=["oauth2", "api_key"],
            description="Meta WhatsApp Cloud API for sending WhatsApp messages, media, interactive messages, and managing templates.",
            homepage_url="https://business.whatsapp.com",
            base_url=WHATSAPP_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Meta OAuth 2.0 User Access Token",
                    "placeholder": "EAAG...",
                    "description": "Authenticate via Meta OAuth 2.0 User Access Token with WhatsApp scopes.",
                    "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
                    "docs_label": "WhatsApp Cloud API Documentation",
                    "setup_guide": {
                        "title": "WhatsApp OAuth Access Token Setup Guide",
                        "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
                        "docs_label": "WhatsApp Cloud API Docs",
                        "instructions": [
                            "1. Go to Meta for Developers (developers.facebook.com) and create or select your Business App.",
                            "2. Add WhatsApp and generate an OAuth Access Token.",
                            "3. Ensure the token has 'whatsapp_business_messaging' and 'whatsapp_business_management' permissions.",
                            "4. Copy and paste the token below."
                        ],
                        "scopes": [
                            "whatsapp_business_messaging",
                            "whatsapp_business_management"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "EAAG...",
                            "description": "Meta WhatsApp OAuth Access Token."
                        },
                        {
                            "key": "phoneNumberId",
                            "label": "Phone Number ID (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "100609349493...",
                            "description": "Default Phone Number ID for outbound messaging."
                        },
                        {
                            "key": "wabaId",
                            "label": "WABA ID (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "10595238249...",
                            "description": "Default WhatsApp Business Account ID for template management."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Meta Access Token / System User Token",
                    "placeholder": "EAAG...",
                    "description": "WhatsApp Cloud API access token generated from Meta for Developers / Business Settings.",
                    "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
                    "docs_label": "WhatsApp Cloud API Documentation",
                    "setup_guide": {
                        "title": "WhatsApp Cloud API Setup Guide",
                        "docs_url": "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
                        "docs_label": "WhatsApp Cloud API Docs",
                        "instructions": [
                            "1. Go to Meta for Developers (developers.facebook.com) and create or select your App.",
                            "2. Add the WhatsApp product to your App and select 'API Setup'.",
                            "3. Copy your Temporary or Permanent System User Access Token (starts with EAAG...).",
                            "4. Ensure your token includes 'whatsapp_business_messaging' and 'whatsapp_business_management' permissions."
                        ],
                        "scopes": [
                            "whatsapp_business_messaging",
                            "whatsapp_business_management"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "EAAG...",
                            "description": "Meta WhatsApp Cloud API Bearer access token."
                        },
                        {
                            "key": "phoneNumberId",
                            "label": "Phone Number ID (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "100609349493...",
                            "description": "Default Phone Number ID for sending outbound messages."
                        },
                        {
                            "key": "wabaId",
                            "label": "WABA ID (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "10595238249...",
                            "description": "Default WhatsApp Business Account ID for template management."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("whatsapp"):
            self.register_action(WhatsAppDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Meta credentials against https://graph.facebook.com/v21.0/me."""
        token = _extract_token(credential)
        headers = _whatsapp_headers(token)
        url = f"{WHATSAPP_API_BASE}/me?fields=id,name"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach WhatsApp Graph API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 190:
            raise ValueError("Invalid WhatsApp access token. Meta API returned 401 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"WhatsApp credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = str(data.get("id") or "me")
        name = data.get("name") or account_id

        return {
            "account_id": account_id,
            "display_name": f"WhatsApp ({name})",
            "granted_scopes": ["whatsapp_business_messaging", "whatsapp_business_management"],
            "avatar_url": None
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """SSRF-guarded proxy forwarder for WhatsApp Cloud API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{WHATSAPP_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_whatsapp_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }

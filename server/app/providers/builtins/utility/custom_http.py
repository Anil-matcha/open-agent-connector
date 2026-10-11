from typing import Dict, Any, Optional
import httpx
from app.providers.base import Provider, Action
from app.core.ssrf import assert_public_url, execute_guarded_request

class HttpRequestAction(Action):
    def __init__(self):
        super().__init__(
            id="custom.http_request",
            name="Custom HTTP Request",
            description="Send a custom SSRF-safe HTTP request to any external API with headers and payload.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full destination HTTP/HTTPS URL"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
                    "headers": {"type": "object", "description": "Optional HTTP headers dictionary"},
                    "body": {"type": "object", "description": "Optional JSON body object"}
                },
                "required": ["url"]
            }
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        url = input_data["url"]
        method = input_data.get("method", "GET").upper()
        headers = dict(input_data.get("headers") or {})
        body = input_data.get("body")

        # Inject custom credential apiKey if present
        if credential and credential.get("apiKey"):
            headers.setdefault("Authorization", f"Bearer {credential['apiKey']}")

        assert_public_url(url)
        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=url,
            json_body=body if body else None,
            headers=headers
        )
        
        try:
            data = resp.json()
        except Exception:
            data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": data
        }

class CustomHttpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="custom",
            display_name="Custom Webhook / HTTP",
            category="Utilities",
            auth_types=["no_auth", "api_key"],
            description="Execute arbitrary SSRF-guarded HTTP requests and webhooks to any external API.",
            homepage_url="",
            auth_configs=[
                {
                    "type": "no_auth",
                    "label": "Anonymous / Public HTTP Request",
                    "description": "Send unauthenticated HTTP calls or webhooks to public APIs.",
                    "setup_guide": {
                        "title": "Public HTTP / Webhook Guide",
                        "instructions": [
                            "Send unauthenticated HTTP calls or webhooks to public APIs.",
                            "All outbound traffic is protected by strict SSRF guardrails blocking private IPs and loopbacks."
                        ]
                    }
                },
                {
                    "type": "api_key",
                    "label": "Custom Bearer Token / API Key",
                    "placeholder": "Bearer secret_token_xyz or api_key_...",
                    "description": "Optionally attach an Authorization Bearer header to all requests.",
                    "setup_guide": {
                        "title": "Custom HTTP / Bearer Auth Guide",
                        "instructions": [
                            "Enter an optional API key or Bearer token to be sent with outbound requests.",
                            "If specified, the token will be attached as 'Authorization: Bearer <token>'."
                        ]
                    }
                }
            ]
        )
        self.register_action(HttpRequestAction())

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = credential.get("apiKey") or credential.get("accessToken")
        return {
            "account_id": "api_key" if api_key else "anonymous",
            "display_name": "Custom HTTP Client",
            "granted_scopes": []
        }

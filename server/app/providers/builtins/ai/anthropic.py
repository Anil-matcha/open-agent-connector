"""
Anthropic Provider for ConnectorHub.
Loads and registers 4 actions from 'actions_catalog.json'.
Supports message creation (Claude), token counting, model inspection, and listing via the Anthropic Messages & Models API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_API_VERSION = "2023-06-01"

ANTHROPIC_ENDPOINT_MAP = {
    "anthropic.count_message_tokens": ("POST", "/v1/messages/count_tokens"),
    "anthropic.create_message": ("POST", "/v1/messages"),
    "anthropic.get_model": ("GET", "/v1/models/{model_id}"),
    "anthropic.list_models": ("GET", "/v1/models"),
}

def _anthropic_headers(api_key: str) -> Dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Anthropic API Key required. Please connect your Anthropic account first.")
    return str(token).strip()

class AnthropicDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = ANTHROPIC_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "count" in action_meta["name"] else "GET", "/v1/models")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _anthropic_headers(api_key)

        path = self.endpoint_template
        for var in ["model_id", "model"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{ANTHROPIC_API_BASE}{path}"
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
                err_msg = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else data.get("message") or str(data)
            raise ValueError(f"Anthropic API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class AnthropicProvider(Provider):
    def __init__(self):
        super().__init__(
            service="anthropic",
            display_name="Anthropic",
            category="AI",
            auth_types=["api_key"],
            description="AI safety and research company, creator of Claude—helpful, harmless, and honest AI assistant models.",
            homepage_url="https://www.anthropic.com",
            base_url=ANTHROPIC_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Anthropic API Key",
                    "placeholder": "sk-ant-api03-...",
                    "description": "Anthropic API key generated in the Anthropic Console.",
                    "docs_url": "https://console.anthropic.com/settings/keys",
                    "docs_label": "Anthropic API Keys Console",
                    "setup_guide": {
                        "title": "Anthropic API Key Guide",
                        "docs_url": "https://console.anthropic.com/settings/keys",
                        "docs_label": "Anthropic Console Settings",
                        "instructions": [
                            "1. Sign in to the Anthropic Console at console.anthropic.com.",
                            "2. Navigate to Settings > API Keys.",
                            "3. Click 'Create Key', provide a name (e.g. 'ConnectorHub').",
                            "4. Copy your secret API key (starts with 'sk-ant-') and paste it below."
                        ],
                        "scopes": ["messages:create", "models:read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "sk-ant-api03-...",
                            "description": "Anthropic Console API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("anthropic"):
            self.register_action(AnthropicDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Anthropic API Key by querying GET /v1/models."""
        api_key = _extract_token(credential)
        headers = _anthropic_headers(api_key)
        url = f"{ANTHROPIC_API_BASE}/v1/models"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Anthropic API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Anthropic API Key. Anthropic returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Anthropic credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        models = [m.get("id") for m in body.get("data", []) if isinstance(m, dict)]
        return {
            "valid": True,
            "accountId": "anthropic_api_key",
            "displayName": "Anthropic API Key",
            "metadata": {
                "validationEndpoint": "/v1/models",
                "modelCount": len(models),
                "sampleModels": models[:5]
            }
        }

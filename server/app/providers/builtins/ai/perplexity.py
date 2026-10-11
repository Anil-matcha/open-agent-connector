"""
Perplexity Provider for ConnectorHub.
Loads and registers 4 actions from 'actions_catalog.json'.
Supports search-augmented chat completions (Sonar), vector embeddings, real-time search, and model listing via the Perplexity API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

PERPLEXITY_API_BASE = "https://api.perplexity.ai"

PERPLEXITY_ENDPOINT_MAP = {
    "perplexity.create_chat_completion": ("POST", "/chat/completions"),
    "perplexity.create_embeddings": ("POST", "/v1/embeddings"),
    "perplexity.list_models": ("GET", "/models"),
    "perplexity.search": ("POST", "/search"),
}

def _perplexity_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Perplexity API Key required. Please connect your Perplexity account first.")
    return str(token).strip()

class PerplexityDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = PERPLEXITY_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "search" in action_meta["name"] else "GET", "/models")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _perplexity_headers(api_key)

        path = self.endpoint_template
        url = f"{PERPLEXITY_API_BASE}{path}"
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
            raise ValueError(f"Perplexity API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class PerplexityProvider(Provider):
    def __init__(self):
        super().__init__(
            service="perplexity",
            display_name="Perplexity",
            category="AI",
            auth_types=["api_key"],
            description="Conversational search engine offering real-time, cited AI models and search grounding via Sonar.",
            homepage_url="https://www.perplexity.ai",
            base_url=PERPLEXITY_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Perplexity API Key",
                    "placeholder": "pplx-...",
                    "description": "Perplexity API key generated under Settings > API.",
                    "docs_url": "https://www.perplexity.ai/settings/api",
                    "docs_label": "Perplexity API Settings",
                    "setup_guide": {
                        "title": "Perplexity API Key Guide",
                        "docs_url": "https://www.perplexity.ai/settings/api",
                        "docs_label": "Perplexity Settings > API",
                        "instructions": [
                            "1. Sign in to Perplexity at perplexity.ai.",
                            "2. Navigate to Settings > API.",
                            "3. Generate an API Key (starts with 'pplx-').",
                            "4. Copy your key and paste it below."
                        ],
                        "scopes": ["chat:complete", "search:execute"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "pplx-...",
                            "description": "Perplexity API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("perplexity"):
            self.register_action(PerplexityDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Perplexity API Key by querying GET /v1/models."""
        api_key = _extract_token(credential)
        headers = _perplexity_headers(api_key)
        url = f"{PERPLEXITY_API_BASE}/v1/models"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Perplexity API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Perplexity API Key. Perplexity returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Perplexity credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        return {
            "valid": True,
            "accountId": "perplexity_api_key",
            "displayName": "Perplexity API Key",
            "metadata": {
                "validationEndpoint": "/v1/models",
                "status": resp.status_code
            }
        }

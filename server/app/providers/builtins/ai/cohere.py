"""
Cohere Provider for ConnectorHub.
Loads and registers 3 actions from 'actions_catalog.json'.
Enterprise AI platform providing Chat, Text Embeddings (Embed v3), and semantic Reranking (Rerank v3).
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

COHERE_API_BASE = "https://api.cohere.com"

COHERE_ENDPOINT_MAP = {
    "cohere.chat": ("POST", "/v2/chat"),
    "cohere.embed_texts": ("POST", "/v2/embed"),
    "cohere.rerank_documents": ("POST", "/v2/rerank"),
}

def _cohere_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Cohere API Key required. Please connect your Cohere account first.")
    return str(token).strip()

class CohereDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = COHERE_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST", "/v2/chat")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _cohere_headers(api_key)

        path = self.endpoint_template
        url = f"{COHERE_API_BASE}{path}"
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
            raise ValueError(f"Cohere API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class CohereProvider(Provider):
    def __init__(self):
        super().__init__(
            service="cohere",
            display_name="Cohere",
            category="AI",
            auth_types=["api_key"],
            description="Enterprise AI platform offering Command chat models, Embed embeddings, and industry-leading Rerank capabilities.",
            homepage_url="https://cohere.com",
            base_url=COHERE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Cohere API Key",
                    "placeholder": "cohere_api_key...",
                    "description": "Cohere API key generated from the Cohere Dashboard.",
                    "docs_url": "https://dashboard.cohere.com/api-keys",
                    "docs_label": "Cohere API Keys Dashboard",
                    "setup_guide": {
                        "title": "Cohere API Key Guide",
                        "docs_url": "https://dashboard.cohere.com/api-keys",
                        "docs_label": "Cohere Dashboard",
                        "instructions": [
                            "1. Sign in to Cohere at dashboard.cohere.com.",
                            "2. Navigate to API Keys.",
                            "3. Copy your Production or Trial API key.",
                            "4. Paste your key below."
                        ],
                        "scopes": ["chat", "embed", "rerank"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "cohere_api_key...",
                            "description": "Cohere API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("cohere"):
            self.register_action(CohereDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Cohere API Key by querying GET /v1/models?page_size=1."""
        api_key = _extract_token(credential)
        headers = _cohere_headers(api_key)
        url = f"{COHERE_API_BASE}/v1/models?page_size=1"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Cohere API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Cohere API Key. Cohere returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Cohere credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        return {
            "valid": True,
            "accountId": "cohere_api_key",
            "displayName": "Cohere API Key",
            "metadata": {
                "validationEndpoint": "/v1/models",
                "status": resp.status_code
            }
        }

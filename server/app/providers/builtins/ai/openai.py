"""
OpenAI Provider for ConnectorHub.
Loads and registers 15 actions from 'actions_catalog.json'.
Supports model listing, chat completions, embeddings, image generation, audio speech/transcription/translation, batches, and moderations.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

OPENAI_API_BASE = "https://api.openai.com/v1"

OPENAI_ENDPOINT_MAP = {
    "openai.cancel_batch": ("POST", "/batches/{batch_id}/cancel"),
    "openai.create_audio_transcription": ("POST", "/audio/transcriptions"),
    "openai.create_audio_translation": ("POST", "/audio/translations"),
    "openai.create_batch": ("POST", "/batches"),
    "openai.create_embeddings": ("POST", "/embeddings"),
    "openai.create_image": ("POST", "/images/generations"),
    "openai.create_moderation": ("POST", "/moderations"),
    "openai.create_response": ("POST", "/chat/completions"),
    "openai.create_speech": ("POST", "/audio/speech"),
    "openai.get_batch": ("GET", "/batches/{batch_id}"),
    "openai.get_input_token_counts": ("POST", "/responses/input_tokens"),
    "openai.get_model": ("GET", "/models/{model}"),
    "openai.get_response": ("GET", "/responses/{response_id}"),
    "openai.list_input_items": ("GET", "/responses/{response_id}/input_items"),
    "openai.list_models": ("GET", "/models"),
}

def _openai_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("OpenAI API Key required. Please connect your OpenAI account first.")
    return str(token).strip()

class OpenAIDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = OPENAI_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "cancel" in action_meta["name"] else "GET", "/models")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _openai_headers(api_key)

        path = self.endpoint_template
        for var in ["batch_id", "model", "response_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{OPENAI_API_BASE}{path}"
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
            raise ValueError(f"OpenAI API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class OpenAIProvider(Provider):
    def __init__(self):
        super().__init__(
            service="openai",
            display_name="OpenAI",
            category="AI",
            auth_types=["api_key"],
            description="Leading AI research and deployment company providing state-of-the-art language models, vision, embeddings, and speech systems.",
            homepage_url="https://openai.com",
            base_url=OPENAI_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "OpenAI API Key",
                    "placeholder": "sk-proj-...",
                    "description": "OpenAI secret API key generated in the OpenAI Platform console.",
                    "docs_url": "https://platform.openai.com/api-keys",
                    "docs_label": "OpenAI API Keys Console",
                    "setup_guide": {
                        "title": "OpenAI API Key Guide",
                        "docs_url": "https://platform.openai.com/api-keys",
                        "docs_label": "OpenAI API Keys Dashboard",
                        "instructions": [
                            "1. Sign in to the OpenAI Platform at platform.openai.com.",
                            "2. Navigate to Dashboard > API Keys.",
                            "3. Click 'Create new secret key', enter a name (e.g. 'ConnectorHub').",
                            "4. Copy the key (starts with 'sk-proj-' or 'sk-') and paste it below."
                        ],
                        "scopes": ["model.read", "model.request"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "sk-proj-...",
                            "description": "OpenAI Secret API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("openai"):
            self.register_action(OpenAIDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate OpenAI API Key by querying GET /v1/models."""
        api_key = _extract_token(credential)
        headers = _openai_headers(api_key)
        url = f"{OPENAI_API_BASE}/models"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach OpenAI API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid OpenAI API Key. OpenAI returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"OpenAI credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        models = [m.get("id") for m in body.get("data", []) if isinstance(m, dict)]
        return {
            "valid": True,
            "accountId": "openai_api_key",
            "displayName": "OpenAI API Key",
            "metadata": {
                "validationEndpoint": "/v1/models",
                "modelCount": len(models),
                "sampleModels": models[:5]
            }
        }

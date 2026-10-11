"""
GroqCloud Provider for ConnectorHub.
Loads and registers 5 actions from 'actions_catalog.json'.
Supports ultra-fast LPU inference for chat completions, Whisper audio transcription and translation, and model management.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

GROQCLOUD_API_BASE = "https://api.groq.com/openai/v1"

GROQCLOUD_ENDPOINT_MAP = {
    "groqcloud.create_audio_transcription": ("POST", "/audio/transcriptions"),
    "groqcloud.create_audio_translation": ("POST", "/audio/translations"),
    "groqcloud.create_chat_completion": ("POST", "/chat/completions"),
    "groqcloud.get_model": ("GET", "/models/{model}"),
    "groqcloud.list_models": ("GET", "/models"),
}

def _groqcloud_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("GroqCloud API Key required. Please connect your GroqCloud account first.")
    return str(token).strip()

class GroqCloudDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = GROQCLOUD_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/models")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _groqcloud_headers(api_key)

        path = self.endpoint_template
        for var in ["model", "model_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{GROQCLOUD_API_BASE}{path}"
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
            raise ValueError(f"GroqCloud API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class GroqCloudProvider(Provider):
    def __init__(self):
        super().__init__(
            service="groqcloud",
            display_name="GroqCloud",
            category="AI",
            auth_types=["api_key"],
            description="Ultra-fast LPU AI inference platform delivering instantaneous responses for open-weights models and Whisper audio processing.",
            homepage_url="https://groq.com",
            base_url=GROQCLOUD_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "GroqCloud API Key",
                    "placeholder": "gsk_...",
                    "description": "GroqCloud API Key created in the GroqCloud Console.",
                    "docs_url": "https://console.groq.com/keys",
                    "docs_label": "GroqCloud API Keys Console",
                    "setup_guide": {
                        "title": "GroqCloud API Key Guide",
                        "docs_url": "https://console.groq.com/keys",
                        "docs_label": "GroqCloud Keys Dashboard",
                        "instructions": [
                            "1. Sign in to GroqCloud Console at console.groq.com.",
                            "2. Navigate to API Keys.",
                            "3. Click 'Create API Key', give it a friendly name.",
                            "4. Copy your key (starts with 'gsk_') and paste it below."
                        ],
                        "scopes": ["chat.write", "audio.write", "models.read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "gsk_...",
                            "description": "GroqCloud API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("groqcloud"):
            self.register_action(GroqCloudDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate GroqCloud API Key by querying GET /openai/v1/models."""
        api_key = _extract_token(credential)
        headers = _groqcloud_headers(api_key)
        url = f"{GROQCLOUD_API_BASE}/models"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach GroqCloud API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid GroqCloud API Key. GroqCloud returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"GroqCloud credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        models = [m.get("id") for m in body.get("data", []) if isinstance(m, dict)]
        return {
            "valid": True,
            "accountId": "groqcloud_api_key",
            "displayName": "GroqCloud API Key",
            "metadata": {
                "validationEndpoint": "/models",
                "modelCount": len(models),
                "sampleModels": models[:5]
            }
        }

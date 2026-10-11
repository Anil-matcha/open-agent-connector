"""
ElevenLabs Provider for ConnectorHub.
Loads and registers 14 actions from 'actions_catalog.json'.
Lifelike Voice AI: text-to-speech, speech-to-speech, AI voice cloning, sound effects, voice settings, history management, and account metrics.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"

ELEVENLABS_ENDPOINT_MAP = {
    "elevenlabs.create_sound_effect": ("POST", "/sound-generation"),
    "elevenlabs.delete_history_item": ("DELETE", "/history/{history_item_id}"),
    "elevenlabs.get_audio_from_history_item": ("GET", "/history/{history_item_id}/audio"),
    "elevenlabs.get_generated_items": ("GET", "/history"),
    "elevenlabs.get_history_item_by_id": ("GET", "/history/{history_item_id}"),
    "elevenlabs.get_models": ("GET", "/models"),
    "elevenlabs.get_user_info": ("GET", "/user"),
    "elevenlabs.get_user_subscription_info": ("GET", "/user/subscription"),
    "elevenlabs.get_voice": ("GET", "/voices/{voice_id}"),
    "elevenlabs.get_voice_settings": ("GET", "/voices/{voice_id}/settings"),
    "elevenlabs.get_voices": ("GET", "/voices"),
    "elevenlabs.search_voices": ("GET", "/voices"),
    "elevenlabs.text_to_speech": ("POST", "/text-to-speech/{voice_id}"),
    "elevenlabs.text_to_speech_with_timestamps": ("POST", "/text-to-speech/{voice_id}/with-timestamps"),
}

def _elevenlabs_headers(api_key: str) -> Dict[str, str]:
    return {
        "xi-api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("ElevenLabs API Key required. Please connect your ElevenLabs account first.")
    return str(token).strip()

class ElevenLabsDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "AI"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = ELEVENLABS_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "speech" in action_meta["name"] else "GET", "/voices")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _elevenlabs_headers(api_key)

        path = self.endpoint_template
        for var in ["voice_id", "voiceId", "history_item_id", "historyItemId"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))
            # normalize camelCase/snake_case
            alt = "voice_id" if var == "voiceId" else "voiceId"
            if "{" + alt + "}" in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace("{" + alt + "}", urllib.parse.quote(str(val), safe=""))

        url = f"{ELEVENLABS_API_BASE}{path}"
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
                err_msg = data.get("detail", {}).get("message") if isinstance(data.get("detail"), dict) else data.get("detail") or data.get("message") or str(data)
            raise ValueError(f"ElevenLabs API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class ElevenLabsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="elevenlabs",
            display_name="ElevenLabs",
            category="AI",
            auth_types=["api_key"],
            description="The most natural and realistic AI voices for creators and developers, featuring multilingual speech synthesis and voice cloning.",
            homepage_url="https://elevenlabs.io",
            base_url=ELEVENLABS_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "ElevenLabs API Key",
                    "placeholder": "xi-api-key...",
                    "description": "ElevenLabs API key sent with the xi-api-key header.",
                    "docs_url": "https://elevenlabs.io/app/api-keys",
                    "docs_label": "ElevenLabs API Keys",
                    "setup_guide": {
                        "title": "ElevenLabs API Key Guide",
                        "docs_url": "https://elevenlabs.io/app/api-keys",
                        "docs_label": "ElevenLabs Dashboard",
                        "instructions": [
                            "1. Sign in to ElevenLabs at elevenlabs.io.",
                            "2. Navigate to Profile > API Keys (or elevenlabs.io/app/api-keys).",
                            "3. Click 'Create API Key' or reveal your existing key.",
                            "4. Copy your key and paste it below."
                        ],
                        "scopes": ["voices.read", "text-to-speech.write", "user.read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "xi-api-key...",
                            "description": "ElevenLabs API Key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("elevenlabs"):
            self.register_action(ElevenLabsDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate ElevenLabs API Key by querying GET /v1/user."""
        api_key = _extract_token(credential)
        headers = _elevenlabs_headers(api_key)
        url = f"{ELEVENLABS_API_BASE}/user"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach ElevenLabs API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid ElevenLabs API Key. ElevenLabs returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"ElevenLabs credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        sub = body.get("subscription", {})
        first_name = body.get("first_name", "")
        display = f"ElevenLabs ({first_name})" if first_name else "ElevenLabs Account"
        return {
            "valid": True,
            "accountId": body.get("user_id") or "elevenlabs_user",
            "displayName": display,
            "metadata": {
                "validationEndpoint": "/user",
                "characterCount": sub.get("character_count", 0),
                "characterLimit": sub.get("character_limit", 0),
                "tier": sub.get("tier", "free")
            }
        }

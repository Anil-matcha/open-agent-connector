"""
Microsoft Text Translate Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Azure AI Translator API v3.0 specifications.
"""
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

TRANSLATE_API_BASE = "https://api.cognitive.microsofttranslator.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("Azure Cognitive / Microsoft Translator API Key required. Please connect your account first.")
    return str(token).strip()

def _translate_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    token = _extract_token(credential)
    headers = {
        "Ocp-Apim-Subscription-Key": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    region = (credential or {}).get("region")
    if region:
        headers["Ocp-Apim-Subscription-Region"] = str(region).strip()
    return headers

class MicrosoftTextTranslateDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/translate?api-version=3.0")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        headers = _translate_headers(credential)
        inputs = dict(input_data or {})

        url = f"{TRANSLATE_API_BASE}{self.endpoint_template}"
        assert_public_url(url)

        body = None
        params = {}

        if self.method in ["POST", "PUT"]:
            # Azure Translator expects list of {"Text": "..."} in body
            texts = inputs.pop("texts", None)
            if texts is not None:
                if isinstance(texts, str):
                    texts = [texts]
                body = [{"Text": str(t)} if isinstance(t, str) else t for t in texts]
            elif "entries" in inputs:
                body = inputs.pop("entries")
            else:
                body = inputs

            # Remaining parameters go to query string
            for k, v in inputs.items():
                if v is not None:
                    if isinstance(v, (list, tuple)):
                        params[k] = ",".join(str(item) for item in v)
                    else:
                        params[k] = str(v)
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
            json_body=body if body is not None and self.method in ["POST", "PUT"] else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"Microsoft Translator API error ({resp.status_code}): {msg}")

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class MicrosoftTextTranslateProvider(Provider):
    def __init__(self):
        super().__init__(
            service="microsoft_text_translate",
            display_name="Microsoft Text Translate",
            category="AI & Machine Learning",
            auth_types=["api_key"],
            description="Azure AI Microsoft Translator for text translation, language detection, sentence breaking, and dictionary lookups.",
            homepage_url="https://azure.microsoft.com/services/cognitive-services/translator/",
            base_url=TRANSLATE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Azure Translator Key",
                    "placeholder": "Azure Cognitive Services Subscription Key",
                    "description": "Subscription key from Azure Portal > Azure AI Translator resource.",
                    "docs_url": "https://learn.microsoft.com/en-us/azure/ai-services/translator/reference/v3-0-reference",
                    "docs_label": "Azure Translator API Docs",
                    "setup_guide": {
                        "title": "Azure AI Translator Key Setup Guide",
                        "docs_url": "https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.CognitiveServices%2Faccounts",
                        "docs_label": "Azure AI Services Portal",
                        "instructions": [
                            "1. In the Azure Portal (portal.azure.com), create or open your Translator resource.",
                            "2. Navigate to Keys and Endpoint.",
                            "3. Copy KEY 1 or KEY 2 and paste below. (Optionally include Location/Region if multi-service)."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Subscription Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "Subscription Key",
                            "description": "Ocp-Apim-Subscription-Key"
                        },
                        {
                            "key": "region",
                            "label": "Region (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "e.g. global, eastus, westeurope",
                            "description": "Resource location/region."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("microsoft_text_translate"):
            self.register_action(MicrosoftTextTranslateDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Azure Translator key by querying supported languages."""
        headers = _translate_headers(credential)
        url = f"{TRANSLATE_API_BASE}/languages?api-version=3.0&scope=translation"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Microsoft Translator API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Azure Translator subscription key (401 Unauthorized).")
        elif resp.status_code != 200:
            raise ValueError(f"Microsoft Translator validation failed ({resp.status_code}): {resp.text[:200]}")

        return {
            "account_id": "azure_translator",
            "display_name": "Azure Translator",
            "granted_scopes": [],
            "avatar_url": None
        }

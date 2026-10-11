"""
Microsoft Clarity Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Microsoft Clarity Data Export API v1 specifications.
"""
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CLARITY_API_BASE = "https://www.clarity.ms/export-data/api/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("Microsoft Clarity API Token required. Please connect your Clarity account first.")
    return str(token).strip()

class MicrosoftClarityDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Analytics"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/project-live-insights")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }
        inputs = dict(input_data or {})

        url = f"{CLARITY_API_BASE}{self.endpoint_template}"
        assert_public_url(url)

        params = {}
        for k, v in inputs.items():
            if v is not None:
                params[k] = str(v)

        resp = await execute_guarded_request(
            client=client,
            method=self.method,
            url=url,
            headers=headers,
            params=params if params else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            raise ValueError(f"Microsoft Clarity API error ({resp.status_code}): {err_text[:300]}")

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class MicrosoftClarityProvider(Provider):
    def __init__(self):
        super().__init__(
            service="microsoft_clarity",
            display_name="Microsoft Clarity",
            category="Data & Analytics",
            auth_types=["api_key"],
            description="Microsoft Clarity analytics API for exporting session recordings, heatmaps, and user insights.",
            homepage_url="https://clarity.microsoft.com",
            base_url=CLARITY_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Clarity API Token",
                    "placeholder": "Clarity Export API Token",
                    "description": "Microsoft Clarity data export access token from Settings > API Tokens.",
                    "docs_url": "https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-api",
                    "docs_label": "Clarity API Documentation",
                    "setup_guide": {
                        "title": "Microsoft Clarity API Setup Guide",
                        "docs_url": "https://clarity.microsoft.com",
                        "docs_label": "Clarity Dashboard",
                        "instructions": [
                            "1. Go to Microsoft Clarity Dashboard (clarity.microsoft.com) and open your project.",
                            "2. Navigate to Settings > API Access / Export API.",
                            "3. Generate and copy your API Token, then paste below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Clarity API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "API Token",
                            "description": "Clarity Export Token"
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("microsoft_clarity"):
            self.register_action(MicrosoftClarityDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Clarity token."""
        token = _extract_token(credential)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }
        url = f"{CLARITY_API_BASE}/project-live-insights?numOfDays=1"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Microsoft Clarity API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Microsoft Clarity API Token (Unauthorized).")
        elif resp.status_code not in [200, 204]:
            raise ValueError(f"Microsoft Clarity validation failed ({resp.status_code}): {resp.text[:200]}")

        return {
            "account_id": "clarity_account",
            "display_name": "Microsoft Clarity",
            "granted_scopes": [],
            "avatar_url": None
        }

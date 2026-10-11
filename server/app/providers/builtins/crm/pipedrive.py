"""
Pipedrive Provider for ConnectorHub.
Loads and registers 27 actions from 'actions_catalog.json'.
Sales CRM and pipeline management: Deals, Persons, Organizations, Activities, Pipelines, Stages, and Search via Pipedrive REST API v1.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

PIPEDRIVE_API_BASE = "https://api.pipedrive.com/v1"

PIPEDRIVE_ENDPOINT_MAP = {
    "pipedrive.create_activity": ("POST", "/activities"),
    "pipedrive.create_deal": ("POST", "/deals"),
    "pipedrive.create_organization": ("POST", "/organizations"),
    "pipedrive.create_person": ("POST", "/persons"),
    "pipedrive.delete_activity": ("DELETE", "/activities/{id}"),
    "pipedrive.delete_deal": ("DELETE", "/deals/{id}"),
    "pipedrive.delete_organization": ("DELETE", "/organizations/{id}"),
    "pipedrive.delete_person": ("DELETE", "/persons/{id}"),
    "pipedrive.get_activity": ("GET", "/activities/{id}"),
    "pipedrive.get_deal": ("GET", "/deals/{id}"),
    "pipedrive.get_organization": ("GET", "/organizations/{id}"),
    "pipedrive.get_person": ("GET", "/persons/{id}"),
    "pipedrive.get_pipeline": ("GET", "/pipelines/{id}"),
    "pipedrive.get_stage": ("GET", "/stages/{id}"),
    "pipedrive.list_activities": ("GET", "/activities"),
    "pipedrive.list_deals": ("GET", "/deals"),
    "pipedrive.list_organizations": ("GET", "/organizations"),
    "pipedrive.list_persons": ("GET", "/persons"),
    "pipedrive.list_pipelines": ("GET", "/pipelines"),
    "pipedrive.list_stages": ("GET", "/stages"),
    "pipedrive.search_deals": ("GET", "/deals/search"),
    "pipedrive.search_organizations": ("GET", "/organizations/search"),
    "pipedrive.search_persons": ("GET", "/persons/search"),
    "pipedrive.update_activity": ("PUT", "/activities/{id}"),
    "pipedrive.update_deal": ("PUT", "/deals/{id}"),
    "pipedrive.update_organization": ("PUT", "/organizations/{id}"),
    "pipedrive.update_person": ("PUT", "/persons/{id}"),
}

def _pipedrive_headers(token: str) -> Dict[str, str]:
    return {
        "x-api-token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Pipedrive API Token required. Please connect your Pipedrive account first.")
    return str(token).strip()

class PipedriveDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "CRM"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = PIPEDRIVE_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] else "GET", "/deals")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _pipedrive_headers(token)

        path = self.endpoint_template
        for var in ["id", "dealId", "personId", "organizationId", "activityId", "pipelineId", "stageId"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))
            # handle {id} substitution from specific field
            if "{id}" in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace("{id}", urllib.parse.quote(str(val), safe=""))

        url = f"{PIPEDRIVE_API_BASE}{path}"
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
                err_msg = data.get("error") or data.get("message") or str(data)
            raise ValueError(f"Pipedrive API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class PipedriveProvider(Provider):
    def __init__(self):
        super().__init__(
            service="pipedrive",
            display_name="Pipedrive",
            category="CRM",
            auth_types=["api_key"],
            description="Visual sales CRM and pipeline management software designed by salespeople, for salespeople.",
            homepage_url="https://www.pipedrive.com",
            base_url=PIPEDRIVE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Pipedrive API Token",
                    "placeholder": "pipedrive_api_token...",
                    "description": "Personal API token found in Settings > Personal preferences > API.",
                    "docs_url": "https://pipedrive.readme.io/docs/how-to-find-the-api-token",
                    "docs_label": "Pipedrive API Token Guide",
                    "setup_guide": {
                        "title": "Pipedrive API Token Guide",
                        "docs_url": "https://app.pipedrive.com/settings/personal/api",
                        "docs_label": "Pipedrive API Settings",
                        "instructions": [
                            "1. Sign in to your Pipedrive account at app.pipedrive.com.",
                            "2. Click your user avatar (top right) > Personal preferences.",
                            "3. Navigate to the 'API' tab.",
                            "4. Copy your personal API token and paste it below."
                        ],
                        "scopes": ["deals:full", "contacts:full", "activities:full"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "pipedrive_api_token...",
                            "description": "Pipedrive personal API token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("pipedrive"):
            self.register_action(PipedriveDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Pipedrive API Token by querying GET /users/me."""
        token = _extract_token(credential)
        headers = _pipedrive_headers(token)
        url = f"{PIPEDRIVE_API_BASE}/users/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Pipedrive API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Pipedrive API token. Pipedrive returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Pipedrive credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user_data = body.get("data", {})
        return {
            "valid": True,
            "accountId": str(user_data.get("id", "pipedrive_user")),
            "displayName": user_data.get("name") or "Pipedrive User",
            "metadata": {
                "validationEndpoint": "/users/me",
                "email": user_data.get("email"),
                "companyName": user_data.get("company_name")
            }
        }

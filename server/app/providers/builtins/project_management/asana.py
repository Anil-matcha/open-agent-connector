"""
Asana Provider for ConnectorHub.
Loads and registers 101 actions from 'actions_catalog.json'.
Comprehensive support for tasks, projects, sections, custom fields, stories, tags, and workspaces via Asana API v1.0.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ASANA_API_BASE = "https://app.asana.com/api/1.0"

def _asana_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Asana Personal Access Token or OAuth Access Token required. Please connect your Asana account first.")
    return str(token).strip()

class AsanaDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/users/me")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _asana_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in [
            "task_gid", "project_gid", "section_gid", "custom_field_gid", "workspace_gid",
            "user_gid", "team_gid", "story_gid", "tag_gid", "attachment_gid", "gid", "id"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{ASANA_API_BASE}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = None
        params = None

        if req_method in ["POST", "PUT", "PATCH"]:
            # Asana expects request bodies wrapped in {"data": ...}
            if "data" in inputs and isinstance(inputs["data"], dict):
                json_body = inputs
            else:
                json_body = {"data": inputs}
        elif req_method == "GET":
            params = {k: v for k, v in inputs.items() if v is not None}

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
            if isinstance(data, dict) and "errors" in data:
                err_msg = "; ".join(e.get("message", "Error") for e in data["errors"])
            raise ValueError(f"Asana API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data.get("data", data) if isinstance(data, dict) else data}

class AsanaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="asana",
            display_name="Asana",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="Work and project management platform designed to help teams orchestrate their work from daily tasks to strategic initiatives.",
            homepage_url="https://asana.com",
            base_url=ASANA_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Personal Access Token (PAT)",
                    "placeholder": "1/1234567890:...",
                    "description": "Personal Access Token generated from your Asana Developer Console.",
                    "docs_url": "https://developers.asana.com/docs/personal-access-token",
                    "docs_label": "Asana PAT Guide",
                    "setup_guide": {
                        "title": "Asana Personal Access Token Guide",
                        "docs_url": "https://app.asana.com/0/developer-console",
                        "docs_label": "Asana Developer Console",
                        "instructions": [
                            "1. Open Asana Developer Console (app.asana.com/0/developer-console).",
                            "2. Under 'Personal access tokens', click '+ New access token'.",
                            "3. Provide a description (e.g., 'ConnectorHub') and copy the generated token.",
                            "4. Paste your token below."
                        ],
                        "scopes": ["default"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "1/1234567890:...",
                            "description": "Asana Personal Access Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Asana OAuth 2.0",
                    "placeholder": "1/1234567890:...",
                    "description": "Connect via official Asana OAuth 2.0 PKCE flow.",
                    "docs_url": "https://developers.asana.com/docs/oauth",
                    "docs_label": "Asana OAuth Documentation",
                    "setup_guide": {
                        "title": "Asana OAuth 2.0 Setup",
                        "docs_url": "https://app.asana.com/0/developer-console",
                        "docs_label": "Asana Developer Console",
                        "instructions": [
                            "1. Go to Asana Developer Console and click 'Create app'.",
                            "2. Add your Redirect URL to OAuth Settings.",
                            "3. Add your Client ID and Client Secret in ConnectorHub settings.",
                            "4. Authorize access to your Asana organization."
                        ],
                        "scopes": ["default"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "1/...",
                            "description": "Asana OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("asana"):
            self.register_action(AsanaDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Asana credentials against GET https://app.asana.com/api/1.0/users/me."""
        token = _extract_token(credential)
        headers = _asana_headers(token)
        url = f"{ASANA_API_BASE}/users/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Asana API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Asana credentials. Asana returned Unauthorized (401/403).")
        elif resp.status_code != 200:
            raise ValueError(f"Asana credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        user_data = body.get("data", {})
        account_id = user_data.get("gid") or "asana-user"
        name = user_data.get("name") or user_data.get("email") or "Asana User"
        email = user_data.get("email")
        photo = (user_data.get("photo") or {}).get("image_128x128")

        workspaces = user_data.get("workspaces", [])
        ws_name = workspaces[0].get("name") if workspaces else None
        display_name = f"Asana ({name} - {ws_name})" if ws_name else f"Asana ({name})"

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["default"],
            "avatar_url": photo
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """SSRF-guarded proxy forwarder for Asana API v1.0."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{ASANA_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_asana_headers(token))

        payload = body
        if payload and method.upper() in ["POST", "PUT", "PATCH"]:
            if isinstance(payload, dict) and "data" not in payload:
                payload = {"data": payload}

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=payload
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }

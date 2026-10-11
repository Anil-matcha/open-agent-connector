"""
ClickUp Provider for ConnectorHub.
Loads and registers 68 actions from 'actions_catalog.json'.
Comprehensive management of workspaces, spaces, folders, lists, tasks, checklists, comments, and views via ClickUp API v2.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"

def _clickup_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("ClickUp Personal API Token or OAuth Access Token required. Please connect your ClickUp account first.")

    token_str = str(token).strip()
    # ClickUp personal API token is passed as raw Authorization header without Bearer,
    # whereas OAuth tokens are passed with Bearer or raw depending on authType.
    is_oauth = bool(cred.get("accessToken")) and not str(token_str).startswith("pk_")
    auth_val = f"Bearer {token_str}" if is_oauth and not token_str.startswith("Bearer ") else token_str

    return {
        "Authorization": auth_val,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class ClickUpDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/user")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        headers = _clickup_headers(credential)
        inputs = dict(input_data or {})

        # Path variable substitution
        path = self.endpoint_template
        for var in [
            "team_id", "space_id", "folder_id", "list_id", "task_id", "checklist_id",
            "checklist_item_id", "comment_id", "view_id", "field_id", "template_id",
            "tag_name", "links_to", "user_id", "id"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{CLICKUP_API_BASE}{path}"
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
                err_msg = data.get("err") or data.get("error") or str(data)
            raise ValueError(f"ClickUp API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class ClickUpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="clickup",
            display_name="ClickUp",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="All-in-one productivity platform for tasks, projects, docs, and team collaboration.",
            homepage_url="https://clickup.com",
            base_url=CLICKUP_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "ClickUp Personal API Token",
                    "placeholder": "pk_12345678_...",
                    "description": "Personal API token generated from your ClickUp user settings.",
                    "docs_url": "https://clickup.com/api/developer-portal/authentication/",
                    "docs_label": "ClickUp Authentication Docs",
                    "setup_guide": {
                        "title": "ClickUp API Token Guide",
                        "docs_url": "https://app.clickup.com/settings/apps",
                        "docs_label": "ClickUp App Settings",
                        "instructions": [
                            "1. In ClickUp, click your profile avatar and go to Settings > Apps.",
                            "2. Under 'API Token', click 'Generate' (or copy existing token).",
                            "3. Copy the token (starts with 'pk_') and paste below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "pk_...",
                            "description": "ClickUp personal API token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "ClickUp OAuth 2.0",
                    "placeholder": "eyJhbGci...",
                    "description": "Connect via ClickUp OAuth 2.0 app authorization.",
                    "docs_url": "https://clickup.com/api/developer-portal/authentication/#oauth-flow",
                    "docs_label": "ClickUp OAuth Flow",
                    "setup_guide": {
                        "title": "ClickUp OAuth App Setup",
                        "docs_url": "https://app.clickup.com/settings/apps",
                        "docs_label": "ClickUp Developer Settings",
                        "instructions": [
                            "1. Go to ClickUp Settings > Integrations > ClickUp API.",
                            "2. Create an App with your Redirect URL.",
                            "3. Add your Client ID and Client Secret into ConnectorHub settings.",
                            "4. Connect and authorize your workspace."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "ClickUp OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("clickup"):
            self.register_action(ClickUpDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate ClickUp credentials against GET https://api.clickup.com/api/v2/user."""
        headers = _clickup_headers(credential)
        url = f"{CLICKUP_API_BASE}/user"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach ClickUp API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid ClickUp token. ClickUp returned 401/403 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"ClickUp credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        user_data = body.get("user", {})
        account_id = str(user_data.get("id") or "clickup-user")
        name = user_data.get("username") or user_data.get("email") or "ClickUp User"
        avatar_url = user_data.get("profilePicture")

        return {
            "account_id": account_id,
            "display_name": f"ClickUp ({name})",
            "granted_scopes": [],
            "avatar_url": avatar_url
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
        """SSRF-guarded proxy forwarder for ClickUp API v2."""
        auth_headers = _clickup_headers(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{CLICKUP_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(auth_headers)

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
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

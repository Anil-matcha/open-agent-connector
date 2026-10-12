"""
Box Provider for ConnectorHub.
Loads and registers 13 actions from 'actions_catalog.json'.
Enterprise content management, file browsing, and folder collaboration via Box Content API v2.0.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

BOX_API_BASE = "https://api.box.com/2.0"
BOX_UPLOAD_BASE = "https://upload.box.com/api/2.0"

BOX_ENDPOINT_MAP = {
    "box.get_current_user": ("GET", "/users/me"),
    "box.get_file": ("GET", "/files/{fileId}"),
    "box.get_folder": ("GET", "/folders/{folderId}"),
    "box.list_folder_items": ("GET", "/folders/{folderId}/items"),
    "box.list_folder_items_continue": ("GET", "/folders/{folderId}/items"),
    "box.search": ("GET", "/search"),
    "box.create_folder": ("POST", "/folders"),
    "box.update_file": ("PUT", "/files/{fileId}"),
    "box.update_folder": ("PUT", "/folders/{folderId}"),
    "box.delete_file": ("DELETE", "/files/{fileId}"),
    "box.delete_folder": ("DELETE", "/folders/{folderId}"),
    "box.download_file": ("GET", "/files/{fileId}/content"),
    "box.upload_file": ("POST", f"{BOX_UPLOAD_BASE}/files/content"),
}

def _box_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("developerToken") or cred.get("token") or ""
    if not str(token).strip():
        raise ValueError("Box access token or developer token required. Please connect your Box account first.")

    return {
        "Authorization": f"Bearer {str(token).strip()}",
        "Accept": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class BoxDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Storage"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        mapped = BOX_ENDPOINT_MAP.get(action_meta["id"], ("GET", "/users/me"))
        self.method = mapped[0]
        self.endpoint_template = mapped[1]

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        headers = _box_headers(credential)

        path = self.endpoint_template
        for var in ["fileId", "file_id", "folderId", "folder_id", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{BOX_API_BASE}/{path.lstrip('/')}"
        assert_public_url(url)

        req_method = self.method

        if self.id == "box.create_folder":
            # Box expects {"name": "...", "parent": {"id": "..."}}
            name = inputs.pop("name", "")
            parent_id = inputs.pop("parentFolderId", None) or inputs.pop("parent_folder_id", "0")
            json_body = {"name": name, "parent": {"id": str(parent_id)}}
            headers["Content-Type"] = "application/json"
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=url,
                headers=headers,
                json_body=json_body
            )
        elif req_method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"
            resp = await execute_guarded_request(
                client=client,
                method=req_method,
                url=url,
                headers=headers,
                json_body=inputs
            )
        else:
            # GET / DELETE
            params = {k: v for k, v in inputs.items() if v is not None}
            resp = await execute_guarded_request(
                client=client,
                method=req_method,
                url=url,
                headers=headers,
                params=params
            )

        try:
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                err_msg = res_data.get("message") or res_data.get("error_description") or str(res_data)
            raise ValueError(f"Box API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class BoxProvider(Provider):
    def __init__(self):
        super().__init__(
            service="box",
            display_name="Box",
            category="Storage",
            auth_types=["oauth2", "api_key"],
            description="Content Cloud for secure file sharing, storage, and workflow collaboration.",
            homepage_url="https://www.box.com",
            base_url=BOX_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Box OAuth 2.0",
                    "description": "Connect your Box account via OAuth 2.0 authorization code flow.",
                    "docs_url": "https://developer.box.com/guides/authentication/oauth2/oauth2-setup/",
                    "docs_label": "Box OAuth 2.0 Setup Guide",
                    "setup_guide": {
                        "title": "Box App Setup Guide",
                        "docs_url": "https://app.box.com/developers/console",
                        "docs_label": "Box Developer Console",
                        "instructions": [
                            "1. Go to the Box Developer Console (https://app.box.com/developers/console).",
                            "2. Click 'Create New App' and choose 'Custom App'.",
                            "3. Select 'User Authentication (OAuth 2.0)' as the authentication method.",
                            "4. In the Configuration tab, add your Redirect URI.",
                            "5. Check 'Read all files and folders stored in Box' and 'Write all files and folders'.",
                            "6. Copy your Client ID and Client Secret."
                        ],
                        "scopes": [
                            "root_readwrite",
                            "manage_webhook"
                        ]
                    }
                },
                {
                    "type": "api_key",
                    "label": "Box Developer Token",
                    "placeholder": "bx_dev_...",
                    "description": "Temporary developer token generated from Box Developer Console > App > Configuration.",
                    "docs_url": "https://developer.box.com/guides/authentication/tokens/developer-tokens/",
                    "docs_label": "Box Developer Tokens Guide",
                    "setup_guide": {
                        "title": "Box Developer Token Guide",
                        "docs_url": "https://app.box.com/developers/console",
                        "docs_label": "Box Developer Console",
                        "instructions": [
                            "1. Go to Box Developer Console (https://app.box.com/developers/console).",
                            "2. Select your Custom App and open the 'Configuration' tab.",
                            "3. Scroll to 'Developer Token' section and click 'Generate Developer Token'.",
                            "4. Copy the token and paste it here."
                        ],
                        "scopes": ["root_readwrite"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Developer Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "Box Developer Token",
                            "description": "Box Developer Token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("box"):
            self.register_action(BoxDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Box credentials by querying GET /2.0/users/me."""
        headers = _box_headers(credential)
        url = f"{BOX_API_BASE}/users/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Box API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Box credentials. Box returned Unauthorized (401/403).")
        elif resp.status_code != 200:
            raise ValueError(f"Box credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user_id = str(body.get("id", "box_user"))
        name = body.get("name") or body.get("login") or f"Box User ({user_id})"

        return {
            "valid": True,
            "accountId": user_id,
            "displayName": name,
            "metadata": {
                "validationEndpoint": "/users/me",
                "login": body.get("login"),
                "status": body.get("status"),
                "space_amount": body.get("space_amount"),
                "space_used": body.get("space_used")
            }
        }

"""
Google Slides Provider for ConnectorHub.
Loads and registers 7 actions for presentations and slide pages.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://slides.googleapis.com/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["accessToken", "apiKey", "token", "access_token", "api_key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    token = _extract_token(credential)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_presentation": ["POST", "/presentations", [], ["title"]],
    "get_page_thumbnail2": ["GET", "/presentations/{presentationId}/pages/{pageObjectId}/thumbnail", ["presentationId", "pageObjectId"], []],
    "presentations_batch_update": ["POST", "/presentations/{presentationId}:batchUpdate", ["presentationId"], ["requests"]],
    "presentations_copy_from_template": ["POST", "/presentations/{presentationId}/copy", ["presentationId"], ["title"]],
    "presentations_get": ["GET", "/presentations/{presentationId}", ["presentationId"], []],
    "presentations_pages_get": ["GET", "/presentations/{presentationId}/pages/{pageObjectId}", ["presentationId", "pageObjectId"], []],
    "presentations_pages_get_thumbnail": ["GET", "/presentations/{presentationId}/pages/{pageObjectId}/thumbnail", ["presentationId", "pageObjectId"], []],
}

class GoogleSlidesDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Productivity"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        headers = _build_headers(cred)
        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        target_url = f"{DEFAULT_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or req_method == "GET":
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message") or err_msg
            except Exception:
                pass
            raise ValueError(f"Google Slides API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class GoogleSlidesProvider(Provider):
    def __init__(self):
        super().__init__(
            service="googleslides",
            display_name="Google Slides",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="Google Slides API v1 for presentations, slides, templates, page elements, and thumbnails with 7 actions.",
            homepage_url="https://workspace.google.com/products/slides/",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Google OAuth 2.0 Access Token",
                    "placeholder": "ya29.a0...",
                    "description": "Authenticate via official Google Workspace OAuth 2.0 flow.",
                    "docs_url": "https://developers.google.com/slides/api",
                    "docs_label": "Google Slides Documentation",
                    "setup_guide": {
                        "title": "Google Slides OAuth Setup Guide",
                        "docs_url": "https://console.cloud.google.com/apis/credentials",
                        "docs_label": "Google Cloud Console",
                        "instructions": [
                            "1. Go to Google Cloud Console and enable Google Slides API.",
                            "2. Set redirect URI: https://connector.suparagent.ai/api/oauth/googleslides/callback",
                            "3. Add scope: https://www.googleapis.com/auth/presentations",
                            "4. Connect via Hosted Connect button."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/presentations",
                            "https://www.googleapis.com/auth/drive.readonly"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("googleslides"):
            self.register_action(GoogleSlidesDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Google Slides access token is required.")

        val_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Google Slides connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Google Slides credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Google Slides validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": data.get("email") or data.get("name") or "Google Slides Account"
        }

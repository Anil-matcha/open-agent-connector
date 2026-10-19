"""
Instagram Provider for ConnectorHub.
Loads and registers 9 actions for Meta / Instagram Graph API.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://graph.instagram.com/v21.0"

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
    "create_comment": ["POST", "/{mediaId}/comments", ["mediaId"], ["message"]],
    "get_current_user": ["GET", "/me", [], ["fields"]],
    "get_media": ["GET", "/{mediaId}", ["mediaId"], ["fields"]],
    "get_media_insights": ["GET", "/{mediaId}/insights", ["mediaId"], ["metric"]],
    "list_media": ["GET", "/me/media", [], ["limit", "after", "before", "fields"]],
    "list_media_comments": ["GET", "/{mediaId}/comments", ["mediaId"], ["limit", "after", "fields"]],
    "publish_media": ["POST", "/me/media_publish", [], ["creation_id"]],
    "reply_to_comment": ["POST", "/{commentId}/replies", ["commentId"], ["message"]],
    "send_message": ["POST", "/me/messages", [], ["recipient", "message"]],
}

class InstagramDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Marketing"),
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
            raise ValueError(f"Instagram API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class InstagramProvider(Provider):
    def __init__(self):
        super().__init__(
            service="instagram",
            display_name="Instagram",
            category="Marketing",
            auth_types=["oauth2"],
            description="Instagram Graph API for media publishing, carousel posts, comments, profile info, and business insights with 9 actions.",
            homepage_url="https://www.instagram.com",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Instagram OAuth 2.0 User Token",
                    "placeholder": "IGQVJ...",
                    "description": "Connect via official Meta / Instagram Business OAuth flow.",
                    "docs_url": "https://developers.facebook.com/docs/instagram-platform",
                    "docs_label": "Instagram Graph API Documentation",
                    "setup_guide": {
                        "title": "Instagram OAuth Setup Guide",
                        "docs_url": "https://developers.facebook.com/apps/",
                        "docs_label": "Meta for Developers",
                        "instructions": [
                            "1. Go to Meta for Developers (developers.facebook.com) and create an App.",
                            "2. Add Instagram Graph API and set Redirect URI to: https://connector.suparagent.ai/api/oauth/instagram/callback",
                            "3. Request permissions for instagram_business_basic and instagram_business_content_publish.",
                            "4. Connect your account via the Hosted Connect button."
                        ],
                        "scopes": [
                            "instagram_business_basic",
                            "instagram_business_manage_comments",
                            "instagram_business_content_publish",
                            "instagram_business_manage_messages"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "IGQVJ..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("instagram"):
            self.register_action(InstagramDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Instagram access token is required.")

        val_url = f"{DEFAULT_API_BASE}/me?fields=id,username"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Instagram connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Instagram credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Instagram validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": data.get("username") or "Instagram Account"
        }

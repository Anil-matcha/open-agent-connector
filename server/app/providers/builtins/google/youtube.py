"""
YouTube Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Google YouTube Data API v3 specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def _youtube_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("YouTube OAuth Access Token or Bearer Token required. Please connect your YouTube account first.")
    return str(token).strip()

class YouTubeDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/videos")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _youtube_headers(token)
        inputs = dict(input_data or {})

        # 1. Path variables substitution
        path = self.endpoint_template
        for var in ["id", "captionId", "playlistId", "videoId"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{YOUTUBE_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

        # Default 'part' parameter if needed
        if self.method == "GET" and "part" not in inputs and "captions" not in path:
            params["part"] = "snippet"

        if self.method in ["POST", "PUT", "PATCH"]:
            body = inputs
        else:
            for k, v in inputs.items():
                if v is not None:
                    if isinstance(v, bool):
                        params[k] = "true" if v else "false"
                    elif isinstance(v, (list, tuple)):
                        params[k] = ",".join(str(item) for item in v)
                    else:
                        params[k] = str(v)

        resp = await execute_guarded_request(
            client=client,
            method=self.method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=body if body is not None and self.method in ["POST", "PUT", "PATCH"] else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"YouTube Data API error ({resp.status_code}): {msg}")

        if resp.status_code == 204 or not resp.content:
            return {"success": True, "message": "Operation completed successfully"}

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class YouTubeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="youtube",
            display_name="YouTube",
            category="Design & Media",
            auth_types=["oauth2", "api_key"],
            description="Google YouTube Data API v3 for uploading videos, managing playlists, reading comments, and searching content.",
            homepage_url="https://youtube.com",
            base_url=YOUTUBE_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Google OAuth 2.0 Access Token",
                    "placeholder": "ya29.a0...",
                    "description": "Authenticate via Google OAuth 2.0 application access token with YouTube scopes.",
                    "docs_url": "https://developers.google.com/youtube/v3",
                    "docs_label": "YouTube Data API Documentation",
                    "setup_guide": {
                        "title": "YouTube Access Token Setup Guide",
                        "docs_url": "https://developers.google.com/oauthplayground",
                        "docs_label": "Google OAuth Playground",
                        "instructions": [
                            "1. Open Google OAuth Playground (developers.google.com/oauthplayground).",
                            "2. In the API list, scroll to 'YouTube Data API v3' and select the required scopes (e.g. youtube, youtube.readonly).",
                            "3. Click 'Authorize APIs' and log in with your Google account.",
                            "4. Click 'Exchange authorization code for tokens', then copy the Access token (starts with ya29...)."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/youtube",
                            "https://www.googleapis.com/auth/youtube.readonly",
                            "https://www.googleapis.com/auth/youtube.force-ssl",
                            "https://www.googleapis.com/auth/youtube.upload"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth 2.0 access token issued with YouTube scopes."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Google Bearer Token / API Token",
                    "placeholder": "ya29.a0...",
                    "description": "Authenticate via Google OAuth Bearer token.",
                    "docs_url": "https://developers.google.com/youtube/v3/getting-started",
                    "docs_label": "YouTube Getting Started Guide",
                    "setup_guide": {
                        "title": "YouTube Bearer Token Setup Guide",
                        "docs_url": "https://developers.google.com/youtube/v3/getting-started",
                        "docs_label": "YouTube Quickstart",
                        "instructions": [
                            "1. Obtain a valid Google OAuth Bearer access token.",
                            "2. Ensure the token has the necessary YouTube scopes (youtube.readonly, youtube).",
                            "3. Enter the token below to connect."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/youtube.readonly",
                            "https://www.googleapis.com/auth/youtube"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bearer Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth Bearer token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("youtube"):
            self.register_action(YouTubeDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate credentials against YouTube channels endpoint."""
        token = _extract_token(credential)
        headers = _youtube_headers(token)
        url = f"{YOUTUBE_API_BASE}/channels?part=snippet&mine=true"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach YouTube API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid YouTube credentials. Google API returned 401 Unauthorized.")
        elif resp.status_code == 403:
            raise ValueError("YouTube permission denied (403 Forbidden). Verify YouTube Data API v3 is enabled.")
        elif resp.status_code != 200:
            raise ValueError(f"YouTube credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        items = data.get("items") or []
        channel = items[0] if items else {}
        account_id = channel.get("id") or "my_channel"
        title = channel.get("snippet", {}).get("title") or account_id

        return {
            "account_id": account_id,
            "display_name": f"YouTube ({title})",
            "granted_scopes": [
                "https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtube.readonly"
            ],
            "avatar_url": None
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
        """SSRF-guarded proxy forwarder for YouTube Data API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{YOUTUBE_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_youtube_headers(token))

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

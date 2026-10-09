"""
Google Photos Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Google Photos Library & Picker REST API specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

PHOTOS_API_BASE = "https://photoslibrary.googleapis.com/v1"
PICKER_API_BASE = "https://photospicker.googleapis.com/v1"

def _photos_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Google Photos OAuth Access Token or Bearer Token required. Please connect your Google Photos account first.")
    return str(token).strip()

class GooglePhotosDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/albums")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _photos_headers(token)
        inputs = dict(input_data or {})

        # 1. Path variables substitution
        path = self.endpoint_template
        for var in ["albumId", "mediaItemId", "sessionId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None:
                    val = inputs.pop("id", None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        # Base URL resolution: picker API vs library API
        if path.startswith("https://"):
            url = path
        elif path.startswith("/sessions"):
            url = f"{PICKER_API_BASE}{path}"
        else:
            url = f"{PHOTOS_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

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
            raise ValueError(f"Google Photos API error ({resp.status_code}): {msg}")

        if resp.status_code == 204 or not resp.content:
            return {"success": True, "message": "Operation completed successfully"}

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class GooglePhotosProvider(Provider):
    def __init__(self):
        super().__init__(
            service="googlephotos",
            display_name="Google Photos",
            category="Google Workspace",
            auth_types=["oauth2", "api_key"],
            description="Google Photos Library & Picker APIs for browsing albums, selecting media items, uploading images, and enriching albums.",
            homepage_url="https://photos.google.com",
            base_url=PHOTOS_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Google OAuth 2.0 Access Token",
                    "placeholder": "ya29.a0...",
                    "description": "Connect seamlessly via official Google Workspace OAuth 2.0 flow.",
                    "docs_url": "https://developers.google.com/photos/library/guides/overview",
                    "docs_label": "Google Photos API Documentation",
                    "setup_guide": {
                        "title": "Google Photos OAuth Setup Guide",
                        "docs_url": "https://developers.google.com/oauthplayground",
                        "docs_label": "Google OAuth Playground",
                        "instructions": [
                            "1. Go to Google Cloud Console (console.cloud.google.com) and enable Google Photos Library API.",
                            "2. In Google OAuth 2.0 Playground (developers.google.com/oauthplayground), authorize Photos scopes:",
                            "   https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
                            "   https://www.googleapis.com/auth/photoslibrary.appendonly",
                            "   https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
                            "3. Exchange authorization code for tokens and paste the ya29... Access Token below."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
                            "https://www.googleapis.com/auth/photoslibrary.appendonly",
                            "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Active Google OAuth 2.0 Access Token with Photos permissions."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Google Bearer Token / Service Account Token",
                    "placeholder": "ya29.a0... or Service Account Token",
                    "description": "Authenticate via Google OAuth Bearer token or service account credentials.",
                    "docs_url": "https://developers.google.com/photos/library/guides/overview",
                    "docs_label": "Google Photos API Documentation",
                    "setup_guide": {
                        "title": "Google Photos Bearer Token Setup Guide",
                        "docs_url": "https://developers.google.com/photos/library/guides/overview",
                        "docs_label": "Google Photos API Quickstart",
                        "instructions": [
                            "1. Obtain a valid Google OAuth Bearer access token or Service Account Token.",
                            "2. Ensure the token has the necessary Photos scopes (https://www.googleapis.com/auth/photoslibrary.appendonly).",
                            "3. Enter the token below to connect."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
                            "https://www.googleapis.com/auth/photoslibrary.appendonly"
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

        for meta in get_provider_actions("googlephotos"):
            self.register_action(GooglePhotosDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate credentials against Google userinfo endpoint."""
        token = _extract_token(credential)
        headers = _photos_headers(token)

        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        assert_public_url(userinfo_url)
        try:
            resp = await execute_guarded_request(client=client, method="GET", url=userinfo_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                email = data.get("email") or data.get("sub") or "google_photos_user"
                name = data.get("name") or email
                return {
                    "account_id": email,
                    "display_name": f"Google Photos ({name})",
                    "granted_scopes": [
                        "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
                        "https://www.googleapis.com/auth/photoslibrary.appendonly"
                    ],
                    "avatar_url": data.get("picture")
                }
        except Exception:
            pass

        url = f"{PHOTOS_API_BASE}/albums?pageSize=1"
        assert_public_url(url)
        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Google Photos API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Google Photos credentials. Google API returned 401 Unauthorized.")
        elif resp.status_code == 403:
            raise ValueError("Google Photos permission denied (403 Forbidden). Verify Google Photos API is enabled.")
        elif resp.status_code != 200:
            raise ValueError(f"Google Photos credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        return {
            "account_id": "google_photos_account",
            "display_name": "Google Photos",
            "granted_scopes": [
                "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
                "https://www.googleapis.com/auth/photoslibrary.appendonly"
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
        """SSRF-guarded proxy forwarder for Google Photos API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{PHOTOS_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_photos_headers(token))

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

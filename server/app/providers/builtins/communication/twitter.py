"""
X (Twitter) Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official X (Twitter) API v2 specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

TWITTER_API_BASE = "https://api.x.com/2"

def _twitter_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("X (Twitter) OAuth 2.0 Access Token or Bearer Token required. Please connect your X account first.")
    return str(token).strip()

class TwitterDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/tweets")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _twitter_headers(token)
        inputs = dict(input_data or {})

        # 1. Path variables substitution
        path = self.endpoint_template
        for var in ["id", "username", "participant_id", "dmConversationId", "listId", "tweet_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None and var == "id" and "user_id" in inputs:
                    val = inputs.pop("user_id", None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{TWITTER_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

        if self.method in ["POST", "PUT", "PATCH"]:
            # Special case payload formatting
            if self.id in ["twitter.creation_of_a_post", "twitter.create_tweet"] and "text" in inputs:
                body = {"text": str(inputs.pop("text"))}
                if inputs:
                    body.update(inputs)
            else:
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
                msg = err_json.get("detail") or err_json.get("title") or err_json.get("error") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"X (Twitter) API error ({resp.status_code}): {msg}")

        if resp.status_code == 204 or not resp.content:
            return {"success": True, "message": "Operation completed successfully"}

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class TwitterProvider(Provider):
    def __init__(self):
        super().__init__(
            service="twitter",
            display_name="X (Twitter)",
            category="Social",
            auth_types=["oauth2", "api_key"],
            description="X (Twitter) API v2 for posting tweets, managing lists, direct messages, bookmarks, and searching posts.",
            homepage_url="https://x.com",
            base_url=TWITTER_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "X (Twitter) OAuth 2.0 User Token",
                    "placeholder": "eyJhbGciOi...",
                    "description": "Authenticate via X (Twitter) OAuth 2.0 User Access Token with tweet.read, tweet.write, users.read.",
                    "docs_url": "https://developer.x.com/en/docs/authentication/oauth-2-0",
                    "docs_label": "X Developer Portal",
                    "setup_guide": {
                        "title": "X (Twitter) Access Token Setup Guide",
                        "docs_url": "https://developer.x.com/en/portal/dashboard",
                        "docs_label": "X Developer Portal",
                        "instructions": [
                            "1. Open the X Developer Portal (developer.x.com/en/portal/dashboard).",
                            "2. Select your Project and App, then navigate to 'User authentication settings'.",
                            "3. Enable OAuth 2.0 with 'Read and write' permissions.",
                            "4. Generate and copy your User Access Token."
                        ],
                        "scopes": [
                            "tweet.read",
                            "tweet.write",
                            "users.read",
                            "offline.access",
                            "like.read",
                            "like.write",
                            "bookmark.read",
                            "bookmark.write"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth 2.0 Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGciOi...",
                            "description": "X (Twitter) OAuth 2.0 User Access Token."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "X API Bearer Token / App Token",
                    "placeholder": "AAAAAAAAAAAAAAAAAAAAA...",
                    "description": "Authenticate via X API v2 Bearer Token.",
                    "docs_url": "https://developer.x.com/en/docs/authentication/oauth-2-0/bearer-tokens",
                    "docs_label": "X Bearer Token Documentation",
                    "setup_guide": {
                        "title": "X Bearer Token Setup Guide",
                        "docs_url": "https://developer.x.com/en/portal/dashboard",
                        "docs_label": "X Developer Portal",
                        "instructions": [
                            "1. Navigate to Keys and Tokens in your X Developer Portal App.",
                            "2. Copy the App Bearer Token (starts with AAAAA...).",
                            "3. Enter the token below to connect."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bearer Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "AAAAAAAAAAAAAAAAAAAAA...",
                            "description": "X API v2 Bearer token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("twitter"):
            self.register_action(TwitterDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate credentials against https://api.x.com/2/users/me."""
        token = _extract_token(credential)
        headers = _twitter_headers(token)
        url = f"{TWITTER_API_BASE}/users/me?user.fields=id,name,username"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach X (Twitter) API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid X (Twitter) access token. X API returned 401 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"X (Twitter) credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json().get("data", {})
        account_id = str(data.get("id") or "x_user")
        username = data.get("username") or account_id
        name = data.get("name") or username

        return {
            "account_id": account_id,
            "display_name": f"@{username} ({name})",
            "granted_scopes": ["tweet.read", "tweet.write", "users.read"],
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
        """SSRF-guarded proxy forwarder for X (Twitter) API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{TWITTER_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_twitter_headers(token))

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

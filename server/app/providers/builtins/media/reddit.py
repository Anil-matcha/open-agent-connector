"""
Reddit Provider for ConnectorHub.
Loads and registers 8 actions from 'actions_catalog.json'.
Subreddit browsing, searching, posting, and commenting via Reddit OAuth API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

REDDIT_API_BASE = "https://oauth.reddit.com"

REDDIT_ENDPOINT_MAP = {
    "reddit.get_me": ("GET", "/api/v1/me"),
    "reddit.list_posts": ("GET", "/r/{subreddit}/{sort}"),
    "reddit.search_posts": ("GET", "/search"),
    "reddit.get_post_comments": ("GET", "/comments/{postId}"),
    "reddit.create_post": ("POST", "/api/submit"),
    "reddit.create_comment": ("POST", "/api/comment"),
    "reddit.edit_content": ("POST", "/api/editusertext"),
    "reddit.delete_content": ("POST", "/api/del"),
}

def _reddit_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("token") or ""
    if not str(token).strip():
        raise ValueError("Reddit access token required. Please connect your Reddit account first.")

    return {
        "Authorization": f"Bearer {str(token).strip()}",
        "User-Agent": "ConnectorHub/1.0 by ConnectorHubAgent",
        "Accept": "application/json"
    }

class RedditDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Social"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        mapped = REDDIT_ENDPOINT_MAP.get(action_meta["id"], ("GET", "/api/v1/me"))
        self.method = mapped[0]
        self.endpoint_template = mapped[1]

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        headers = _reddit_headers(credential)

        subreddit = inputs.get("subreddit")
        sort = inputs.get("sort") or "hot"
        post_id = inputs.get("postId") or inputs.get("post_id")

        path = self.endpoint_template

        if self.id == "reddit.list_posts":
            sub_str = urllib.parse.quote(str(subreddit or "all"), safe="")
            sort_str = urllib.parse.quote(str(sort), safe="")
            path = f"/r/{sub_str}/{sort_str}"
            inputs.pop("subreddit", None)
            inputs.pop("sort", None)
        elif self.id == "reddit.search_posts":
            if subreddit:
                sub_str = urllib.parse.quote(str(subreddit), safe="")
                path = f"/r/{sub_str}/search"
                inputs.pop("subreddit", None)
                inputs["restrict_sr"] = "true"
            else:
                path = "/search"
        elif self.id == "reddit.get_post_comments":
            clean_pid = urllib.parse.quote(str(post_id or ""), safe="")
            if subreddit:
                sub_str = urllib.parse.quote(str(subreddit), safe="")
                path = f"/r/{sub_str}/comments/{clean_pid}"
                inputs.pop("subreddit", None)
            else:
                path = f"/comments/{clean_pid}"
            inputs.pop("postId", None)
            inputs.pop("post_id", None)
            inputs["raw_json"] = 1
        elif self.id == "reddit.create_comment":
            # Map input parameters to Reddit form fields
            parent_fullname = inputs.pop("parentFullname", None) or inputs.pop("parent_fullname", None) or inputs.pop("thing_id", None)
            text = inputs.pop("text", "")
            inputs["api_type"] = "json"
            inputs["thing_id"] = parent_fullname
            inputs["text"] = text
        elif self.id == "reddit.create_post":
            sr = inputs.pop("subreddit", "")
            inputs["api_type"] = "json"
            inputs["sr"] = sr
            inputs["resubmit"] = True
        elif self.id == "reddit.edit_content":
            fullname = inputs.pop("fullname", None) or inputs.pop("thing_id", None)
            text = inputs.pop("text", "")
            inputs["api_type"] = "json"
            inputs["thing_id"] = fullname
            inputs["text"] = text
        elif self.id == "reddit.delete_content":
            fullname = inputs.pop("fullname", None) or inputs.pop("id", None)
            inputs["id"] = fullname

        url = f"{REDDIT_API_BASE}/{path.lstrip('/')}"
        assert_public_url(url)

        req_method = self.method
        if req_method == "POST":
            # Reddit expects URL-encoded form data for these endpoints
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            resp = await execute_guarded_request(
                client=client,
                method=req_method,
                url=url,
                headers=headers,
                data=inputs
            )
        else:
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
                err_msg = res_data.get("message") or res_data.get("error") or str(res_data)
            raise ValueError(f"Reddit API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class RedditProvider(Provider):
    def __init__(self):
        super().__init__(
            service="reddit",
            display_name="Reddit",
            category="Social",
            auth_types=["oauth2"],
            description="Social news aggregation, web content rating, and discussion website.",
            homepage_url="https://www.reddit.com",
            base_url=REDDIT_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Reddit OAuth 2.0",
                    "description": "Authenticate with your Reddit account to read, search, post, and comment.",
                    "docs_url": "https://www.reddit.com/dev/api/oauth",
                    "docs_label": "Reddit OAuth Documentation",
                    "setup_guide": {
                        "title": "Reddit App Setup Guide",
                        "docs_url": "https://www.reddit.com/prefs/apps",
                        "docs_label": "Reddit App Preferences",
                        "instructions": [
                            "1. Go to Reddit App Preferences (https://www.reddit.com/prefs/apps).",
                            "2. Click 'are you a developer? create an app...' or 'create another app...'.",
                            "3. Select 'web app' as the application type.",
                            "4. Set the redirect URI to your ConnectorHub callback URL.",
                            "5. Copy your Client ID (shown under your app name) and Client Secret.",
                            "6. Request scopes: identity, read, submit, edit."
                        ],
                        "scopes": ["identity", "read", "submit", "edit"]
                    }
                }
            ]
        )

        for meta in get_provider_actions("reddit"):
            self.register_action(RedditDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Reddit credentials by querying GET /api/v1/me."""
        headers = _reddit_headers(credential)
        url = f"{REDDIT_API_BASE}/api/v1/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Reddit API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Reddit credentials. Reddit returned Unauthorized (401/403).")
        elif resp.status_code != 200:
            raise ValueError(f"Reddit credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        account_id = str(body.get("id", "reddit_user"))
        username = body.get("name") or f"Reddit User ({account_id})"

        return {
            "valid": True,
            "accountId": account_id,
            "displayName": f"u/{username}" if not username.startswith("u/") else username,
            "metadata": {
                "validationEndpoint": "/api/v1/me",
                "name": username,
                "is_mod": body.get("is_mod"),
                "total_karma": body.get("total_karma")
            }
        }

"""
Bitbucket Provider for ConnectorHub.
Loads and registers 41 actions from 'actions_catalog.json'.
Comprehensive Git repository, branch, commit, pull request, pipeline, and issue management via Bitbucket API 2.0.
"""
import base64
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"

def _bitbucket_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("token")
    username = cred.get("username")

    if not token or not str(token).strip():
        raise ValueError("Bitbucket OAuth Token or App Password required. Please connect your Bitbucket account first.")

    token_str = str(token).strip()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    # If username and app password provided, use Basic auth
    if username and not token_str.startswith("Bearer "):
        auth_str = f"{username}:{token_str}"
        encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {encoded}"
    else:
        # Standard Bearer token (OAuth 2.0)
        headers["Authorization"] = f"Bearer {token_str}" if not token_str.startswith("Bearer ") else token_str

    return headers

class BitbucketDynamicAction(Action):
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
        headers = _bitbucket_headers(credential)
        inputs = dict(input_data or {})

        # Path variable substitution
        path = self.endpoint_template
        for var in [
            "workspace", "repo_slug", "pull_request_id", "issue_id", "commit", "name",
            "pipeline_uuid", "variable_uuid", "encoded_id", "task_id", "id"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{BITBUCKET_API_BASE}{path}"
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
                err_msg = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else str(data.get("error") or data)
            raise ValueError(f"Bitbucket API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class BitbucketProvider(Provider):
    def __init__(self):
        super().__init__(
            service="bitbucket",
            display_name="Bitbucket",
            category="Developer Tools",
            auth_types=["oauth2", "api_key"],
            description="Git-based code hosting, collaborative pull requests, pipelines CI/CD, and project planning.",
            homepage_url="https://bitbucket.org",
            base_url=BITBUCKET_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Bitbucket OAuth 2.0",
                    "placeholder": "eyJhbGci...",
                    "description": "Connect via Bitbucket OAuth 2.0 authorization code flow.",
                    "docs_url": "https://support.atlassian.com/bitbucket-cloud/docs/use-oauth-on-bitbucket-cloud/",
                    "docs_label": "Bitbucket OAuth Guide",
                    "setup_guide": {
                        "title": "Bitbucket OAuth Consumer Setup",
                        "docs_url": "https://bitbucket.org/account/settings/api-tokens/",
                        "docs_label": "Bitbucket Workspace Settings",
                        "instructions": [
                            "1. Go to Bitbucket Workspace settings > OAuth consumers > Add consumer.",
                            "2. Set name and add your Redirect URL.",
                            "3. Enable permissions: account, repository:write, pullrequest:write, pipeline:write.",
                            "4. Copy Key and Secret into ConnectorHub settings."
                        ],
                        "scopes": [
                            "account", "repository", "repository:write", "pullrequest", "pullrequest:write", "pipeline"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "Bitbucket OAuth access token."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Bitbucket App Password",
                    "placeholder": "ATBB...",
                    "description": "App Password generated from Bitbucket Personal settings.",
                    "docs_url": "https://support.atlassian.com/bitbucket-cloud/docs/create-an-app-password/",
                    "docs_label": "Bitbucket App Passwords",
                    "setup_guide": {
                        "title": "Bitbucket App Password Guide",
                        "docs_url": "https://bitbucket.org/account/settings/app-passwords/",
                        "docs_label": "Bitbucket App Passwords Page",
                        "instructions": [
                            "1. In Bitbucket, click your avatar > Personal settings > App passwords.",
                            "2. Click 'Create app password', select needed permissions (Repositories, Pull requests).",
                            "3. Enter your Bitbucket username and copy the app password."
                        ],
                        "scopes": ["repository", "pullrequest", "pipeline"]
                    },
                    "fields": [
                        {
                            "key": "username",
                            "label": "Bitbucket Username",
                            "type": "text",
                            "required": True,
                            "placeholder": "your_username",
                            "description": "Your Bitbucket account username."
                        },
                        {
                            "key": "apiKey",
                            "label": "App Password",
                            "type": "password",
                            "required": True,
                            "placeholder": "ATBB...",
                            "description": "Bitbucket app password."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("bitbucket"):
            self.register_action(BitbucketDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Bitbucket credentials against GET /2.0/user."""
        headers = _bitbucket_headers(credential)
        url = f"{BITBUCKET_API_BASE}/user"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Bitbucket API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Bitbucket credentials. Bitbucket returned 401/403 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Bitbucket credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = data.get("uuid") or data.get("username") or "bitbucket-user"
        name = data.get("display_name") or data.get("username") or "Bitbucket User"
        username = data.get("username")
        avatar_url = (data.get("links", {}).get("avatar", {})).get("href")

        display_name = f"Bitbucket (@{username})" if username else f"Bitbucket ({name})"

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["account", "repository", "pullrequest", "pipeline"],
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
        """SSRF-guarded proxy forwarder for Bitbucket API 2.0."""
        auth_headers = _bitbucket_headers(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{BITBUCKET_API_BASE}{clean_endpoint}"
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

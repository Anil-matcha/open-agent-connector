"""
GitLab Provider for ConnectorHub.
Loads and registers 15 actions from 'actions_catalog.json'.
Supports projects, issues, merge requests, branches, and user management via GitLab REST API v4.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_GITLAB_BASE = "https://gitlab.com/api/v4"

def _gitlab_headers_and_base(credential: Optional[Dict[str, Any]]) -> tuple[Dict[str, str], str]:
    cred = credential or {}
    token = cred.get("apiKey") or cred.get("accessToken") or cred.get("token")
    if not token or not str(token).strip():
        raise ValueError("GitLab Personal Access Token or OAuth Access Token required. Please connect your GitLab account first.")

    token_str = str(token).strip()
    instance_url = (cred.get("instanceUrl") or "https://gitlab.com").rstrip("/")
    api_base = f"{instance_url}/api/v4"

    # GitLab accepts either Authorization: Bearer <token> or PRIVATE-TOKEN: <token>
    auth_header = f"Bearer {token_str}" if cred.get("accessToken") and not token_str.startswith("glpat-") else token_str
    headers = {
        "PRIVATE-TOKEN": token_str,
        "Authorization": f"Bearer {token_str}" if not token_str.startswith("Bearer ") else token_str,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    return headers, api_base

class GitLabDynamicAction(Action):
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
        headers, base_url = _gitlab_headers_and_base(credential)
        inputs = dict(input_data or {})

        # Path variable substitution
        path = self.endpoint_template
        for var in ["id", "issue_iid", "merge_request_iid", "project_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                # GitLab project paths may be URL encoded (e.g. namespace/repo -> namespace%2Frepo)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{base_url}{path}"
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
                err_msg = data.get("message") or data.get("error") or str(data)
            raise ValueError(f"GitLab API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class GitLabProvider(Provider):
    def __init__(self):
        super().__init__(
            service="gitlab",
            display_name="GitLab",
            category="Developer Tools",
            auth_types=["api_key", "oauth2"],
            description="Complete DevOps platform delivered as a single application: source code management, CI/CD, and issue tracking.",
            homepage_url="https://gitlab.com",
            base_url=DEFAULT_GITLAB_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "GitLab Personal Access Token",
                    "placeholder": "glpat-...",
                    "description": "Personal Access Token generated from your GitLab User Settings.",
                    "docs_url": "https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html",
                    "docs_label": "GitLab PAT Documentation",
                    "setup_guide": {
                        "title": "GitLab Personal Access Token Guide",
                        "docs_url": "https://gitlab.com/-/user_settings/personal_access_tokens",
                        "docs_label": "GitLab Access Tokens Settings",
                        "instructions": [
                            "1. In GitLab, click your avatar > Edit profile > Access Tokens.",
                            "2. Click 'Add new token', set name and expiration.",
                            "3. Select scopes: 'api', 'read_api', 'read_user'.",
                            "4. Copy your token (starts with 'glpat-') and paste below."
                        ],
                        "scopes": ["api", "read_api", "read_user"]
                    },
                    "fields": [
                        {
                            "key": "instanceUrl",
                            "label": "Instance URL (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "https://gitlab.com",
                            "description": "Your GitLab instance URL. Leave blank for GitLab.com SaaS."
                        },
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "glpat-...",
                            "description": "GitLab personal access token with api scopes."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "GitLab OAuth 2.0",
                    "placeholder": "eyJhbGci...",
                    "description": "Connect via GitLab OAuth 2.0 authorization code flow.",
                    "docs_url": "https://docs.gitlab.com/ee/api/oauth2.html",
                    "docs_label": "GitLab OAuth Docs",
                    "setup_guide": {
                        "title": "GitLab OAuth Application Setup",
                        "docs_url": "https://gitlab.com/-/user_settings/applications",
                        "docs_label": "GitLab Applications Settings",
                        "instructions": [
                            "1. Go to GitLab User Settings > Applications.",
                            "2. Set name to 'ConnectorHub', add your Redirect URI.",
                            "3. Enable scopes: api, read_api, read_user.",
                            "4. Copy Application ID & Secret into ConnectorHub settings."
                        ],
                        "scopes": ["api", "read_api", "read_user"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "GitLab OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("gitlab"):
            self.register_action(GitLabDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate GitLab credentials against GET /api/v4/user."""
        headers, base_url = _gitlab_headers_and_base(credential)
        url = f"{base_url}/user"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach GitLab API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid GitLab token. GitLab returned 401/403 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"GitLab credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = str(data.get("id") or data.get("username") or "gitlab-user")
        name = data.get("name") or data.get("username") or "GitLab User"
        username = data.get("username")
        avatar_url = data.get("avatar_url")

        display_name = f"GitLab (@{username})" if username else f"GitLab ({name})"

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["api", "read_api", "read_user"],
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
        """SSRF-guarded proxy forwarder for GitLab REST API v4."""
        auth_headers, base_url = _gitlab_headers_and_base(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{base_url}{clean_endpoint}"
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

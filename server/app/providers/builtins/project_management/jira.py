"""
Jira Provider for ConnectorHub.
Loads and registers 7 actions from 'actions_catalog.json'.
Supports issues, projects, search, and comments across Atlassian Jira Cloud & Data Center.
"""
import base64
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

ATLASSIAN_API_BASE = "https://api.atlassian.com"

def _resolve_jira_auth(credential: Optional[Dict[str, Any]]) -> Tuple[Dict[str, str], str]:
    """Returns headers and effective base url for Jira request."""
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("token")
    email = cred.get("email") or cred.get("username")
    base_url = (cred.get("baseUrl") or cred.get("domain") or "").rstrip("/")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    if not token:
        raise ValueError("Jira API Token or OAuth Access Token required. Please connect your Jira account first.")

    # Basic auth (email:api_token) if email is provided
    if email and not str(token).startswith("Bearer "):
        token_str = str(token).strip()
        auth_str = f"{email}:{token_str}"
        encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        headers["Authorization"] = f"Basic {encoded}"
    else:
        # Bearer token for OAuth 2.0 or PAT
        headers["Authorization"] = f"Bearer {token}" if not str(token).startswith("Bearer ") else str(token)

    effective_base = base_url if base_url else ATLASSIAN_API_BASE
    return headers, effective_base

class JiraDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/rest/api/3/project/search")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        headers, base_url = _resolve_jira_auth(credential)
        inputs = dict(input_data or {})

        # CloudId substitution for Atlassian Cloud API if applicable
        cloud_id = inputs.pop("cloudId", None) or (credential or {}).get("cloudId")

        path = self.endpoint_template
        for var in ["projectIdOrKey", "issueIdOrKey", "id", "key"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        if base_url == ATLASSIAN_API_BASE and cloud_id and not path.startswith("/ex/jira/"):
            target_url = f"{base_url}/ex/jira/{cloud_id}{path}"
        else:
            target_url = f"{base_url}{path}"

        assert_public_url(target_url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT"] else None
        params = inputs if req_method == "GET" else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
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
                err_msg = "; ".join(data.get("errorMessages", [])) or str(data.get("errors", data))
            raise ValueError(f"Jira API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class JiraProvider(Provider):
    def __init__(self):
        super().__init__(
            service="jira",
            display_name="Jira",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="Agile project management and issue tracking across Atlassian Jira Cloud & Data Center.",
            homepage_url="https://www.atlassian.com/software/jira",
            base_url=ATLASSIAN_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Atlassian API Token",
                    "placeholder": "ATATT3x...",
                    "description": "Atlassian API Token with your account email for Jira Cloud.",
                    "docs_url": "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
                    "docs_label": "Atlassian API Tokens",
                    "setup_guide": {
                        "title": "Jira API Token Setup Guide",
                        "docs_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
                        "docs_label": "Atlassian Security Tokens",
                        "instructions": [
                            "1. Go to Atlassian Security Settings (id.atlassian.com/manage-profile/security/api-tokens).",
                            "2. Click 'Create API token', enter a label, and copy the generated token.",
                            "3. Enter your Atlassian account email, instance URL (e.g. https://your-domain.atlassian.net), and API token below."
                        ],
                        "scopes": ["read:jira-work", "write:jira-work", "read:jira-user"]
                    },
                    "fields": [
                        {
                            "key": "baseUrl",
                            "label": "Jira Instance URL",
                            "type": "text",
                            "required": True,
                            "placeholder": "https://your-domain.atlassian.net",
                            "description": "Your Jira Cloud or Data Center site URL."
                        },
                        {
                            "key": "email",
                            "label": "Account Email",
                            "type": "text",
                            "required": True,
                            "placeholder": "you@company.com",
                            "description": "Email address associated with your Atlassian account."
                        },
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ATATT3x...",
                            "description": "Atlassian API token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Jira Cloud OAuth 2.0 (3LO)",
                    "placeholder": "eyJhbGci...",
                    "description": "Connect via Atlassian Cloud 3-legged OAuth 2.0 authorization code flow.",
                    "docs_url": "https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/",
                    "docs_label": "Jira OAuth 2.0 Docs",
                    "setup_guide": {
                        "title": "Atlassian OAuth 2.0 Setup",
                        "docs_url": "https://developer.atlassian.com/console/myapps/",
                        "docs_label": "Atlassian Developer Console",
                        "instructions": [
                            "1. Open Atlassian Developer Console (developer.atlassian.com/console/myapps).",
                            "2. Create an OAuth 2.0 (3LO) app, add Jira API permissions (read:jira-work, write:jira-work).",
                            "3. Set your Callback URL and copy Client ID & Secret.",
                            "4. Authorize access to your Atlassian Cloud site."
                        ],
                        "scopes": ["read:jira-work", "write:jira-work", "read:jira-user", "offline_access"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJhbGci...",
                            "description": "Atlassian Cloud OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("jira"):
            self.register_action(JiraDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Jira credentials against /rest/api/3/myself or Atlassian accessible-resources."""
        headers, base_url = _resolve_jira_auth(credential)

        if base_url == ATLASSIAN_API_BASE:
            # OAuth 2.0 Cloud validation
            validate_url = f"{ATLASSIAN_API_BASE}/oauth/token/accessible-resources"
        else:
            # Site-specific validation
            validate_url = f"{base_url}/rest/api/3/myself"

        assert_public_url(validate_url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=validate_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Jira API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Jira credentials. Jira returned Unauthorized/Forbidden.")
        elif resp.status_code != 200:
            raise ValueError(f"Jira credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            # Accessible resources list
            res = data[0]
            account_id = res.get("id") or "jira-resource"
            name = res.get("name") or "Jira Cloud"
            avatar_url = res.get("avatarUrl")
            display_name = f"Jira ({name})"
        elif isinstance(data, dict):
            account_id = data.get("accountId") or data.get("name") or "jira-user"
            name = data.get("displayName") or data.get("emailAddress") or "Jira User"
            avatar_url = (data.get("avatarUrls") or {}).get("48x48")
            display_name = f"Jira ({name})"
        else:
            account_id = "jira-account"
            display_name = "Jira"
            avatar_url = None

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["read:jira-work", "write:jira-work", "read:jira-user"],
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
        """SSRF-guarded proxy forwarder for Jira."""
        auth_headers, base_url = _resolve_jira_auth(credential)
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

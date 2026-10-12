"""
LinkedIn Provider for ConnectorHub.
Loads and registers 5 actions from 'actions_catalog.json'.
Posts and Member management via LinkedIn REST API (v2 and /rest/posts).
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_API_VERSION = "202605"

LINKEDIN_ENDPOINT_MAP = {
    "linkedin.get_current_member": ("GET", "/v2/userinfo"),
    "linkedin.create_text_post": ("POST", "/rest/posts"),
    "linkedin.create_article_post": ("POST", "/rest/posts"),
    "linkedin.create_reshare": ("POST", "/rest/posts"),
    "linkedin.delete_post": ("DELETE", "/rest/posts/{postUrn}"),
}

def _linkedin_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("token") or ""
    if not str(token).strip():
        raise ValueError("LinkedIn OAuth2 access token required. Please connect your LinkedIn account first.")

    return {
        "Authorization": f"Bearer {str(token).strip()}",
        "linkedin-version": LINKEDIN_API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class LinkedInDynamicAction(Action):
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
        mapped_method, mapped_endpoint = LINKEDIN_ENDPOINT_MAP.get(action_meta["id"], ("GET", "/v2/userinfo"))
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        headers = _linkedin_headers(credential)

        path = self.endpoint_template
        for var in ["postUrn", "post_urn", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{LINKEDIN_API_BASE}/{path.lstrip('/')}"
        assert_public_url(url)

        req_method = self.method
        if req_method == "DELETE":
            headers["x-restli-method"] = "DELETE"

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
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                err_msg = res_data.get("message") or res_data.get("error") or str(res_data)
            raise ValueError(f"LinkedIn API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class LinkedInProvider(Provider):
    def __init__(self):
        super().__init__(
            service="linkedin",
            display_name="LinkedIn",
            category="Social",
            auth_types=["oauth2"],
            description="Professional networking platform for content sharing, member connections, and articles.",
            homepage_url="https://www.linkedin.com",
            base_url=LINKEDIN_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "LinkedIn OAuth 2.0",
                    "description": "Authenticate via LinkedIn OAuth 2.0 authorization code flow.",
                    "docs_url": "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow",
                    "docs_label": "LinkedIn OAuth 2.0 Guide",
                    "setup_guide": {
                        "title": "LinkedIn App Setup Guide",
                        "docs_url": "https://www.linkedin.com/developers/apps",
                        "docs_label": "LinkedIn Developer Portal",
                        "instructions": [
                            "1. Go to the LinkedIn Developer Portal (https://www.linkedin.com/developers/apps).",
                            "2. Create an App or select your existing app.",
                            "3. Navigate to the 'Auth' tab and set your authorized redirect URL.",
                            "4. Enable 'Sign In with LinkedIn using OpenID Connect' and 'Share on LinkedIn' products.",
                            "5. Copy your Client ID and Client Secret.",
                            "6. Request scopes: openid, profile, email, w_member_social."
                        ],
                        "scopes": ["openid", "profile", "email", "w_member_social"]
                    }
                }
            ]
        )

        for meta in get_provider_actions("linkedin"):
            self.register_action(LinkedInDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate LinkedIn credentials by querying GET /v2/userinfo."""
        headers = _linkedin_headers(credential)
        url = f"{LINKEDIN_API_BASE}/v2/userinfo"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach LinkedIn API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid LinkedIn credentials. LinkedIn returned Unauthorized (401/403).")
        elif resp.status_code != 200:
            raise ValueError(f"LinkedIn credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        sub = str(body.get("sub", "linkedin_member"))
        name = body.get("name") or body.get("email") or f"LinkedIn Member ({sub})"

        return {
            "valid": True,
            "accountId": sub,
            "displayName": name,
            "metadata": {
                "validationEndpoint": "/v2/userinfo",
                "sub": sub,
                "email": body.get("email"),
                "picture": body.get("picture")
            }
        }

"""
Supabase Provider for ConnectorHub.
Loads and registers 23 actions from 'actions_catalog.json'.
Comprehensive management of Supabase organizations, projects, API keys, secrets, database queries, edge functions, and storage buckets.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SUPABASE_API_BASE = "https://api.supabase.com/v1"

def _supabase_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("Supabase Personal Access Token (PAT) or OAuth token required. Please connect your Supabase account first.")
    return str(token).strip()

class SupabaseDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/projects")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _supabase_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["ref", "slug", "key_id", "function_slug", "bucket", "path", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{SUPABASE_API_BASE}{path}"
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
            raise ValueError(f"Supabase API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class SupabaseProvider(Provider):
    def __init__(self):
        super().__init__(
            service="supabase",
            display_name="Supabase",
            category="Developer Tools",
            auth_types=["api_key", "oauth2"],
            description="The open source Firebase alternative: PostgreSQL database, Authentication, Instant APIs, Realtime, Functions, and Storage.",
            homepage_url="https://supabase.com",
            base_url=SUPABASE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Personal Access Token (PAT)",
                    "placeholder": "sbp_...",
                    "description": "Supabase Personal Access Token generated from your Account settings.",
                    "docs_url": "https://supabase.com/docs/guides/platform/management-api",
                    "docs_label": "Supabase Management API Docs",
                    "setup_guide": {
                        "title": "Supabase Access Token Guide",
                        "docs_url": "https://supabase.com/dashboard/account/tokens",
                        "docs_label": "Supabase Account Tokens",
                        "instructions": [
                            "1. Open Supabase Dashboard (supabase.com/dashboard/account/tokens).",
                            "2. Click 'Generate new token', provide a name (e.g. 'ConnectorHub').",
                            "3. Copy the token (starts with 'sbp_') and paste below."
                        ],
                        "scopes": ["all"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "sbp_...",
                            "description": "Supabase personal access token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Supabase OAuth 2.0",
                    "placeholder": "sbp_...",
                    "description": "Connect via Supabase OAuth 2.0 application flow.",
                    "docs_url": "https://supabase.com/docs/guides/integrations/oauth-apps",
                    "docs_label": "Supabase OAuth Apps",
                    "setup_guide": {
                        "title": "Supabase OAuth App Setup",
                        "docs_url": "https://supabase.com/dashboard/account/apps",
                        "docs_label": "Supabase OAuth Apps Dashboard",
                        "instructions": [
                            "1. In Supabase Dashboard, go to Account > OAuth Apps.",
                            "2. Create an application with your Redirect URI.",
                            "3. Copy Client ID and Secret into ConnectorHub settings.",
                            "4. Authorize access to your organizations and projects."
                        ],
                        "scopes": ["all"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "sbp_...",
                            "description": "Supabase OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("supabase"):
            self.register_action(SupabaseDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Supabase credentials against GET /v1/organizations."""
        token = _extract_token(credential)
        headers = _supabase_headers(token)
        url = f"{SUPABASE_API_BASE}/organizations"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Supabase API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Supabase token. Supabase returned 401/403 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Supabase credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        orgs = resp.json()
        org_name = orgs[0].get("name") if isinstance(orgs, list) and orgs else "Supabase Account"
        org_id = orgs[0].get("id") if isinstance(orgs, list) and orgs else "supabase-user"

        return {
            "account_id": str(org_id),
            "display_name": f"Supabase ({org_name})",
            "granted_scopes": ["all"],
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
        """SSRF-guarded proxy forwarder for Supabase Management API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{SUPABASE_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_supabase_headers(token))

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

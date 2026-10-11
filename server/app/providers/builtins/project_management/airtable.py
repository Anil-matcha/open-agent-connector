"""
Airtable Provider for ConnectorHub.
Loads and registers 14 actions from 'actions_catalog.json'.
Full lifecycle management for bases, tables, fields, schemas, and records via Airtable Web API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

AIRTABLE_API_BASE = "https://api.airtable.com/v0"

def _airtable_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Airtable Personal Access Token or OAuth Access Token required. Please connect your Airtable account first.")
    return str(token).strip()

class AirtableDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/meta/bases")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _airtable_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["baseId", "tableIdOrName", "tableId", "recordId", "fieldId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{AIRTABLE_API_BASE}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PATCH", "PUT"] else None
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
            if isinstance(data, dict) and "error" in data:
                err_val = data["error"]
                err_msg = err_val.get("message") if isinstance(err_val, dict) else str(err_val)
            raise ValueError(f"Airtable API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class AirtableProvider(Provider):
    def __init__(self):
        super().__init__(
            service="airtable",
            display_name="Airtable",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="Connected apps platform that combines spreadsheet flexibility with relational database power.",
            homepage_url="https://airtable.com",
            base_url=AIRTABLE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Personal Access Token (PAT)",
                    "placeholder": "pat...",
                    "description": "Personal Access Token generated in the Airtable Developer Hub.",
                    "docs_url": "https://airtable.com/developers/web/api/personal-access-tokens",
                    "docs_label": "Airtable PAT Guide",
                    "setup_guide": {
                        "title": "Airtable Token Guide",
                        "docs_url": "https://airtable.com/create/tokens",
                        "docs_label": "Airtable Create Token Hub",
                        "instructions": [
                            "1. Go to Airtable Developer Hub (airtable.com/create/tokens).",
                            "2. Click '+ Create new token', give it a name (e.g. 'ConnectorHub').",
                            "3. Add scopes: data.records:read, data.records:write, schema.bases:read, schema.bases:write.",
                            "4. Add access to all needed workspaces or bases, create, and copy your token.",
                            "5. Paste below (starts with 'pat')."
                        ],
                        "scopes": ["data.records:read", "data.records:write", "schema.bases:read", "schema.bases:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "pat...",
                            "description": "Airtable Personal Access Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Airtable OAuth 2.0 (PKCE)",
                    "placeholder": "oat_...",
                    "description": "Connect via Airtable OAuth 2.0 authorization code with PKCE flow.",
                    "docs_url": "https://airtable.com/developers/web/api/oauth-reference",
                    "docs_label": "Airtable OAuth Docs",
                    "setup_guide": {
                        "title": "Airtable OAuth App Setup",
                        "docs_url": "https://airtable.com/create/oauth",
                        "docs_label": "Airtable OAuth Builder",
                        "instructions": [
                            "1. Visit Airtable OAuth App Builder (airtable.com/create/oauth).",
                            "2. Register a new integration with your Redirect URL.",
                            "3. Select Scopes: data.records:read, data.records:write, schema.bases:read.",
                            "4. Add Client ID & Secret in ConnectorHub and complete authorization."
                        ],
                        "scopes": ["data.records:read", "data.records:write", "schema.bases:read", "schema.bases:write"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "oat_...",
                            "description": "Airtable OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("airtable"):
            self.register_action(AirtableDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Airtable credentials against GET https://api.airtable.com/v0/meta/whoami."""
        token = _extract_token(credential)
        headers = _airtable_headers(token)
        url = f"{AIRTABLE_API_BASE}/meta/whoami"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Airtable API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Airtable Token. Airtable returned 401/403 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Airtable credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        account_id = str(body.get("id") or "airtable-user")
        email = body.get("email")
        display_name = f"Airtable ({email})" if email else f"Airtable ({account_id})"

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["data.records:read", "data.records:write", "schema.bases:read", "schema.bases:write"],
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
        """SSRF-guarded proxy forwarder for Airtable Web API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{AIRTABLE_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_airtable_headers(token))

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

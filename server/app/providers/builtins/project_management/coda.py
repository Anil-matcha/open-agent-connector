"""
Coda Provider for ConnectorHub.
Loads and registers 11 actions from 'actions_catalog.json'.
Full collaborative doc management for documents, pages, tables, columns, rows, and mutations via Coda REST API v1.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CODA_API_BASE = "https://coda.io/apis/v1"

def _coda_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("Coda API Token required. Please connect your Coda account first.")
    return str(token).strip()

class CodaDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/whoami")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _coda_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["docId", "tableIdOrName", "requestId", "pageId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{CODA_API_BASE}{path}"
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
                err_msg = data.get("message") or data.get("statusCode") or str(data)
            raise ValueError(f"Coda API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class CodaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="coda",
            display_name="Coda",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="All-in-one collaborative doc platform bringing words, data, and workflows together.",
            homepage_url="https://coda.io",
            base_url=CODA_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Coda API Token",
                    "placeholder": "coda_api_token...",
                    "description": "API token generated from your Coda account settings page.",
                    "docs_url": "https://coda.io/developers/apis/v1",
                    "docs_label": "Coda API Documentation",
                    "setup_guide": {
                        "title": "Coda API Token Guide",
                        "docs_url": "https://coda.io/account",
                        "docs_label": "Coda Account Page",
                        "instructions": [
                            "1. Open Coda account settings (coda.io/account).",
                            "2. Scroll down to the 'Coda API Tokens' section.",
                            "3. Click 'Generate API token', assign name & permissions, and copy the token.",
                            "4. Paste your token below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "coda_...",
                            "description": "Coda personal API token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("coda"):
            self.register_action(CodaDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Coda credentials against GET https://coda.io/apis/v1/whoami."""
        token = _extract_token(credential)
        headers = _coda_headers(token)
        url = f"{CODA_API_BASE}/whoami"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Coda API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Coda API token. Coda returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Coda credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        account_id = str(body.get("loginId") or body.get("id") or "coda-user")
        name = body.get("name") or account_id
        display_name = f"Coda ({name})"

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": [],
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
        """SSRF-guarded proxy forwarder for Coda REST API v1."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{CODA_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_coda_headers(token))

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

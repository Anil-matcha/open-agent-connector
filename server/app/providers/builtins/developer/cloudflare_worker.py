"""
Cloudflare Worker Provider for ConnectorHub.
Loads and registers 25 actions from 'actions_catalog.json'.
Comprehensive management of Cloudflare Workers scripts, script settings, secrets, CI/CD builds, and execution triggers.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

def _cloudflare_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token_and_account(credential: Optional[Dict[str, Any]]) -> tuple[str, Optional[str]]:
    cred = credential or {}
    token = cred.get("apiKey") or cred.get("accessToken") or cred.get("token")
    if not token or not str(token).strip():
        raise ValueError("Cloudflare API Token required. Please connect your Cloudflare account first.")
    account_id = cred.get("accountId")
    return str(token).strip(), account_id

class CloudflareWorkerDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/accounts")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token, cred_account_id = _extract_token_and_account(credential)
        inputs = dict(input_data or {})
        headers = _cloudflare_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["accountId", "scriptName", "secretName", "buildId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None and var == "accountId" and cred_account_id:
                    val = cred_account_id
                if val is not None:
                    path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{CLOUDFLARE_API_BASE}{path}"
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
            if isinstance(data, dict) and "errors" in data:
                err_msg = "; ".join(e.get("message", "Error") for e in data["errors"])
            raise ValueError(f"Cloudflare Worker API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data.get("result", data) if isinstance(data, dict) else data}

class CloudflareWorkerProvider(Provider):
    def __init__(self):
        super().__init__(
            service="cloudflare_worker",
            display_name="Cloudflare Worker",
            category="Developer Tools",
            auth_types=["api_key", "oauth2"],
            description="Serverless execution environment that allows you to create entirely new applications or augment existing ones without configuring or maintaining infrastructure.",
            homepage_url="https://workers.cloudflare.com",
            base_url=CLOUDFLARE_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Cloudflare API Token",
                    "placeholder": "cloudflare_api_token...",
                    "description": "Cloudflare API Token with Workers Scripts read/write permissions.",
                    "docs_url": "https://developers.cloudflare.com/workers/platform/api/",
                    "docs_label": "Cloudflare Workers API Docs",
                    "setup_guide": {
                        "title": "Cloudflare Workers API Token Guide",
                        "docs_url": "https://dash.cloudflare.com/profile/api-tokens",
                        "docs_label": "Cloudflare API Tokens Page",
                        "instructions": [
                            "1. Go to Cloudflare Profile > API Tokens (dash.cloudflare.com/profile/api-tokens).",
                            "2. Click 'Create Token', choose 'Edit Cloudflare Workers' template.",
                            "3. Select Account Resources: Include your account.",
                            "4. Copy your token and account ID and paste below."
                        ],
                        "scopes": ["workers-scripts:write", "workers-ci:write"]
                    },
                    "fields": [
                        {
                            "key": "accountId",
                            "label": "Account ID",
                            "type": "text",
                            "required": False,
                            "placeholder": "023e105f4ecef8ad9ca31a8372d0c353",
                            "description": "Your Cloudflare Account ID (found on the right sidebar of Cloudflare Dashboard)."
                        },
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "API Token with Workers permissions",
                            "description": "Cloudflare API Token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("cloudflare_worker"):
            self.register_action(CloudflareWorkerDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Cloudflare API token against GET /user/tokens/verify."""
        token, _ = _extract_token_and_account(credential)
        headers = _cloudflare_headers(token)
        url = f"{CLOUDFLARE_API_BASE}/user/tokens/verify"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Cloudflare API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Cloudflare API Token. Cloudflare returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Cloudflare credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        result = body.get("result", {})
        account_id = result.get("id") or "cloudflare-user"
        status = result.get("status", "active")

        return {
            "account_id": account_id,
            "display_name": f"Cloudflare Worker ({status})",
            "granted_scopes": ["workers-scripts:write"],
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
        """SSRF-guarded proxy forwarder for Cloudflare Client API v4."""
        token, _ = _extract_token_and_account(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{CLOUDFLARE_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_cloudflare_headers(token))

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

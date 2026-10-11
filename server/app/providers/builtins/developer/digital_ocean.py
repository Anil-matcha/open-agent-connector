"""
DigitalOcean Provider for ConnectorHub.
Loads and registers 11 actions from 'actions_catalog.json'.
Cloud infrastructure management for Droplets, compute lifecycle, databases, App Platform, firewalls, load balancers, VPCs, and DNS domains via DigitalOcean API v2.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DIGITALOCEAN_API_BASE = "https://api.digitalocean.com/v2"

def _digitalocean_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("DigitalOcean Personal Access Token required. Please connect your DigitalOcean account first.")
    return str(token).strip()

class DigitalOceanDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/account")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _digitalocean_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["droplet_id", "domain_name", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{DIGITALOCEAN_API_BASE}{path}"
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
            raise ValueError(f"DigitalOcean API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class DigitalOceanProvider(Provider):
    def __init__(self):
        super().__init__(
            service="digital_ocean",
            display_name="DigitalOcean",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Cloud services platform that helps developers build, deploy, and scale applications easily with Droplets, Kubernetes, Databases, and App Platform.",
            homepage_url="https://www.digitalocean.com",
            base_url=DIGITALOCEAN_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "DigitalOcean Personal Access Token",
                    "placeholder": "dop_v1_...",
                    "description": "Personal Access Token generated from DigitalOcean API settings.",
                    "docs_url": "https://docs.digitalocean.com/reference/api/create-personal-access-token/",
                    "docs_label": "DigitalOcean API Token Guide",
                    "setup_guide": {
                        "title": "DigitalOcean Token Guide",
                        "docs_url": "https://cloud.digitalocean.com/account/api/tokens",
                        "docs_label": "DigitalOcean API Tokens Page",
                        "instructions": [
                            "1. Go to DigitalOcean Control Panel > API > Tokens (cloud.digitalocean.com/account/api/tokens).",
                            "2. Click 'Generate New Token', give it a name (e.g. 'ConnectorHub').",
                            "3. Select scopes (Read and Write).",
                            "4. Copy your token (starts with 'dop_v1_') and paste below."
                        ],
                        "scopes": ["account:read", "droplet:read", "droplet:update", "app:read", "database:read"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "dop_v1_...",
                            "description": "DigitalOcean personal access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("digital_ocean"):
            self.register_action(DigitalOceanDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate DigitalOcean credentials against GET /v2/account."""
        token = _extract_token(credential)
        headers = _digitalocean_headers(token)
        url = f"{DIGITALOCEAN_API_BASE}/account"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach DigitalOcean API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid DigitalOcean token. DigitalOcean returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"DigitalOcean credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        account = body.get("account", {})
        account_id = account.get("uuid") or account.get("email") or "digitalocean-user"
        email = account.get("email") or "DigitalOcean User"

        return {
            "account_id": str(account_id),
            "display_name": f"DigitalOcean ({email})",
            "granted_scopes": ["account:read", "droplet:read"],
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
        """SSRF-guarded proxy forwarder for DigitalOcean API v2."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{DIGITALOCEAN_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_digitalocean_headers(token))

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

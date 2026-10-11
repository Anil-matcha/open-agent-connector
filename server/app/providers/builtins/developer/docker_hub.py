"""
Docker Hub Provider for ConnectorHub.
Loads and registers 14 actions from 'actions_catalog.json'.
Container image repository management, tags, images, organizations, teams, members, and access tokens via Docker Hub API v2.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DOCKER_HUB_API_BASE = "https://hub.docker.com/v2"

def _docker_headers(token: str) -> Dict[str, str]:
    auth = f"Bearer {token}" if not token.startswith("Bearer ") and not token.startswith("JWT ") else token
    return {
        "Authorization": auth,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Docker Hub Personal Access Token (PAT) or Bearer Token required. Please connect your Docker Hub account first.")
    return str(token).strip()

class DockerHubDynamicAction(Action):
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
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _docker_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in ["namespace", "repository", "tag", "orgname", "teamname", "member", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{DOCKER_HUB_API_BASE}{path}"
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
                err_msg = data.get("detail") or data.get("message") or str(data)
            raise ValueError(f"Docker Hub API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class DockerHubProvider(Provider):
    def __init__(self):
        super().__init__(
            service="docker_hub",
            display_name="Docker Hub",
            category="Developer Tools",
            auth_types=["api_key"],
            description="The world's easiest way to create, manage, and deliver your team's container applications and container images.",
            homepage_url="https://hub.docker.com",
            base_url=DOCKER_HUB_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Docker Hub Personal Access Token",
                    "placeholder": "dckr_pat_...",
                    "description": "Personal Access Token generated from Docker Hub Security settings.",
                    "docs_url": "https://docs.docker.com/security/for-developers/access-tokens/",
                    "docs_label": "Docker Hub PAT Guide",
                    "setup_guide": {
                        "title": "Docker Hub PAT Guide",
                        "docs_url": "https://app.docker.com/settings/personal-access-tokens",
                        "docs_label": "Docker Security Settings",
                        "instructions": [
                            "1. Open Docker Hub Account Settings (app.docker.com/settings/personal-access-tokens).",
                            "2. Click 'Generate new token', provide an access token description (e.g. 'ConnectorHub').",
                            "3. Select permissions (Read & Write).",
                            "4. Copy your token (starts with 'dckr_pat_') and paste below."
                        ],
                        "scopes": ["repo:read", "repo:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "dckr_pat_...",
                            "description": "Docker Hub PAT."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("docker_hub"):
            self.register_action(DockerHubDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Docker Hub credentials against GET /v2/user."""
        token = _extract_token(credential)
        headers = _docker_headers(token)
        url = f"{DOCKER_HUB_API_BASE}/user"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Docker Hub API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Docker Hub token. Docker Hub returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Docker Hub credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = str(data.get("id") or data.get("username") or "docker-user")
        username = data.get("username") or "Docker User"
        avatar_url = data.get("gravatar_url")

        return {
            "account_id": account_id,
            "display_name": f"Docker Hub (@{username})",
            "granted_scopes": ["repo:read", "repo:write"],
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
        """SSRF-guarded proxy forwarder for Docker Hub API v2."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{DOCKER_HUB_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_docker_headers(token))

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

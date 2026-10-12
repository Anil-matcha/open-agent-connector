"""
CircleCI Provider for ConnectorHub.
Continuous integration and continuous delivery (CI/CD) automation platform for engineering teams.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

CIRCLECI_API_BASE = "https://circleci.com/api/v2"

def _circleci_headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    headers = {
        "Circle-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    return headers

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    token = None
    for k in ['apiKey', 'token', 'circleToken']:
        if cred.get(k):
            token = cred[k]
            break
    if not token or not str(token).strip():
        raise ValueError("CircleCI API credential required. Please connect your CircleCI account first.")
    return str(token).strip()

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    custom_base = cred.get("baseUrl") or cred.get("clusterUrl") or cred.get("url")
    if custom_base and str(custom_base).strip():
        return str(custom_base).strip().rstrip("/")
    return CIRCLECI_API_BASE

def _resolve_route(name: str) -> tuple[str, str]:
    n = name.lower()
    if n.startswith("trigger_") or n.startswith("create_"):
        method = "POST"
    elif n.startswith("delete_") or n.startswith("cancel_"):
        method = "POST"
    else:
        method = "GET"

    if "me" in n or "current_user" in n:
        endpoint = "/me"
    elif "pipeline" in n:
        endpoint = "/pipeline"
    elif "job" in n:
        endpoint = "/project/{project-slug}/job/{job-number}"
    elif "workflow" in n:
        endpoint = "/workflow/{id}"
    elif "project" in n:
        endpoint = "/project/{project-slug}"
    else:
        endpoint = "/pipeline"
    return method, endpoint


class CircleCIDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Developer Tools"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method, self.endpoint_template = _resolve_route(action_meta["name"])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        inputs = dict(input_data or {})
        headers = _circleci_headers(token, credential)

        path = self.endpoint_template
        for var in ["id", "projectId", "project_id", "project-slug", "workflow-id", "job-number", "tailnet", "organization_slug", "collection_name", "index_name", "chatId", "uid"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
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
                err_msg = data.get("message") or data.get("error") or data.get("detail") or str(data)
            raise ValueError(f"CircleCI API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class CircleCIProvider(Provider):
    def __init__(self):
        super().__init__(
            service="circleci",
            display_name="CircleCI",
            category="Developer Tools",
            auth_types=['api_key'],
            description="Continuous integration and continuous delivery (CI/CD) automation platform for engineering teams.",
            homepage_url="https://circleci.com",
            base_url=CIRCLECI_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "CircleCI API Key",
                    "placeholder": "...",
                    "description": "CircleCI access token or API key.",
                    "docs_url": "https://circleci.com",
                    "docs_label": "CircleCI Documentation",
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "...",
                            "description": "CircleCI API key or access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("circleci"):
            self.register_action(CircleCIDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _circleci_headers(token, credential)
        url = f"{base_url}/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach CircleCI API: {str(e)}")

        if resp.status_code in [401, 403]:
            raise ValueError("Invalid CircleCI credentials. Returned 401/403 Unauthorized.")
        elif resp.status_code >= 400:
            raise ValueError(f"CircleCI credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        try:
            account_id = resp.json().get("id", "circleci-user")
            display_name = f"CircleCI ({resp.json().get('login', 'User')})"
        except Exception:
            account_id = "circleci-account"
            display_name = "CircleCI Account"

        return {
            "account_id": str(account_id),
            "display_name": display_name,
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
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{base_url}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_circleci_headers(token, credential))

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

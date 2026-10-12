"""
Sentry Provider for ConnectorHub.
Application monitoring and error tracking platform for diagnosing crashes and software health.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SENTRY_API_BASE = "https://sentry.io/api/0"

def _sentry_headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    return headers

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    token = None
    for k in ['apiKey', 'accessToken', 'token']:
        if cred.get(k):
            token = cred[k]
            break
    if not token or not str(token).strip():
        raise ValueError("Sentry API credential required. Please connect your Sentry account first.")
    return str(token).strip()

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    custom_base = cred.get("baseUrl") or cred.get("clusterUrl") or cred.get("url")
    if custom_base and str(custom_base).strip():
        return str(custom_base).strip().rstrip("/")
    return SENTRY_API_BASE

def _resolve_route(name: str) -> tuple[str, str]:
    n = name.lower()
    if n.startswith("delete_"):
        method = "DELETE"
    elif n.startswith("update_"):
        method = "PUT"
    elif n.startswith("create_"):
        method = "POST"
    else:
        method = "GET"

    if "issue" in n:
        endpoint = "/organizations/{organization_slug}/issues/"
    elif "project" in n:
        endpoint = "/organizations/{organization_slug}/projects/"
    elif "release" in n:
        endpoint = "/organizations/{organization_slug}/releases/"
    elif "alert" in n:
        endpoint = "/organizations/{organization_slug}/alert-rules/"
    elif "replay" in n:
        endpoint = "/organizations/{organization_slug}/replays/"
    elif "integration" in n:
        endpoint = "/organizations/{organization_slug}/integrations/"
    else:
        endpoint = "/organizations/{organization_slug}/issues/"
    return method, endpoint


class SentryDynamicAction(Action):
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
        headers = _sentry_headers(token, credential)

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
            raise ValueError(f"Sentry API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class SentryProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sentry",
            display_name="Sentry",
            category="Developer Tools",
            auth_types=['api_key', 'oauth2'],
            description="Application monitoring and error tracking platform for diagnosing crashes and software health.",
            homepage_url="https://sentry.io",
            base_url=SENTRY_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Sentry API Key",
                    "placeholder": "...",
                    "description": "Sentry access token or API key.",
                    "docs_url": "https://sentry.io",
                    "docs_label": "Sentry Documentation",
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "...",
                            "description": "Sentry API key or access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("sentry"):
            self.register_action(SentryDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _sentry_headers(token, credential)
        url = f"{base_url}/users/me/"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Sentry API: {str(e)}")

        if resp.status_code in [401, 403]:
            raise ValueError("Invalid Sentry credentials. Returned 401/403 Unauthorized.")
        elif resp.status_code >= 400:
            raise ValueError(f"Sentry credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        try:
            account_id = str(resp.json().get("id", "sentry-user"))
            display_name = f"Sentry ({resp.json().get('email', 'User')})"
        except Exception:
            account_id = "sentry-account"
            display_name = "Sentry Account"

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
        req_headers.update(_sentry_headers(token, credential))

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

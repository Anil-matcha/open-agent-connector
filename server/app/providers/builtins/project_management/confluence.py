"""
Confluence Provider for ConnectorHub.
Loads and registers 5 actions for Atlassian Confluence spaces, pages, and content search.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.atlassian.com/ex/confluence"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "personalAccessToken", "api_key", "access_token"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    token = _extract_token(credential)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_page": ["POST", "/wiki/api/v2/pages", [], ["spaceId", "title", "body"]],
    "get_page": ["GET", "/wiki/api/v2/pages/{pageId}", ["pageId"], []],
    "list_spaces": ["GET", "/wiki/api/v2/spaces", [], ["limit", "cursor"]],
    "search_content": ["GET", "/wiki/rest/api/content/search", [], ["cql", "limit", "cursor"]],
    "update_page": ["PUT", "/wiki/api/v2/pages/{pageId}", ["pageId"], ["title", "body", "version"]],
}

class ConfluenceDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Productivity"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        headers = _build_headers(cred)
        cloud_id = cred.get("cloudId") or cred.get("cloud_id") or ""
        base = f"{DEFAULT_API_BASE}/{cloud_id}" if cloud_id else DEFAULT_API_BASE

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        target_url = f"{base}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or req_method == "GET":
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("errorMessages", [None])[0] or err_msg
            except Exception:
                pass
            raise ValueError(f"Confluence API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class ConfluenceProvider(Provider):
    def __init__(self):
        super().__init__(
            service="confluence",
            display_name="Confluence",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="Atlassian Confluence spaces, documentation pages, versioning, and CQL content search with 5 actions.",
            homepage_url="https://www.atlassian.com/software/confluence",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Atlassian OAuth 2.0 User Token",
                    "placeholder": "eyJ...",
                    "description": "Authenticate via official Atlassian OAuth 2.0 3LO flow.",
                    "docs_url": "https://developer.atlassian.com/cloud/confluence/rest/v2/intro/",
                    "docs_label": "Confluence Cloud REST API",
                    "setup_guide": {
                        "title": "Confluence OAuth Setup Guide",
                        "docs_url": "https://developer.atlassian.com/console/myapps/",
                        "docs_label": "Atlassian Developer Console",
                        "instructions": [
                            "1. Go to Atlassian Developer Console and create an OAuth 2.0 integration.",
                            "2. Set Callback URL to: https://connector.suparagent.ai/api/oauth/confluence/callback",
                            "3. Add Confluence Cloud API scopes: read:page:confluence, write:page:confluence, read:space:confluence, search:confluence, offline_access.",
                            "4. Connect via Hosted Connect button."
                        ],
                        "scopes": [
                            "read:page:confluence",
                            "write:page:confluence",
                            "read:space:confluence",
                            "search:confluence",
                            "offline_access"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "eyJ..."
                        },
                        {
                            "key": "cloudId",
                            "label": "Atlassian Cloud ID",
                            "type": "text",
                            "required": False,
                            "placeholder": "your-atlassian-cloud-id"
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("confluence"):
            self.register_action(ConfluenceDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Confluence access token is required.")

        val_url = "https://api.atlassian.com/me"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Confluence connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Confluence credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Confluence validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("account_id") or token[:8] + "..."),
            "display_name": data.get("name") or data.get("email") or "Confluence Account"
        }

"""
Netlify Provider for ConnectorHub.
Loads and registers 20 actions for Netlify deploys, sites, and serverless builds.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.netlify.com/api/v1"

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
    "cancel_deploy": ["POST", "/deploys/{deployId}/cancel", ["deployId"], []],
    "create_site": ["POST", "/sites", [], ["name", "custom_domain"]],
    "create_site_build": ["POST", "/sites/{siteId}/builds", ["siteId"], ["clear_cache"]],
    "create_site_deploy_from_zip_url": ["POST", "/sites/{siteId}/deploys", ["siteId"], []],
    "delete_submission": ["DELETE", "/submissions/{submissionId}", ["submissionId"], []],
    "get_account": ["GET", "/accounts/{accountId}", ["accountId"], []],
    "get_build": ["GET", "/builds/{buildId}", ["buildId"], []],
    "get_current_user": ["GET", "/user", [], []],
    "get_deploy": ["GET", "/deploys/{deployId}", ["deployId"], []],
    "get_site": ["GET", "/sites/{siteId}", ["siteId"], []],
    "list_accounts": ["GET", "/accounts", [], []],
    "list_site_deploys": ["GET", "/sites/{siteId}/deploys", ["siteId"], ["page", "per_page"]],
    "list_site_forms": ["GET", "/sites/{siteId}/forms", ["siteId"], []],
    "list_sites": ["GET", "/sites", [], ["filter", "page", "per_page"]],
    "list_submissions": ["GET", "/sites/{siteId}/submissions", ["siteId"], ["page", "per_page"]],
    "lock_deploy": ["POST", "/deploys/{deployId}/lock", ["deployId"], []],
    "notify_build_start": ["POST", "/builds/{buildId}/start", ["buildId"], []],
    "unlock_deploy": ["POST", "/deploys/{deployId}/unlock", ["deployId"], []],
    "upload_deploy_file_from_url": ["PUT", "/deploys/{deployId}/files/{path}", ["deployId", "path"], []],
    "upload_deploy_function_from_zip_url": ["PUT", "/deploys/{deployId}/functions/{name}", ["deployId", "name"], []],
}

class NetlifyDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Developer Tools"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        headers = _build_headers(cred)
        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        target_url = f"{DEFAULT_API_BASE}{path}"
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
                err_msg = err_json.get("message") or err_json.get("error") or err_msg
            except Exception:
                pass
            raise ValueError(f"Netlify API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class NetlifyProvider(Provider):
    def __init__(self):
        super().__init__(
            service="netlify",
            display_name="Netlify",
            category="Developer Tools",
            auth_types=["oauth2", "api_key"],
            description="Netlify continuous cloud hosting, site management, builds, deployments, and forms with 20 actions.",
            homepage_url="https://www.netlify.com",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Personal Access Token",
                    "placeholder": "nfp_...",
                    "description": "Your Netlify personal access token from User Settings > Applications.",
                    "docs_url": "https://docs.netlify.com/api/get-started/",
                    "docs_label": "Netlify API Documentation",
                    "setup_guide": {
                        "title": "Netlify API Key Setup Guide",
                        "docs_url": "https://app.netlify.com/user/applications#personal-access-tokens",
                        "docs_label": "Create Netlify Token",
                        "instructions": [
                            "1. Go to Netlify User Settings > Applications > Personal Access Tokens.",
                            "2. Click 'New access token' and enter a descriptive name.",
                            "3. Copy the token (starts with nfp_...) and paste it below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "nfp_..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("netlify"):
            self.register_action(NetlifyDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Netlify API token is required.")

        val_url = f"{DEFAULT_API_BASE}/user"
        assert_public_url(val_url)
        headers = _build_headers(credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Netlify connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Netlify credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Netlify validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": data.get("full_name") or data.get("email") or "Netlify Account"
        }

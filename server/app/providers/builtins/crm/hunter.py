"""
Hunter Provider for ConnectorHub.
Loads and registers 18 actions for domain search, email finder, email verification, and lead management.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.hunter.io/v2"

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
        headers["X-API-KEY"] = token
    return headers

ROUTES: Dict[str, List[Any]] = {
    "account_information": ["GET", "/account", [], []],
    "domain_search": ["GET", "/domain-search", [], ["domain", "company", "limit", "offset", "type", "seniority", "department"]],
    "email_finder": ["GET", "/email-finder", [], ["domain", "company", "first_name", "last_name", "full_name"]],
    "email_verifier": ["GET", "/email-verifier", [], ["email"]],
    "email_count": ["GET", "/email-count", [], ["domain", "company", "type"]],
    "people_enrichment": ["GET", "/people-enrichment", [], ["email", "linkedin_handle"]],
    "company_enrichment": ["GET", "/company-enrichment", [], ["domain"]],
    "combined_enrichment": ["GET", "/combined-enrichment", [], ["email", "linkedin_handle"]],
    "discover_companies": ["GET", "/discover-companies", [], ["query", "limit", "offset"]],
    "list_leads": ["GET", "/leads", [], ["leads_list_id", "limit", "offset"]],
    "get_lead": ["GET", "/leads/{id}", ["id"], []],
    "create_lead": ["POST", "/leads", [], []],
    "update_lead": ["PUT", "/leads/{id}", ["id"], []],
    "delete_lead": ["DELETE", "/leads/{id}", ["id"], []],
    "upsert_lead": ["POST", "/leads/upsert", [], []],
    "list_leads_lists": ["GET", "/leads_lists", [], ["limit", "offset"]],
    "create_leads_list": ["POST", "/leads_lists", [], []],
    "list_custom_attributes": ["GET", "/custom_attributes", [], []],
}

class HunterDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Marketing"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
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
        if token:
            params["api_key"] = token

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
                errors = err_json.get("errors")
                if isinstance(errors, list) and errors:
                    err_msg = errors[0].get("details") or str(errors[0])
                else:
                    err_msg = err_json.get("message") or err_msg
            except Exception:
                pass
            raise ValueError(f"Hunter API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class HunterProvider(Provider):
    def __init__(self):
        super().__init__(
            service="hunter",
            display_name="Hunter",
            category="Marketing",
            auth_types=["api_key"],
            description="Email finder, verification, domain search, and lead management with 18 actions.",
            homepage_url="https://hunter.io",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Hunter API Key",
                    "placeholder": "9a8b7c...",
                    "description": "Your Hunter API secret key from API Settings.",
                    "docs_url": "https://hunter.io/api-documentation/v2",
                    "docs_label": "Hunter API Documentation",
                    "setup_guide": {
                        "title": "Hunter API Key Setup Guide",
                        "docs_url": "https://hunter.io/api_keys",
                        "docs_label": "Hunter API Keys",
                        "instructions": [
                            "1. Log in to Hunter.io.",
                            "2. Click on your profile icon and select 'API'.",
                            "3. Copy your API Key.",
                            "4. Paste it below to connect."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "Paste Hunter API key..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("hunter"):
            self.register_action(HunterDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Hunter API key is required.")

        val_url = f"{DEFAULT_API_BASE}/account"
        assert_public_url(val_url)
        headers = _build_headers(credential)
        params = {"api_key": token}

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers, params=params)
        except Exception as e:
            raise ValueError(f"Hunter connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Hunter credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Hunter validation failed: {resp.status_code} {resp.text}")

        data = resp.json().get("data", {}) if resp.status_code == 200 else {}
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        return {
            "account_id": str(data.get("id") or token[:8] + "..."),
            "display_name": full_name or data.get("email") or "Hunter Account"
        }

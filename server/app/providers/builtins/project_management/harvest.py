"""
Harvest Provider for ConnectorHub.
Loads and registers 15 actions for time tracking, projects, clients, and time entries.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.harvestapp.com/v2"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "personalAccessToken", "api_key", "access_token"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    account_id = cred.get("accountId") or cred.get("account_id") or cred.get("harvestAccountId")
    if account_id:
        headers["Harvest-Account-Id"] = str(account_id).strip()
    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_time_entry": ["POST", "/time_entries", [], ["project_id", "task_id", "spent_date", "hours", "notes"]],
    "delete_time_entry": ["DELETE", "/time_entries/{timeEntryId}", ["timeEntryId"], []],
    "get_client": ["GET", "/clients/{clientId}", ["clientId"], []],
    "get_current_user": ["GET", "/users/me", [], []],
    "get_project": ["GET", "/projects/{projectId}", ["projectId"], []],
    "get_task": ["GET", "/tasks/{taskId}", ["taskId"], []],
    "get_time_entry": ["GET", "/time_entries/{timeEntryId}", ["timeEntryId"], []],
    "list_clients": ["GET", "/clients", [], ["is_active", "page", "per_page"]],
    "list_project_task_assignments": ["GET", "/projects/{projectId}/task_assignments", ["projectId"], []],
    "list_projects": ["GET", "/projects", [], ["is_active", "client_id", "page", "per_page"]],
    "list_tasks": ["GET", "/tasks", [], ["is_active", "page", "per_page"]],
    "list_time_entries": ["GET", "/time_entries", [], ["user_id", "client_id", "project_id", "from", "to", "page", "per_page"]],
    "restart_time_entry": ["PATCH", "/time_entries/{timeEntryId}/restart", ["timeEntryId"], []],
    "stop_time_entry": ["PATCH", "/time_entries/{timeEntryId}/stop", ["timeEntryId"], []],
    "update_time_entry": ["PATCH", "/time_entries/{timeEntryId}", ["timeEntryId"], ["project_id", "task_id", "hours", "notes"]],
}

class HarvestDynamicAction(Action):
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
            raise ValueError(f"Harvest API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class HarvestProvider(Provider):
    def __init__(self):
        super().__init__(
            service="harvest",
            display_name="Harvest",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="Harvest time tracking, timesheets, project budgets, clients, and invoicing with 15 actions.",
            homepage_url="https://www.getharvest.com",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Harvest Personal Access Token",
                    "placeholder": "Bearer ...",
                    "description": "Your Harvest personal access token and Account ID.",
                    "docs_url": "https://help.getharvest.com/api-v2/",
                    "docs_label": "Harvest API Documentation",
                    "setup_guide": {
                        "title": "Harvest API Token Setup Guide",
                        "docs_url": "https://id.getharvest.com/developers",
                        "docs_label": "Harvest Developer Tools",
                        "instructions": [
                            "1. Go to Harvest Developers (id.getharvest.com/developers).",
                            "2. Click 'Create New Personal Access Token'.",
                            "3. Copy your Personal Access Token and your Account ID.",
                            "4. Paste them into the fields below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "Bearer ..."
                        },
                        {
                            "key": "accountId",
                            "label": "Harvest Account ID",
                            "type": "text",
                            "required": False,
                            "placeholder": "1234567"
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("harvest"):
            self.register_action(HarvestDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("Harvest access token is required.")

        account_id = credential.get("accountId") or credential.get("account_id") or credential.get("harvestAccountId")
        company_name = ""

        # Auto-discover accounts via Harvest ID endpoint if accountId is not provided (e.g. in OAuth flows)
        if not account_id:
            accounts_url = "https://id.getharvest.com/api/v2/accounts"
            assert_public_url(accounts_url)
            acc_resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=accounts_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": "ConnectorHub/1.0"
                }
            )
            if acc_resp.status_code == 200:
                try:
                    acc_data = acc_resp.json()
                    accounts = acc_data.get("accounts", [])
                    if accounts:
                        first_acc = accounts[0]
                        account_id = str(first_acc.get("id"))
                        company_name = first_acc.get("name", "")
                except Exception:
                    pass

        val_url = f"{DEFAULT_API_BASE}/users/me"
        assert_public_url(val_url)
        headers = _build_headers({**credential, "accountId": account_id} if account_id else credential)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, headers=headers)
        except Exception as e:
            raise ValueError(f"Harvest connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Harvest credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Harvest validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        display_name = f"Harvest ({company_name})" if company_name else (full_name or data.get("email") or "Harvest Account")

        return {
            "account_id": str(account_id or data.get("id") or "verified"),
            "display_name": display_name,
            "metadata": {
                "accountId": str(account_id) if account_id else None,
                "companyName": company_name or None
            }
        }

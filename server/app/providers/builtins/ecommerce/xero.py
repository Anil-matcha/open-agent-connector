"""
Xero Provider for ConnectorHub.
Loads and registers 15 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

XERO_API_BASE = "https://api.xero.com/api.xro/2.0"
XERO_IDENTITY_BASE = "https://api.xero.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["accessToken", "token", "access_token", "apiKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Xero OAuth access token required. Please connect your Xero account first.")

def _headers(token: str, tenant_id: Optional[str] = None) -> Dict[str, str]:
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }
    if tenant_id:
        h["Xero-Tenant-Id"] = tenant_id
    return h

ROUTES: Dict[str, List[Any]] = {
    "create_contact": [
        "POST",
        "/Contacts",
        [],
        []
    ],
    "create_invoice": [
        "POST",
        "/Invoices",
        [],
        []
    ],
    "get_account": [
        "GET",
        "/Accounts/{account_id}",
        [
            "account_id"
        ],
        []
    ],
    "get_balance_sheet": [
        "GET",
        "/Reports/BalanceSheet",
        [],
        [
            "date",
            "paymentsOnly"
        ]
    ],
    "get_bank_transaction": [
        "GET",
        "/BankTransactions/{bank_transaction_id}",
        [
            "bank_transaction_id"
        ],
        []
    ],
    "get_contact": [
        "GET",
        "/Contacts/{contact_id}",
        [
            "contact_id"
        ],
        []
    ],
    "get_invoice": [
        "GET",
        "/Invoices/{invoice_id}",
        [
            "invoice_id"
        ],
        []
    ],
    "get_organisation": [
        "GET",
        "/Organisation",
        [],
        []
    ],
    "get_profit_and_loss": [
        "GET",
        "/Reports/ProfitAndLoss",
        [],
        [
            "fromDate",
            "toDate"
        ]
    ],
    "list_accounts": [
        "GET",
        "/Accounts",
        [],
        [
            "status"
        ]
    ],
    "list_organisations": [
        "GET",
        "/connections",
        [],
        []
    ],
    "search_bank_transactions": [
        "GET",
        "/BankTransactions",
        [],
        [
            "page",
            "status"
        ]
    ],
    "search_contacts": [
        "GET",
        "/Contacts",
        [],
        [
            "page",
            "search"
        ]
    ],
    "search_invoices": [
        "GET",
        "/Invoices",
        [],
        [
            "page",
            "status"
        ]
    ],
    "update_invoice_status": [
        "POST",
        "/Invoices/{invoice_id}",
        [
            "invoice_id"
        ],
        []
    ]
}

class XeroDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Accounting & Finance"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        cred = credential or {}
        tenant_id = cred.get("tenantId") or cred.get("tenant_id") or input_data.get("tenantId") or input_data.get("tenant_id")

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        if path.startswith("/connections"):
            target_url = f"{XERO_IDENTITY_BASE}{path}"
            headers = _headers(token, None)
        else:
            target_url = f"{XERO_API_BASE}{path}"
            headers = _headers(token, str(tenant_id) if tenant_id else None)

        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in ["tenantId", "tenant_id"] or k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("Detail") or data.get("Message") or data.get("message") or resp.text
            raise ValueError(f"Xero API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class XeroProvider(Provider):
    def __init__(self):
        super().__init__(
            service="xero",
            display_name="Xero",
            category="Accounting & Finance",
            auth_types=["oauth2"],
            description="Xero accounting and invoicing integration suite with 15 actions.",
            auth_configs=[
                {
                    "type": "oauth2",
                    "fields": [
                        {
                            "key": "tenantId",
                            "label": "Tenant ID",
                            "type": "text",
                            "required": False,
                            "placeholder": "...",
                            "description": "Default Xero Organization Tenant ID. Automatically resolved if omitted."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("xero"):
            self.register_action(XeroDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{XERO_IDENTITY_BASE}/connections"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token, None)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Xero credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Xero validation failed: {resp.status_code} {resp.text}")

        try:
            conns = resp.json()
            if isinstance(conns, list) and len(conns) > 0:
                first = conns[0]
                t_id = first.get("tenantId") or "connected"
                t_name = first.get("tenantName") or t_id
            else:
                t_id = "connected"
                t_name = "Xero Organization"
        except Exception:
            t_id = "connected"
            t_name = "Xero Organization"

        return {
            "account_id": t_id,
            "display_name": f"Xero ({t_name})"
        }

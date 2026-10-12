"""
Mailtrap Provider for ConnectorHub.
Loads and registers 50 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

MAILTRAP_API_BASE = "https://mailtrap.io"
MAILTRAP_SEND_BASE = "https://send.api.mailtrap.io"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "token", "accessToken", "api_key", "apiToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Mailtrap API token required. Please connect your Mailtrap account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "Api-Token": token,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "clean_inbox": [
        "PATCH",
        "/api/accounts/{accountId}/inboxes/{inboxId}/clean",
        [
            "accountId",
            "inboxId"
        ],
        []
    ],
    "create_contact": [
        "POST",
        "/api/accounts/{accountId}/contacts",
        [
            "accountId"
        ],
        []
    ],
    "create_contact_event": [
        "POST",
        "/api/accounts/{accountId}/contacts/{contactIdentifier}/events",
        [
            "accountId",
            "contactIdentifier"
        ],
        []
    ],
    "create_contact_export": [
        "POST",
        "/api/accounts/{accountId}/contacts/exports",
        [
            "accountId"
        ],
        []
    ],
    "create_contact_field": [
        "POST",
        "/api/accounts/{accountId}/contacts/fields",
        [
            "accountId"
        ],
        []
    ],
    "create_contact_list": [
        "POST",
        "/api/accounts/{accountId}/contacts/lists",
        [
            "accountId"
        ],
        []
    ],
    "create_email_template": [
        "POST",
        "/api/accounts/{accountId}/email_templates",
        [
            "accountId"
        ],
        []
    ],
    "create_sending_domain": [
        "POST",
        "/api/accounts/{accountId}/sending_domains",
        [
            "accountId"
        ],
        []
    ],
    "delete_contact": [
        "DELETE",
        "/api/accounts/{accountId}/contacts/{contactIdentifier}",
        [
            "accountId",
            "contactIdentifier"
        ],
        []
    ],
    "delete_contact_field": [
        "DELETE",
        "/api/accounts/{accountId}/contacts/fields/{fieldId}",
        [
            "accountId",
            "fieldId"
        ],
        []
    ],
    "delete_contact_list": [
        "DELETE",
        "/api/accounts/{accountId}/contacts/lists/{listId}",
        [
            "accountId",
            "listId"
        ],
        []
    ],
    "delete_email_template": [
        "DELETE",
        "/api/accounts/{accountId}/email_templates/{emailTemplateId}",
        [
            "accountId",
            "emailTemplateId"
        ],
        []
    ],
    "delete_project": [
        "DELETE",
        "/api/accounts/{accountId}/projects/{projectId}",
        [
            "accountId",
            "projectId"
        ],
        []
    ],
    "delete_sending_domain": [
        "DELETE",
        "/api/accounts/{accountId}/sending_domains/{sendingDomainId}",
        [
            "accountId",
            "sendingDomainId"
        ],
        []
    ],
    "get_billing_usage": [
        "GET",
        "/api/accounts/{accountId}/billing/usage",
        [
            "accountId"
        ],
        []
    ],
    "get_contact": [
        "GET",
        "/api/accounts/{accountId}/contacts/{contactIdentifier}",
        [
            "accountId",
            "contactIdentifier"
        ],
        []
    ],
    "get_contact_export": [
        "GET",
        "/api/accounts/{accountId}/contacts/exports/{exportId}",
        [
            "accountId",
            "exportId"
        ],
        []
    ],
    "get_contact_field": [
        "GET",
        "/api/accounts/{accountId}/contacts/fields/{fieldId}",
        [
            "accountId",
            "fieldId"
        ],
        []
    ],
    "get_contact_import": [
        "GET",
        "/api/accounts/{accountId}/contacts/imports/{importId}",
        [
            "accountId",
            "importId"
        ],
        []
    ],
    "get_contact_list": [
        "GET",
        "/api/accounts/{accountId}/contacts/lists/{listId}",
        [
            "accountId",
            "listId"
        ],
        []
    ],
    "get_email_template": [
        "GET",
        "/api/accounts/{accountId}/email_templates/{emailTemplateId}",
        [
            "accountId",
            "emailTemplateId"
        ],
        []
    ],
    "get_inbox": [
        "GET",
        "/api/accounts/{accountId}/inboxes/{inboxId}",
        [
            "accountId",
            "inboxId"
        ],
        []
    ],
    "get_message": [
        "GET",
        "/api/accounts/{accountId}/inboxes/{inboxId}/messages/{messageId}",
        [
            "accountId",
            "inboxId",
            "messageId"
        ],
        []
    ],
    "get_message_html_source": [
        "GET",
        "/api/accounts/{accountId}/inboxes/{inboxId}/messages/{messageId}/body.htmlsource",
        [
            "accountId",
            "inboxId",
            "messageId"
        ],
        []
    ],
    "get_permission_resources": [
        "GET",
        "/api/accounts/{accountId}/permissions/resources",
        [
            "accountId"
        ],
        []
    ],
    "get_project": [
        "GET",
        "/api/accounts/{accountId}/projects/{projectId}",
        [
            "accountId",
            "projectId"
        ],
        []
    ],
    "get_sending_domain": [
        "GET",
        "/api/accounts/{accountId}/sending_domains/{sendingDomainId}",
        [
            "accountId",
            "sendingDomainId"
        ],
        []
    ],
    "get_sending_stats": [
        "GET",
        "/api/accounts/{accountId}/stats",
        [
            "accountId"
        ],
        []
    ],
    "get_sending_stats_by_categories": [
        "GET",
        "/api/accounts/{accountId}/stats/categories",
        [
            "accountId"
        ],
        []
    ],
    "get_sending_stats_by_date": [
        "GET",
        "/api/accounts/{accountId}/stats/date",
        [
            "accountId"
        ],
        []
    ],
    "get_sending_stats_by_domains": [
        "GET",
        "/api/accounts/{accountId}/stats/domains",
        [
            "accountId"
        ],
        []
    ],
    "get_sending_stats_by_esp": [
        "GET",
        "/api/accounts/{accountId}/stats/email_service_providers",
        [
            "accountId"
        ],
        []
    ],
    "import_contacts": [
        "POST",
        "/api/accounts/{accountId}/contacts/imports",
        [
            "accountId"
        ],
        []
    ],
    "list_accounts": [
        "GET",
        "/api/accounts",
        [],
        []
    ],
    "list_contact_fields": [
        "GET",
        "/api/accounts/{accountId}/contacts/fields",
        [
            "accountId"
        ],
        []
    ],
    "list_contact_lists": [
        "GET",
        "/api/accounts/{accountId}/contacts/lists",
        [
            "accountId"
        ],
        []
    ],
    "list_email_templates": [
        "GET",
        "/api/accounts/{accountId}/email_templates",
        [
            "accountId"
        ],
        []
    ],
    "list_inboxes": [
        "GET",
        "/api/accounts/{accountId}/inboxes",
        [
            "accountId"
        ],
        []
    ],
    "list_messages": [
        "GET",
        "/api/accounts/{accountId}/inboxes/{inboxId}/messages",
        [
            "accountId",
            "inboxId"
        ],
        [
            "page",
            "lastId"
        ]
    ],
    "list_projects": [
        "GET",
        "/api/accounts/{accountId}/projects",
        [
            "accountId"
        ],
        []
    ],
    "list_sending_domains": [
        "GET",
        "/api/accounts/{accountId}/sending_domains",
        [
            "accountId"
        ],
        []
    ],
    "list_suppressions": [
        "GET",
        "/api/accounts/{accountId}/suppressions",
        [
            "accountId"
        ],
        []
    ],
    "mark_inbox_as_read": [
        "PATCH",
        "/api/accounts/{accountId}/inboxes/{inboxId}/all_read",
        [
            "accountId",
            "inboxId"
        ],
        []
    ],
    "reset_inbox_credentials": [
        "PATCH",
        "/api/accounts/{accountId}/inboxes/{inboxId}/reset_credentials",
        [
            "accountId",
            "inboxId"
        ],
        []
    ],
    "update_contact": [
        "PATCH",
        "/api/accounts/{accountId}/contacts/{contactIdentifier}",
        [
            "accountId",
            "contactIdentifier"
        ],
        []
    ],
    "update_contact_field": [
        "PATCH",
        "/api/accounts/{accountId}/contacts/fields/{fieldId}",
        [
            "accountId",
            "fieldId"
        ],
        []
    ],
    "update_contact_list": [
        "PATCH",
        "/api/accounts/{accountId}/contacts/lists/{listId}",
        [
            "accountId",
            "listId"
        ],
        []
    ],
    "update_email_template": [
        "PATCH",
        "/api/accounts/{accountId}/email_templates/{emailTemplateId}",
        [
            "accountId",
            "emailTemplateId"
        ],
        []
    ],
    "update_inbox": [
        "PATCH",
        "/api/accounts/{accountId}/inboxes/{inboxId}",
        [
            "accountId",
            "inboxId"
        ],
        []
    ],
    "update_project": [
        "PATCH",
        "/api/accounts/{accountId}/projects/{projectId}",
        [
            "accountId",
            "projectId"
        ],
        []
    ]
}

class MailtrapDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        cred = credential or {}
        headers = _headers(token)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        account_id = input_data.get("accountId") or input_data.get("account_id") or cred.get("accountId") or cred.get("account_id")
        if account_id:
            path = path.replace("{accountId}", urllib.parse.quote(str(account_id), safe=""))
            path = path.replace("{account_id}", urllib.parse.quote(str(account_id), safe=""))

        for var in path_vars:
            if var in ["accountId", "account_id"]:
                continue
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        base_url = MAILTRAP_SEND_BASE if path.startswith("/api/send") else MAILTRAP_API_BASE
        target_url = f"{base_url}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in ["accountId", "account_id"] or k in path_vars:
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
            err_msg = data.get("error") or data.get("errors") or data.get("message") or resp.text
            raise ValueError(f"Mailtrap API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class MailtrapProvider(Provider):
    def __init__(self):
        super().__init__(
            service="mailtrap",
            display_name="Mailtrap",
            category="Communication",
            auth_types=["api_key"],
            description="Mailtrap email delivery, testing, and marketing integration suite with 50 actions.",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "API Token",
                    "placeholder": "MAILTRAP_API_TOKEN",
                    "description": "Mailtrap API token used with the Api-Token or Authorization Bearer header.",
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "MAILTRAP_API_TOKEN",
                            "description": "Mailtrap API token from Mailtrap Settings > API Tokens."
                        },
                        {
                            "key": "accountId",
                            "label": "Account ID",
                            "type": "text",
                            "required": False,
                            "placeholder": "123456",
                            "description": "Default Mailtrap Account ID (optional)."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("mailtrap"):
            self.register_action(MailtrapDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{MAILTRAP_API_BASE}/api/accounts"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Mailtrap credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Mailtrap validation failed: {resp.status_code} {resp.text}")

        try:
            accounts = resp.json()
            if isinstance(accounts, list) and len(accounts) > 0:
                first = accounts[0]
                acc_id = str(first.get("id", "verified"))
                acc_name = first.get("name") or acc_id
            else:
                acc_id = "verified"
                acc_name = "Mailtrap Account"
        except Exception:
            acc_id = "verified"
            acc_name = "Mailtrap Account"

        return {
            "account_id": acc_id,
            "display_name": f"Mailtrap ({acc_name})"
        }

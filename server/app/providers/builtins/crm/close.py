"""
Close Provider for ConnectorHub.
Loads and registers 16 actions with exact route definitions and parameters.
"""
import base64
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.close.com/api/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    # Replace any custom domains/subdomains/tenants in base template
    for key in ["domain", "subdomain", "host", "tenant"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "basic_key"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "basic_key":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "basic_key_secret":
        k = str(cred.get("accessKey") or cred.get("key") or token).strip()
        s = str(cred.get("accessKeySecret") or cred.get("secret") or "").strip()
        pair = f"{k}:{s}"
        headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "ssws":
        if token:
            headers["Authorization"] = f"SSWS {token}"
    elif auth_mode == "bamboo_basic":
        if token:
            pair = f"{token}:x"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "api_key_or_bearer":
        if token:
            headers["Authorization"] = f"API-Key {token}"

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_contact": [
        "POST",
        "/contact",
        [
            "leadId"
        ],
        [
            "name",
            "title",
            "emails",
            "phones",
            "urls"
        ]
    ],
    "create_lead": [
        "POST",
        "/lead",
        [
            "statusId"
        ],
        [
            "name",
            "description",
            "url",
            "addresses",
            "contacts"
        ]
    ],
    "create_opportunity": [
        "POST",
        "/opportunity",
        [
            "leadId",
            "contactId",
            "userId",
            "statusId"
        ],
        [
            "confidence",
            "note",
            "value",
            "valuePeriod",
            "dateWon"
        ]
    ],
    "create_task": [
        "POST",
        "/task",
        [
            "leadId"
        ],
        [
            "text",
            "assignedTo",
            "date",
            "dueDate",
            "isComplete",
            "isDateless"
        ]
    ],
    "get_contact": [
        "GET",
        "/contact/{contactId}",
        [
            "contactId"
        ],
        [
            "includeFields"
        ]
    ],
    "get_lead": [
        "GET",
        "/lead/{leadId}",
        [
            "leadId"
        ],
        [
            "includeFields"
        ]
    ],
    "get_opportunity": [
        "GET",
        "/opportunity/{opportunityId}",
        [
            "opportunityId"
        ],
        [
            "includeFields"
        ]
    ],
    "get_task": [
        "GET",
        "/task/{taskId}",
        [
            "taskId"
        ],
        [
            "includeFields"
        ]
    ],
    "list_contacts": [
        "GET",
        "/contact",
        [
            "leadId"
        ],
        [
            "limit",
            "skip",
            "includeFields"
        ]
    ],
    "list_leads": [
        "GET",
        "/lead",
        [],
        [
            "limit",
            "skip",
            "includeFields"
        ]
    ],
    "list_opportunities": [
        "GET",
        "/me",
        [
            "leadId",
            "userId",
            "statusId"
        ],
        [
            "limit",
            "skip",
            "includeFields",
            "statusType",
            "valuePeriod",
            "isStalled",
            "query",
            "leadQuery",
            "orderBy"
        ]
    ],
    "list_tasks": [
        "GET",
        "/task",
        [
            "leadId"
        ],
        [
            "limit",
            "skip",
            "includeFields",
            "assignedTo",
            "isComplete",
            "view"
        ]
    ],
    "update_contact": [
        "PUT",
        "/contact/{contactId}",
        [
            "contactId"
        ],
        [
            "name",
            "title",
            "emails",
            "phones",
            "urls"
        ]
    ],
    "update_lead": [
        "PUT",
        "/lead/{leadId}",
        [
            "leadId",
            "statusId"
        ],
        [
            "name",
            "description",
            "url"
        ]
    ],
    "update_opportunity": [
        "PUT",
        "/opportunity/{opportunityId}",
        [
            "opportunityId",
            "contactId",
            "userId",
            "statusId"
        ],
        [
            "confidence",
            "note",
            "value",
            "valuePeriod",
            "dateWon"
        ]
    ],
    "update_task": [
        "PUT",
        "/task/{taskId}",
        [
            "taskId"
        ],
        [
            "text",
            "assignedTo",
            "date",
            "dueDate",
            "isComplete",
            "isDateless"
        ]
    ]
}

class CloseDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "CRM & Sales"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        base_url = _resolve_base_url(cred)
        headers = _build_headers(cred)

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

        target_url = f"{base_url}{path}" if not path.startswith("http") else path
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        # For Trello, append key & token to params
        if "close" == "trello":
            if cred.get("apiKey") or cred.get("key"):
                params["key"] = str(cred.get("apiKey") or cred.get("key"))
            if cred.get("token"):
                params["token"] = str(cred.get("token"))

        for k, v in input_data.items():
            if k in path_vars:
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
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Close API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class CloseProvider(Provider):
    def __init__(self):
        super().__init__(
            service="close",
            display_name="Close",
            category="CRM & Sales",
            auth_types=["api_key"],
            description="Close CRM sales engagement, leads, contacts, opportunities, and tasks with 16 actions."
        )
        for act in get_provider_actions("close"):
            self.register_action(CloseDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.close.com/api/v1/me"
        for key in ["domain", "subdomain", "host", "tenant"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "close" == "trello":
            if cred.get("apiKey") or cred.get("key"):
                params["key"] = str(cred.get("apiKey") or cred.get("key"))
            if cred.get("token"):
                params["token"] = str(cred.get("token"))

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers,
            params=params if params else None
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Close credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Close validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Close Account"
        }

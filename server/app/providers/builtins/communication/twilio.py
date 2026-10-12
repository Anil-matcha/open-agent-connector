"""
Twilio Provider for ConnectorHub.
Loads and registers 8 actions with exact route definitions and parameters.
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

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

def _extract_creds(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    account_sid = cred.get("accountSid") or cred.get("account_sid") or cred.get("sid") or ""
    auth_token = cred.get("authToken") or cred.get("auth_token") or cred.get("token") or cred.get("apiKey") or ""

    if not account_sid or not auth_token:
        raise ValueError("Twilio requires accountSid and authToken.")

    return {
        "account_sid": str(account_sid).strip(),
        "auth_token": str(auth_token).strip()
    }

def _headers(account_sid: str, auth_token: str) -> Dict[str, str]:
    auth_pair = f"{account_sid}:{auth_token}"
    b64_auth = base64.b64encode(auth_pair.encode()).decode()
    return {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "create_call": [
        "POST",
        "/Accounts/{accountSid}/Calls.json",
        [
            "accountSid"
        ],
        []
    ],
    "get_account": [
        "GET",
        "/Accounts/{accountSid}.json",
        [
            "accountSid"
        ],
        []
    ],
    "get_call": [
        "GET",
        "/Accounts/{accountSid}/Calls/{callSid}.json",
        [
            "accountSid",
            "callSid"
        ],
        []
    ],
    "get_message": [
        "GET",
        "/Accounts/{accountSid}/Messages/{messageSid}.json",
        [
            "accountSid",
            "messageSid"
        ],
        []
    ],
    "list_calls": [
        "GET",
        "/Accounts/{accountSid}/Calls.json",
        [
            "accountSid"
        ],
        [
            "To",
            "From",
            "Status",
            "StartTime",
            "PageSize"
        ]
    ],
    "list_messages": [
        "GET",
        "/Accounts/{accountSid}/Messages.json",
        [
            "accountSid"
        ],
        [
            "To",
            "From",
            "DateSent",
            "PageSize"
        ]
    ],
    "list_usage_records": [
        "GET",
        "/Accounts/{accountSid}/Usage/Records.json",
        [
            "accountSid"
        ],
        [
            "Category",
            "StartDate",
            "EndDate"
        ]
    ],
    "send_message": [
        "POST",
        "/Accounts/{accountSid}/Messages.json",
        [
            "accountSid"
        ],
        []
    ]
}

class TwilioDynamicAction(Action):
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
        creds = _extract_creds(credential)
        headers = _headers(creds["account_sid"], creds["auth_token"])

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        path = path.replace("{accountSid}", urllib.parse.quote(creds["account_sid"], safe=""))
        path = path.replace("{account_sid}", urllib.parse.quote(creds["account_sid"], safe=""))

        for var in path_vars:
            if var in ["accountSid", "account_sid"]:
                continue
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{TWILIO_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in ["accountSid", "account_sid"] or k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
                params[k] = v
            else:
                body[k] = v

        if req_method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            resp = await client.request(
                method=req_method,
                url=target_url,
                headers=headers,
                data=body if body else None,
                params=params if params else None
            )
        else:
            resp = await execute_guarded_request(
                client=client,
                method=req_method,
                url=target_url,
                headers=headers,
                params=params if params else None
            )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("detail") or resp.text
            raise ValueError(f"Twilio API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class TwilioProvider(Provider):
    def __init__(self):
        super().__init__(
            service="twilio",
            display_name="Twilio",
            category="Communication",
            auth_types=["custom_credential"],
            description="Twilio messaging, voice, calls, and usage integration suite with 8 actions.",
            auth_configs=[
                {
                    "type": "custom_credential",
                    "fields": [
                        {
                            "key": "accountSid",
                            "label": "Account SID",
                            "type": "text",
                            "required": True,
                            "placeholder": "AC...",
                            "description": "Twilio Account SID from twilio.com/console."
                        },
                        {
                            "key": "authToken",
                            "label": "Auth Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "...",
                            "description": "Twilio Auth Token from twilio.com/console."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("twilio"):
            self.register_action(TwilioDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        creds = _extract_creds(credential)
        val_url = f"{TWILIO_API_BASE}/Accounts/{creds['account_sid']}.json"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(creds["account_sid"], creds["auth_token"])
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Twilio credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Twilio validation failed: {resp.status_code} {resp.text}")

        try:
            acc = resp.json()
            friendly = acc.get("friendly_name") or creds["account_sid"]
        except Exception:
            friendly = creds["account_sid"]

        return {
            "account_id": creds["account_sid"],
            "display_name": f"Twilio ({friendly})"
        }

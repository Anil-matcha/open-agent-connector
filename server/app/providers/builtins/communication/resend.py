"""
Resend Provider for ConnectorHub.
Loads and registers 12 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

RESEND_API_BASE = "https://api.resend.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "token", "accessToken", "key", "api_key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Resend API key required. Please connect your Resend account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "cancel_scheduled_email": [
        "POST",
        "/emails/{emailId}/cancel",
        [
            "emailId"
        ],
        []
    ],
    "get_received_email": [
        "GET",
        "/emails/receiving/{emailId}",
        [
            "emailId"
        ],
        []
    ],
    "get_received_email_attachment": [
        "GET",
        "/emails/receiving/{emailId}/attachments/{attachmentId}",
        [
            "emailId",
            "attachmentId"
        ],
        []
    ],
    "get_sent_email": [
        "GET",
        "/emails/{emailId}",
        [
            "emailId"
        ],
        []
    ],
    "get_sent_email_attachment": [
        "GET",
        "/emails/{emailId}/attachments/{attachmentId}",
        [
            "emailId",
            "attachmentId"
        ],
        []
    ],
    "list_received_email_attachments": [
        "GET",
        "/emails/receiving/{emailId}/attachments",
        [
            "emailId"
        ],
        []
    ],
    "list_received_emails": [
        "GET",
        "/emails/receiving",
        [],
        []
    ],
    "list_sent_email_attachments": [
        "GET",
        "/emails/{emailId}/attachments",
        [
            "emailId"
        ],
        []
    ],
    "list_sent_emails": [
        "GET",
        "/emails",
        [],
        [
            "limit"
        ]
    ],
    "send_batch_emails": [
        "POST",
        "/emails/batch",
        [],
        []
    ],
    "send_email": [
        "POST",
        "/emails",
        [],
        []
    ],
    "update_scheduled_email": [
        "PATCH",
        "/emails/{emailId}",
        [
            "emailId"
        ],
        []
    ]
}

class ResendDynamicAction(Action):
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
        headers = _headers(token)

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

        target_url = f"{RESEND_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

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
            err_msg = data.get("message") or data.get("name") or resp.text
            raise ValueError(f"Resend API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ResendProvider(Provider):
    def __init__(self):
        super().__init__(
            service="resend",
            display_name="Resend",
            category="Communication",
            auth_types=["api_key"],
            description="Resend transactional email integration suite with 12 actions."
        )
        for act in get_provider_actions("resend"):
            self.register_action(ResendDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{RESEND_API_BASE}/api-keys"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Resend credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            # Check /emails endpoint with validation check
            test_url = f"{RESEND_API_BASE}/emails"
            resp2 = await execute_guarded_request(
                client=client,
                method="POST",
                url=test_url,
                headers=_headers(token),
                json_body={}
            )
            # If 401/403, key is invalid
            if resp2.status_code in [401, 403]:
                raise ValueError(f"Invalid Resend API key: {resp2.text}")

        return {
            "account_id": token[:8] + "...",
            "display_name": f"Resend ({token[:8]}...)"
        }

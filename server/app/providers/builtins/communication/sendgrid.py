"""
SendGrid Provider for ConnectorHub.
Loads and registers 4 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SENDGRID_API_BASE = "https://api.sendgrid.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "token", "accessToken", "api_key", "key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("SendGrid API key required. Please connect your SendGrid account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "get_account_info": [
        "GET",
        "/v3/user/account",
        [],
        []
    ],
    "get_user_scopes": [
        "GET",
        "/v3/scopes",
        [],
        []
    ],
    "list_transactional_templates": [
        "GET",
        "/v3/templates",
        [],
        [
            "generations",
            "page_size"
        ]
    ],
    "send_email": [
        "POST",
        "/v3/mail/send",
        [],
        []
    ]
}

class SendGridDynamicAction(Action):
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

        target_url = f"{SENDGRID_API_BASE}{path}"
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
            err_msg = data.get("errors", [{}])[0].get("message") or data.get("message") or resp.text
            raise ValueError(f"SendGrid API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class SendGridProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sendgrid",
            display_name="SendGrid",
            category="Communication",
            auth_types=["api_key"],
            description="SendGrid email delivery and transactional templates suite with 4 actions."
        )
        for act in get_provider_actions("sendgrid"):
            self.register_action(SendGridDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{SENDGRID_API_BASE}/v3/user/account"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            # Try scopes endpoint
            resp2 = await execute_guarded_request(
                client=client,
                method="GET",
                url=f"{SENDGRID_API_BASE}/v3/scopes",
                headers=_headers(token)
            )
            if resp2.status_code in [401, 403]:
                raise ValueError(f"Invalid SendGrid API key: {resp2.text}")
            elif resp2.status_code < 400:
                return {
                    "account_id": "verified",
                    "display_name": "SendGrid API Key"
                }
            raise ValueError(f"Invalid SendGrid credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"SendGrid validation failed: {resp.status_code} {resp.text}")

        try:
            acc = resp.json()
            acc_type = acc.get("type") or "Account"
        except Exception:
            acc_type = "Account"

        return {
            "account_id": token[:8] + "...",
            "display_name": f"SendGrid ({acc_type})"
        }

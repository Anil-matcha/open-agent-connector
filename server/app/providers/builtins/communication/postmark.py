"""
Postmark Provider for ConnectorHub.
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

POSTMARK_API_BASE = "https://api.postmarkapp.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "serverToken", "token", "server_token", "key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Postmark server token required. Please connect your Postmark account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "X-Postmark-Server-Token": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "create_template": [
        "POST",
        "/templates",
        [],
        []
    ],
    "edit_template": [
        "PUT",
        "/templates/{templateId}",
        [
            "templateId"
        ],
        []
    ],
    "get_bounces": [
        "GET",
        "/bounces",
        [],
        [
            "count",
            "offset",
            "type",
            "inactive",
            "emailFilter"
        ]
    ],
    "get_outbound_message_details": [
        "GET",
        "/messages/outbound/{messageId}/details",
        [
            "messageId"
        ],
        []
    ],
    "get_server": [
        "GET",
        "/server",
        [],
        []
    ],
    "get_template": [
        "GET",
        "/templates/{templateId}",
        [
            "templateId"
        ],
        []
    ],
    "list_templates": [
        "GET",
        "/templates",
        [],
        [
            "count",
            "offset"
        ]
    ],
    "search_outbound_messages": [
        "GET",
        "/messages/outbound",
        [],
        [
            "count",
            "offset",
            "recipient",
            "fromemail",
            "tag",
            "status"
        ]
    ],
    "send_batch_with_templates": [
        "POST",
        "/email/batchWithTemplates",
        [],
        []
    ],
    "send_email": [
        "POST",
        "/email",
        [],
        []
    ],
    "send_email_with_template": [
        "POST",
        "/email/withTemplate",
        [],
        []
    ],
    "validate_template": [
        "POST",
        "/templates/validate",
        [],
        []
    ]
}

class PostmarkDynamicAction(Action):
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

        target_url = f"{POSTMARK_API_BASE}{path}"
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
            err_msg = data.get("Message") or data.get("message") or resp.text
            raise ValueError(f"Postmark API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PostmarkProvider(Provider):
    def __init__(self):
        super().__init__(
            service="postmark",
            display_name="Postmark",
            category="Communication",
            auth_types=["api_key"],
            description="Postmark transactional email, templates, and outbound delivery suite with 12 actions."
        )
        for act in get_provider_actions("postmark"):
            self.register_action(PostmarkDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{POSTMARK_API_BASE}/server"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Postmark credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Postmark validation failed: {resp.status_code} {resp.text}")

        try:
            srv = resp.json()
            srv_id = str(srv.get("ID", "verified"))
            srv_name = srv.get("Name") or srv_id
        except Exception:
            srv_id = "verified"
            srv_name = "Postmark Server"

        return {
            "account_id": srv_id,
            "display_name": f"Postmark ({srv_name})"
        }

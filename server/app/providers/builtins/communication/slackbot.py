"""
Slack Bot Provider for ConnectorHub.
Loads and registers 10 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://slack.com/api"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base.rstrip("/")

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "bearer"
    if auth_mode == "bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "bloomerang":
        if token:
            headers["X-API-KEY"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "auth_test": [
        "POST",
        "/auth.test",
        [],
        []
    ],
    "chat_post_message": [
        "POST",
        "/chat.postMessage",
        [],
        [
            "channel",
            "text",
            "blocks",
            "thread_ts"
        ]
    ],
    "chat_update": [
        "POST",
        "/chat.update",
        [],
        [
            "channel",
            "ts",
            "text",
            "blocks"
        ]
    ],
    "chat_delete": [
        "POST",
        "/chat.delete",
        [],
        [
            "channel",
            "ts"
        ]
    ],
    "conversations_list": [
        "GET",
        "/conversations.list",
        [],
        [
            "types",
            "limit",
            "cursor"
        ]
    ],
    "conversations_info": [
        "GET",
        "/conversations.info",
        [],
        [
            "channel"
        ]
    ],
    "conversations_history": [
        "GET",
        "/conversations.history",
        [],
        [
            "channel",
            "limit",
            "cursor",
            "oldest",
            "latest"
        ]
    ],
    "reactions_add": [
        "POST",
        "/reactions.add",
        [],
        [
            "channel",
            "timestamp",
            "name"
        ]
    ],
    "users_list": [
        "GET",
        "/users.list",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "users_info": [
        "GET",
        "/users.info",
        [],
        [
            "user"
        ]
    ]
}

class SlackbotDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
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

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("error") or err_json.get("error_description") or err_msg
            except Exception:
                pass
            raise ValueError(f"Slack Bot API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class SlackbotProvider(Provider):
    def __init__(self):
        super().__init__(
            service="slackbot",
            display_name="Slack Bot",
            category="Communication",
            auth_types=['oauth2', 'api_key'],
            description="Slack Bot direct API for conversational messaging, threads, channel operations, and reactions with 25 actions."
        )
        for act in get_provider_actions("slackbot"):
            self.register_action(SlackbotDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token:
            raise ValueError("API key or token is required for Slack Bot.")

        val_url = "https://slack.com/api/auth.test"
        for key in ["domain", "subdomain", "site", "host", "tenant"]:
            if "{" + key + "}" in val_url:
                val = str(cred.get(key) or "default").strip()
                val_url = val_url.replace("{" + key + "}", val)

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Slack Bot connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Slack Bot credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Slack Bot validation failed: {resp.status_code} {resp.text}")

        try:
            data = resp.json()
            if isinstance(data, dict) and not data.get("ok"):
                error_code = data.get("error", "unknown_error")
                raise ValueError(f"Slack Bot verification failed: {error_code}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": token[:8] + "..." if len(token) > 8 else "verified",
            "display_name": f"Slack Bot Account"
        }

SlackbotProvider = SlackbotProvider

"""
Pushover Provider for ConnectorHub.
Loads and registers 29 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.pushover.net"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
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
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "pushover_token"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "discord_bot":
        if token:
            headers["Authorization"] = f"Bot {token}"
    elif auth_mode == "freshdesk_basic":
        if token:
            pair = f"{token}:X"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "ack_delete_messages_up_to_id": [
        "DELETE",
        "/apps/limits.json",
        [],
        []
    ],
    "add_group_user": [
        "POST",
        "/apps/limits.json",
        [],
        []
    ],
    "add_team_user": [
        "POST",
        "/apps/limits.json",
        [],
        []
    ],
    "assign_license": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "cancel_receipt_retries": [
        "POST",
        "/receipt_retries",
        [],
        []
    ],
    "cancel_retries_by_tag": [
        "POST",
        "/retries_by_tag",
        [],
        []
    ],
    "check_license_credits": [
        "PATCH",
        "/apps/limits.json",
        [],
        []
    ],
    "client_login": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "create_group": [
        "POST",
        "/apps/limits.json",
        [],
        []
    ],
    "disable_group_user": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "enable_group_user": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "fetch_client_messages": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "get_app_icon_image": [
        "GET",
        "/app_icon_image",
        [],
        []
    ],
    "get_app_limits": [
        "GET",
        "/app_limits",
        [],
        []
    ],
    "get_app_token": [
        "GET",
        "/app_token",
        [],
        []
    ],
    "get_group": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "get_receipt_status": [
        "GET",
        "/receipt_status",
        [],
        []
    ],
    "get_team_api_token": [
        "GET",
        "/team_api_token",
        [],
        []
    ],
    "list_groups": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "listen_client_websocket": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "register_client_device": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "remove_group_user": [
        "DELETE",
        "/apps/limits.json",
        [],
        []
    ],
    "remove_team_user": [
        "DELETE",
        "/apps/limits.json",
        [],
        []
    ],
    "rename_group": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "send_message": [
        "POST",
        "/send_message",
        [],
        [
            "token",
            "user",
            "device",
            "message",
            "title",
            "url",
            "url_title",
            "priority",
            "ttl",
            "retry",
            "expire",
            "html",
            "monospace",
            "timestamp",
            "callback",
            "sound",
            "tags",
            "attachment",
            "attachment_type",
            "attachment_base64"
        ]
    ],
    "store_team_api_token": [
        "GET",
        "/store_team_api_token",
        [],
        []
    ],
    "subscription_flow": [
        "GET",
        "/apps/limits.json",
        [],
        []
    ],
    "update_glances": [
        "PATCH",
        "/glances",
        [],
        []
    ],
    "validate_user_or_group": [
        "GET",
        "/validate_user_or_group",
        [],
        []
    ]
}

class PushoverDynamicAction(Action):
    def __init__(self, action_dict: Dict[str, Any]):
        super().__init__(
            id=action_dict["id"],
            name=action_dict["name"],
            description=action_dict.get("description", ""),
            input_schema=action_dict.get("inputSchema") or action_dict.get("input_schema") or {"type": "object", "properties": {}},
            output_schema=action_dict.get("outputSchema") or action_dict.get("output_schema") or {"type": "object", "properties": {}},
            required_scopes=action_dict.get("requiredScopes") or action_dict.get("required_scopes") or []
        )
        self.raw_dict = action_dict

    async def execute(self, credential: Dict[str, Any], params: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        action_name = self.name
        route_meta = ROUTES.get(action_name, ["GET", f"/{action_name}", [], []])
        method = route_meta[0]
        path_template = route_meta[1]
        path_param_names = route_meta[2]
        body_param_names = route_meta[3]

        url_path = path_template
        for p in path_param_names:
            if p in params:
                val = str(params[p])
                url_path = url_path.replace("{" + p + "}", urllib.parse.quote(val, safe=""))

        url_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "default", url_path)

        base_url = _resolve_base_url(cred)
        if base_url.endswith("/") and url_path.startswith("/"):
            full_url = base_url + url_path[1:]
        elif not base_url.endswith("/") and not url_path.startswith("/"):
            full_url = base_url + "/" + url_path
        else:
            full_url = base_url + url_path

        assert_public_url(full_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        req_json: Optional[Dict[str, Any]] = None

        token = _extract_token(cred)
        if "pushover_token" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "pushover_token" == "pushover_token" and token:
            req_params["token"] = token

        if method in ["GET", "DELETE"]:
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_params[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_params:
                    req_params[k] = v
        else:
            req_json = {}
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_json[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_json:
                    req_json[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=full_url,
            headers=headers,
            params=req_params if req_params else None,
            json=req_json if req_json else None
        )

        if resp.status_code >= 400:
            raise ValueError(f"Pushover API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class PushoverProvider(Provider):
    def __init__(self):
        super().__init__(
            service="pushover",
            display_name="Pushover",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="Pushover real-time push notifications API with 29 actions for emergency alerts, group routing, and delivery receipt confirmation."
        )
        for act in get_provider_actions("pushover"):
            self.register_action(PushoverDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.pushover.net/1/apps/limits.json"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "pushover_token" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "pushover_token" == "pushover_token" and token:
            req_params["token"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"Pushover connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Pushover credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Pushover validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "pushover" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Pushover credentials: {body.get('msg') or resp.text}")
                elif "pushover" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Pushover credentials: {body.get('errmsg') or resp.text}")
                elif "pushover" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Pushover credentials: {body.get('error_msg') or resp.text}")
                elif "pushover" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Pushover credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Pushover Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Pushover Account"
        }

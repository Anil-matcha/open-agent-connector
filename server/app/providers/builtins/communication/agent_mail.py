"""
AgentMail Provider for ConnectorHub.
Loads and registers 102 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.agentmail.to"

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

    auth_mode = "Bearer"
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
    "batch_get_messages": [
        "GET",
        "/batch_get_messages",
        [],
        [
            "inbox_id",
            "message_ids"
        ]
    ],
    "create_api_key": [
        "POST",
        "/api_key",
        [],
        [
            "name",
            "permissions"
        ]
    ],
    "create_domain": [
        "POST",
        "/domain",
        [],
        [
            "domain",
            "feedback_enabled"
        ]
    ],
    "create_draft": [
        "POST",
        "/draft",
        [],
        [
            "inbox_id",
            "labels",
            "reply_to",
            "to",
            "cc",
            "bcc",
            "subject",
            "text",
            "html",
            "attachments",
            "in_reply_to",
            "send_at",
            "client_id"
        ]
    ],
    "create_inbox": [
        "POST",
        "/inbox",
        [],
        [
            "username",
            "domain",
            "display_name",
            "client_id",
            "metadata"
        ]
    ],
    "create_inbox_api_key": [
        "POST",
        "/inbox_api_key",
        [],
        [
            "inbox_id",
            "name",
            "permissions"
        ]
    ],
    "create_inbox_list_entry": [
        "POST",
        "/inbox_list_entry",
        [],
        [
            "inbox_id",
            "direction",
            "type",
            "entry",
            "reason"
        ]
    ],
    "create_list_entry": [
        "POST",
        "/list_entry",
        [],
        [
            "direction",
            "type",
            "entry",
            "reason"
        ]
    ],
    "create_pod": [
        "POST",
        "/pod",
        [],
        [
            "name",
            "client_id"
        ]
    ],
    "create_pod_api_key": [
        "POST",
        "/pod_api_key",
        [],
        [
            "pod_id",
            "name",
            "permissions"
        ]
    ],
    "create_pod_domain": [
        "POST",
        "/pod_domain",
        [],
        [
            "pod_id",
            "domain",
            "feedback_enabled"
        ]
    ],
    "create_pod_inbox": [
        "POST",
        "/pod_inbox",
        [],
        [
            "pod_id",
            "username",
            "domain",
            "display_name",
            "client_id",
            "metadata"
        ]
    ],
    "create_pod_list_entry": [
        "POST",
        "/pod_list_entry",
        [],
        [
            "pod_id",
            "direction",
            "type",
            "entry",
            "reason"
        ]
    ],
    "create_webhook": [
        "POST",
        "/webhook",
        [],
        [
            "url",
            "event_types",
            "pod_ids",
            "inbox_ids",
            "client_id"
        ]
    ],
    "delete_api_key": [
        "DELETE",
        "/api_key",
        [],
        [
            "api_key_id"
        ]
    ],
    "delete_domain": [
        "DELETE",
        "/domain",
        [],
        [
            "domain_id"
        ]
    ],
    "delete_draft": [
        "DELETE",
        "/draft",
        [],
        [
            "inbox_id",
            "draft_id"
        ]
    ],
    "delete_inbox": [
        "DELETE",
        "/inbox",
        [],
        [
            "inbox_id"
        ]
    ],
    "delete_inbox_api_key": [
        "DELETE",
        "/inbox_api_key",
        [],
        [
            "inbox_id",
            "api_key_id"
        ]
    ],
    "delete_inbox_list_entry": [
        "DELETE",
        "/inbox_list_entry",
        [],
        [
            "inbox_id",
            "direction",
            "type",
            "entry"
        ]
    ],
    "delete_inbox_thread": [
        "DELETE",
        "/inbox_thread",
        [],
        [
            "inbox_id",
            "thread_id",
            "permanent"
        ]
    ],
    "delete_list_entry": [
        "DELETE",
        "/list_entry",
        [],
        [
            "direction",
            "type",
            "entry"
        ]
    ],
    "delete_pod": [
        "DELETE",
        "/pod",
        [],
        [
            "pod_id"
        ]
    ],
    "delete_pod_api_key": [
        "DELETE",
        "/pod_api_key",
        [],
        [
            "pod_id",
            "api_key_id"
        ]
    ],
    "delete_pod_domain": [
        "DELETE",
        "/pod_domain",
        [],
        [
            "pod_id",
            "domain_id"
        ]
    ],
    "delete_pod_inbox": [
        "DELETE",
        "/pod_inbox",
        [],
        [
            "pod_id",
            "inbox_id"
        ]
    ],
    "delete_pod_list_entry": [
        "DELETE",
        "/pod_list_entry",
        [],
        [
            "pod_id",
            "direction",
            "type",
            "entry"
        ]
    ],
    "delete_pod_thread": [
        "DELETE",
        "/pod_thread",
        [],
        [
            "pod_id",
            "thread_id",
            "permanent"
        ]
    ],
    "delete_thread": [
        "DELETE",
        "/thread",
        [],
        [
            "thread_id",
            "permanent"
        ]
    ],
    "delete_webhook": [
        "DELETE",
        "/webhook",
        [],
        [
            "webhook_id"
        ]
    ],
    "forward_message": [
        "GET",
        "/forward_message",
        [],
        [
            "inbox_id",
            "message_id",
            "labels",
            "reply_to",
            "to",
            "cc",
            "bcc",
            "subject",
            "text",
            "html",
            "attachments",
            "headers"
        ]
    ],
    "get_domain": [
        "GET",
        "/domain",
        [],
        [
            "domain_id"
        ]
    ],
    "get_domain_zone_file": [
        "GET",
        "/domain_zone_file",
        [],
        [
            "domain_id"
        ]
    ],
    "get_draft": [
        "GET",
        "/draft",
        [],
        [
            "inbox_id",
            "draft_id"
        ]
    ],
    "get_draft_attachment": [
        "GET",
        "/draft_attachment",
        [],
        [
            "inbox_id",
            "draft_id",
            "attachment_id"
        ]
    ],
    "get_global_draft": [
        "GET",
        "/global_draft",
        [],
        [
            "draft_id"
        ]
    ],
    "get_global_draft_attachment": [
        "GET",
        "/global_draft_attachment",
        [],
        [
            "draft_id",
            "attachment_id"
        ]
    ],
    "get_inbox": [
        "GET",
        "/inbox",
        [],
        [
            "inbox_id"
        ]
    ],
    "get_inbox_list_entry": [
        "GET",
        "/inbox_list_entry",
        [],
        [
            "inbox_id",
            "direction",
            "type",
            "entry"
        ]
    ],
    "get_inbox_thread": [
        "GET",
        "/inbox_thread",
        [],
        [
            "inbox_id",
            "thread_id"
        ]
    ],
    "get_inbox_thread_attachment": [
        "GET",
        "/inbox_thread_attachment",
        [],
        [
            "inbox_id",
            "thread_id",
            "attachment_id"
        ]
    ],
    "get_list_entry": [
        "GET",
        "/list_entry",
        [],
        [
            "direction",
            "type",
            "entry"
        ]
    ],
    "get_message": [
        "GET",
        "/message",
        [],
        [
            "inbox_id",
            "message_id"
        ]
    ],
    "get_message_attachment": [
        "GET",
        "/message_attachment",
        [],
        [
            "inbox_id",
            "message_id",
            "attachment_id"
        ]
    ],
    "get_organization": [
        "GET",
        "/organization",
        [],
        []
    ],
    "get_pod": [
        "GET",
        "/pod",
        [],
        [
            "pod_id"
        ]
    ],
    "get_pod_domain": [
        "GET",
        "/pod_domain",
        [],
        [
            "pod_id",
            "domain_id"
        ]
    ],
    "get_pod_domain_zone_file": [
        "GET",
        "/pod_domain_zone_file",
        [],
        [
            "pod_id",
            "domain_id"
        ]
    ],
    "get_pod_draft": [
        "GET",
        "/pod_draft",
        [],
        [
            "pod_id",
            "draft_id"
        ]
    ],
    "get_pod_draft_attachment": [
        "GET",
        "/pod_draft_attachment",
        [],
        [
            "pod_id",
            "draft_id",
            "attachment_id"
        ]
    ],
    "get_pod_inbox": [
        "GET",
        "/pod_inbox",
        [],
        [
            "pod_id",
            "inbox_id"
        ]
    ],
    "get_pod_list_entry": [
        "GET",
        "/pod_list_entry",
        [],
        [
            "pod_id",
            "direction",
            "type",
            "entry"
        ]
    ],
    "get_pod_thread": [
        "GET",
        "/pod_thread",
        [],
        [
            "pod_id",
            "thread_id"
        ]
    ],
    "get_pod_thread_attachment": [
        "GET",
        "/pod_thread_attachment",
        [],
        [
            "pod_id",
            "thread_id",
            "attachment_id"
        ]
    ],
    "get_raw_message": [
        "GET",
        "/raw_message",
        [],
        [
            "inbox_id",
            "message_id"
        ]
    ],
    "get_thread": [
        "GET",
        "/thread",
        [],
        [
            "thread_id"
        ]
    ],
    "get_thread_attachment": [
        "GET",
        "/thread_attachment",
        [],
        [
            "thread_id",
            "attachment_id"
        ]
    ],
    "get_webhook": [
        "GET",
        "/webhook",
        [],
        [
            "webhook_id"
        ]
    ],
    "list_api_keys": [
        "GET",
        "/api_keys",
        [],
        [
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_domains": [
        "GET",
        "/domains",
        [],
        [
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_drafts": [
        "GET",
        "/drafts",
        [],
        [
            "inbox_id",
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending"
        ]
    ],
    "list_global_drafts": [
        "GET",
        "/global_drafts",
        [],
        [
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending"
        ]
    ],
    "list_inbox_api_keys": [
        "GET",
        "/inbox_api_keys",
        [],
        [
            "inbox_id",
            "limit",
            "page_token"
        ]
    ],
    "list_inbox_events": [
        "GET",
        "/inbox_events",
        [],
        [
            "inbox_id",
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_inbox_list_entries": [
        "GET",
        "/inbox_list_entries",
        [],
        [
            "inbox_id",
            "direction",
            "type",
            "limit",
            "page_token"
        ]
    ],
    "list_inbox_threads": [
        "GET",
        "/inbox_threads",
        [],
        [
            "inbox_id",
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending",
            "include_spam",
            "include_blocked",
            "include_unauthenticated",
            "include_trash",
            "senders",
            "recipients",
            "subject"
        ]
    ],
    "list_inboxes": [
        "GET",
        "/inboxes",
        [],
        [
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_list_entries": [
        "GET",
        "/list_entries",
        [],
        [
            "direction",
            "type",
            "limit",
            "page_token"
        ]
    ],
    "list_messages": [
        "GET",
        "/messages",
        [],
        [
            "inbox_id",
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending",
            "include_spam",
            "include_blocked",
            "include_unauthenticated",
            "include_trash",
            "from",
            "to",
            "subject"
        ]
    ],
    "list_pod_api_keys": [
        "GET",
        "/pod_api_keys",
        [],
        [
            "pod_id",
            "limit",
            "page_token"
        ]
    ],
    "list_pod_domains": [
        "GET",
        "/pod_domains",
        [],
        [
            "pod_id",
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_pod_drafts": [
        "GET",
        "/pod_drafts",
        [],
        [
            "pod_id",
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending"
        ]
    ],
    "list_pod_inboxes": [
        "GET",
        "/pod_inboxes",
        [],
        [
            "pod_id",
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_pod_list_entries": [
        "GET",
        "/pod_list_entries",
        [],
        [
            "pod_id",
            "direction",
            "type",
            "limit",
            "page_token"
        ]
    ],
    "list_pod_threads": [
        "GET",
        "/pod_threads",
        [],
        [
            "pod_id",
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending",
            "include_spam",
            "include_blocked",
            "include_unauthenticated",
            "include_trash",
            "senders",
            "recipients",
            "subject"
        ]
    ],
    "list_pods": [
        "GET",
        "/pods",
        [],
        [
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "list_threads": [
        "GET",
        "/threads",
        [],
        [
            "limit",
            "page_token",
            "labels",
            "before",
            "after",
            "ascending",
            "include_spam",
            "include_blocked",
            "include_unauthenticated",
            "include_trash",
            "senders",
            "recipients",
            "subject"
        ]
    ],
    "list_webhooks": [
        "GET",
        "/webhooks",
        [],
        [
            "limit",
            "page_token",
            "ascending"
        ]
    ],
    "query_inbox_metrics": [
        "GET",
        "/query_inbox_metrics",
        [],
        [
            "inbox_id",
            "event_types",
            "start",
            "end",
            "period",
            "limit",
            "descending"
        ]
    ],
    "query_metrics": [
        "GET",
        "/query_metrics",
        [],
        [
            "event_types",
            "start",
            "end",
            "period",
            "limit",
            "descending"
        ]
    ],
    "query_pod_metrics": [
        "GET",
        "/query_pod_metrics",
        [],
        [
            "pod_id",
            "event_types",
            "start",
            "end",
            "period",
            "limit",
            "descending"
        ]
    ],
    "reply_all_message": [
        "GET",
        "/reply_all_message",
        [],
        [
            "inbox_id",
            "message_id",
            "labels",
            "reply_to",
            "text",
            "html",
            "attachments",
            "headers"
        ]
    ],
    "reply_to_message": [
        "GET",
        "/reply_to_message",
        [],
        [
            "inbox_id",
            "message_id",
            "labels",
            "reply_to",
            "to",
            "cc",
            "bcc",
            "reply_all",
            "text",
            "html",
            "attachments",
            "headers"
        ]
    ],
    "search_inbox_threads": [
        "GET",
        "/search_inbox_threads",
        [],
        [
            "inbox_id",
            "q",
            "limit",
            "page_token",
            "before",
            "after"
        ]
    ],
    "search_messages": [
        "GET",
        "/search_messages",
        [],
        [
            "inbox_id",
            "q",
            "limit",
            "page_token",
            "before",
            "after"
        ]
    ],
    "search_pod_threads": [
        "GET",
        "/search_pod_threads",
        [],
        [
            "pod_id",
            "q",
            "limit",
            "page_token",
            "before",
            "after"
        ]
    ],
    "search_threads": [
        "GET",
        "/search_threads",
        [],
        [
            "q",
            "limit",
            "page_token",
            "before",
            "after"
        ]
    ],
    "send_draft": [
        "POST",
        "/send_draft",
        [],
        [
            "inbox_id",
            "draft_id",
            "add_labels",
            "remove_labels"
        ]
    ],
    "send_message": [
        "POST",
        "/send_message",
        [],
        [
            "inbox_id",
            "labels",
            "reply_to",
            "to",
            "cc",
            "bcc",
            "subject",
            "text",
            "html",
            "attachments",
            "headers"
        ]
    ],
    "update_domain": [
        "PATCH",
        "/domain",
        [],
        [
            "domain_id",
            "feedback_enabled"
        ]
    ],
    "update_draft": [
        "PATCH",
        "/draft",
        [],
        [
            "inbox_id",
            "draft_id",
            "reply_to",
            "to",
            "cc",
            "bcc",
            "subject",
            "text",
            "html",
            "send_at"
        ]
    ],
    "update_inbox": [
        "PATCH",
        "/inbox",
        [],
        [
            "inbox_id",
            "display_name",
            "metadata"
        ]
    ],
    "update_inbox_thread": [
        "PATCH",
        "/inbox_thread",
        [],
        [
            "inbox_id",
            "thread_id",
            "add_labels",
            "remove_labels"
        ]
    ],
    "update_message": [
        "PATCH",
        "/message",
        [],
        [
            "inbox_id",
            "message_id",
            "add_labels",
            "remove_labels"
        ]
    ],
    "update_pod_domain": [
        "PATCH",
        "/pod_domain",
        [],
        [
            "pod_id",
            "domain_id",
            "feedback_enabled"
        ]
    ],
    "update_pod_inbox": [
        "PATCH",
        "/pod_inbox",
        [],
        [
            "pod_id",
            "inbox_id",
            "display_name",
            "metadata"
        ]
    ],
    "update_pod_thread": [
        "PATCH",
        "/pod_thread",
        [],
        [
            "pod_id",
            "thread_id",
            "add_labels",
            "remove_labels"
        ]
    ],
    "update_thread": [
        "PATCH",
        "/thread",
        [],
        [
            "thread_id",
            "add_labels",
            "remove_labels"
        ]
    ],
    "update_webhook": [
        "PATCH",
        "/webhook",
        [],
        [
            "webhook_id",
            "add_inbox_ids",
            "remove_inbox_ids",
            "add_pod_ids",
            "remove_pod_ids",
            "event_types"
        ]
    ],
    "verify_domain": [
        "GET",
        "/verify_domain",
        [],
        [
            "domain_id"
        ]
    ],
    "verify_pod_domain": [
        "GET",
        "/verify_pod_domain",
        [],
        [
            "pod_id",
            "domain_id"
        ]
    ],
    "who_am_i": [
        "GET",
        "/who_am_i",
        [],
        []
    ]
}

class AgentMailDynamicAction(Action):
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
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
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
            raise ValueError(f"AgentMail API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class AgentMailProvider(Provider):
    def __init__(self):
        super().__init__(
            service="agent_mail",
            display_name="AgentMail",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="AgentMail programmable AI email inbox, domain, and message dispatch platform with 102 actions."
        )
        for act in get_provider_actions("agent_mail"):
            self.register_action(AgentMailDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.agentmail.to/v1/inboxes"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
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
            raise ValueError(f"AgentMail connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid AgentMail credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"AgentMail validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "agent_mail" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid AgentMail credentials: {body.get('msg') or resp.text}")
                elif "agent_mail" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid AgentMail credentials: {body.get('errmsg') or resp.text}")
                elif "agent_mail" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid AgentMail credentials: {body.get('error_msg') or resp.text}")
                elif "agent_mail" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid AgentMail credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"AgentMail Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"AgentMail Account"
        }

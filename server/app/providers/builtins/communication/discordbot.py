"""
Discord Bot Provider for ConnectorHub.
Loads and registers 55 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://discord.com/api/v10"

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

    auth_mode = "discord_bot"
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
    "add_guild_member": [
        "PATCH",
        "{guildPath}/members/@me",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id",
            "access_token",
            "nick",
            "roles",
            "mute",
            "deaf"
        ]
    ],
    "add_guild_member_role": [
        "PUT",
        "{memberPath}/roles/${requiredPath(input.role_id, ",
        [
            "memberPath"
        ],
        [
            "guild_id",
            "user_id",
            "role_id",
            "audit_log_reason"
        ]
    ],
    "begin_guild_prune": [
        "POST",
        "{guildPath}/prune",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "days",
            "compute_prune_count",
            "include_roles",
            "audit_log_reason"
        ]
    ],
    "bulk_guild_ban": [
        "POST",
        "{guildPath}/bulk-ban",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_ids",
            "delete_message_seconds",
            "audit_log_reason"
        ]
    ],
    "create_guild_ban": [
        "PUT",
        "{guildPath}/bulk-ban",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id",
            "delete_message_seconds",
            "audit_log_reason"
        ]
    ],
    "create_guild_channel": [
        "POST",
        "{guildPath}/channels",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "name",
            "type",
            "topic",
            "bitrate",
            "user_limit",
            "rate_limit_per_user",
            "position",
            "permission_overwrites",
            "parent_id",
            "nsfw",
            "rtc_region",
            "video_quality_mode",
            "default_auto_archive_duration",
            "default_reaction_emoji",
            "available_tags",
            "default_sort_order",
            "default_forum_layout",
            "default_thread_rate_limit_per_user",
            "flags",
            "audit_log_reason"
        ]
    ],
    "create_guild_role": [
        "POST",
        "{guildPath}/roles",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "name",
            "permissions",
            "color",
            "colors",
            "hoist",
            "icon",
            "unicode_emoji",
            "mentionable",
            "audit_log_reason"
        ]
    ],
    "create_message": [
        "POST",
        "/channels/${requiredPath(input.channel_id, ",
        [],
        [
            "channel_id",
            "content",
            "embeds",
            "components",
            "allowed_mentions",
            "message_reference",
            "tts",
            "flags"
        ]
    ],
    "delete_guild_integration": [
        "DELETE",
        "{guildPath}/integrations/${requiredPath(input.integration_id, ",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "integration_id",
            "audit_log_reason"
        ]
    ],
    "delete_guild_role": [
        "DELETE",
        "{guildPath}/prune",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "role_id",
            "audit_log_reason"
        ]
    ],
    "delete_message": [
        "DELETE",
        "/channels/${requiredPath(input.channel_id, ",
        [],
        [
            "channel_id",
            "message_id"
        ]
    ],
    "get_application": [
        "POST",
        "/applications/${requiredPath(input.application_id, ",
        [],
        [
            "application_id"
        ]
    ],
    "get_bot_gateway": [
        "POST",
        "/gateway/bot",
        [],
        []
    ],
    "get_channel": [
        "POST",
        "/channels/${requiredPath(input.channel_id, ",
        [],
        [
            "channel_id"
        ]
    ],
    "get_gateway": [
        "POST",
        "/gateway",
        [],
        []
    ],
    "get_guild": [
        "PATCH",
        "{guildPath}/preview",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "with_counts"
        ]
    ],
    "get_guild_ban": [
        "PUT",
        "{guildPath}/bulk-ban",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id"
        ]
    ],
    "get_guild_member": [
        "PATCH",
        "{guildPath}/members",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id"
        ]
    ],
    "get_guild_onboarding": [
        "PUT",
        "{guildPath}/onboarding",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_preview": [
        "PATCH",
        "{guildPath}/preview",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_prune_count": [
        "POST",
        "{guildPath}/prune",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "days",
            "include_roles"
        ]
    ],
    "get_guild_role": [
        "POST",
        "{guildPath}/roles/member-counts",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "role_id"
        ]
    ],
    "get_guild_role_member_counts": [
        "POST",
        "{guildPath}/roles/member-counts",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_vanity_url": [
        "PATCH",
        "{guildPath}/vanity-url",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_welcome_screen": [
        "PATCH",
        "{guildPath}/welcome-screen",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_widget": [
        "PATCH",
        "{guildPath}/widget.json",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_guild_widget_png": [
        "PATCH",
        "{guildPath}/welcome-screen",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "style"
        ]
    ],
    "get_guild_widget_settings": [
        "PATCH",
        "{guildPath}/widget",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "get_my_application": [
        "POST",
        "/applications/@me",
        [],
        []
    ],
    "get_public_keys": [
        "POST",
        "/oauth2/keys",
        [],
        []
    ],
    "get_user": [
        "POST",
        "/users/${requiredPath(input.user_id, ",
        [],
        [
            "user_id"
        ]
    ],
    "list_active_guild_threads": [
        "PATCH",
        "{guildPath}/threads/active",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_guild_bans": [
        "PUT",
        "{guildPath}/bans",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "limit",
            "before",
            "after"
        ]
    ],
    "list_guild_channels": [
        "POST",
        "{guildPath}/channels",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_guild_integrations": [
        "DELETE",
        "{guildPath}/integrations",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_guild_invites": [
        "DELETE",
        "{guildPath}/invites",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_guild_members": [
        "PATCH",
        "{guildPath}/members",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "limit",
            "after"
        ]
    ],
    "list_guild_roles": [
        "POST",
        "{guildPath}/roles",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_guild_voice_regions": [
        "DELETE",
        "{guildPath}/regions",
        [
            "guildPath"
        ],
        [
            "guild_id"
        ]
    ],
    "list_messages": [
        "POST",
        "/channels/${requiredPath(input.channel_id, ",
        [],
        [
            "channel_id",
            "around",
            "before",
            "after",
            "limit"
        ]
    ],
    "modify_current_member": [
        "PATCH",
        "{guildPath}/members/@me",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "nick",
            "avatar",
            "banner",
            "bio",
            "audit_log_reason"
        ]
    ],
    "modify_guild": [
        "PATCH",
        "{guildPath}/channels",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "name",
            "verification_level",
            "default_message_notifications",
            "explicit_content_filter",
            "afk_channel_id",
            "afk_timeout",
            "icon",
            "splash",
            "discovery_splash",
            "banner",
            "system_channel_id",
            "system_channel_flags",
            "rules_channel_id",
            "public_updates_channel_id",
            "safety_alerts_channel_id",
            "preferred_locale",
            "features",
            "description",
            "premium_progress_bar_enabled",
            "audit_log_reason"
        ]
    ],
    "modify_guild_channel_positions": [
        "PATCH",
        "{guildPath}/channels",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "positions"
        ]
    ],
    "modify_guild_incident_actions": [
        "PUT",
        "{guildPath}/incident-actions",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "invites_disabled_until",
            "dms_disabled_until"
        ]
    ],
    "modify_guild_member": [
        "PATCH",
        "{guildPath}/members/@me",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id",
            "nick",
            "roles",
            "mute",
            "deaf",
            "channel_id",
            "communication_disabled_until",
            "flags",
            "audit_log_reason"
        ]
    ],
    "modify_guild_onboarding": [
        "PUT",
        "{guildPath}/onboarding",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "prompts",
            "default_channel_ids",
            "enabled",
            "mode",
            "audit_log_reason"
        ]
    ],
    "modify_guild_role": [
        "PATCH",
        "{guildPath}/prune",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "role_id",
            "name",
            "permissions",
            "color",
            "colors",
            "hoist",
            "icon",
            "unicode_emoji",
            "mentionable",
            "audit_log_reason"
        ]
    ],
    "modify_guild_role_positions": [
        "PATCH",
        "{guildPath}/roles",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "positions",
            "audit_log_reason"
        ]
    ],
    "modify_guild_welcome_screen": [
        "PATCH",
        "{guildPath}/welcome-screen",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "enabled",
            "welcome_channels",
            "description",
            "audit_log_reason"
        ]
    ],
    "modify_guild_widget": [
        "PATCH",
        "{guildPath}/widget",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "enabled",
            "channel_id",
            "audit_log_reason"
        ]
    ],
    "remove_guild_ban": [
        "DELETE",
        "{guildPath}/bulk-ban",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id",
            "audit_log_reason"
        ]
    ],
    "remove_guild_member": [
        "DELETE",
        "{guildPath}/bans",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "user_id",
            "audit_log_reason"
        ]
    ],
    "remove_guild_member_role": [
        "DELETE",
        "{memberPath}/roles/${requiredPath(input.role_id, ",
        [
            "memberPath"
        ],
        [
            "guild_id",
            "user_id",
            "role_id",
            "audit_log_reason"
        ]
    ],
    "search_guild_members": [
        "PATCH",
        "{guildPath}/members/search",
        [
            "guildPath"
        ],
        [
            "guild_id",
            "query",
            "limit"
        ]
    ],
    "test_auth": [
        "POST",
        "/applications/@me",
        [],
        []
    ]
}

class DiscordBotDynamicAction(Action):
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
        if "discord_bot" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "discord_bot" == "pushover_token" and token:
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
            raise ValueError(f"Discord Bot API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class DiscordBotProvider(Provider):
    def __init__(self):
        super().__init__(
            service="discordbot",
            display_name="Discord Bot",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="Discord Bot API with 55 actions for server guild management, channels, roles, webhooks, and messages."
        )
        for act in get_provider_actions("discordbot"):
            self.register_action(DiscordBotDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://discord.com/api/v10/users/@me"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "discord_bot" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "discord_bot" == "pushover_token" and token:
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
            raise ValueError(f"Discord Bot connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Discord Bot credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Discord Bot validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "discordbot" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Discord Bot credentials: {body.get('msg') or resp.text}")
                elif "discordbot" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Discord Bot credentials: {body.get('errmsg') or resp.text}")
                elif "discordbot" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Discord Bot credentials: {body.get('error_msg') or resp.text}")
                elif "discordbot" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Discord Bot credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Discord Bot Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Discord Bot Account"
        }

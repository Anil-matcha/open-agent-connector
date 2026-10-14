"""
Discord Provider for ConnectorHub.
Loads and registers 19 actions from 'actions_catalog.json'.
Supports both OAuth2 (User Bearer) and Bot Tokens (API Key).
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DISCORD_API_BASE = "https://discord.com/api/v10"

DISCORD_ENDPOINT_MAP = {
    "discord.delete_my_application_role_connection": ("DELETE", "/users/@me/applications/{application_id}/role-connection"),
    "discord.get_current_user_application_entitlements": ("GET", "/users/@me/applications/{application_id}/entitlements"),
    "discord.get_gateway": ("GET", "/gateway"),
    "discord.get_guild_template": ("GET", "/guilds/templates/{code}"),
    "discord.get_guild_widget": ("GET", "/guilds/{guild_id}/widget.json"),
    "discord.get_guild_widget_png": ("GET", "/guilds/{guild_id}/widget.png"),
    "discord.get_invite": ("GET", "/invites/{invite_code}"),
    "discord.get_my_application_role_connection": ("GET", "/users/@me/applications/{application_id}/role-connection"),
    "discord.get_my_guild_member": ("GET", "/users/@me/guilds/{guild_id}/member"),
    "discord.get_my_oauth2_authorization": ("GET", "https://discord.com/api/oauth2/@me"),
    "discord.get_my_user": ("GET", "/users/@me"),
    "discord.get_openid_connect_userinfo": ("GET", "https://discord.com/api/oauth2/userinfo"),
    "discord.get_public_keys": ("GET", "https://discord.com/api/oauth2/keys"),
    "discord.get_user": ("GET", "/users/{user_id}"),
    "discord.list_my_connections": ("GET", "/users/@me/connections"),
    "discord.list_my_guilds": ("GET", "/users/@me/guilds"),
    "discord.list_sticker_packs": ("GET", "/sticker-packs"),
    "discord.resolve_invite": ("GET", "/invites/{code}"),
    "discord.update_my_application_role_connection": ("PUT", "/users/@me/applications/{application_id}/role-connection"),
}

def _discord_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("botToken") or cred.get("token") or ""
    token_str = str(token).strip()
    if not token_str:
        raise ValueError("Discord token or credentials required. Please connect your Discord account first.")

    # Determine Bot or Bearer
    if token_str.startswith("Bot ") or cred.get("tokenType") == "Bot" or cred.get("isBot"):
        auth_header = token_str if token_str.startswith("Bot ") else f"Bot {token_str}"
    elif token_str.startswith("Bearer "):
        auth_header = token_str
    else:
        # Default to Bearer for OAuth2 tokens; if it has a period separated bot structure or explicitly apiKey, handle appropriately
        auth_header = f"Bearer {token_str}"

    return {
        "Authorization": auth_header,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class DiscordDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        mapped_method, mapped_endpoint = DISCORD_ENDPOINT_MAP.get(action_meta["id"], ("GET", "/users/@me"))
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        headers = _discord_headers(credential)

        path = self.endpoint_template
        # Substitute path parameters
        for var in ["application_id", "guild_id", "invite_code", "code", "user_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{DISCORD_API_BASE}/{path.lstrip('/')}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method in ["GET", "DELETE"] else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                err_msg = res_data.get("message") or str(res_data)
            raise ValueError(f"Discord API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class DiscordProvider(Provider):
    def __init__(self):
        super().__init__(
            service="discord",
            display_name="Discord",
            category="Communication",
            auth_types=["oauth2", "api_key"],
            description="Voice, video, and text communication platform for communities and developers.",
            homepage_url="https://discord.com",
            base_url=DISCORD_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Discord OAuth 2.0",
                    "description": "Connect your Discord account via OAuth2 authorization flow.",
                    "docs_url": "https://discord.com/developers/docs/topics/oauth2",
                    "docs_label": "Discord Developer Portal",
                    "setup_guide": {
                        "title": "Discord OAuth2 Setup Guide",
                        "docs_url": "https://discord.com/developers/applications",
                        "docs_label": "Discord Developer Portal",
                        "instructions": [
                            "1. Go to the Discord Developer Portal and select your application.",
                            "2. Navigate to OAuth2 > General.",
                            "3. Add your Redirect URI under Redirects.",
                            "4. Copy your Client ID and Client Secret.",
                            "5. Configure the required scopes: identify, email, guilds, connections."
                        ],
                        "scopes": ["identify", "email", "guilds", "guilds.members.read", "connections"]
                    }
                },
                {
                    "type": "api_key",
                    "label": "Discord Bot Token",
                    "placeholder": "MTA4...",
                    "description": "Discord Bot Token from Discord Developer Portal > Applications > Bot > Reset Token.",
                    "docs_url": "https://discord.com/developers/docs/topics/oauth2#bot-vs-user-accounts",
                    "docs_label": "Discord Bot Token Documentation",
                    "setup_guide": {
                        "title": "Discord Bot Token Guide",
                        "docs_url": "https://discord.com/developers/applications",
                        "docs_label": "Discord Developer Applications",
                        "instructions": [
                            "1. Visit the Discord Developer Portal (https://discord.com/developers/applications).",
                            "2. Select or create an Application and navigate to 'Bot' in the left menu.",
                            "3. Click 'Reset Token' and copy your bot token.",
                            "4. Paste your token here (it will automatically authenticate as a Bot)."
                        ],
                        "scopes": ["bot"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bot Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "Bot token from Discord Developer Portal",
                            "description": "Discord Bot Token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("discord"):
            self.register_action(DiscordDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Discord credentials by querying GET /users/@me."""
        headers = _discord_headers(credential)
        url = f"{DISCORD_API_BASE}/users/@me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Discord API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Discord credentials. Discord returned Unauthorized (401/403).")
        elif resp.status_code != 200:
            raise ValueError(f"Discord credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user_id = str(body.get("id", "discord_user"))
        username = body.get("global_name") or body.get("username") or f"Discord User ({user_id})"

        return {
            "valid": True,
            "accountId": user_id,
            "displayName": username,
            "metadata": {
                "validationEndpoint": "/users/@me",
                "username": body.get("username"),
                "discriminator": body.get("discriminator"),
                "email": body.get("email"),
                "avatar": body.get("avatar")
            }
        }

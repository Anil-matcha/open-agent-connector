"""
Slack Provider for ConnectorHub.
Loads and registers actions from 'actions_catalog.json'.
Aligned with the official Slack Web API specifications.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SLACK_API_BASE = "https://slack.com/api"

def _slack_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("Slack Bot Token (xoxb-...) or User Token required. Please connect your Slack account first.")
    return str(token).strip()

def _build_slack_params(action_id: str, endpoint: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Translate catalog parameters to Slack Web API parameters."""
    params = {}
    for k, v in (input_data or {}).items():
        if v is None:
            continue
        if k == "channelId":
            params["channel"] = v
        elif k == "messageTs":
            if endpoint.startswith("reactions."):
                params["timestamp"] = str(v)
            else:
                params["ts"] = str(v)
        elif k == "threadTs":
            params["thread_ts"] = str(v)
        elif k == "userId":
            params["user"] = str(v)
        elif k == "fileId":
            params["file"] = str(v)
        elif k == "postAt":
            params["post_at"] = v
        elif k == "unfurlLinks":
            params["unfurl_links"] = v
        elif k == "unfurlMedia":
            params["unfurl_media"] = v
        elif k == "replyBroadcast":
            params["reply_broadcast"] = v
        elif k == "includeLocale":
            params["include_locale"] = v
        elif k == "contextChannelId":
            params["context_channel_id"] = v
        elif k == "termClauses":
            params["term_clauses"] = v
        elif k == "channelTypes":
            params["channel_types"] = v
        elif k == "includeContextMessages":
            params["include_context_messages"] = v
        elif k == "includeBots":
            params["include_bots"] = v
        elif k == "includeMessageBlocks":
            params["include_message_blocks"] = v
        elif k == "includeArchivedChannels":
            params["include_archived_channels"] = v
        elif k == "disableSemanticSearch":
            params["disable_semantic_search"] = v
        elif k == "sortDir":
            params["sort_dir"] = v
        elif k == "teamId":
            params["team_id"] = v
        elif k == "name" and endpoint.startswith("reactions."):
            # Emoji name without surrounding colons
            params["name"] = str(v).strip(":")
        else:
            params[k] = v

    if action_id == "slack.reply_message" and "threadTs" in input_data:
        params["thread_ts"] = str(input_data["threadTs"])

    return params

class SlackDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.endpoint = action_meta.get("endpoint", "chat.postMessage")
        self.method = action_meta.get("method", "POST").upper()

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _slack_headers(token)
        url = f"{SLACK_API_BASE}/{self.endpoint}"
        assert_public_url(url)

        params = _build_slack_params(self.id, self.endpoint, input_data)

        if self.method == "GET":
            # For GET requests, serialize parameters into query string
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers,
                params={k: str(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in params.items()}
            )
        else:
            # For POST requests, send JSON body
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=url,
                headers=headers,
                json_body=params
            )

        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            error_code = data.get("error", "unknown_error")
            detail = data.get("response_metadata", {}).get("messages", [error_code])
            raise ValueError(f"Slack API error ({self.endpoint}): {error_code} - {detail}")

        return data

class SlackProvider(Provider):
    def __init__(self):
        super().__init__(
            service="slack",
            display_name="Slack",
            category="Communication",
            auth_types=["api_key", "oauth2"],
            description="Slack Web API for messaging, channels, team directory, and reactions.",
            homepage_url="https://slack.com",
            base_url="https://slack.com/api",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Bot User OAuth Token",
                    "placeholder": "xoxb-...",
                    "description": "Create a Slack App at api.slack.com/apps, install to your workspace, and copy the Bot User OAuth Token.",
                    "docs_url": "https://api.slack.com/apps",
                    "docs_label": "Create app on Slack API",
                    "setup_guide": {
                        "title": "Slack Token Setup Guide",
                        "docs_url": "https://api.slack.com/apps",
                        "docs_label": "Create app on Slack API",
                        "instructions": [
                            "1. Create an App at api.slack.com/apps (From scratch) and select your workspace.",
                            "2. Under OAuth & Permissions > Bot Token Scopes, add the permissions you need.",
                            "3. Click Install to Workspace at the top, then copy the Bot User OAuth Token (starts with xoxb-...)."
                        ],
                        "scopes": [
                            "chat:write",
                            "channels:read",
                            "channels:history",
                            "groups:read",
                            "users:read",
                            "reactions:write"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bot User OAuth Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "xoxb-...",
                            "description": "Bot token with chat:write, channels:read, and users:read scopes."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Slack OAuth 2.0 User Token",
                    "placeholder": "xoxp-...",
                    "description": "Authorize via Slack OAuth 2.0 application or enter a user access token.",
                    "docs_url": "https://api.slack.com/authentication/oauth-v2",
                    "docs_label": "Slack OAuth Docs",
                    "setup_guide": {
                        "title": "Slack OAuth Setup Guide",
                        "docs_url": "https://api.slack.com/authentication/oauth-v2",
                        "docs_label": "Slack OAuth Docs",
                        "instructions": [
                            "Authorize directly via Slack OAuth 2.0 PKCE flow, or provide a user access token (xoxp-...)."
                        ],
                        "scopes": ["chat:write", "channels:read", "users:read"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "xoxp-...",
                            "description": "OAuth access token issued by Slack."
                        }
                    ]
                }
            ]
        )

        # Load all actions from the centralized actions catalog
        for meta in get_provider_actions("slack"):
            self.register_action(SlackDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = credential.get("apiKey") or credential.get("accessToken")
        if not token or not str(token).strip():
            raise ValueError("Slack Bot Token or User Token is required.")

        token = str(token).strip()
        headers = _slack_headers(token)
        url = "https://slack.com/api/auth.test"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach Slack API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Slack token. Slack API returned 401 Unauthorized.")

        data = resp.json()
        if not data.get("ok"):
            error_code = data.get("error", "unknown_error")
            raise ValueError(f"Slack verification failed: {error_code}")

        # Extract scopes from x-oauth-scopes header if present
        scopes_header = resp.headers.get("x-oauth-scopes", "")
        scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]

        user_name = data.get("user") or "Bot"
        team_name = data.get("team") or "Workspace"
        user_id = data.get("user_id") or data.get("bot_id") or "slack_user"

        return {
            "account_id": user_id,
            "display_name": f"{user_name} @ {team_name}",
            "granted_scopes": scopes
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        query_params: Dict[str, Any],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Proxy arbitrary Slack API calls with stored credentials and SSRF protection."""
        token = _extract_token(credential)
        clean_endpoint = endpoint.lstrip("/")
        url = f"{SLACK_API_BASE}/{clean_endpoint}"
        assert_public_url(url)

        headers = _slack_headers(token)
        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=url,
            headers=headers,
            params=query_params if query_params else None,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": data
        }

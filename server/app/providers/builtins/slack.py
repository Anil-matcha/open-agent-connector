from typing import Dict, Any, Optional
import httpx
from app.providers.base import Provider, Action
from app.core.ssrf import assert_public_url

class SlackPostMessageAction(Action):
    def __init__(self):
        super().__init__(
            id="slack.post_message",
            name="Post Message",
            description="Send a message to a Slack channel or user.",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID or channel name (e.g. #general or C12345)"},
                    "text": {"type": "string", "description": "Text message content to send"}
                },
                "required": ["channel", "text"]
            },
            required_scopes=["chat:write"]
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
        if not token:
            raise ValueError("Slack Bot User OAuth Token required (xoxb-...)")
        url = "https://slack.com/api/chat.postMessage"
        assert_public_url(url)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "channel": input_data["channel"],
            "text": input_data["text"]
        }
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error', 'unknown_error')}")
        return {
            "ok": True,
            "channel": data.get("channel"),
            "ts": data.get("ts"),
            "message": data.get("message")
        }

class SlackListChannelsAction(Action):
    def __init__(self):
        super().__init__(
            id="slack.list_channels",
            name="List Channels",
            description="List public or private channels in the Slack workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "types": {"type": "string", "default": "public_channel,private_channel"},
                    "limit": {"type": "integer", "default": 20}
                }
            },
            required_scopes=["channels:read"]
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
        if not token:
            raise ValueError("Slack Bot User OAuth Token required")
        types = input_data.get("types", "public_channel")
        limit = int(input_data.get("limit", 20))
        url = f"https://slack.com/api/conversations.list?types={types}&limit={limit}"
        assert_public_url(url)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        channels = [
            {"id": c.get("id"), "name": c.get("name"), "is_private": c.get("is_private"), "num_members": c.get("num_members")}
            for c in data.get("channels", [])
        ]
        return {"channels": channels, "count": len(channels)}

class SlackProvider(Provider):
    def __init__(self):
        super().__init__(
            service="slack",
            display_name="Slack",
            category="Communication",
            auth_types=["api_key", "oauth2"],
            description="Slack Web API for messaging, channels, and team notifications.",
            homepage_url="https://slack.com",
            base_url="https://slack.com/api"
        )
        self.register_action(SlackPostMessageAction())
        self.register_action(SlackListChannelsAction())

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = credential.get("apiKey") or credential.get("accessToken")
        if not token:
            raise ValueError("Slack token required")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post("https://slack.com/api/auth.test", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise ValueError(f"Slack verification failed: {data.get('error')}")
        return {
            "account_id": data.get("user_id") or data.get("team_id"),
            "display_name": f"{data.get('user')} @ {data.get('team')}",
            "granted_scopes": []
        }

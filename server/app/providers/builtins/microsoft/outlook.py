"""
Outlook Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Microsoft Graph API v1.0 specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

def _graph_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Microsoft OAuth Access Token or Bearer Token required. Please connect your Outlook account first.")
    return str(token).strip()

class OutlookDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/me/messages")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _graph_headers(token)
        inputs = dict(input_data or {})

        # Path variable substitution
        path = self.endpoint_template
        for var in ["messageId", "mailFolderId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{GRAPH_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

        if self.method in ["POST", "PUT", "PATCH"]:
            # Special payload handling for Outlook send_email
            if self.id == "outlook.send_email" and "message" not in inputs:
                subject = inputs.pop("subject", "")
                content = inputs.pop("body", inputs.pop("content", ""))
                to_recipients = inputs.pop("to", inputs.pop("toRecipients", []))
                if isinstance(to_recipients, str):
                    to_recipients = [to_recipients]
                recipients_list = [
                    {"emailAddress": {"address": r}} if isinstance(r, str) else r
                    for r in to_recipients
                ]
                body = {
                    "message": {
                        "subject": subject,
                        "body": {
                            "contentType": inputs.pop("contentType", "Text"),
                            "content": content
                        },
                        "toRecipients": recipients_list
                    },
                    "saveToSentItems": inputs.pop("saveToSentItems", True)
                }
            elif self.id == "outlook.create_draft" and "subject" in inputs and "body" not in inputs.get("body", {}):
                subject = inputs.pop("subject", "")
                content = inputs.pop("body", inputs.pop("content", ""))
                to_recipients = inputs.pop("to", inputs.pop("toRecipients", []))
                if isinstance(to_recipients, str):
                    to_recipients = [to_recipients]
                recipients_list = [
                    {"emailAddress": {"address": r}} if isinstance(r, str) else r
                    for r in to_recipients
                ]
                body = {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": str(content)
                    },
                    "toRecipients": recipients_list
                }
            elif self.id == "outlook.reply_email" and "comment" in inputs:
                body = {"comment": inputs.pop("comment", "")}
            else:
                body = inputs
        else:
            for k, v in inputs.items():
                if v is not None:
                    if isinstance(v, bool):
                        params[k] = "true" if v else "false"
                    elif isinstance(v, (list, tuple)):
                        params[k] = ",".join(str(item) for item in v)
                    else:
                        params[k] = str(v)

        resp = await execute_guarded_request(
            client=client,
            method=self.method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=body if body is not None and self.method in ["POST", "PUT", "PATCH"] else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"Microsoft Outlook API error ({resp.status_code}): {msg}")

        if resp.status_code == 204 or not resp.content:
            return {"success": True, "message": "Operation completed successfully"}

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

class OutlookProvider(Provider):
    def __init__(self):
        super().__init__(
            service="outlook",
            display_name="Outlook",
            category="Communication",
            auth_types=["oauth2", "api_key"],
            description="Microsoft Outlook email service for sending, receiving, organizing messages, drafts, and mailboxes.",
            homepage_url="https://outlook.live.com",
            base_url=GRAPH_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Microsoft OAuth 2.0 Access Token",
                    "placeholder": "EwB...",
                    "description": "Connect seamlessly via Microsoft Graph OAuth 2.0 flow.",
                    "docs_url": "https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview",
                    "docs_label": "Microsoft Graph Mail API Docs",
                    "setup_guide": {
                        "title": "Microsoft Outlook OAuth Setup Guide",
                        "docs_url": "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
                        "docs_label": "Azure App Registrations",
                        "instructions": [
                            "1. Register an application in Azure Portal (portal.azure.com) under Microsoft Entra ID > App registrations.",
                            "2. Add Delegated API permissions for Microsoft Graph: Mail.Read, Mail.ReadWrite, Mail.Send, User.Read.",
                            "3. Generate an access token via OAuth 2.0 Authorization Code flow and paste below."
                        ],
                        "scopes": [
                            "User.Read",
                            "Mail.Read",
                            "Mail.ReadWrite",
                            "Mail.Send"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "EwB...",
                            "description": "Microsoft Graph Access Token with Mail permissions."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Microsoft Graph Bearer Token",
                    "placeholder": "EwB... or Bearer token",
                    "description": "Direct Microsoft Graph Bearer Access Token.",
                    "docs_url": "https://learn.microsoft.com/en-us/graph/auth-v2-user",
                    "docs_label": "Microsoft Graph Authentication Guide",
                    "setup_guide": {
                        "title": "Microsoft Graph Bearer Token Guide",
                        "docs_url": "https://developer.microsoft.com/en-us/graph/graph-explorer",
                        "docs_label": "Graph Explorer",
                        "instructions": [
                            "1. Open Microsoft Graph Explorer (developer.microsoft.com/graph/graph-explorer).",
                            "2. Sign in with your Microsoft account and consent to Mail permissions.",
                            "3. Copy your Access Token from Graph Explorer and paste below."
                        ],
                        "scopes": [
                            "User.Read",
                            "Mail.Read",
                            "Mail.Send"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bearer Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "EwB...",
                            "description": "Microsoft Graph Bearer token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("outlook"):
            self.register_action(OutlookDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Microsoft Graph credentials against https://graph.microsoft.com/v1.0/me."""
        token = _extract_token(credential)
        headers = _graph_headers(token)
        url = f"{GRAPH_API_BASE}/me?$select=id,displayName,mail,userPrincipalName"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Microsoft Graph API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Microsoft credentials. Microsoft Graph returned 401 Unauthorized.")
        elif resp.status_code == 403:
            raise ValueError("Microsoft Outlook permission denied (403 Forbidden). Verify Mail.Read and User.Read scopes.")
        elif resp.status_code != 200:
            raise ValueError(f"Microsoft Outlook credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        account_id = data.get("id") or data.get("userPrincipalName") or "me"
        email = data.get("mail") or data.get("userPrincipalName") or account_id
        name = data.get("displayName") or email

        return {
            "account_id": account_id,
            "display_name": f"Outlook ({name})",
            "granted_scopes": [
                "User.Read",
                "Mail.Read",
                "Mail.ReadWrite",
                "Mail.Send"
            ],
            "avatar_url": None
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """SSRF-guarded proxy forwarder for Microsoft Outlook via Microsoft Graph."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{GRAPH_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_graph_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }

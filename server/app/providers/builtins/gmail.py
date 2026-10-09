"""
Gmail Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with the official Google Gmail REST API v1 specifications and open-connector definitions.
"""
import base64
import urllib.parse
from email.message import EmailMessage
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"

def _gmail_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Gmail OAuth Access Token or Bearer Token required. Please connect your Gmail account first.")
    return str(token).strip()

def _build_mime_raw(input_data: Dict[str, Any]) -> str:
    """Build RFC 2822 base64url-encoded message for Gmail API."""
    if input_data.get("raw"):
        raw_val = str(input_data["raw"]).strip()
        # Ensure it's URL-safe base64 without padding errors
        return raw_val

    msg = EmailMessage()
    to_val = input_data.get("to")
    if isinstance(to_val, list):
        msg["To"] = ", ".join(str(t) for t in to_val)
    elif to_val:
        msg["To"] = str(to_val)

    if input_data.get("subject"):
        msg["Subject"] = str(input_data["subject"])

    if input_data.get("from"):
        msg["From"] = str(input_data["from"])

    if input_data.get("cc"):
        cc_val = input_data["cc"]
        msg["Cc"] = ", ".join(cc_val) if isinstance(cc_val, list) else str(cc_val)

    if input_data.get("bcc"):
        bcc_val = input_data["bcc"]
        msg["Bcc"] = ", ".join(bcc_val) if isinstance(bcc_val, list) else str(bcc_val)

    if input_data.get("inReplyTo"):
        msg["In-Reply-To"] = str(input_data["inReplyTo"])

    if input_data.get("references"):
        msg["References"] = str(input_data["references"])

    body_text = input_data.get("body") or input_data.get("bodyText") or input_data.get("text") or ""
    msg.set_content(body_text)

    # If HTML body is provided
    if input_data.get("bodyHtml") or input_data.get("html"):
        html_content = input_data.get("bodyHtml") or input_data.get("html")
        msg.add_alternative(html_content, subtype="html")

    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii")

class GmailDynamicAction(Action):
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
        self.endpoint_template = action_meta.get("endpoint_template", "/users/{userId}/messages")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _gmail_headers(token)
        inputs = dict(input_data or {})

        user_id = str(inputs.pop("userId", "me") or "me")

        # 1. Path variables substitution
        path = self.endpoint_template.replace("{userId}", urllib.parse.quote(user_id, safe=""))
        for var in ["messageId", "threadId", "draftId", "labelId", "filterId", "attachmentId"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None:
                    snake = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                    val = inputs.pop(snake, None)
                if val is None and var in ["messageId", "id"]:
                    val = inputs.pop("id", None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{GMAIL_API_BASE}{path}"
        assert_public_url(url)

        # 2. Email payload construction
        body = None
        params = {}

        if self.id in ["gmail.send_email", "gmail.reply_email", "gmail.reply_to_thread"]:
            raw_msg = _build_mime_raw(inputs)
            payload: Dict[str, Any] = {"raw": raw_msg}
            thread_id = inputs.get("threadId") or inputs.get("thread_id")
            if thread_id:
                payload["threadId"] = str(thread_id)
            body = payload

        elif self.id in ["gmail.create_draft", "gmail.create_email_draft"]:
            raw_msg = _build_mime_raw(inputs)
            body = {"message": {"raw": raw_msg}}
            if inputs.get("threadId"):
                body["message"]["threadId"] = str(inputs["threadId"])

        elif self.id == "gmail.update_draft":
            raw_msg = _build_mime_raw(inputs)
            body = {"message": {"raw": raw_msg}}

        elif self.id == "gmail.send_draft":
            draft_id = inputs.get("draftId") or inputs.get("id")
            body = {"id": draft_id} if draft_id else {}

        elif self.method in ["POST", "PUT", "PATCH"]:
            body = inputs

        else:
            # GET / DELETE query parameters
            for k, v in inputs.items():
                if v is not None and v != "":
                    if isinstance(v, list):
                        params[k] = ",".join(str(item) for item in v)
                    else:
                        params[k] = v

        # 3. Guarded HTTP Execution
        if self.method == "GET":
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers,
                params=params or None
            )
        elif self.method == "DELETE":
            resp = await execute_guarded_request(
                client=client,
                method="DELETE",
                url=url,
                headers=headers
            )
            if resp.status_code in [200, 204]:
                return {"success": True, "message": f"Resource deleted successfully ({self.id})."}
        else:
            resp = await execute_guarded_request(
                client=client,
                method=self.method,
                url=url,
                headers=headers,
                json_body=body
            )

        if resp.status_code == 204:
            return {"success": True, "message": "Operation completed successfully."}
        if resp.status_code == 401:
            raise ValueError("Gmail authentication failed: invalid or expired access token (401 Unauthorized).")
        if resp.status_code == 403:
            raise ValueError(f"Gmail permission denied (403 Forbidden). Verify required scopes: {resp.text[:300]}")
        if resp.status_code == 404:
            raise ValueError(f"Gmail resource not found at '{url}' (404 Not Found).")
        if resp.status_code >= 400:
            try:
                err_data = resp.json()
                msg = err_data.get("error", {}).get("message", resp.text[:300])
            except Exception:
                msg = resp.text[:300]
            raise ValueError(f"Gmail API error ({resp.status_code}): {msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class GmailProvider(Provider):
    def __init__(self):
        super().__init__(
            service="gmail",
            display_name="Gmail",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="Google Gmail REST API for sending, reading, searching, drafting, and organizing emails.",
            homepage_url="https://mail.google.com",
            base_url=GMAIL_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Google OAuth 2.0 Access Token",
                    "placeholder": "ya29.a0...",
                    "description": "Authenticate via Google OAuth 2.0 application access token with Gmail scopes.",
                    "docs_url": "https://developers.google.com/gmail/api/guides",
                    "docs_label": "Gmail API Documentation",
                    "setup_guide": {
                        "title": "Gmail Access Token Setup Guide",
                        "docs_url": "https://developers.google.com/oauthplayground",
                        "docs_label": "Google OAuth Playground",
                        "instructions": [
                            "1. Open Google OAuth Playground (developers.google.com/oauthplayground).",
                            "2. In the API list, select 'Gmail API v1' and choose the scopes you need (e.g. gmail.modify, gmail.send).",
                            "3. Click 'Authorize APIs' and log in with your Google account.",
                            "4. Click 'Exchange authorization code for tokens', then copy the Access token (starts with ya29...)."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/gmail.readonly",
                            "https://www.googleapis.com/auth/gmail.send",
                            "https://www.googleapis.com/auth/gmail.modify",
                            "https://www.googleapis.com/auth/gmail.compose",
                            "https://www.googleapis.com/auth/gmail.labels"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth 2.0 access token issued with Gmail scopes."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Google Bearer Token / API Token",
                    "placeholder": "ya29.a0... or Service Account Token",
                    "description": "Authenticate via OAuth Bearer token or service account credentials.",
                    "docs_url": "https://developers.google.com/gmail/api/quickstart/python",
                    "docs_label": "Gmail Quickstart Guide",
                    "setup_guide": {
                        "title": "Gmail Bearer Token Setup Guide",
                        "docs_url": "https://developers.google.com/gmail/api/quickstart/python",
                        "docs_label": "Gmail Quickstart Guide",
                        "instructions": [
                            "1. Obtain a valid Google OAuth Bearer access token or Service Account Token.",
                            "2. Ensure the token has the necessary Gmail permissions (gmail.send, gmail.readonly).",
                            "3. Enter the token below to connect."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/gmail.readonly",
                            "https://www.googleapis.com/auth/gmail.send",
                            "https://www.googleapis.com/auth/gmail.modify"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bearer Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth Bearer token."
                        }
                    ]
                }
            ]
        )

        # Load all actions cleanly from the centralized actions catalog
        for meta in get_provider_actions("gmail"):
            self.register_action(GmailDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate credentials against live Gmail API profile endpoint."""
        token = _extract_token(credential)
        headers = _gmail_headers(token)
        url = f"{GMAIL_API_BASE}/users/me/profile"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach Gmail API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Gmail credentials. Google API returned 401 Unauthorized.")
        elif resp.status_code == 403:
            raise ValueError("Gmail permission denied (403 Forbidden). Verify Gmail API is enabled and scopes are granted.")
        elif resp.status_code != 200:
            raise ValueError(f"Gmail credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        email_addr = data.get("emailAddress") or "me"

        return {
            "account_id": email_addr,
            "display_name": f"Gmail ({email_addr})",
            "granted_scopes": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify"
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
        """SSRF-guarded proxy forwarder for Gmail API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{GMAIL_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_gmail_headers(token))

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

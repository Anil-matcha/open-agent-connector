"""
Mailchimp Provider for ConnectorHub.
Loads and registers 11 actions from 'actions_catalog.json'.
Email marketing and audience management: Lists, Audiences, Members, Tags, and Merge Fields via Mailchimp Marketing API v3.0.
"""
import base64
import hashlib
import re
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

_MAILCHIMP_DC_RE = re.compile(r"^[a-z0-9-]{1,32}$")


def _resolve_mailchimp_base(credential: Optional[Dict[str, Any]]) -> str:
    """Return the Mailchimp API base URL, never pointing credentials at a non-Mailchimp host."""
    cred = credential or {}
    key = str(cred.get("apiKey") or cred.get("accessToken") or "")
    if cred.get("apiEndpoint"):
        endpoint = str(cred["apiEndpoint"]).strip().rstrip("/")
        parsed = urllib.parse.urlparse(endpoint)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or not host.endswith(".api.mailchimp.com")
        ):
            raise ValueError("Invalid Mailchimp API endpoint: must be https://<dc>.api.mailchimp.com")
        return endpoint if endpoint.endswith("/3.0") else f"{endpoint}/3.0"
    server = str(cred.get("serverPrefix") or cred.get("dc") or "").strip().lower()
    if not server and "-" in key:
        server = key.split("-")[-1].strip().lower()
    server = server or "us1"
    if not _MAILCHIMP_DC_RE.match(server):
        raise ValueError("Invalid Mailchimp datacenter prefix")
    return f"https://{server}.api.mailchimp.com/3.0"

def _mailchimp_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    key = str(cred.get("apiKey") or cred.get("accessToken") or "").strip()
    if not key:
        raise ValueError("Mailchimp API key or OAuth access token required.")

    # OAuth access tokens use OAuth / Bearer header
    if "-" not in key and (cred.get("authType") == "oauth2" or cred.get("accessToken")):
        return {
            "Authorization": f"OAuth {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }

    # API keys (format: {hash}-{dc}) use HTTP Basic Auth
    auth_str = base64.b64encode(f"anystring:{key}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {auth_str}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class MailchimpDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Marketing"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.endpoint_template = self._map_endpoint(action_meta["id"])
        self.method = self._map_method(action_meta["id"])

    def _map_endpoint(self, action_id: str) -> str:
        endpoints = {
            "mailchimp.archive_member": "/lists/{list_id}/members/{subscriber_hash}",
            "mailchimp.delete_member_permanently": "/lists/{list_id}/members/{subscriber_hash}/actions/delete-permanent",
            "mailchimp.get_list": "/lists/{list_id}",
            "mailchimp.get_member": "/lists/{list_id}/members/{subscriber_hash}",
            "mailchimp.list_lists": "/lists",
            "mailchimp.list_member_tags": "/lists/{list_id}/members/{subscriber_hash}/tags",
            "mailchimp.list_members": "/lists/{list_id}/members",
            "mailchimp.list_merge_fields": "/lists/{list_id}/merge-fields",
            "mailchimp.update_member": "/lists/{list_id}/members/{subscriber_hash}",
            "mailchimp.update_member_tags": "/lists/{list_id}/members/{subscriber_hash}/tags",
            "mailchimp.upsert_member": "/lists/{list_id}/members/{subscriber_hash}",
        }
        return endpoints.get(action_id, "/lists")

    def _map_method(self, action_id: str) -> str:
        methods = {
            "mailchimp.archive_member": "DELETE",
            "mailchimp.delete_member_permanently": "POST",
            "mailchimp.get_list": "GET",
            "mailchimp.get_member": "GET",
            "mailchimp.list_lists": "GET",
            "mailchimp.list_member_tags": "GET",
            "mailchimp.list_members": "GET",
            "mailchimp.list_merge_fields": "GET",
            "mailchimp.update_member": "PATCH",
            "mailchimp.update_member_tags": "POST",
            "mailchimp.upsert_member": "PUT",
        }
        return methods.get(action_id, "GET")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        base_url = _resolve_mailchimp_base(credential)
        inputs = dict(input_data or {})
        headers = _mailchimp_headers(credential)

        # Compute subscriber_hash from email if email is provided and subscriber_hash is not
        if "email" in inputs and "subscriber_hash" not in inputs:
            email_val = str(inputs.get("email")).lower().strip()
            inputs["subscriber_hash"] = hashlib.md5(email_val.encode("utf-8")).hexdigest()

        path = self.endpoint_template
        for var in ["list_id", "subscriber_hash", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method == "GET" else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            err_msg = str(data)
            if isinstance(data, dict):
                err_msg = data.get("detail") or data.get("title") or str(data)
            raise ValueError(f"Mailchimp API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class MailchimpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="mailchimp",
            display_name="Mailchimp",
            category="Marketing",
            auth_types=["api_key", "oauth2"],
            description="Leading marketing automation and email marketing platform for growing businesses.",
            homepage_url="https://mailchimp.com",
            base_url="https://{server}.api.mailchimp.com/3.0",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Mailchimp API Key",
                    "placeholder": "0123456789abcdef-us1",
                    "description": "Mailchimp Marketing API key with server prefix (e.g. -us1).",
                    "docs_url": "https://mailchimp.com/help/about-api-keys/",
                    "docs_label": "Mailchimp API Keys Guide",
                    "setup_guide": {
                        "title": "Mailchimp API Key Guide",
                        "docs_url": "https://admin.mailchimp.com/account/api/",
                        "docs_label": "Mailchimp API Keys Page",
                        "instructions": [
                            "1. Sign in to your Mailchimp account at admin.mailchimp.com.",
                            "2. Click Profile > Extras > API keys.",
                            "3. Click 'Create A Key', label it (e.g. 'ConnectorHub').",
                            "4. Copy your key (includes server suffix like '-us1' or '-us19') and paste it below."
                        ],
                        "scopes": ["lists:read", "lists:write", "members:read", "members:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "0123456789abcdef-us1",
                            "description": "Mailchimp API key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("mailchimp"):
            self.register_action(MailchimpDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Mailchimp API credentials or OAuth access token."""
        cred = credential or {}
        key = str(cred.get("apiKey") or cred.get("accessToken") or "").strip()
        if not key:
            raise ValueError("Mailchimp API key or OAuth access token required.")

        # Check if OAuth token or API key
        is_oauth = "-" not in key and (cred.get("authType") == "oauth2" or bool(cred.get("accessToken")))

        if is_oauth:
            # Discover user's datacenter and API endpoint via Mailchimp OAuth metadata endpoint
            metadata_url = "https://login.mailchimp.com/oauth2/metadata"
            assert_public_url(metadata_url)
            headers = {
                "Authorization": f"OAuth {key}",
                "Accept": "application/json",
                "User-Agent": "ConnectorHub/1.0"
            }
            try:
                resp = await execute_guarded_request(client=client, method="GET", url=metadata_url, headers=headers)
            except Exception as e:
                raise ValueError(f"Unable to reach Mailchimp metadata API: {str(e)}")

            if resp.status_code in (401, 403):
                raise ValueError("Invalid Mailchimp OAuth token. Mailchimp returned Unauthorized.")
            elif resp.status_code != 200:
                raise ValueError(f"Mailchimp OAuth validation failed with status {resp.status_code}: {resp.text[:300]}")

            meta = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
            dc = meta.get("dc")
            api_endpoint = meta.get("api_endpoint") or (f"https://{dc}.api.mailchimp.com" if dc else None)
            account_id = str(meta.get("user_id") or meta.get("login", {}).get("email") or meta.get("accountname") or "mailchimp_user")
            account_name = meta.get("accountname") or meta.get("login", {}).get("login_name") or "Mailchimp Account"

            return {
                "valid": True,
                "account_id": account_id,
                "accountId": account_id,
                "display_name": f"{account_name} ({dc})" if dc else account_name,
                "displayName": f"{account_name} ({dc})" if dc else account_name,
                "granted_scopes": ["lists:read", "lists:write", "members:read", "members:write"],
                "avatar_url": (meta.get("login") or {}).get("avatar") if isinstance(meta.get("login"), dict) else None,
                "metadata": {
                    "dc": dc,
                    "serverPrefix": dc,
                    "apiEndpoint": api_endpoint,
                    "role": meta.get("role"),
                    "accountname": account_name,
                    "login": meta.get("login")
                }
            }

        # Otherwise validate API key via /ping
        base_url = _resolve_mailchimp_base(credential)
        headers = _mailchimp_headers(credential)
        url = f"{base_url}/ping"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Mailchimp API: {str(e)}")

        if resp.status_code in (401, 403):
            raise ValueError("Invalid Mailchimp API key. Mailchimp returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Mailchimp credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        server_prefix = credential.get("serverPrefix") or (key.split("-")[-1].strip() if "-" in key else "us1")
        return {
            "valid": True,
            "account_id": f"mailchimp_{server_prefix}",
            "accountId": f"mailchimp_{server_prefix}",
            "display_name": f"Mailchimp ({server_prefix})",
            "displayName": f"Mailchimp ({server_prefix})",
            "granted_scopes": ["lists:read", "lists:write", "members:read", "members:write"],
            "metadata": {
                "validationEndpoint": "/ping",
                "health": body.get("health_status") or "ok",
                "serverPrefix": server_prefix,
                "dc": server_prefix
            }
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
        base_url = _resolve_mailchimp_base(credential)
        clean_ep = "/" + endpoint.lstrip("/")
        url = f"{base_url}{clean_ep}"
        assert_public_url(url)

        auth_headers = _mailchimp_headers(credential)
        fwd_headers = dict(headers or {})
        fwd_headers.update(auth_headers)

        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=url,
            headers=fwd_headers,
            json_body=body if method in ["POST", "PUT", "PATCH"] else None
        )
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return {"status": resp.status_code, "data": data}

"""
Clerk Provider for ConnectorHub.
Loads and registers 11 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.clerk.com/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl"]:
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
    elif auth_mode == "upstash_bearer":
        rt = cred.get("restToken") or token
        if rt:
            headers["Authorization"] = f"Bearer {rt}"
    elif auth_mode == "figma_token":
        if token:
            if str(token).startswith("figd_") or not str(token).startswith("ey"):
                headers["X-Figma-Token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "wordpress_auth":
        if cred.get("username") and (cred.get("password") or token):
            u = str(cred.get("username"))
            p = str(cred.get("password") or token)
            pair = f"{u}:{p}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
        elif token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "mixpanel_basic":
        u = str(cred.get("serviceAccountUsername") or cred.get("username") or "")
        p = str(cred.get("secret") or token)
        pair = f"{u}:{p}"
        headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "klaviyo_api_key":
        if token:
            headers["Authorization"] = f"Klaviyo-API-Key {token}"
            headers["revision"] = "2024-10-15"
    elif auth_mode == "segment_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "activecampaign_token":
        if token:
            headers["Api-Token"] = token
    elif auth_mode == "ghost_key":
        pass

    return headers

ROUTES: Dict[str, List[Any]] = {
    "ban_user": [
        "GET",
        "/instance",
        [],
        [
            "user_id"
        ]
    ],
    "count_users": [
        "GET",
        "/users/count",
        [],
        [
            "email_address",
            "phone_number",
            "username",
            "user_id",
            "external_id",
            "query"
        ]
    ],
    "create_user": [
        "POST",
        "/users",
        [],
        [
            "email_address",
            "phone_number",
            "web3_wallet",
            "external_id",
            "first_name",
            "last_name",
            "username",
            "password",
            "password_digest",
            "password_hasher",
            "skip_password_checks",
            "skip_password_requirement",
            "totp_secret",
            "backup_codes",
            "public_metadata",
            "private_metadata",
            "unsafe_metadata",
            "created_at"
        ]
    ],
    "delete_user": [
        "DELETE",
        "/users/${encodeURIComponent(requiredInputString(input.user_id, ",
        [],
        [
            "user_id"
        ]
    ],
    "get_user": [
        "GET",
        "/users/${encodeURIComponent(requiredInputString(input.user_id, ",
        [],
        [
            "user_id"
        ]
    ],
    "list_users": [
        "GET",
        "/users",
        [],
        [
            "email_address",
            "phone_number",
            "username",
            "user_id",
            "external_id",
            "query",
            "order_by",
            "limit",
            "offset"
        ]
    ],
    "lock_user": [
        "GET",
        "/instance",
        [],
        [
            "user_id"
        ]
    ],
    "unban_user": [
        "GET",
        "/instance",
        [],
        [
            "user_id"
        ]
    ],
    "unlock_user": [
        "GET",
        "/instance",
        [],
        [
            "user_id"
        ]
    ],
    "update_user": [
        "PATCH",
        "/users/${encodeURIComponent(requiredInputString(user_id, ",
        [],
        [
            "user_id",
            "first_name",
            "last_name",
            "primary_email_address_id",
            "primary_phone_number_id",
            "primary_web3_wallet_id",
            "username",
            "password",
            "password_digest",
            "password_hasher",
            "skip_password_checks",
            "skip_password_requirement",
            "sign_out_of_other_sessions",
            "totp_secret",
            "backup_codes",
            "public_metadata",
            "private_metadata",
            "unsafe_metadata"
        ]
    ],
    "update_user_metadata": [
        "PATCH",
        "/users/${encodeURIComponent(requiredInputString(user_id, ",
        [],
        [
            "user_id",
            "public_metadata",
            "private_metadata",
            "unsafe_metadata"
        ]
    ]
}

class ClerkDynamicAction(Action):
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

        if "Bearer" == "ghost_key":
            token = _extract_token(cred)
            if token:
                req_params["key"] = token

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

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Clerk API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ClerkProvider(Provider):
    def __init__(self):
        super().__init__(
            service="clerk",
            display_name="Clerk",
            category="Identity & Security",
            auth_types=["api_key"],
            description="Clerk authentication, user management, and session controls with 11 actions."
        )
        for act in get_provider_actions("clerk"):
            self.register_action(ClerkDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.clerk.com/v1/users/count"
        for key in ["domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "Bearer" == "ghost_key":
            token = _extract_token(cred)
            if token:
                params["key"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=params if params else None
            )
        except Exception as e:
            raise ValueError(f"Clerk connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Clerk credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Clerk validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Clerk Account"
        }

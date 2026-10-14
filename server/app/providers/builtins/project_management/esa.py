"""
esa Provider for ConnectorHub.
Loads and registers 17 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.esa.io"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken"]:
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
    return base.rstrip("/")

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "bearer"
    if auth_mode == "bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "bloomerang":
        if token:
            headers["X-API-KEY"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "get_current_user": [
        "GET",
        "/v1/user",
        [],
        []
    ],
    "list_teams": [
        "GET",
        "/v1/teams",
        [],
        []
    ],
    "get_team": [
        "GET",
        "/v1/teams/{team_name}",
        [
            "team_name"
        ],
        []
    ],
    "get_team_stats": [
        "GET",
        "/v1/teams/{team_name}/stats",
        [
            "team_name"
        ],
        []
    ],
    "list_posts": [
        "GET",
        "/v1/teams/{team_name}/posts",
        [
            "team_name"
        ],
        [
            "q",
            "include",
            "sort",
            "order",
            "page",
            "per_page"
        ]
    ],
    "get_post": [
        "GET",
        "/v1/teams/{team_name}/posts/{post_number}",
        [
            "team_name",
            "post_number"
        ],
        []
    ],
    "create_post": [
        "POST",
        "/v1/teams/{team_name}/posts",
        [
            "team_name"
        ],
        [
            "name",
            "body_md",
            "tags",
            "category",
            "wip",
            "message"
        ]
    ],
    "update_post": [
        "PATCH",
        "/v1/teams/{team_name}/posts/{post_number}",
        [
            "team_name",
            "post_number"
        ],
        [
            "name",
            "body_md",
            "tags",
            "category",
            "wip",
            "message"
        ]
    ],
    "delete_post": [
        "DELETE",
        "/v1/teams/{team_name}/posts/{post_number}",
        [
            "team_name",
            "post_number"
        ],
        []
    ],
    "list_comments": [
        "GET",
        "/v1/teams/{team_name}/comments",
        [
            "team_name"
        ],
        [
            "page",
            "per_page"
        ]
    ],
    "get_comment": [
        "GET",
        "/v1/teams/{team_name}/comments/{comment_id}",
        [
            "team_name",
            "comment_id"
        ],
        []
    ],
    "create_comment": [
        "POST",
        "/v1/teams/{team_name}/posts/{post_number}/comments",
        [
            "team_name",
            "post_number"
        ],
        [
            "body_md"
        ]
    ],
    "update_comment": [
        "PATCH",
        "/v1/teams/{team_name}/comments/{comment_id}",
        [
            "team_name",
            "comment_id"
        ],
        [
            "body_md"
        ]
    ],
    "delete_comment": [
        "DELETE",
        "/v1/teams/{team_name}/comments/{comment_id}",
        [
            "team_name",
            "comment_id"
        ],
        []
    ],
    "list_categories": [
        "GET",
        "/v1/teams/{team_name}/categories",
        [
            "team_name"
        ],
        []
    ],
    "list_tags": [
        "GET",
        "/v1/teams/{team_name}/tags",
        [
            "team_name"
        ],
        []
    ],
    "list_members": [
        "GET",
        "/v1/teams/{team_name}/members",
        [
            "team_name"
        ],
        []
    ]
}

class EsaDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Productivity"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["POST", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        base_url = _resolve_base_url(cred)
        headers = _build_headers(cred)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{base_url}{path}" if not path.startswith("http") else path
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("error") or err_json.get("error_description") or err_msg
            except Exception:
                pass
            raise ValueError(f"esa API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class EsaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="esa",
            display_name="esa",
            category="Productivity",
            auth_types=['oauth2', 'api_key'],
            description="esa team knowledge base, markdown posts, revisions, comments, team categories, and tags with 30 actions."
        )
        for act in get_provider_actions("esa"):
            self.register_action(EsaDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token:
            raise ValueError("API key or token is required for esa.")

        val_url = "https://api.esa.io/v1/user"
        for key in ["domain", "subdomain", "site", "host", "tenant"]:
            if "{" + key + "}" in val_url:
                val = str(cred.get(key) or "default").strip()
                val_url = val_url.replace("{" + key + "}", val)

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"esa connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid esa credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"esa validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": token[:8] + "..." if len(token) > 8 else "verified",
            "display_name": f"esa Account"
        }

EsaProvider = EsaProvider

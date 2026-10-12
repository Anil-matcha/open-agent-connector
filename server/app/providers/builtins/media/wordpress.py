"""
WordPress Provider for ConnectorHub.
Loads and registers 18 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "{siteUrl}/wp-json/wp/v2"

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

    auth_mode = "wordpress_auth"
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
    "create_category": [
        "POST",
        "/categories",
        [],
        [
            "name",
            "slug",
            "description",
            "parent",
            "meta"
        ]
    ],
    "create_page": [
        "POST",
        "/pages",
        [],
        [
            "title",
            "content",
            "excerpt",
            "slug",
            "status",
            "parent",
            "featuredMedia",
            "menuOrder",
            "meta"
        ]
    ],
    "create_post": [
        "POST",
        "/posts",
        [],
        [
            "title",
            "content",
            "excerpt",
            "slug",
            "status",
            "categories",
            "tags",
            "featuredMedia",
            "meta"
        ]
    ],
    "create_tag": [
        "POST",
        "/tags",
        [],
        [
            "name",
            "slug",
            "description",
            "parent",
            "meta"
        ]
    ],
    "delete_comment": [
        "DELETE",
        "/comments",
        [],
        [
            "id",
            "force"
        ]
    ],
    "delete_page": [
        "POST",
        "/pages",
        [],
        [
            "id",
            "force"
        ]
    ],
    "delete_post": [
        "POST",
        "/posts",
        [],
        [
            "id",
            "force"
        ]
    ],
    "get_current_user": [
        "GET",
        "/posts",
        [],
        []
    ],
    "get_page": [
        "POST",
        "/pages",
        [],
        [
            "id"
        ]
    ],
    "get_post": [
        "POST",
        "/posts",
        [],
        [
            "id"
        ]
    ],
    "list_categories": [
        "GET",
        "/categories",
        [],
        [
            "search",
            "page",
            "perPage",
            "order",
            "include",
            "exclude",
            "parent",
            "slug",
            "hideEmpty",
            "orderby"
        ]
    ],
    "list_comments": [
        "GET",
        "/comments",
        [],
        [
            "search",
            "page",
            "perPage",
            "order",
            "status",
            "post",
            "author",
            "parent",
            "include",
            "exclude",
            "orderby"
        ]
    ],
    "list_pages": [
        "POST",
        "/pages",
        [],
        [
            "search",
            "page",
            "perPage",
            "order",
            "status",
            "include",
            "exclude",
            "parent",
            "author",
            "slug",
            "orderby"
        ]
    ],
    "list_posts": [
        "POST",
        "/posts",
        [],
        [
            "search",
            "page",
            "perPage",
            "order",
            "status",
            "categories",
            "tags",
            "include",
            "exclude",
            "author",
            "slug",
            "orderby"
        ]
    ],
    "list_tags": [
        "GET",
        "/tags",
        [],
        [
            "search",
            "page",
            "perPage",
            "order",
            "include",
            "exclude",
            "parent",
            "slug",
            "hideEmpty",
            "orderby"
        ]
    ],
    "update_comment": [
        "PATCH",
        "/comments",
        [],
        [
            "id",
            "content",
            "status",
            "authorName",
            "authorEmail",
            "authorUrl"
        ]
    ],
    "update_page": [
        "POST",
        "/pages",
        [],
        [
            "id",
            "title",
            "content",
            "excerpt",
            "slug",
            "status",
            "parent",
            "featuredMedia",
            "menuOrder",
            "meta"
        ]
    ],
    "update_post": [
        "POST",
        "/posts",
        [],
        [
            "id",
            "title",
            "content",
            "excerpt",
            "slug",
            "status",
            "categories",
            "tags",
            "featuredMedia",
            "meta"
        ]
    ]
}

class WordPressDynamicAction(Action):
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

        if "wordpress_auth" == "ghost_key":
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
            raise ValueError(f"WordPress API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class WordPressProvider(Provider):
    def __init__(self):
        super().__init__(
            service="wordpress",
            display_name="WordPress",
            category="Content & Media",
            auth_types=["oauth2", "api_key"],
            description="WordPress publishing, posts, pages, categories, tags, and media with 18 actions."
        )
        for act in get_provider_actions("wordpress"):
            self.register_action(WordPressDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "{siteUrl}/wp-json/wp/v2/users/me"
        for key in ["domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "wordpress_auth" == "ghost_key":
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
            raise ValueError(f"WordPress connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid WordPress credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"WordPress validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"WordPress Account"
        }

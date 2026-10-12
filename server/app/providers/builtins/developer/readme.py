"""
ReadMe Provider for ConnectorHub.
Loads and registers 33 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://dash.readme.com/api/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    if base.startswith("{instanceUrl}"):
        inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
        base = base.replace("{instanceUrl}", inst)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "readme_basic"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "gitea_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "zerotier_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "n8n_header":
        if token:
            headers["X-N8N-API-KEY"] = token
    elif auth_mode == "readme_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mingdao_auth":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cred.get("appKey"):
            headers["X-App-Key"] = str(cred["appKey"])
        if cred.get("sign"):
            headers["X-Sign"] = str(cred["sign"])

    return headers

ROUTES: Dict[str, List[Any]] = {
    "ask_owlbot": [
        "GET",
        "/ask_owlbot",
        [],
        [
            "question"
        ]
    ],
    "create_category": [
        "POST",
        "/category",
        [],
        [
            "version",
            "title",
            "type"
        ]
    ],
    "create_changelog": [
        "POST",
        "/changelog",
        [],
        [
            "title",
            "type",
            "body",
            "hidden"
        ]
    ],
    "create_custom_page": [
        "POST",
        "/custom_page",
        [],
        [
            "title",
            "body",
            "html",
            "htmlmode",
            "hidden"
        ]
    ],
    "create_doc": [
        "POST",
        "/doc",
        [],
        [
            "version",
            "title",
            "type",
            "body",
            "category",
            "categorySlug",
            "hidden",
            "order",
            "parentDoc",
            "parentDocSlug",
            "error"
        ]
    ],
    "create_version": [
        "POST",
        "/version",
        [],
        [
            "version",
            "codename",
            "from",
            "is_stable",
            "is_beta",
            "is_hidden",
            "is_deprecated",
            "pdfStatus"
        ]
    ],
    "delete_api_specification": [
        "DELETE",
        "/api_specification",
        [],
        [
            "id"
        ]
    ],
    "delete_category": [
        "DELETE",
        "/category",
        [],
        [
            "slug",
            "version"
        ]
    ],
    "delete_changelog": [
        "DELETE",
        "/changelog",
        [],
        [
            "slug"
        ]
    ],
    "delete_custom_page": [
        "DELETE",
        "/custom_page",
        [],
        [
            "slug"
        ]
    ],
    "delete_doc": [
        "DELETE",
        "/doc",
        [],
        [
            "slug",
            "version"
        ]
    ],
    "delete_version": [
        "DELETE",
        "/version",
        [],
        [
            "versionId"
        ]
    ],
    "get_api_registry": [
        "GET",
        "/api_registry",
        [],
        [
            "uuid"
        ]
    ],
    "get_category": [
        "GET",
        "/category",
        [],
        [
            "slug",
            "version"
        ]
    ],
    "get_changelog": [
        "GET",
        "/changelog",
        [],
        [
            "slug"
        ]
    ],
    "get_custom_page": [
        "GET",
        "/custom_page",
        [],
        [
            "slug"
        ]
    ],
    "get_doc": [
        "GET",
        "/doc",
        [],
        [
            "slug",
            "production",
            "version"
        ]
    ],
    "get_openapi_schema": [
        "GET",
        "/openapi_schema",
        [],
        []
    ],
    "get_project": [
        "GET",
        "/project",
        [],
        []
    ],
    "get_version": [
        "GET",
        "/version",
        [],
        [
            "versionId"
        ]
    ],
    "list_api_specifications": [
        "GET",
        "/api_specifications",
        [],
        [
            "version",
            "perPage",
            "page"
        ]
    ],
    "list_categories": [
        "GET",
        "/categories",
        [],
        [
            "version",
            "perPage",
            "page"
        ]
    ],
    "list_category_docs": [
        "GET",
        "/category_docs",
        [],
        [
            "slug",
            "version"
        ]
    ],
    "list_changelogs": [
        "GET",
        "/changelogs",
        [],
        [
            "perPage",
            "page"
        ]
    ],
    "list_custom_pages": [
        "GET",
        "/custom_pages",
        [],
        [
            "perPage",
            "page"
        ]
    ],
    "list_outbound_ips": [
        "GET",
        "/outbound_ips",
        [],
        []
    ],
    "list_versions": [
        "GET",
        "/versions",
        [],
        []
    ],
    "search_docs": [
        "GET",
        "/search_docs",
        [],
        [
            "search",
            "version"
        ]
    ],
    "update_category": [
        "PATCH",
        "/category",
        [],
        [
            "slug",
            "version",
            "title",
            "type"
        ]
    ],
    "update_changelog": [
        "PATCH",
        "/changelog",
        [],
        [
            "slug",
            "title",
            "type",
            "body",
            "hidden"
        ]
    ],
    "update_custom_page": [
        "PATCH",
        "/custom_page",
        [],
        [
            "slug",
            "title",
            "body",
            "html",
            "htmlmode",
            "hidden"
        ]
    ],
    "update_doc": [
        "PATCH",
        "/doc",
        [],
        [
            "slug",
            "version",
            "title",
            "type",
            "body",
            "category",
            "categorySlug",
            "hidden",
            "order",
            "parentDoc",
            "parentDocSlug",
            "error"
        ]
    ],
    "update_version": [
        "PATCH",
        "/version",
        [],
        [
            "versionId",
            "version",
            "codename",
            "from",
            "is_stable",
            "is_beta",
            "is_hidden",
            "is_deprecated",
            "pdfStatus"
        ]
    ]
}

class ReadMeDynamicAction(Action):
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
            raise ValueError(f"ReadMe API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class ReadMeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="readme",
            display_name="ReadMe",
            category="Developer Tools",
            auth_types=["api_key"],
            description="ReadMe interactive developer documentation, API references, and metrics with 33 actions."
        )
        for act in get_provider_actions("readme"):
            self.register_action(ReadMeDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://dash.readme.com/api/v1/"
        for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))
        if val_url.startswith("{instanceUrl}"):
            inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
            val_url = val_url.replace("{instanceUrl}", inst)

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
            raise ValueError(f"ReadMe connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid ReadMe credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"ReadMe validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"ReadMe Account"
        }

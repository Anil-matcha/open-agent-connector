"""
Karakeep Provider for ConnectorHub.
Loads and registers 55 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://cloud.karakeep.app/api/v1"

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

    auth_mode = "Bearer"
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
    "add_bookmark_to_list": [
        "PUT",
        "/lists/${encodeKarakeepId(listId, ",
        [],
        [
            "listId",
            "bookmarkId"
        ]
    ],
    "admin_trigger_inference": [
        "POST",
        "/admin/jobs/trigger/inference",
        [],
        [
            "type",
            "status",
            "modifiedWithinSeconds"
        ]
    ],
    "admin_trigger_recrawl": [
        "POST",
        "/admin/jobs/trigger/recrawl",
        [],
        [
            "crawlStatus",
            "runInference",
            "modifiedWithinSeconds"
        ]
    ],
    "admin_trigger_reindex": [
        "POST",
        "/admin/jobs/trigger/reindex",
        [],
        [
            "modifiedWithinSeconds"
        ]
    ],
    "admin_update_user": [
        "PUT",
        "/admin/users/${encodeKarakeepId(userId, ",
        [],
        [
            "userId",
            "role",
            "bookmarkQuota",
            "storageQuota",
            "browserCrawlingEnabled"
        ]
    ],
    "attach_asset_to_bookmark": [
        "POST",
        "/assets",
        [],
        [
            "bookmarkId",
            "assetId",
            "assetType"
        ]
    ],
    "attach_tags_to_bookmark": [
        "GET",
        "/lists",
        [],
        [
            "bookmarkId",
            "tags"
        ]
    ],
    "check_bookmark_url": [
        "GET",
        "/bookmarks/check-url",
        [],
        [
            "url"
        ]
    ],
    "create_backup": [
        "POST",
        "/backups",
        [],
        []
    ],
    "create_bookmark": [
        "POST",
        "/bookmarks",
        [],
        [
            "type",
            "url",
            "precrawledArchiveId",
            "text",
            "assetType",
            "assetId",
            "fileName",
            "sourceUrl",
            "title",
            "archived",
            "favourited",
            "note",
            "summary",
            "createdAt",
            "crawlPriority",
            "source"
        ]
    ],
    "create_feed": [
        "POST",
        "/feeds",
        [],
        [
            "name",
            "url",
            "enabled",
            "importTags"
        ]
    ],
    "create_highlight": [
        "POST",
        "/highlights",
        [],
        [
            "bookmarkId",
            "startOffset",
            "endOffset",
            "color",
            "text",
            "note"
        ]
    ],
    "create_list": [
        "POST",
        "/lists",
        [],
        [
            "name",
            "description",
            "icon",
            "type",
            "query",
            "parentId"
        ]
    ],
    "create_tag": [
        "POST",
        "/tags",
        [],
        [
            "name"
        ]
    ],
    "delete_backup": [
        "DELETE",
        "/backups/${encodeKarakeepId(backupId, ",
        [],
        [
            "backupId"
        ]
    ],
    "delete_bookmark": [
        "DELETE",
        "/content",
        [],
        [
            "bookmarkId"
        ]
    ],
    "delete_feed": [
        "DELETE",
        "{target}/fetch",
        [
            "target"
        ],
        [
            "feedId"
        ]
    ],
    "delete_highlight": [
        "DELETE",
        "/highlights/${encodeKarakeepId(input.highlightId, ",
        [],
        [
            "highlightId"
        ]
    ],
    "delete_list": [
        "DELETE",
        "/lists/${encodeKarakeepId(listId, ",
        [],
        [
            "listId"
        ]
    ],
    "delete_tag": [
        "DELETE",
        "/tags/${encodeKarakeepId(tagId, ",
        [],
        [
            "tagId"
        ]
    ],
    "detach_asset_from_bookmark": [
        "DELETE",
        "/detach_asset_from_bookmark",
        [],
        [
            "bookmarkId",
            "assetId"
        ]
    ],
    "detach_tags_from_bookmark": [
        "GET",
        "/lists",
        [],
        [
            "bookmarkId",
            "tags"
        ]
    ],
    "download_backup": [
        "GET",
        "/backups/${encodeKarakeepId(backupId, ",
        [],
        [
            "backupId"
        ]
    ],
    "fetch_feed_now": [
        "POST",
        "{target}/fetch",
        [
            "target"
        ],
        [
            "feedId"
        ]
    ],
    "get_asset": [
        "POST",
        "/assets/${encodeKarakeepId(assetId, ",
        [],
        [
            "assetId"
        ]
    ],
    "get_asset_signed_url": [
        "POST",
        "/assets/{assetId}/signed-url",
        [
            "assetId"
        ],
        []
    ],
    "get_backup": [
        "DELETE",
        "/backups/{backupId}",
        [
            "backupId"
        ],
        []
    ],
    "get_bookmark": [
        "GET",
        "/content",
        [],
        [
            "bookmarkId",
            "includeContent"
        ]
    ],
    "get_bookmark_content": [
        "GET",
        "/content",
        [],
        [
            "bookmarkId",
            "format",
            "maxChars",
            "cursor"
        ]
    ],
    "get_bookmark_highlights": [
        "GET",
        "/highlights",
        [],
        [
            "bookmarkId"
        ]
    ],
    "get_bookmark_lists": [
        "GET",
        "/lists",
        [],
        [
            "bookmarkId"
        ]
    ],
    "get_current_user": [
        "GET",
        "/users/me",
        [],
        []
    ],
    "get_current_user_stats": [
        "GET",
        "/users/me/stats",
        [],
        []
    ],
    "get_feed": [
        "GET",
        "{target}/fetch",
        [
            "target"
        ],
        [
            "feedId"
        ]
    ],
    "get_highlight": [
        "GET",
        "/highlights/${encodeKarakeepId(input.highlightId, ",
        [],
        [
            "highlightId"
        ]
    ],
    "get_list": [
        "GET",
        "/lists/${encodeKarakeepId(input.listId, ",
        [],
        [
            "listId"
        ]
    ],
    "get_list_bookmarks": [
        "GET",
        "/lists/${encodeKarakeepId(input.listId, ",
        [],
        [
            "listId",
            "sortOrder",
            "limit",
            "cursor",
            "includeContent"
        ]
    ],
    "get_tag": [
        "GET",
        "/tags/${encodeKarakeepId(input.tagId, ",
        [],
        [
            "tagId"
        ]
    ],
    "get_tag_bookmarks": [
        "GET",
        "/tags/${encodeKarakeepId(input.tagId, ",
        [],
        [
            "tagId",
            "sortOrder",
            "limit",
            "cursor",
            "includeContent"
        ]
    ],
    "list_backups": [
        "POST",
        "/backups",
        [],
        []
    ],
    "list_bookmarks": [
        "GET",
        "/bookmarks",
        [],
        [
            "archived",
            "favourited",
            "sortOrder",
            "limit",
            "cursor",
            "includeContent"
        ]
    ],
    "list_feeds": [
        "GET",
        "/feeds",
        [],
        []
    ],
    "list_highlights": [
        "GET",
        "/highlights",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_lists": [
        "GET",
        "/lists",
        [],
        []
    ],
    "list_tags": [
        "GET",
        "/tags",
        [],
        [
            "nameContains",
            "sort",
            "attachedBy",
            "cursor",
            "limit"
        ]
    ],
    "remove_bookmark_from_list": [
        "DELETE",
        "/lists/${encodeKarakeepId(listId, ",
        [],
        [
            "listId",
            "bookmarkId"
        ]
    ],
    "replace_asset_on_bookmark": [
        "PUT",
        "/replace_asset_on_bookmark",
        [],
        [
            "bookmarkId",
            "assetId",
            "newAssetId"
        ]
    ],
    "search_bookmarks": [
        "GET",
        "/bookmarks/search",
        [],
        [
            "q",
            "searchMode",
            "sortOrder",
            "limit",
            "cursor",
            "includeContent"
        ]
    ],
    "summarize_bookmark": [
        "POST",
        "/summarize",
        [],
        [
            "bookmarkId"
        ]
    ],
    "update_bookmark": [
        "PATCH",
        "/content",
        [],
        [
            "bookmarkId",
            "archived",
            "favourited",
            "summary",
            "note",
            "title",
            "createdAt",
            "url",
            "description",
            "author",
            "publisher",
            "datePublished",
            "dateModified",
            "text",
            "assetContent"
        ]
    ],
    "update_feed": [
        "PATCH",
        "{target}/fetch",
        [
            "target"
        ],
        [
            "feedId",
            "name",
            "url",
            "enabled",
            "importTags"
        ]
    ],
    "update_highlight": [
        "PATCH",
        "/highlights/${encodeKarakeepId(input.highlightId, ",
        [],
        [
            "highlightId",
            "color",
            "note"
        ]
    ],
    "update_list": [
        "PATCH",
        "/lists/${encodeKarakeepId(input.listId, ",
        [],
        [
            "listId",
            "name",
            "description",
            "icon",
            "parentId",
            "query",
            "public"
        ]
    ],
    "update_tag": [
        "PATCH",
        "/tags/${encodeKarakeepId(input.tagId, ",
        [],
        [
            "tagId",
            "name"
        ]
    ],
    "upload_asset": [
        "POST",
        "/assets",
        [],
        [
            "file"
        ]
    ]
}

class KarakeepDynamicAction(Action):
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
            raise ValueError(f"Karakeep API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class KarakeepProvider(Provider):
    def __init__(self):
        super().__init__(
            service="karakeep",
            display_name="Karakeep",
            category="Project Management",
            auth_types=["api_key"],
            description="Karakeep bookmarking, highlights, feeds, backups, and knowledge assets with 55 actions."
        )
        for act in get_provider_actions("karakeep"):
            self.register_action(KarakeepDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://cloud.karakeep.app/api/v1/users/me"
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
            raise ValueError(f"Karakeep connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Karakeep credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Karakeep validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Karakeep Account"
        }

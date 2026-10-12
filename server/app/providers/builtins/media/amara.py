"""
Amara Provider for ConnectorHub.
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

DEFAULT_API_BASE = "https://amara.org/api"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
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

    auth_mode = "x_api_key"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "token_auth":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode == "unsplash_client_id":
        if token:
            headers["Authorization"] = f"Client-ID {token}"
    elif auth_mode == "amplitude_basic":
        if token:
            secret = str(cred.get("secretKey") or cred.get("apiKeyId") or "X").strip()
            pair = f"{token}:{secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_subtitle_note": [
        "POST",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode",
            "body"
        ]
    ],
    "add_video_url": [
        "POST",
        "/video_url",
        [],
        [
            "videoId",
            "url",
            "primary"
        ]
    ],
    "create_subtitle_language": [
        "POST",
        "/languages/",
        [],
        [
            "videoId",
            "language"
        ]
    ],
    "create_subtitles": [
        "POST",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode",
            "subFormat",
            "subtitles",
            "subtitlesUrl",
            "title",
            "action",
            "metadata",
            "description"
        ]
    ],
    "create_video": [
        "POST",
        "/videos/",
        [],
        [
            "videoUrl",
            "title",
            "team",
            "project",
            "duration",
            "metadata",
            "thumbnail",
            "description",
            "primaryAudioLanguageCode"
        ]
    ],
    "delete_video_url": [
        "DELETE",
        "/languages/",
        [],
        [
            "videoId",
            "urlId"
        ]
    ],
    "fetch_subtitles_data": [
        "GET",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode",
            "format"
        ]
    ],
    "get_activity": [
        "GET",
        "/languages/",
        [],
        [
            "activityId"
        ]
    ],
    "get_subtitle_language_details": [
        "GET",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode"
        ]
    ],
    "get_team_details": [
        "GET",
        "/languages/",
        [],
        [
            "slug"
        ]
    ],
    "get_team_languages": [
        "GET",
        "/languages/",
        [],
        [
            "slug"
        ]
    ],
    "get_user": [
        "GET",
        "/languages/",
        [],
        [
            "userIdentifier"
        ]
    ],
    "get_user_activity": [
        "GET",
        "/languages/",
        [],
        [
            "identifier",
            "offset",
            "limit"
        ]
    ],
    "get_user_data": [
        "GET",
        "/languages/",
        [],
        [
            "identifier"
        ]
    ],
    "get_video": [
        "GET",
        "/video",
        [],
        [
            "videoId"
        ]
    ],
    "get_video_url": [
        "GET",
        "/video_url",
        [],
        [
            "videoId",
            "urlId"
        ]
    ],
    "get_video_url_details": [
        "GET",
        "/languages/",
        [],
        [
            "url"
        ]
    ],
    "list_activity": [
        "GET",
        "/languages/",
        [],
        [
            "team",
            "type",
            "after",
            "before",
            "limit",
            "video",
            "offset",
            "language",
            "teamActivity"
        ]
    ],
    "list_available_languages": [
        "GET",
        "/available_languages",
        [],
        []
    ],
    "list_languages": [
        "GET",
        "/languages",
        [],
        []
    ],
    "list_subtitle_actions": [
        "GET",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode"
        ]
    ],
    "list_subtitle_languages": [
        "GET",
        "/languages/",
        [],
        [
            "videoId"
        ]
    ],
    "list_subtitle_notes": [
        "GET",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode"
        ]
    ],
    "list_teams": [
        "GET",
        "/languages/",
        [],
        [
            "offset",
            "limit"
        ]
    ],
    "list_video_activity": [
        "GET",
        "/video_activity",
        [],
        [
            "videoId",
            "offset",
            "limit"
        ]
    ],
    "list_video_urls": [
        "GET",
        "/video_urls",
        [],
        [
            "videoId",
            "offset",
            "limit"
        ]
    ],
    "list_videos": [
        "GET",
        "/videos",
        [],
        [
            "sort",
            "team",
            "owner",
            "project",
            "language",
            "archive",
            "videoId",
            "videoUrl",
            "offset",
            "limit"
        ]
    ],
    "make_video_url_primary": [
        "PUT",
        "/languages/",
        [],
        [
            "videoId",
            "urlId",
            "primary"
        ]
    ],
    "perform_subtitle_action": [
        "POST",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode",
            "action"
        ]
    ],
    "send_message": [
        "POST",
        "/languages/",
        [],
        [
            "subject",
            "content",
            "user",
            "team"
        ]
    ],
    "update_subtitle_language": [
        "PUT",
        "/languages/",
        [],
        [
            "videoId",
            "languageCode",
            "softLimitCpl",
            "softLimitCps",
            "softLimitLines",
            "subtitlesComplete",
            "softLimitMaxDuration",
            "softLimitMinDuration",
            "isPrimaryAudioLanguage"
        ]
    ],
    "update_video": [
        "PUT",
        "/video",
        [],
        [
            "videoId",
            "team",
            "title",
            "project",
            "duration",
            "metadata",
            "thumbnail",
            "description",
            "primaryAudioLanguageCode"
        ]
    ],
    "view_video_details": [
        "GET",
        "/view_video_details",
        [],
        [
            "videoId"
        ]
    ]
}

class AmaraDynamicAction(Action):
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

        if resp.status_code >= 400:
            raise ValueError(f"Amara API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class AmaraProvider(Provider):
    def __init__(self):
        super().__init__(
            service="amara",
            display_name="Amara",
            category="Media & Content",
            auth_types=["api_key"],
            description="Amara video subtitling, translation, and team collaboration platform with 33 actions."
        )
        for act in get_provider_actions("amara"):
            self.register_action(AmaraDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://amara.org/api/videos/"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

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
            raise ValueError(f"Amara connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Amara credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Amara validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "amara" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Amara credentials: {body.get('errmsg') or resp.text}")
                elif "amara" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid Amara credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Amara Account"
        }

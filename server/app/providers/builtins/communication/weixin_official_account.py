"""
WeChat Official Account Provider for ConnectorHub.
Loads and registers 42 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.weixin.qq.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
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
    elif auth_mode == "discord_bot":
        if token:
            headers["Authorization"] = f"Bot {token}"
    elif auth_mode == "freshdesk_basic":
        if token:
            pair = f"{token}:X"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_draft": [
        "POST",
        "/cgi-bin/draft/add",
        [],
        [
            "articles"
        ]
    ],
    "add_material": [
        "POST",
        "/cgi-bin/material/add_material",
        [],
        [
            "type",
            "file",
            "title",
            "introduction"
        ]
    ],
    "add_template": [
        "POST",
        "/cgi-bin/template/api_add_template",
        [],
        [
            "templateIdShort"
        ]
    ],
    "batch_get_draft": [
        "POST",
        "/cgi-bin/draft/batchget",
        [],
        [
            "offset",
            "count",
            "noContent"
        ]
    ],
    "batch_get_material": [
        "POST",
        "/cgi-bin/material/batchget_material",
        [],
        [
            "type",
            "offset",
            "count"
        ]
    ],
    "batch_get_published": [
        "POST",
        "/cgi-bin/freepublish/batchget",
        [],
        [
            "offset",
            "count",
            "noContent"
        ]
    ],
    "callback_check": [
        "POST",
        "/cgi-bin/callback/check",
        [],
        [
            "action",
            "checkOperator"
        ]
    ],
    "clear_quota": [
        "POST",
        "/cgi-bin/clear_quota",
        [],
        []
    ],
    "delete_draft": [
        "POST",
        "/cgi-bin/draft/delete",
        [],
        [
            "mediaId"
        ]
    ],
    "delete_mass_message": [
        "POST",
        "/cgi-bin/message/mass/delete",
        [],
        [
            "msgId",
            "articleIdx"
        ]
    ],
    "delete_material": [
        "POST",
        "/cgi-bin/material/del_material",
        [],
        [
            "mediaId"
        ]
    ],
    "delete_publish": [
        "POST",
        "/cgi-bin/freepublish/delete",
        [],
        [
            "articleId",
            "index"
        ]
    ],
    "delete_template": [
        "POST",
        "/cgi-bin/template/del_private_template",
        [],
        [
            "templateId"
        ]
    ],
    "get_all_templates": [
        "GET",
        "/cgi-bin/template/get_all_private_template",
        [],
        []
    ],
    "get_api_domain_ip": [
        "GET",
        "/cgi-bin/get_api_domain_ip",
        [],
        []
    ],
    "get_article_read": [
        "GET",
        "/article_read",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "get_article_share": [
        "GET",
        "/article_share",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "get_article_total_detail": [
        "GET",
        "/article_total_detail",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "get_biz_summary": [
        "GET",
        "/biz_summary",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "get_callback_ip": [
        "GET",
        "/cgi-bin/getcallbackip",
        [],
        []
    ],
    "get_draft": [
        "POST",
        "/cgi-bin/draft/get",
        [],
        [
            "mediaId"
        ]
    ],
    "get_draft_count": [
        "GET",
        "/cgi-bin/draft/count",
        [],
        []
    ],
    "get_mass_message_status": [
        "POST",
        "/cgi-bin/message/mass/get",
        [],
        [
            "msgId"
        ]
    ],
    "get_material": [
        "POST",
        "/cgi-bin/material/get_material",
        [],
        [
            "mediaId",
            "fileName"
        ]
    ],
    "get_material_count": [
        "GET",
        "/cgi-bin/material/get_materialcount",
        [],
        []
    ],
    "get_publish_status": [
        "POST",
        "/cgi-bin/freepublish/get",
        [],
        [
            "publishId"
        ]
    ],
    "get_published_article": [
        "POST",
        "/cgi-bin/freepublish/getarticle",
        [],
        [
            "articleId"
        ]
    ],
    "get_temp_media": [
        "GET",
        "/cgi-bin/media/get",
        [],
        [
            "mediaId",
            "fileName"
        ]
    ],
    "get_template_industry": [
        "GET",
        "/cgi-bin/template/get_industry",
        [],
        []
    ],
    "get_user_cumulate": [
        "GET",
        "/user_cumulate",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "get_user_summary": [
        "GET",
        "/user_summary",
        [],
        [
            "beginDate",
            "endDate"
        ]
    ],
    "preview_mass_message": [
        "POST",
        "/cgi-bin/message/mass/preview",
        [],
        [
            "toUser",
            "toWxName",
            "msgType",
            "content"
        ]
    ],
    "publish_draft": [
        "POST",
        "/cgi-bin/freepublish/submit",
        [],
        [
            "mediaId"
        ]
    ],
    "send_custom_message": [
        "POST",
        "/cgi-bin/message/custom/send",
        [],
        [
            "toUser",
            "msgType",
            "content"
        ]
    ],
    "send_mass_message": [
        "POST",
        "/cgi-bin/message/mass/send",
        [],
        [
            "toUsers",
            "msgType",
            "content",
            "sendIgnoreReprint"
        ]
    ],
    "send_mass_message_by_tag": [
        "POST",
        "/cgi-bin/message/mass/sendall",
        [],
        [
            "isToAll",
            "tagId",
            "msgType",
            "content"
        ]
    ],
    "send_template_message": [
        "POST",
        "/cgi-bin/message/template/send",
        [],
        [
            "toUser",
            "templateId",
            "url",
            "miniprogram",
            "clientMsgId",
            "data"
        ]
    ],
    "set_template_industry": [
        "POST",
        "/cgi-bin/template/api_set_industry",
        [],
        [
            "industryId1",
            "industryId2"
        ]
    ],
    "set_typing_status": [
        "POST",
        "/cgi-bin/message/custom/typing",
        [],
        [
            "toUser",
            "command"
        ]
    ],
    "update_draft": [
        "POST",
        "/cgi-bin/draft/update",
        [],
        [
            "mediaId",
            "index",
            "article"
        ]
    ],
    "upload_article_image": [
        "POST",
        "/cgi-bin/media/uploadimg",
        [],
        [
            "file"
        ]
    ],
    "upload_temp_media": [
        "GET",
        "/cgi-bin/media/upload",
        [],
        [
            "type",
            "file"
        ]
    ]
}

class WeixinOfficialAccountDynamicAction(Action):
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

        token = _extract_token(cred)
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
            req_params["token"] = token

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
            raise ValueError(f"WeChat Official Account API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class WeixinOfficialAccountProvider(Provider):
    def __init__(self):
        super().__init__(
            service="weixin_official_account",
            display_name="WeChat Official Account",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="WeChat Official Account management API with 42 actions for drafts, material, templates, and publishing."
        )
        for act in get_provider_actions("weixin_official_account"):
            self.register_action(WeixinOfficialAccountDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.weixin.qq.com/cgi-bin/get_api_domain_ip?access_token={{token}}"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
            req_params["token"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"WeChat Official Account connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid WeChat Official Account credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"WeChat Official Account validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "weixin_official_account" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid WeChat Official Account credentials: {body.get('msg') or resp.text}")
                elif "weixin_official_account" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid WeChat Official Account credentials: {body.get('errmsg') or resp.text}")
                elif "weixin_official_account" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid WeChat Official Account credentials: {body.get('error_msg') or resp.text}")
                elif "weixin_official_account" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid WeChat Official Account credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"WeChat Official Account Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"WeChat Official Account Account"
        }

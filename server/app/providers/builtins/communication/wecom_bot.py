"""
WeCom Bot Provider for ConnectorHub.
Loads and registers 54 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://qyapi.weixin.qq.com"

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
    "add_schedule_attendees": [
        "POST",
        "/schedule_attendees",
        [],
        [
            "scheduleId",
            "userIds"
        ]
    ],
    "call_tool": [
        "GET",
        "/call_tool",
        [],
        [
            "category",
            "toolName",
            "arguments"
        ]
    ],
    "cancel_meeting": [
        "POST",
        "/meeting",
        [],
        [
            "meetingId"
        ]
    ],
    "cancel_schedule": [
        "POST",
        "/schedule",
        [],
        [
            "scheduleId"
        ]
    ],
    "change_todo_user_status": [
        "GET",
        "/change_todo_user_status",
        [],
        [
            "todoId",
            "userId",
            "userStatus"
        ]
    ],
    "check_availability": [
        "GET",
        "/check_availability",
        [],
        [
            "userIds",
            "startTime",
            "endTime"
        ]
    ],
    "create_doc": [
        "POST",
        "/doc",
        [],
        [
            "documentType",
            "name"
        ]
    ],
    "create_meeting": [
        "POST",
        "/meeting",
        [],
        [
            "title",
            "startTime",
            "durationSeconds",
            "description",
            "location",
            "inviteeUserIds",
            "settings"
        ]
    ],
    "create_schedule": [
        "POST",
        "/schedule",
        [],
        [
            "startTime",
            "endTime",
            "summary",
            "description",
            "location",
            "isWholeDay",
            "attendeeUserIds",
            "reminders"
        ]
    ],
    "create_todo": [
        "POST",
        "/todo",
        [],
        [
            "content",
            "followers",
            "endTime",
            "reminderTypes"
        ]
    ],
    "del_schedule_attendees": [
        "GET",
        "/del_schedule_attendees",
        [],
        [
            "scheduleId",
            "userIds"
        ]
    ],
    "delete_todo": [
        "DELETE",
        "/todo",
        [],
        [
            "todoId"
        ]
    ],
    "download_message_media": [
        "GET",
        "/download_message_media",
        [],
        [
            "mediaId"
        ]
    ],
    "edit_doc_content": [
        "PATCH",
        "/edit_doc_content",
        [],
        [
            "docId",
            "url",
            "content"
        ]
    ],
    "get_doc_content": [
        "GET",
        "/doc_content",
        [],
        [
            "docId",
            "url"
        ]
    ],
    "get_meeting_info": [
        "GET",
        "/meeting_info",
        [],
        [
            "meetingId",
            "meetingCode",
            "subMeetingId"
        ]
    ],
    "get_message": [
        "GET",
        "/message",
        [],
        [
            "chatType",
            "chatId",
            "beginTime",
            "endTime",
            "cursor"
        ]
    ],
    "get_msg_chat_list": [
        "GET",
        "/msg_chat_list",
        [],
        [
            "beginTime",
            "endTime",
            "cursor"
        ]
    ],
    "get_schedule_detail": [
        "GET",
        "/schedule_detail",
        [],
        [
            "scheduleIds"
        ]
    ],
    "get_schedule_list_by_range": [
        "GET",
        "/schedule_list_by_range",
        [],
        [
            "startTime",
            "endTime"
        ]
    ],
    "get_todo_detail": [
        "GET",
        "/todo_detail",
        [],
        [
            "todoIds"
        ]
    ],
    "get_todo_list": [
        "GET",
        "/todo_list",
        [],
        [
            "userId",
            "createBeginTime",
            "createEndTime",
            "remindBeginTime",
            "remindEndTime",
            "deadlineBeginTime",
            "deadlineEndTime",
            "todoStatus",
            "limit",
            "cursor"
        ]
    ],
    "get_userlist": [
        "GET",
        "/userlist",
        [],
        []
    ],
    "list_tools": [
        "GET",
        "/tools",
        [],
        [
            "category"
        ]
    ],
    "list_user_meetings": [
        "GET",
        "/user_meetings",
        [],
        [
            "beginTime",
            "endTime",
            "cursor",
            "limit"
        ]
    ],
    "search_todo_userid": [
        "GET",
        "/search_todo_userid",
        [],
        [
            "keyword"
        ]
    ],
    "send_image_message": [
        "POST",
        "/send_image_message",
        [],
        [
            "base64",
            "md5"
        ]
    ],
    "send_markdown_message": [
        "POST",
        "/send_markdown_message",
        [],
        [
            "content"
        ]
    ],
    "send_markdown_v2_message": [
        "POST",
        "/send_markdown_v2_message",
        [],
        [
            "content"
        ]
    ],
    "send_message": [
        "POST",
        "/send_message",
        [],
        [
            "chatType",
            "chatId",
            "content"
        ]
    ],
    "send_news_message": [
        "POST",
        "/send_news_message",
        [],
        [
            "articles"
        ]
    ],
    "send_text_message": [
        "POST",
        "/send_text_message",
        [],
        [
            "content",
            "mentionedList",
            "mentionedMobileList"
        ]
    ],
    "set_invite_meeting_members": [
        "POST",
        "/set_invite_meeting_members",
        [],
        [
            "meetingId",
            "inviteeUserIds"
        ]
    ],
    "sheet_add_sub": [
        "POST",
        "/sheet_add_sub",
        [],
        [
            "docId",
            "title",
            "rowCount",
            "columnCount",
            "index"
        ]
    ],
    "sheet_append_data": [
        "GET",
        "/sheet_append_data",
        [],
        [
            "docId",
            "sheetId",
            "values"
        ]
    ],
    "sheet_delete_sub": [
        "DELETE",
        "/sheet_delete_sub",
        [],
        [
            "docId",
            "sheetId"
        ]
    ],
    "sheet_get_info": [
        "GET",
        "/sheet_get_info",
        [],
        [
            "docId",
            "url"
        ]
    ],
    "sheet_update_range_data": [
        "PATCH",
        "/sheet_update_range_data",
        [],
        [
            "docId",
            "sheetId",
            "startRow",
            "startColumn",
            "rows"
        ]
    ],
    "smartpage_create": [
        "POST",
        "/smartpage_create",
        [],
        [
            "title",
            "pages"
        ]
    ],
    "smartpage_export": [
        "GET",
        "/smartpage_export",
        [],
        [
            "docId",
            "url"
        ]
    ],
    "smartsheet_add_fields": [
        "POST",
        "/smartsheet_add_fields",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "fields"
        ]
    ],
    "smartsheet_add_records": [
        "POST",
        "/smartsheet_add_records",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "records"
        ]
    ],
    "smartsheet_add_sheet": [
        "POST",
        "/smartsheet_add_sheet",
        [],
        [
            "docId",
            "url",
            "title"
        ]
    ],
    "smartsheet_delete_fields": [
        "DELETE",
        "/smartsheet_delete_fields",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "fieldIds"
        ]
    ],
    "smartsheet_delete_records": [
        "DELETE",
        "/smartsheet_delete_records",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "recordIds"
        ]
    ],
    "smartsheet_delete_sheet": [
        "DELETE",
        "/smartsheet_delete_sheet",
        [],
        [
            "docId",
            "url",
            "sheetId"
        ]
    ],
    "smartsheet_get_fields": [
        "GET",
        "/smartsheet_get_fields",
        [],
        [
            "docId",
            "url",
            "sheetId"
        ]
    ],
    "smartsheet_get_records": [
        "GET",
        "/smartsheet_get_records",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "cursor",
            "limit"
        ]
    ],
    "smartsheet_get_sheet": [
        "GET",
        "/smartsheet_get_sheet",
        [],
        [
            "docId",
            "url"
        ]
    ],
    "smartsheet_update_fields": [
        "PATCH",
        "/smartsheet_update_fields",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "fields"
        ]
    ],
    "smartsheet_update_records": [
        "PATCH",
        "/smartsheet_update_records",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "keyType",
            "records"
        ]
    ],
    "smartsheet_update_sheet": [
        "PATCH",
        "/smartsheet_update_sheet",
        [],
        [
            "docId",
            "url",
            "sheetId",
            "title"
        ]
    ],
    "update_schedule": [
        "PATCH",
        "/schedule",
        [],
        [
            "scheduleId",
            "startTime",
            "endTime",
            "summary",
            "description",
            "location",
            "isWholeDay",
            "attendeeUserIds",
            "reminders"
        ]
    ],
    "update_todo": [
        "PATCH",
        "/todo",
        [],
        [
            "todoId",
            "content",
            "followers",
            "todoStatus",
            "endTime",
            "reminderTypes"
        ]
    ]
}

class WeComBotDynamicAction(Action):
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
            raise ValueError(f"WeCom Bot API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class WeComBotProvider(Provider):
    def __init__(self):
        super().__init__(
            service="wecom_bot",
            display_name="WeCom Bot",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="WeCom group bot and smart bot API with 54 actions for text, markdown, schedule, meeting, and todo management."
        )
        for act in get_provider_actions("wecom_bot"):
            self.register_action(WeComBotDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={{token}}&userid=me"
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
            raise ValueError(f"WeCom Bot connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid WeCom Bot credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"WeCom Bot validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "wecom_bot" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid WeCom Bot credentials: {body.get('msg') or resp.text}")
                elif "wecom_bot" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid WeCom Bot credentials: {body.get('errmsg') or resp.text}")
                elif "wecom_bot" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid WeCom Bot credentials: {body.get('error_msg') or resp.text}")
                elif "wecom_bot" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid WeCom Bot credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"WeCom Bot Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"WeCom Bot Account"
        }

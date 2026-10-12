"""
Feishu App Bot Provider for ConnectorHub.
Loads and registers 332 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://open.feishu.cn/open-apis"

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
    "add_chat_members": [
        "POST",
        "/chat_members",
        [],
        [
            "chatId",
            "memberIdType",
            "memberIds"
        ]
    ],
    "add_drive_permission": [
        "POST",
        "/drive_permission",
        [],
        [
            "token",
            "resourceType",
            "memberId",
            "memberType",
            "permission",
            "permType",
            "memberKind",
            "needNotification"
        ]
    ],
    "add_message_reaction": [
        "POST",
        "/message_reaction",
        [],
        [
            "messageId",
            "emojiType"
        ]
    ],
    "add_task_comment": [
        "POST",
        "/task_comment",
        [],
        [
            "taskGuid",
            "content",
            "userIdType"
        ]
    ],
    "add_task_to_tasklist": [
        "POST",
        "/task_to_tasklist",
        [],
        [
            "taskGuid",
            "tasklistGuid",
            "userIdType"
        ]
    ],
    "add_wiki_member": [
        "POST",
        "/wiki_member",
        [],
        [
            "spaceId",
            "memberId",
            "memberType",
            "memberRole",
            "notify"
        ]
    ],
    "arrange_base_dashboard": [
        "GET",
        "/arrange_base_dashboard",
        [],
        [
            "baseToken",
            "dashboardId",
            "userIdType"
        ]
    ],
    "batch_create_base_records": [
        "POST",
        "/batch_create_base_records",
        [],
        [
            "appToken",
            "tableId",
            "records",
            "userIdType"
        ]
    ],
    "batch_create_okrs": [
        "POST",
        "/batch_create_okrs",
        [],
        [
            "cycleId",
            "objectives",
            "rollbackOnFailure",
            "userIdType"
        ]
    ],
    "batch_delete_base_records": [
        "DELETE",
        "/batch_delete_base_records",
        [],
        [
            "appToken",
            "tableId",
            "recordIds"
        ]
    ],
    "batch_get_messages": [
        "GET",
        "/batch_get_messages",
        [],
        [
            "messageIds"
        ]
    ],
    "batch_update_base_records": [
        "PATCH",
        "/batch_update_base_records",
        [],
        [
            "appToken",
            "tableId",
            "records",
            "userIdType"
        ]
    ],
    "batch_update_sheet": [
        "PATCH",
        "/batch_update_sheet",
        [],
        [
            "spreadsheetToken",
            "operations",
            "continueOnError"
        ]
    ],
    "clear_cells": [
        "GET",
        "/clear_cells",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "clearType"
        ]
    ],
    "complete_task": [
        "GET",
        "/complete_task",
        [],
        [
            "taskGuid",
            "userIdType"
        ]
    ],
    "copy_base": [
        "GET",
        "/copy_base",
        [],
        [
            "appToken",
            "name",
            "folderToken",
            "withoutContent",
            "timeZone"
        ]
    ],
    "copy_drive_file": [
        "GET",
        "/copy_drive_file",
        [],
        [
            "fileToken",
            "type",
            "name",
            "folderToken",
            "userIdType"
        ]
    ],
    "copy_sheet_range": [
        "GET",
        "/copy_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "sourceRange",
            "targetRange",
            "targetSheetId",
            "pasteType"
        ]
    ],
    "copy_wiki_node": [
        "GET",
        "/copy_wiki_node",
        [],
        [
            "spaceId",
            "nodeToken",
            "targetSpaceId",
            "targetParentToken",
            "title"
        ]
    ],
    "create_app_slash_command": [
        "POST",
        "/app_slash_command",
        [],
        [
            "command",
            "description",
            "descriptionI18n",
            "iconKey",
            "force"
        ]
    ],
    "create_base": [
        "POST",
        "/base",
        [],
        [
            "name",
            "folderToken",
            "timeZone",
            "initialTable"
        ]
    ],
    "create_base_block": [
        "POST",
        "/base_block",
        [],
        [
            "baseToken",
            "type",
            "name",
            "parentId"
        ]
    ],
    "create_base_dashboard": [
        "POST",
        "/base_dashboard",
        [],
        [
            "baseToken",
            "name",
            "themeStyle"
        ]
    ],
    "create_base_dashboard_block": [
        "POST",
        "/base_dashboard_block",
        [],
        [
            "baseToken",
            "dashboardId",
            "name",
            "type",
            "dataConfig",
            "userIdType"
        ]
    ],
    "create_base_field": [
        "POST",
        "/base_field",
        [],
        [
            "appToken",
            "tableId",
            "field"
        ]
    ],
    "create_base_form": [
        "POST",
        "/base_form",
        [],
        [
            "baseToken",
            "tableId",
            "name",
            "description"
        ]
    ],
    "create_base_form_questions": [
        "POST",
        "/base_form_questions",
        [],
        [
            "baseToken",
            "tableId",
            "formId",
            "questions"
        ]
    ],
    "create_base_record": [
        "POST",
        "/base_record",
        [],
        [
            "appToken",
            "tableId",
            "fields",
            "userIdType"
        ]
    ],
    "create_base_record_share_links": [
        "POST",
        "/base_record_share_links",
        [],
        [
            "baseToken",
            "tableId",
            "recordIds"
        ]
    ],
    "create_base_role": [
        "POST",
        "/base_role",
        [],
        [
            "baseToken",
            "role"
        ]
    ],
    "create_base_table": [
        "POST",
        "/base_table",
        [],
        [
            "appToken",
            "name",
            "fields"
        ]
    ],
    "create_base_views": [
        "POST",
        "/base_views",
        [],
        [
            "appToken",
            "tableId",
            "views"
        ]
    ],
    "create_base_workflow": [
        "POST",
        "/base_workflow",
        [],
        [
            "baseToken",
            "workflow"
        ]
    ],
    "create_calendar_event": [
        "POST",
        "/calendar_event",
        [],
        [
            "calendarId",
            "summary",
            "description",
            "startTime",
            "endTime",
            "timezone",
            "isAllDay",
            "visibility",
            "attendeeAbility",
            "freeBusyStatus",
            "location",
            "recurrence",
            "reminders",
            "attendees",
            "notifyAttendees"
        ]
    ],
    "create_chat": [
        "POST",
        "/chat",
        [],
        [
            "name",
            "description",
            "ownerId",
            "userIdType",
            "userIds",
            "botIds",
            "chatMode",
            "chatType",
            "external"
        ]
    ],
    "create_document": [
        "POST",
        "/document",
        [],
        [
            "content",
            "title",
            "format",
            "parentToken",
            "parentPosition",
            "referenceMap"
        ]
    ],
    "create_drive_comment": [
        "POST",
        "/drive_comment",
        [],
        [
            "fileToken",
            "fileType",
            "replyElements",
            "anchor"
        ]
    ],
    "create_drive_comment_reply": [
        "POST",
        "/drive_comment_reply",
        [],
        [
            "fileToken",
            "fileType",
            "commentId",
            "replyElements"
        ]
    ],
    "create_drive_folder": [
        "POST",
        "/drive_folder",
        [],
        [
            "name",
            "folderToken"
        ]
    ],
    "create_drive_shortcut": [
        "POST",
        "/drive_shortcut",
        [],
        [
            "fileToken",
            "type",
            "folderToken"
        ]
    ],
    "create_mail_template": [
        "POST",
        "/mail_template",
        [],
        [
            "mailboxId",
            "name",
            "subject",
            "templateContent",
            "isPlainText",
            "to",
            "cc",
            "bcc",
            "attachments"
        ]
    ],
    "create_markdown_file": [
        "POST",
        "/markdown_file",
        [],
        [
            "fileName",
            "markdown",
            "folderToken",
            "wikiToken"
        ]
    ],
    "create_okr": [
        "POST",
        "/okr",
        [],
        [
            "targetType",
            "parentId",
            "text",
            "mentions",
            "notes",
            "notesMentions",
            "categoryId",
            "userIdType"
        ]
    ],
    "create_okr_alignment": [
        "POST",
        "/okr_alignment",
        [],
        [
            "objectiveId",
            "toObjectiveId"
        ]
    ],
    "create_okr_progress": [
        "POST",
        "/okr_progress",
        [],
        [
            "targetType",
            "targetId",
            "content",
            "percent",
            "status",
            "sourceTitle",
            "sourceUrl",
            "userIdType"
        ]
    ],
    "create_sheet": [
        "POST",
        "/sheet",
        [],
        [
            "spreadsheetToken",
            "title",
            "index",
            "rowCount",
            "columnCount"
        ]
    ],
    "create_sheet_chart": [
        "POST",
        "/sheet_chart",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_conditional_format": [
        "POST",
        "/sheet_conditional_format",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_filter": [
        "POST",
        "/sheet_filter",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_filter_view": [
        "POST",
        "/sheet_filter_view",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_float_image": [
        "POST",
        "/sheet_float_image",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_pivot_table": [
        "POST",
        "/sheet_pivot_table",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_sheet_sparkline": [
        "POST",
        "/sheet_sparkline",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "properties"
        ]
    ],
    "create_slide": [
        "POST",
        "/slide",
        [],
        [
            "presentationToken",
            "presentationType",
            "content",
            "beforeSlideId",
            "revisionId"
        ]
    ],
    "create_slides_presentation": [
        "POST",
        "/slides_presentation",
        [],
        [
            "title",
            "slides"
        ]
    ],
    "create_task": [
        "POST",
        "/task",
        [],
        [
            "summary",
            "description",
            "start",
            "due",
            "members",
            "tasklistGuids",
            "reminderOffsetsMinutes",
            "clientToken",
            "userIdType"
        ]
    ],
    "create_tasklist": [
        "POST",
        "/tasklist",
        [],
        [
            "name",
            "members",
            "userIdType"
        ]
    ],
    "create_whiteboard_diagram": [
        "POST",
        "/whiteboard_diagram",
        [],
        [
            "whiteboardToken",
            "format",
            "source",
            "overwrite",
            "idempotentToken"
        ]
    ],
    "create_whiteboard_nodes": [
        "POST",
        "/whiteboard_nodes",
        [],
        [
            "whiteboardToken",
            "nodes",
            "overwrite",
            "idempotentToken"
        ]
    ],
    "create_wiki_node": [
        "POST",
        "/wiki_node",
        [],
        [
            "spaceId",
            "objectType",
            "parentNodeToken",
            "nodeType",
            "title",
            "originNodeToken"
        ]
    ],
    "create_workbook": [
        "POST",
        "/workbook",
        [],
        [
            "title",
            "folderToken"
        ]
    ],
    "delete_app_slash_command": [
        "DELETE",
        "/app_slash_command",
        [],
        [
            "commandId",
            "command"
        ]
    ],
    "delete_base_block": [
        "DELETE",
        "/base_block",
        [],
        [
            "baseToken",
            "blockId"
        ]
    ],
    "delete_base_dashboard": [
        "DELETE",
        "/base_dashboard",
        [],
        [
            "baseToken",
            "dashboardId"
        ]
    ],
    "delete_base_dashboard_block": [
        "DELETE",
        "/base_dashboard_block",
        [],
        [
            "baseToken",
            "dashboardId",
            "blockId"
        ]
    ],
    "delete_base_field": [
        "DELETE",
        "/base_field",
        [],
        [
            "appToken",
            "tableId",
            "fieldId"
        ]
    ],
    "delete_base_form": [
        "DELETE",
        "/base_form",
        [],
        [
            "baseToken",
            "tableId",
            "formId"
        ]
    ],
    "delete_base_form_questions": [
        "DELETE",
        "/base_form_questions",
        [],
        [
            "baseToken",
            "tableId",
            "formId",
            "questionIds"
        ]
    ],
    "delete_base_record": [
        "DELETE",
        "/base_record",
        [],
        [
            "appToken",
            "tableId",
            "recordId"
        ]
    ],
    "delete_base_role": [
        "DELETE",
        "/base_role",
        [],
        [
            "baseToken",
            "roleId"
        ]
    ],
    "delete_base_table": [
        "DELETE",
        "/base_table",
        [],
        [
            "appToken",
            "tableId"
        ]
    ],
    "delete_base_view": [
        "DELETE",
        "/base_view",
        [],
        [
            "appToken",
            "tableId",
            "viewId"
        ]
    ],
    "delete_calendar_event": [
        "DELETE",
        "/calendar_event",
        [],
        [
            "calendarId",
            "eventId",
            "notifyAttendees"
        ]
    ],
    "delete_document_cover": [
        "DELETE",
        "/document_cover",
        [],
        [
            "documentId"
        ]
    ],
    "delete_drive_comment": [
        "DELETE",
        "/drive_comment",
        [],
        [
            "fileToken",
            "fileType",
            "commentId"
        ]
    ],
    "delete_drive_comment_reply": [
        "DELETE",
        "/drive_comment_reply",
        [],
        [
            "fileToken",
            "fileType",
            "commentId",
            "replyId"
        ]
    ],
    "delete_drive_item": [
        "DELETE",
        "/drive_item",
        [],
        [
            "fileToken",
            "type"
        ]
    ],
    "delete_drive_version": [
        "DELETE",
        "/drive_version",
        [],
        [
            "fileToken",
            "version"
        ]
    ],
    "delete_okr_alignment": [
        "DELETE",
        "/okr_alignment",
        [],
        [
            "alignmentId"
        ]
    ],
    "delete_okr_progress": [
        "DELETE",
        "/okr_progress",
        [],
        [
            "progressId"
        ]
    ],
    "delete_sheet": [
        "DELETE",
        "/sheet",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName"
        ]
    ],
    "delete_sheet_chart": [
        "DELETE",
        "/sheet_chart",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_conditional_format": [
        "DELETE",
        "/sheet_conditional_format",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_dimension": [
        "DELETE",
        "/sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "groupState"
        ]
    ],
    "delete_sheet_dropdowns": [
        "DELETE",
        "/sheet_dropdowns",
        [],
        [
            "spreadsheetToken",
            "ranges"
        ]
    ],
    "delete_sheet_filter": [
        "DELETE",
        "/sheet_filter",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_filter_view": [
        "DELETE",
        "/sheet_filter_view",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_float_image": [
        "DELETE",
        "/sheet_float_image",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_pivot_table": [
        "DELETE",
        "/sheet_pivot_table",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_sheet_sparkline": [
        "DELETE",
        "/sheet_sparkline",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "delete_slide": [
        "DELETE",
        "/slide",
        [],
        [
            "presentationToken",
            "presentationType",
            "slideId",
            "revisionId"
        ]
    ],
    "delete_wiki_node": [
        "DELETE",
        "/wiki_node",
        [],
        [
            "spaceId",
            "nodeToken",
            "objectType",
            "includeChildren"
        ]
    ],
    "delete_wiki_space": [
        "DELETE",
        "/wiki_space",
        [],
        [
            "spaceId"
        ]
    ],
    "diff_markdown_file": [
        "GET",
        "/diff_markdown_file",
        [],
        [
            "fileToken",
            "fromVersion",
            "toVersion",
            "markdown",
            "contextLines"
        ]
    ],
    "disable_base_advanced_permissions": [
        "GET",
        "/disable_base_advanced_permissions",
        [],
        [
            "baseToken"
        ]
    ],
    "disable_base_workflow": [
        "GET",
        "/disable_base_workflow",
        [],
        [
            "baseToken",
            "workflowId"
        ]
    ],
    "download_base_attachments": [
        "GET",
        "/download_base_attachments",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "fileTokens"
        ]
    ],
    "download_docs_media": [
        "GET",
        "/download_docs_media",
        [],
        [
            "token",
            "type",
            "fileName"
        ]
    ],
    "download_document_cover": [
        "GET",
        "/download_document_cover",
        [],
        [
            "documentId",
            "fileName"
        ]
    ],
    "download_drive_cover": [
        "GET",
        "/download_drive_cover",
        [],
        [
            "fileToken",
            "spec",
            "version",
            "fileName"
        ]
    ],
    "download_drive_export": [
        "GET",
        "/download_drive_export",
        [],
        [
            "fileToken",
            "fileName"
        ]
    ],
    "download_drive_file": [
        "GET",
        "/download_drive_file",
        [],
        [
            "fileToken",
            "fileName"
        ]
    ],
    "download_drive_preview": [
        "GET",
        "/download_drive_preview",
        [],
        [
            "fileToken",
            "previewType",
            "version",
            "fileName"
        ]
    ],
    "download_file": [
        "GET",
        "/download_file",
        [],
        [
            "fileKey",
            "fileName"
        ]
    ],
    "download_image": [
        "GET",
        "/download_image",
        [],
        [
            "imageKey",
            "fileName"
        ]
    ],
    "download_message_resource": [
        "GET",
        "/download_message_resource",
        [],
        [
            "messageId",
            "fileKey",
            "type",
            "fileName"
        ]
    ],
    "download_minutes_media": [
        "GET",
        "/download_minutes_media",
        [],
        [
            "minuteToken",
            "fileName"
        ]
    ],
    "edit_message": [
        "PATCH",
        "/edit_message",
        [],
        [
            "messageId",
            "msgType",
            "content"
        ]
    ],
    "enable_base_advanced_permissions": [
        "GET",
        "/enable_base_advanced_permissions",
        [],
        [
            "baseToken"
        ]
    ],
    "enable_base_workflow": [
        "GET",
        "/enable_base_workflow",
        [],
        [
            "baseToken",
            "workflowId"
        ]
    ],
    "export_whiteboard_svg": [
        "GET",
        "/export_whiteboard_svg",
        [],
        [
            "whiteboardToken"
        ]
    ],
    "fetch_document": [
        "GET",
        "/fetch_document",
        [],
        [
            "documentId",
            "format",
            "detail",
            "lang",
            "revisionId",
            "scope",
            "startBlockId",
            "endBlockId",
            "keyword",
            "contextBefore",
            "contextAfter",
            "maxDepth"
        ]
    ],
    "fetch_markdown_file": [
        "GET",
        "/fetch_markdown_file",
        [],
        [
            "fileToken",
            "version"
        ]
    ],
    "fill_sheet_range": [
        "GET",
        "/fill_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "sourceRange",
            "targetRange",
            "seriesType"
        ]
    ],
    "find_calendar_rooms": [
        "GET",
        "/find_calendar_rooms",
        [],
        [
            "timeSlots",
            "attendeeUserIds",
            "attendeeChatIds",
            "city",
            "building",
            "floor",
            "roomName",
            "minCapacity",
            "maxCapacity",
            "timezone",
            "recurrence"
        ]
    ],
    "freeze_sheet_dimension": [
        "GET",
        "/freeze_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "dimension",
            "count"
        ]
    ],
    "get_app_info": [
        "GET",
        "/app_info",
        [],
        []
    ],
    "get_app_permissions": [
        "GET",
        "/app_permissions",
        [],
        []
    ],
    "get_base": [
        "GET",
        "/base",
        [],
        [
            "appToken"
        ]
    ],
    "get_base_dashboard": [
        "GET",
        "/base_dashboard",
        [],
        [
            "baseToken",
            "dashboardId"
        ]
    ],
    "get_base_dashboard_block": [
        "GET",
        "/base_dashboard_block",
        [],
        [
            "baseToken",
            "dashboardId",
            "blockId",
            "userIdType"
        ]
    ],
    "get_base_dashboard_block_data": [
        "GET",
        "/base_dashboard_block_data",
        [],
        [
            "baseToken",
            "blockId"
        ]
    ],
    "get_base_field": [
        "GET",
        "/base_field",
        [],
        [
            "appToken",
            "tableId",
            "fieldId"
        ]
    ],
    "get_base_form": [
        "GET",
        "/base_form",
        [],
        [
            "baseToken",
            "tableId",
            "formId"
        ]
    ],
    "get_base_form_detail": [
        "GET",
        "/base_form_detail",
        [],
        [
            "shareToken"
        ]
    ],
    "get_base_record": [
        "GET",
        "/base_record",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "selectFields",
            "userIdType"
        ]
    ],
    "get_base_role": [
        "GET",
        "/base_role",
        [],
        [
            "baseToken",
            "roleId"
        ]
    ],
    "get_base_table": [
        "GET",
        "/base_table",
        [],
        [
            "appToken",
            "tableId"
        ]
    ],
    "get_base_view": [
        "GET",
        "/base_view",
        [],
        [
            "appToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_card": [
        "GET",
        "/base_view_card",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_filter": [
        "GET",
        "/base_view_filter",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_group": [
        "GET",
        "/base_view_group",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_sort": [
        "GET",
        "/base_view_sort",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_timebar": [
        "GET",
        "/base_view_timebar",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_view_visible_fields": [
        "GET",
        "/base_view_visible_fields",
        [],
        [
            "baseToken",
            "tableId",
            "viewId"
        ]
    ],
    "get_base_workflow": [
        "GET",
        "/base_workflow",
        [],
        [
            "baseToken",
            "workflowId",
            "userIdType"
        ]
    ],
    "get_calendar_event": [
        "GET",
        "/calendar_event",
        [],
        [
            "calendarId",
            "eventId"
        ]
    ],
    "get_cells": [
        "GET",
        "/cells",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "ranges",
            "includeStyles",
            "renderFormulas",
            "skipHidden",
            "maxCharacters"
        ]
    ],
    "get_chat": [
        "GET",
        "/chat",
        [],
        [
            "chatId",
            "userIdType"
        ]
    ],
    "get_document_revert_status": [
        "GET",
        "/document_revert_status",
        [],
        [
            "documentId",
            "taskId"
        ]
    ],
    "get_drive_export": [
        "GET",
        "/drive_export",
        [],
        [
            "exportHandle",
            "ticket",
            "sourceToken"
        ]
    ],
    "get_drive_import": [
        "GET",
        "/drive_import",
        [],
        [
            "ticket"
        ]
    ],
    "get_drive_task_status": [
        "GET",
        "/drive_task_status",
        [],
        [
            "taskId"
        ]
    ],
    "get_drive_version": [
        "GET",
        "/drive_version",
        [],
        [
            "fileToken",
            "version",
            "fileName"
        ]
    ],
    "get_mail_message": [
        "GET",
        "/mail_message",
        [],
        [
            "mailboxId",
            "messageId",
            "includeHtml"
        ]
    ],
    "get_mail_recall_detail": [
        "GET",
        "/mail_recall_detail",
        [],
        [
            "mailboxId",
            "messageId"
        ]
    ],
    "get_mail_thread": [
        "GET",
        "/mail_thread",
        [],
        [
            "mailboxId",
            "threadId",
            "includeHtml",
            "includeSpamTrash"
        ]
    ],
    "get_message": [
        "GET",
        "/message",
        [],
        [
            "messageId",
            "userIdType",
            "cardMsgContentType"
        ]
    ],
    "get_message_read_users": [
        "GET",
        "/message_read_users",
        [],
        [
            "messageId",
            "userIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "get_okr_comment": [
        "GET",
        "/okr_comment",
        [],
        [
            "commentId",
            "userIdType"
        ]
    ],
    "get_okr_cycle_detail": [
        "GET",
        "/okr_cycle_detail",
        [],
        [
            "cycleId",
            "userIdType"
        ]
    ],
    "get_okr_progress": [
        "GET",
        "/okr_progress",
        [],
        [
            "progressId",
            "userIdType"
        ]
    ],
    "get_sheet": [
        "GET",
        "/sheet",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName"
        ]
    ],
    "get_sheet_changeset": [
        "POST",
        "/sheet_changeset",
        [],
        [
            "spreadsheetToken",
            "startRevision",
            "endRevision"
        ]
    ],
    "get_sheet_dropdown": [
        "GET",
        "/sheet_dropdown",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range"
        ]
    ],
    "get_sheet_history_revert_status": [
        "GET",
        "/sheet_history_revert_status",
        [],
        [
            "spreadsheetToken",
            "transactionId"
        ]
    ],
    "get_slide": [
        "GET",
        "/slide",
        [],
        [
            "presentationToken",
            "presentationType",
            "slideId",
            "slideNumber",
            "revisionId"
        ]
    ],
    "get_slides_presentation": [
        "GET",
        "/slides_presentation",
        [],
        [
            "presentationToken",
            "presentationType",
            "revisionId",
            "removeAttributeIds"
        ]
    ],
    "get_slides_revert_status": [
        "GET",
        "/slides_revert_status",
        [],
        [
            "presentationToken",
            "presentationType",
            "taskId"
        ]
    ],
    "get_slides_screenshots": [
        "GET",
        "/slides_screenshots",
        [],
        [
            "presentationToken",
            "slideIds",
            "slideNumbers"
        ]
    ],
    "get_task": [
        "GET",
        "/task",
        [],
        [
            "taskGuid",
            "userIdType"
        ]
    ],
    "get_typed_table": [
        "GET",
        "/typed_table",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "noHeader"
        ]
    ],
    "get_user": [
        "GET",
        "/user",
        [],
        [
            "userId",
            "userIdType"
        ]
    ],
    "get_wiki_node": [
        "GET",
        "/wiki_node",
        [],
        [
            "token",
            "objectType"
        ]
    ],
    "get_wiki_space": [
        "GET",
        "/wiki_space",
        [],
        [
            "spaceId"
        ]
    ],
    "get_wiki_task": [
        "GET",
        "/wiki_task",
        [],
        [
            "taskId",
            "taskType"
        ]
    ],
    "get_workbook": [
        "GET",
        "/workbook",
        [],
        [
            "spreadsheetToken"
        ]
    ],
    "group_sheet_dimension": [
        "GET",
        "/group_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "groupState"
        ]
    ],
    "hide_sheet_dimension": [
        "GET",
        "/hide_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "groupState"
        ]
    ],
    "insert_docs_media": [
        "GET",
        "/insert_docs_media",
        [],
        [
            "documentId",
            "fileUrl",
            "fileName",
            "type",
            "align",
            "caption",
            "width",
            "height",
            "fileView"
        ]
    ],
    "insert_sheet_dimension": [
        "GET",
        "/insert_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "position",
            "count",
            "inheritStyle"
        ]
    ],
    "inspect_drive_item": [
        "GET",
        "/inspect_drive_item",
        [],
        [
            "token",
            "type"
        ]
    ],
    "join_vc_meeting": [
        "GET",
        "/join_vc_meeting",
        [],
        [
            "meetingNumber",
            "password",
            "callId"
        ]
    ],
    "leave_vc_meeting": [
        "GET",
        "/leave_vc_meeting",
        [],
        [
            "meetingId"
        ]
    ],
    "list_active_vc_meetings": [
        "GET",
        "/active_vc_meetings",
        [],
        [
            "userId"
        ]
    ],
    "list_app_slash_commands": [
        "GET",
        "/app_slash_commands",
        [],
        []
    ],
    "list_base_blocks": [
        "GET",
        "/base_blocks",
        [],
        [
            "baseToken",
            "parentId",
            "type"
        ]
    ],
    "list_base_dashboard_blocks": [
        "GET",
        "/base_dashboard_blocks",
        [],
        [
            "baseToken",
            "dashboardId",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_base_dashboards": [
        "GET",
        "/base_dashboards",
        [],
        [
            "baseToken",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_base_fields": [
        "GET",
        "/base_fields",
        [],
        [
            "appToken",
            "tableId",
            "offset",
            "limit"
        ]
    ],
    "list_base_form_questions": [
        "GET",
        "/base_form_questions",
        [],
        [
            "baseToken",
            "tableId",
            "formId"
        ]
    ],
    "list_base_forms": [
        "GET",
        "/base_forms",
        [],
        [
            "baseToken",
            "tableId",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_base_record_history": [
        "GET",
        "/base_record_history",
        [],
        [
            "baseToken",
            "tableId",
            "recordId",
            "maxVersion",
            "pageSize"
        ]
    ],
    "list_base_records": [
        "GET",
        "/base_records",
        [],
        [
            "appToken",
            "tableId",
            "viewId",
            "fieldIds",
            "filter",
            "sort",
            "userIdType",
            "offset",
            "limit"
        ]
    ],
    "list_base_roles": [
        "GET",
        "/base_roles",
        [],
        [
            "baseToken"
        ]
    ],
    "list_base_tables": [
        "GET",
        "/base_tables",
        [],
        [
            "appToken",
            "offset",
            "limit"
        ]
    ],
    "list_base_views": [
        "GET",
        "/base_views",
        [],
        [
            "appToken",
            "tableId",
            "offset",
            "limit"
        ]
    ],
    "list_base_workflows": [
        "GET",
        "/base_workflows",
        [],
        [
            "baseToken",
            "status",
            "pageSize"
        ]
    ],
    "list_calendar_agenda": [
        "GET",
        "/calendar_agenda",
        [],
        [
            "calendarId",
            "startTime",
            "endTime"
        ]
    ],
    "list_chat_members": [
        "GET",
        "/chat_members",
        [],
        [
            "chatId",
            "memberIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_chats": [
        "GET",
        "/chats",
        [],
        [
            "userIdType",
            "sortType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_department_users": [
        "GET",
        "/department_users",
        [],
        [
            "departmentId",
            "departmentIdType",
            "userIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_departments": [
        "GET",
        "/departments",
        [],
        [
            "departmentId",
            "departmentIdType",
            "userIdType",
            "fetchChild",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_document_history": [
        "GET",
        "/document_history",
        [],
        [
            "documentId",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_drive_comments": [
        "GET",
        "/drive_comments",
        [],
        [
            "fileToken",
            "fileType",
            "solved",
            "whole",
            "needReaction",
            "needRelation",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_drive_files": [
        "GET",
        "/drive_files",
        [],
        [
            "folderToken",
            "pageSize",
            "pageToken",
            "orderBy",
            "direction"
        ]
    ],
    "list_drive_permissions": [
        "GET",
        "/drive_permissions",
        [],
        [
            "token",
            "resourceType",
            "fields",
            "permType"
        ]
    ],
    "list_drive_previews": [
        "GET",
        "/drive_previews",
        [],
        [
            "fileToken",
            "version"
        ]
    ],
    "list_drive_versions": [
        "GET",
        "/drive_versions",
        [],
        [
            "fileToken",
            "pageSize",
            "cursor"
        ]
    ],
    "list_mail_messages": [
        "GET",
        "/mail_messages",
        [],
        [
            "mailboxId",
            "folderId",
            "labelId",
            "onlyUnread",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_message_reactions": [
        "GET",
        "/message_reactions",
        [],
        [
            "messageId",
            "reactionType",
            "pageSize",
            "pageToken",
            "userIdType"
        ]
    ],
    "list_messages": [
        "GET",
        "/messages",
        [],
        [
            "containerIdType",
            "containerId",
            "startTime",
            "endTime",
            "sortType",
            "pageSize",
            "pageToken",
            "cardMsgContentType"
        ]
    ],
    "list_okr_alignments": [
        "GET",
        "/okr_alignments",
        [],
        [
            "objectiveId",
            "alignType",
            "userIdType",
            "departmentIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_okr_categories": [
        "GET",
        "/okr_categories",
        [],
        [
            "ownerType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_okr_comments": [
        "GET",
        "/okr_comments",
        [],
        [
            "targetType",
            "targetId",
            "pageSize",
            "pageToken",
            "userIdType"
        ]
    ],
    "list_okr_cycles": [
        "GET",
        "/okr_cycles",
        [],
        [
            "userId",
            "userIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_okr_progress": [
        "GET",
        "/okr_progress",
        [],
        [
            "targetType",
            "targetId",
            "userIdType",
            "departmentIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_pins": [
        "GET",
        "/pins",
        [],
        [
            "chatId",
            "startTime",
            "endTime",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_sheet_charts": [
        "GET",
        "/sheet_charts",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_sheet_conditional_formats": [
        "GET",
        "/sheet_conditional_formats",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_sheet_filter_views": [
        "GET",
        "/sheet_filter_views",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_sheet_filters": [
        "GET",
        "/sheet_filters",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName"
        ]
    ],
    "list_sheet_float_images": [
        "GET",
        "/sheet_float_images",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_sheet_history": [
        "GET",
        "/sheet_history",
        [],
        [
            "spreadsheetToken",
            "endVersion"
        ]
    ],
    "list_sheet_pivot_tables": [
        "GET",
        "/sheet_pivot_tables",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_sheet_sparklines": [
        "GET",
        "/sheet_sparklines",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId"
        ]
    ],
    "list_slides_history": [
        "GET",
        "/slides_history",
        [],
        [
            "presentationToken",
            "presentationType",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_thread_messages": [
        "GET",
        "/thread_messages",
        [],
        [
            "threadId",
            "startTime",
            "endTime",
            "pageSize",
            "pageToken",
            "sortType"
        ]
    ],
    "list_vc_meeting_events": [
        "GET",
        "/vc_meeting_events",
        [],
        [
            "meetingId",
            "startTime",
            "endTime",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_whiteboard_nodes": [
        "GET",
        "/whiteboard_nodes",
        [],
        [
            "whiteboardToken"
        ]
    ],
    "list_wiki_members": [
        "GET",
        "/wiki_members",
        [],
        [
            "spaceId",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_wiki_nodes": [
        "GET",
        "/wiki_nodes",
        [],
        [
            "spaceId",
            "parentNodeToken",
            "pageSize",
            "pageToken"
        ]
    ],
    "list_wiki_spaces": [
        "GET",
        "/wiki_spaces",
        [],
        [
            "pageSize",
            "pageToken"
        ]
    ],
    "manage_task_assignees": [
        "GET",
        "/manage_task_assignees",
        [],
        [
            "taskGuid",
            "operation",
            "assigneeIds",
            "clientToken",
            "userIdType"
        ]
    ],
    "manage_task_followers": [
        "GET",
        "/manage_task_followers",
        [],
        [
            "taskGuid",
            "operation",
            "followerIds",
            "clientToken",
            "userIdType"
        ]
    ],
    "manage_task_reminders": [
        "GET",
        "/manage_task_reminders",
        [],
        [
            "taskGuid",
            "operation",
            "offsetsMinutes",
            "reminderIds",
            "userIdType"
        ]
    ],
    "manage_tasklist_members": [
        "GET",
        "/manage_tasklist_members",
        [],
        [
            "tasklistGuid",
            "operation",
            "members",
            "userIdType"
        ]
    ],
    "merge_sheet_range": [
        "GET",
        "/merge_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "mergeType"
        ]
    ],
    "move_base_block": [
        "GET",
        "/move_base_block",
        [],
        [
            "baseToken",
            "blockId",
            "parentId",
            "beforeId",
            "afterId"
        ]
    ],
    "move_drive_item": [
        "GET",
        "/move_drive_item",
        [],
        [
            "fileToken",
            "type",
            "folderToken"
        ]
    ],
    "move_sheet_dimension": [
        "GET",
        "/move_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sourceRange",
            "target"
        ]
    ],
    "move_sheet_range": [
        "GET",
        "/move_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "sourceRange",
            "targetRange",
            "targetSheetId",
            "pasteType"
        ]
    ],
    "move_wiki_node": [
        "GET",
        "/move_wiki_node",
        [],
        [
            "spaceId",
            "nodeToken",
            "targetSpaceId",
            "targetParentToken"
        ]
    ],
    "overwrite_markdown_file": [
        "GET",
        "/overwrite_markdown_file",
        [],
        [
            "fileToken",
            "markdown",
            "fileName"
        ]
    ],
    "patch_markdown_file": [
        "PATCH",
        "/patch_markdown_file",
        [],
        [
            "fileToken",
            "pattern",
            "replacement",
            "regex",
            "fileName"
        ]
    ],
    "patch_okr": [
        "PATCH",
        "/patch_okr",
        [],
        [
            "targetType",
            "targetId",
            "text",
            "mentions",
            "notes",
            "score",
            "deadline",
            "userIdType"
        ]
    ],
    "pin_message": [
        "GET",
        "/pin_message",
        [],
        [
            "messageId"
        ]
    ],
    "preview_docs_media": [
        "GET",
        "/preview_docs_media",
        [],
        [
            "token",
            "fileName"
        ]
    ],
    "put_typed_table": [
        "GET",
        "/put_typed_table",
        [],
        [
            "spreadsheetToken",
            "table"
        ]
    ],
    "query_base_data": [
        "GET",
        "/query_base_data",
        [],
        [
            "appToken",
            "dsl"
        ]
    ],
    "query_calendar_freebusy": [
        "GET",
        "/query_calendar_freebusy",
        [],
        [
            "userId",
            "userIdType",
            "startTime",
            "endTime",
            "includeRsvpStatus"
        ]
    ],
    "recall_message": [
        "GET",
        "/recall_message",
        [],
        [
            "messageId"
        ]
    ],
    "recall_sent_mail": [
        "GET",
        "/recall_sent_mail",
        [],
        [
            "mailboxId",
            "messageId"
        ]
    ],
    "remove_base_attachments": [
        "DELETE",
        "/base_attachments",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "fieldId",
            "fileTokens"
        ]
    ],
    "remove_chat_members": [
        "DELETE",
        "/chat_members",
        [],
        [
            "chatId",
            "memberIdType",
            "memberIds"
        ]
    ],
    "remove_drive_permission": [
        "DELETE",
        "/drive_permission",
        [],
        [
            "token",
            "resourceType",
            "memberId",
            "memberType",
            "permType"
        ]
    ],
    "remove_message_reaction": [
        "DELETE",
        "/message_reaction",
        [],
        [
            "messageId",
            "reactionId"
        ]
    ],
    "remove_pin": [
        "DELETE",
        "/pin",
        [],
        [
            "messageId"
        ]
    ],
    "remove_wiki_member": [
        "DELETE",
        "/wiki_member",
        [],
        [
            "spaceId",
            "memberId",
            "memberType",
            "memberRole"
        ]
    ],
    "rename_base_block": [
        "GET",
        "/rename_base_block",
        [],
        [
            "baseToken",
            "blockId",
            "name"
        ]
    ],
    "rename_base_view": [
        "GET",
        "/rename_base_view",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "name"
        ]
    ],
    "render_slide_screenshot": [
        "GET",
        "/render_slide_screenshot",
        [],
        [
            "content",
            "fileName"
        ]
    ],
    "reopen_task": [
        "GET",
        "/reopen_task",
        [],
        [
            "taskGuid",
            "userIdType"
        ]
    ],
    "reorder_okrs": [
        "GET",
        "/reorder_okrs",
        [],
        [
            "targetType",
            "parentId",
            "orderedIds"
        ]
    ],
    "replace_cells": [
        "GET",
        "/replace_cells",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "searchTerm",
            "replacement",
            "range",
            "options"
        ]
    ],
    "replace_slide_elements": [
        "GET",
        "/replace_slide_elements",
        [],
        [
            "presentationToken",
            "presentationType",
            "slideId",
            "parts",
            "revisionId",
            "transactionId"
        ]
    ],
    "replace_slides": [
        "GET",
        "/replace_slides",
        [],
        [
            "presentationToken",
            "presentationType",
            "pages",
            "revisionId"
        ]
    ],
    "reply_calendar_event": [
        "GET",
        "/reply_calendar_event",
        [],
        [
            "calendarId",
            "eventId",
            "status"
        ]
    ],
    "reply_message": [
        "GET",
        "/reply_message",
        [],
        [
            "messageId",
            "msgType",
            "content",
            "replyInThread",
            "uuid"
        ]
    ],
    "resize_sheet_range": [
        "GET",
        "/resize_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "dimension",
            "range",
            "type",
            "pixels"
        ]
    ],
    "revert_document": [
        "GET",
        "/revert_document",
        [],
        [
            "documentId",
            "historyVersionId",
            "waitTimeoutMs"
        ]
    ],
    "revert_drive_version": [
        "GET",
        "/revert_drive_version",
        [],
        [
            "fileToken",
            "version"
        ]
    ],
    "revert_sheet_history": [
        "GET",
        "/revert_sheet_history",
        [],
        [
            "spreadsheetToken",
            "historyVersionId"
        ]
    ],
    "revert_slides_history": [
        "GET",
        "/revert_slides_history",
        [],
        [
            "presentationToken",
            "presentationType",
            "historyVersionId"
        ]
    ],
    "search_base_field_options": [
        "GET",
        "/search_base_field_options",
        [],
        [
            "appToken",
            "tableId",
            "fieldId",
            "keyword",
            "offset",
            "limit"
        ]
    ],
    "search_base_records": [
        "GET",
        "/search_base_records",
        [],
        [
            "appToken",
            "tableId",
            "keyword",
            "searchFields",
            "selectFields",
            "viewId",
            "filter",
            "sort",
            "userIdType",
            "offset",
            "limit"
        ]
    ],
    "search_cells": [
        "GET",
        "/search_cells",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "searchTerm",
            "range",
            "options",
            "offset",
            "maxMatches"
        ]
    ],
    "search_chats": [
        "GET",
        "/search_chats",
        [],
        [
            "query",
            "userIdType",
            "pageSize",
            "pageToken"
        ]
    ],
    "search_drive_items": [
        "GET",
        "/search_drive_items",
        [],
        [
            "query",
            "docFilter",
            "wikiFilter",
            "pageSize",
            "pageToken"
        ]
    ],
    "send_message": [
        "POST",
        "/send_message",
        [],
        [
            "receiveIdType",
            "receiveId",
            "msgType",
            "content",
            "uuid"
        ]
    ],
    "send_rich_message": [
        "POST",
        "/send_rich_message",
        [],
        [
            "receiveId",
            "receiveIdType",
            "contentKind",
            "text",
            "markdown",
            "imageKey",
            "imageUrl",
            "fileKey",
            "fileUrl",
            "fileName",
            "fileType",
            "videoCoverKey",
            "videoCoverUrl",
            "rawMsgType",
            "rawContent",
            "idempotencyKey"
        ]
    ],
    "send_vc_meeting_message": [
        "POST",
        "/send_vc_meeting_message",
        [],
        [
            "meetingId",
            "messageType",
            "content",
            "uuid"
        ]
    ],
    "set_base_view_card": [
        "POST",
        "/set_base_view_card",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_base_view_filter": [
        "POST",
        "/set_base_view_filter",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_base_view_group": [
        "POST",
        "/set_base_view_group",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_base_view_sort": [
        "POST",
        "/set_base_view_sort",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_base_view_timebar": [
        "POST",
        "/set_base_view_timebar",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_base_view_visible_fields": [
        "POST",
        "/set_base_view_visible_fields",
        [],
        [
            "baseToken",
            "tableId",
            "viewId",
            "config"
        ]
    ],
    "set_cells": [
        "POST",
        "/set_cells",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "cells",
            "allowOverwrite",
            "copyToRange"
        ]
    ],
    "set_sheet_cell_image": [
        "POST",
        "/set_sheet_cell_image",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "imageUrl",
            "fileName",
            "allowOverwrite"
        ]
    ],
    "set_sheet_dropdown": [
        "POST",
        "/set_sheet_dropdown",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "options",
            "sourceRange",
            "colors",
            "multiple",
            "highlight"
        ]
    ],
    "set_task_ancestor": [
        "POST",
        "/set_task_ancestor",
        [],
        [
            "taskGuid",
            "ancestorGuid",
            "userIdType"
        ]
    ],
    "sort_sheet_range": [
        "GET",
        "/sort_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "sortConditions",
            "hasHeader"
        ]
    ],
    "submit_base_form": [
        "POST",
        "/submit_base_form",
        [],
        [
            "shareToken",
            "content"
        ]
    ],
    "submit_drive_export": [
        "POST",
        "/submit_drive_export",
        [],
        [
            "token",
            "type",
            "fileExtension",
            "subId",
            "onlySchema"
        ]
    ],
    "submit_drive_import": [
        "POST",
        "/submit_drive_import",
        [],
        [
            "fileUrl",
            "fileName",
            "fileExtension",
            "type",
            "folderToken",
            "name",
            "targetToken"
        ]
    ],
    "submit_wiki_move_to_drive": [
        "POST",
        "/submit_wiki_move_to_drive",
        [],
        [
            "nodeToken",
            "folderToken"
        ]
    ],
    "suggest_calendar_times": [
        "GET",
        "/suggest_calendar_times",
        [],
        [
            "timeRanges",
            "durationMinutes",
            "attendeeUserIds",
            "attendeeChatIds"
        ]
    ],
    "triage_mail_messages": [
        "GET",
        "/triage_mail_messages",
        [],
        [
            "mailboxId",
            "query",
            "folderId",
            "labelId",
            "folder",
            "label",
            "from",
            "to",
            "cc",
            "bcc",
            "subject",
            "unread",
            "hasAttachment",
            "startTime",
            "endTime",
            "includeLabels",
            "maxResults",
            "pageToken"
        ]
    ],
    "ungroup_sheet_dimension": [
        "GET",
        "/ungroup_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "groupState"
        ]
    ],
    "unhide_sheet_dimension": [
        "GET",
        "/unhide_sheet_dimension",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "groupState"
        ]
    ],
    "unmerge_sheet_range": [
        "GET",
        "/unmerge_sheet_range",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "range",
            "mergeType"
        ]
    ],
    "update_app_slash_command": [
        "PATCH",
        "/app_slash_command",
        [],
        [
            "commandId",
            "command",
            "description",
            "descriptionI18n",
            "iconKey"
        ]
    ],
    "update_base_dashboard": [
        "PATCH",
        "/base_dashboard",
        [],
        [
            "baseToken",
            "dashboardId",
            "name",
            "themeStyle"
        ]
    ],
    "update_base_dashboard_block": [
        "PATCH",
        "/base_dashboard_block",
        [],
        [
            "baseToken",
            "dashboardId",
            "blockId",
            "name",
            "dataConfig",
            "userIdType"
        ]
    ],
    "update_base_field": [
        "PATCH",
        "/base_field",
        [],
        [
            "appToken",
            "tableId",
            "fieldId",
            "field"
        ]
    ],
    "update_base_form": [
        "PATCH",
        "/base_form",
        [],
        [
            "baseToken",
            "tableId",
            "formId",
            "name",
            "description"
        ]
    ],
    "update_base_form_questions": [
        "PATCH",
        "/base_form_questions",
        [],
        [
            "baseToken",
            "tableId",
            "formId",
            "questions"
        ]
    ],
    "update_base_record": [
        "PATCH",
        "/base_record",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "fields",
            "userIdType"
        ]
    ],
    "update_base_role": [
        "PATCH",
        "/base_role",
        [],
        [
            "baseToken",
            "roleId",
            "changes"
        ]
    ],
    "update_base_table": [
        "PATCH",
        "/base_table",
        [],
        [
            "appToken",
            "tableId",
            "name"
        ]
    ],
    "update_base_workflow": [
        "PATCH",
        "/base_workflow",
        [],
        [
            "baseToken",
            "workflowId",
            "workflow"
        ]
    ],
    "update_calendar_event": [
        "PATCH",
        "/calendar_event",
        [],
        [
            "calendarId",
            "eventId",
            "summary",
            "description",
            "startTime",
            "endTime",
            "timezone",
            "isAllDay",
            "visibility",
            "attendeeAbility",
            "freeBusyStatus",
            "location",
            "recurrence",
            "reminders",
            "addAttendees",
            "removeAttendeeIds",
            "notifyAttendees"
        ]
    ],
    "update_chat": [
        "PATCH",
        "/chat",
        [],
        [
            "chatId",
            "name",
            "description",
            "userIdType"
        ]
    ],
    "update_document": [
        "PATCH",
        "/document",
        [],
        [
            "documentId",
            "command",
            "format",
            "content",
            "pattern",
            "blockId",
            "sourceBlockIds",
            "revisionId",
            "referenceMap"
        ]
    ],
    "update_document_cover": [
        "PATCH",
        "/document_cover",
        [],
        [
            "documentId",
            "fileUrl",
            "fileName",
            "offsetRatioX",
            "offsetRatioY"
        ]
    ],
    "update_drive_comment": [
        "PATCH",
        "/drive_comment",
        [],
        [
            "fileToken",
            "fileType",
            "commentId",
            "solved"
        ]
    ],
    "update_drive_permission": [
        "PATCH",
        "/drive_permission",
        [],
        [
            "token",
            "resourceType",
            "memberId",
            "memberType",
            "permission",
            "needNotification"
        ]
    ],
    "update_mail_template": [
        "PATCH",
        "/mail_template",
        [],
        [
            "mailboxId",
            "templateId",
            "name",
            "subject",
            "templateContent",
            "isPlainText",
            "to",
            "cc",
            "bcc",
            "attachments",
            "attachmentsMode"
        ]
    ],
    "update_okr_indicator": [
        "PATCH",
        "/okr_indicator",
        [],
        [
            "targetType",
            "targetId",
            "currentValue"
        ]
    ],
    "update_okr_progress": [
        "PATCH",
        "/okr_progress",
        [],
        [
            "progressId",
            "content",
            "percent",
            "status",
            "userIdType"
        ]
    ],
    "update_okr_weights": [
        "PATCH",
        "/okr_weights",
        [],
        [
            "targetType",
            "parentId",
            "weights"
        ]
    ],
    "update_sheet": [
        "PATCH",
        "/sheet",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "title",
            "index",
            "hidden",
            "tabColor"
        ]
    ],
    "update_sheet_chart": [
        "PATCH",
        "/sheet_chart",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_conditional_format": [
        "PATCH",
        "/sheet_conditional_format",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_dropdowns": [
        "PATCH",
        "/sheet_dropdowns",
        [],
        [
            "spreadsheetToken",
            "ranges",
            "validation"
        ]
    ],
    "update_sheet_filter": [
        "PATCH",
        "/sheet_filter",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_filter_view": [
        "PATCH",
        "/sheet_filter_view",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_float_image": [
        "PATCH",
        "/sheet_float_image",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_pivot_table": [
        "PATCH",
        "/sheet_pivot_table",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_sheet_sparkline": [
        "PATCH",
        "/sheet_sparkline",
        [],
        [
            "spreadsheetToken",
            "sheetId",
            "sheetName",
            "objectId",
            "properties"
        ]
    ],
    "update_task": [
        "PATCH",
        "/task",
        [],
        [
            "taskGuid",
            "summary",
            "description",
            "start",
            "due",
            "clearStart",
            "clearDue",
            "userIdType"
        ]
    ],
    "upload_base_attachments": [
        "POST",
        "/upload_base_attachments",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "fieldId",
            "files"
        ]
    ],
    "upload_docs_media": [
        "POST",
        "/upload_docs_media",
        [],
        [
            "fileUrl",
            "fileName",
            "parentType",
            "parentNode",
            "documentId"
        ]
    ],
    "upload_drive_file": [
        "POST",
        "/upload_drive_file",
        [],
        [
            "fileUrl",
            "fileName",
            "folderToken",
            "wikiToken",
            "existingFileToken"
        ]
    ],
    "upload_file": [
        "POST",
        "/upload_file",
        [],
        [
            "fileUrl",
            "fileType",
            "fileName",
            "duration"
        ]
    ],
    "upload_image": [
        "POST",
        "/upload_image",
        [],
        [
            "imageUrl"
        ]
    ],
    "upload_okr_image": [
        "POST",
        "/upload_okr_image",
        [],
        [
            "targetId",
            "targetType",
            "fileUrl",
            "fileName"
        ]
    ],
    "upload_slides_media": [
        "POST",
        "/upload_slides_media",
        [],
        [
            "presentationToken",
            "presentationType",
            "fileUrl",
            "fileName"
        ]
    ],
    "upload_task_attachment": [
        "POST",
        "/upload_task_attachment",
        [],
        [
            "resourceId",
            "resourceType",
            "userIdType",
            "fileUrl",
            "fileName"
        ]
    ],
    "upsert_base_record": [
        "PATCH",
        "/upsert_base_record",
        [],
        [
            "appToken",
            "tableId",
            "recordId",
            "fields",
            "userIdType"
        ]
    ],
    "verify_sheet_formulas": [
        "GET",
        "/verify_sheet_formulas",
        [],
        [
            "spreadsheetToken",
            "sheetIds",
            "sheetNames",
            "ranges",
            "maxLocations"
        ]
    ]
}

class FeishuAppBotDynamicAction(Action):
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
            raise ValueError(f"Feishu App Bot API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class FeishuAppBotProvider(Provider):
    def __init__(self):
        super().__init__(
            service="feishu_app_bot",
            display_name="Feishu App Bot",
            category="Communication & Messaging",
            auth_types=["api_key"],
            description="Feishu App Bot platform with 332 actions for interactive messaging, group bots, chat administration, approvals, and base tables."
        )
        for act in get_provider_actions("feishu_app_bot"):
            self.register_action(FeishuAppBotDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://open.feishu.cn/open-apis/im/v1/chats"
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
            raise ValueError(f"Feishu App Bot connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Feishu App Bot credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Feishu App Bot validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "feishu_app_bot" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Feishu App Bot credentials: {body.get('msg') or resp.text}")
                elif "feishu_app_bot" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Feishu App Bot credentials: {body.get('errmsg') or resp.text}")
                elif "feishu_app_bot" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Feishu App Bot credentials: {body.get('error_msg') or resp.text}")
                elif "feishu_app_bot" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Feishu App Bot credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Feishu App Bot Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Feishu App Bot Account"
        }

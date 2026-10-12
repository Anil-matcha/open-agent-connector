"""
Sunsama MCP Provider for ConnectorHub.
Loads and registers 59 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.sunsama.com"

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
    "accept_meeting_invite": [
        "POST",
        "/mcp",
        [],
        [
            "eventId"
        ]
    ],
    "add_subtasks_to_task": [
        "POST",
        "/mcp",
        [],
        [
            "taskId",
            "subtasks"
        ]
    ],
    "add_task_to_channel": [
        "POST",
        "/mcp",
        [],
        [
            "taskId",
            "channel"
        ]
    ],
    "align_task_with_objective": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "objectiveId"
        ]
    ],
    "append_task_notes": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "notes"
        ]
    ],
    "call_tool": [
        "GET",
        "/mcp",
        [],
        [
            "toolName",
            "arguments"
        ]
    ],
    "change_backlog_folder": [
        "GET",
        "/mcp",
        [],
        [
            "taskIds",
            "folderId"
        ]
    ],
    "create_calendar_event": [
        "POST",
        "/mcp",
        [],
        [
            "title",
            "startDate",
            "startTime",
            "duration",
            "isAllDay",
            "description",
            "calendarId"
        ]
    ],
    "create_channel": [
        "POST",
        "/mcp",
        [],
        [
            "channelName",
            "categoryName",
            "isPersonal"
        ]
    ],
    "create_task": [
        "POST",
        "/mcp",
        [],
        [
            "title",
            "notes",
            "timeEstimate",
            "objectiveId",
            "day",
            "backlog",
            "channel",
            "position",
            "subtasks",
            "recurrenceRule",
            "recurringTaskStartTime",
            "isRecurringTaskStartTimeOnlyAnEstimate",
            "backlogPriority",
            "dailyPriority",
            "integration",
            "integrationUrl"
        ]
    ],
    "create_weekly_objective": [
        "POST",
        "/mcp",
        [],
        [
            "title",
            "weekStartDay",
            "timeEstimate",
            "channel"
        ]
    ],
    "decline_meeting_invite": [
        "POST",
        "/mcp",
        [],
        [
            "eventId"
        ]
    ],
    "delete_all_incomplete_recurring_task_instances": [
        "DELETE",
        "/mcp",
        [],
        [
            "taskId",
            "afterDate"
        ]
    ],
    "delete_calendar_event": [
        "DELETE",
        "/mcp",
        [],
        [
            "eventId"
        ]
    ],
    "delete_channel": [
        "DELETE",
        "/mcp",
        [],
        [
            "channelId"
        ]
    ],
    "delete_task": [
        "DELETE",
        "/mcp",
        [],
        [
            "taskId"
        ]
    ],
    "edit_subtask_title": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId",
            "newTitle"
        ]
    ],
    "edit_task_due_date": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "dueDate"
        ]
    ],
    "edit_task_notes": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "notes"
        ]
    ],
    "edit_task_recurrence_rule": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "recurrenceRule",
            "firstOccurrenceOnOrAfter",
            "deleteOldInstancesAfter",
            "startTime",
            "isStartTimeOnlyAnEstimate"
        ]
    ],
    "edit_task_time_estimate": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId",
            "timeEstimate"
        ]
    ],
    "edit_task_title": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "title"
        ]
    ],
    "get_archived_tasks": [
        "GET",
        "/mcp",
        [],
        [
            "offset"
        ]
    ],
    "get_backlog_tasks": [
        "GET",
        "/mcp",
        [],
        [
            "page",
            "queryId",
            "folderIds"
        ]
    ],
    "get_daily_highlights": [
        "GET",
        "/mcp",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "get_help_article": [
        "GET",
        "/mcp",
        [],
        [
            "articleId"
        ]
    ],
    "get_task_by_id": [
        "GET",
        "/mcp",
        [],
        [
            "taskId"
        ]
    ],
    "get_task_time_estimate": [
        "GET",
        "/mcp",
        [],
        [
            "title"
        ]
    ],
    "import_task_from_calendar_event": [
        "GET",
        "/mcp",
        [],
        [
            "eventId"
        ]
    ],
    "list_help_articles": [
        "GET",
        "/mcp",
        [],
        []
    ],
    "list_resources": [
        "GET",
        "/mcp",
        [],
        []
    ],
    "list_tools": [
        "GET",
        "/mcp",
        [],
        []
    ],
    "mark_subtask_as_completed": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId"
        ]
    ],
    "mark_subtask_as_incomplete": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId"
        ]
    ],
    "mark_task_as_completed": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "finishedDay"
        ]
    ],
    "mark_task_as_incomplete": [
        "GET",
        "/mcp",
        [],
        [
            "taskId"
        ]
    ],
    "move_calendar_event": [
        "GET",
        "/mcp",
        [],
        [
            "eventId",
            "startDate",
            "startTime",
            "duration",
            "isAllDay"
        ]
    ],
    "move_task_from_backlog": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "calendarDay",
            "sortOrder"
        ]
    ],
    "move_task_to_backlog": [
        "GET",
        "/mcp",
        [],
        [
            "taskId"
        ]
    ],
    "move_task_to_day": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "calendarDay",
            "sortOrder"
        ]
    ],
    "read_resource": [
        "GET",
        "/mcp",
        [],
        [
            "uri"
        ]
    ],
    "rename_channel": [
        "GET",
        "/mcp",
        [],
        [
            "channelId",
            "newName"
        ]
    ],
    "reorder_tasks": [
        "GET",
        "/mcp",
        [],
        [
            "taskIds",
            "calendarDay"
        ]
    ],
    "reposition_task_in_backlog": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "timeBucket",
            "position"
        ]
    ],
    "restore_task": [
        "GET",
        "/mcp",
        [],
        [
            "taskId"
        ]
    ],
    "search_channels": [
        "GET",
        "/mcp",
        [],
        [
            "searchText",
            "numResults",
            "isPersonal",
            "isCategory",
            "categoryStreamId"
        ]
    ],
    "search_tasks": [
        "GET",
        "/mcp",
        [],
        [
            "searchTerm"
        ]
    ],
    "set_backlog_priority": [
        "POST",
        "/mcp",
        [],
        [
            "taskId",
            "backlogPriority"
        ]
    ],
    "set_calendar_event_allow_task_projections": [
        "POST",
        "/mcp",
        [],
        [
            "eventId",
            "allowTasksProjectedAtSameTime"
        ]
    ],
    "set_daily_priority": [
        "POST",
        "/mcp",
        [],
        [
            "taskId",
            "dailyPriority"
        ]
    ],
    "set_shutdown_time": [
        "POST",
        "/mcp",
        [],
        [
            "calendarDay",
            "hour",
            "minute",
            "addToTheCalendar"
        ]
    ],
    "start_task_timer": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId"
        ]
    ],
    "stop_task_timer": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "subtaskId"
        ]
    ],
    "timebox_a_task_to_calendar": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "startDate",
            "startTime",
            "duration"
        ]
    ],
    "toggle_auto_import_events": [
        "GET",
        "/mcp",
        [],
        [
            "enabled"
        ]
    ],
    "unarchive_task": [
        "GET",
        "/mcp",
        [],
        [
            "taskId",
            "calendarDay",
            "sortOrder"
        ]
    ],
    "update_all_incomplete_recurring_task_instances": [
        "PATCH",
        "/mcp",
        [],
        [
            "taskId",
            "updateType"
        ]
    ],
    "update_calendar_preferences": [
        "PATCH",
        "/mcp",
        [],
        [
            "calendarId",
            "isDefaultForTasks",
            "isDefaultForEvents",
            "includedInAutoImportingOfEvents"
        ]
    ],
    "update_import_event_filters": [
        "PATCH",
        "/mcp",
        [],
        [
            "excludedEventFilters"
        ]
    ]
}

class SunsamaMcpDynamicAction(Action):
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
            raise ValueError(f"Sunsama MCP API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class SunsamaMcpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sunsama_mcp",
            display_name="Sunsama MCP",
            category="Project Management",
            auth_types=["oauth2", "api_key"],
            description="Sunsama daily planner, tasks, calendar events, channels, and MCP tools with 59 actions."
        )
        for act in get_provider_actions("sunsama_mcp"):
            self.register_action(SunsamaMcpDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.sunsama.com/mcp"
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
            raise ValueError(f"Sunsama MCP connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Sunsama MCP credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Sunsama MCP validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Sunsama MCP Account"
        }

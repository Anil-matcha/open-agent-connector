"""
Mingdao Provider for ConnectorHub.
Loads and registers 47 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.mingdao.com/v3"

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

    auth_mode = "mingdao_auth"
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
    "add_role_members": [
        "POST",
        "/role_members",
        [],
        [
            "roleId",
            "userIds",
            "departmentIds",
            "departmentTreeIds",
            "jobIds",
            "projectOrganizeIds"
        ]
    ],
    "batch_create_custom_actions": [
        "POST",
        "/batch_create_custom_actions",
        [],
        [
            "worksheetId",
            "actions"
        ]
    ],
    "batch_create_records": [
        "POST",
        "/batch_create_records",
        [],
        [
            "worksheetId",
            "triggerWorkflow",
            "rows"
        ]
    ],
    "batch_create_views": [
        "POST",
        "/batch_create_views",
        [],
        [
            "worksheetId",
            "views"
        ]
    ],
    "batch_delete_records": [
        "DELETE",
        "/batch_delete_records",
        [],
        [
            "worksheetId",
            "rowIds",
            "triggerWorkflow",
            "permanent"
        ]
    ],
    "batch_update_records": [
        "PATCH",
        "/batch_update_records",
        [],
        [
            "worksheetId",
            "rowIds",
            "fields",
            "triggerWorkflow"
        ]
    ],
    "create_app_items": [
        "POST",
        "/app_items",
        [],
        [
            "items"
        ]
    ],
    "create_app_sections": [
        "POST",
        "/app_sections",
        [],
        [
            "parentId",
            "sections"
        ]
    ],
    "create_chart": [
        "POST",
        "/chart",
        [],
        [
            "worksheetId",
            "chartName",
            "viewId",
            "chartType",
            "dataScope",
            "timeFieldId",
            "timeRange",
            "customDynamicRange",
            "customRange",
            "dimension",
            "rows",
            "columns",
            "values",
            "rightValues",
            "targetValues",
            "gaugeMin",
            "gaugeMax",
            "mapScope",
            "mapRegionCode",
            "filter",
            "sorts",
            "limit"
        ]
    ],
    "create_chatbot": [
        "POST",
        "/chatbot",
        [],
        [
            "appId",
            "name",
            "sectionId",
            "description",
            "icon",
            "prompt",
            "welcomeMessage",
            "presetQuestions"
        ]
    ],
    "create_optionset": [
        "POST",
        "/optionset",
        [],
        [
            "name",
            "options",
            "enableColor",
            "enableScore"
        ]
    ],
    "create_record": [
        "POST",
        "/record",
        [],
        [
            "worksheetId",
            "fields",
            "triggerWorkflow"
        ]
    ],
    "create_role": [
        "POST",
        "/role",
        [],
        [
            "name",
            "description",
            "hideAppForMembers",
            "type",
            "permissionScope",
            "globalPermissions",
            "worksheetPermissions",
            "pagePermissions"
        ]
    ],
    "create_worksheet": [
        "POST",
        "/worksheet",
        [],
        [
            "name",
            "alias",
            "remark",
            "sectionId",
            "fields"
        ]
    ],
    "delete_record": [
        "DELETE",
        "/record",
        [],
        [
            "worksheetId",
            "rowId",
            "triggerWorkflow",
            "permanent"
        ]
    ],
    "delete_role": [
        "DELETE",
        "/role",
        [],
        [
            "roleId"
        ]
    ],
    "delete_worksheet": [
        "DELETE",
        "/worksheet",
        [],
        [
            "worksheetId"
        ]
    ],
    "disable_optionset": [
        "POST",
        "/disable_optionset",
        [],
        [
            "optionsetId"
        ]
    ],
    "generate_record_share_link": [
        "POST",
        "/generate_record_share_link",
        [],
        [
            "worksheetId",
            "rowId",
            "visibleFields",
            "expiredIn",
            "password"
        ]
    ],
    "get_app": [
        "GET",
        "/app",
        [],
        []
    ],
    "get_approval": [
        "GET",
        "/approval",
        [],
        [
            "worksheetId",
            "rowId",
            "approvalId"
        ]
    ],
    "get_record": [
        "GET",
        "/record",
        [],
        [
            "worksheetId",
            "rowId",
            "responseFormat",
            "includeSystemFields"
        ]
    ],
    "get_related_records": [
        "GET",
        "/related_records",
        [],
        [
            "worksheetId",
            "rowId",
            "field",
            "pageSize",
            "pageIndex",
            "isReturnSystemFields"
        ]
    ],
    "get_role": [
        "GET",
        "/role",
        [],
        [
            "roleId"
        ]
    ],
    "get_workflow": [
        "GET",
        "/workflow",
        [],
        [
            "processId"
        ]
    ],
    "get_worksheet": [
        "GET",
        "/worksheet",
        [],
        [
            "worksheetId",
            "responseFormat"
        ]
    ],
    "list_approvals": [
        "GET",
        "/approvals",
        [],
        [
            "worksheetId",
            "rowId",
            "pageIndex",
            "pageSize",
            "complete"
        ]
    ],
    "list_knowledge": [
        "GET",
        "/knowledge",
        [],
        [
            "knowledgeIds"
        ]
    ],
    "list_optionsets": [
        "POST",
        "/optionsets",
        [],
        []
    ],
    "list_record_discussions": [
        "GET",
        "/record_discussions",
        [],
        [
            "worksheetId",
            "rowId",
            "pageIndex",
            "pageSize",
            "search",
            "onlyWithAttachments",
            "responseFormat"
        ]
    ],
    "list_record_logs": [
        "GET",
        "/record_logs",
        [],
        [
            "worksheetId",
            "rowId",
            "operatorIds",
            "field",
            "pageIndex",
            "pageSize",
            "startDate",
            "endDate"
        ]
    ],
    "list_records": [
        "GET",
        "/records",
        [],
        [
            "worksheetId",
            "responseFormat",
            "pageSize",
            "pageIndex",
            "viewId",
            "fields",
            "filter",
            "sorts",
            "search",
            "tableView",
            "useFieldIdAsKey",
            "includeTotalCount",
            "includeSystemFields"
        ]
    ],
    "list_regions": [
        "GET",
        "/regions",
        [],
        [
            "id",
            "search"
        ]
    ],
    "list_roles": [
        "GET",
        "/roles",
        [],
        []
    ],
    "list_workflows": [
        "GET",
        "/workflows",
        [],
        []
    ],
    "list_worksheets": [
        "GET",
        "/worksheets",
        [],
        [
            "responseFormat",
            "worksheets"
        ]
    ],
    "lookup_departments": [
        "GET",
        "/lookup_departments",
        [],
        [
            "name",
            "orgId"
        ]
    ],
    "lookup_users": [
        "GET",
        "/lookup_users",
        [],
        [
            "name",
            "orgId"
        ]
    ],
    "pivot_records": [
        "GET",
        "/pivot_records",
        [],
        [
            "worksheetId",
            "pageSize",
            "pageIndex",
            "viewId",
            "columns",
            "rows",
            "values",
            "filter",
            "sorts",
            "includeSummary"
        ]
    ],
    "remove_role_members": [
        "DELETE",
        "/role_members",
        [],
        [
            "roleId",
            "userIds",
            "departmentIds",
            "departmentTreeIds",
            "jobIds",
            "orgRoleIds"
        ]
    ],
    "remove_user_from_all_roles": [
        "DELETE",
        "/user_from_all_roles",
        [],
        [
            "userId"
        ]
    ],
    "search_knowledge": [
        "GET",
        "/search_knowledge",
        [],
        [
            "knowledgeIds",
            "query",
            "searchMode",
            "topK",
            "minRelevance",
            "rrfK",
            "filter"
        ]
    ],
    "trigger_workflow": [
        "POST",
        "/trigger_workflow",
        [],
        [
            "processId",
            "parameters"
        ]
    ],
    "update_custom_page": [
        "PATCH",
        "/custom_page",
        [],
        [
            "pageId",
            "components"
        ]
    ],
    "update_optionset": [
        "POST",
        "/optionset",
        [],
        [
            "optionsetId",
            "name",
            "options",
            "enableColor",
            "enableScore"
        ]
    ],
    "update_record": [
        "PATCH",
        "/record",
        [],
        [
            "worksheetId",
            "rowId",
            "fields",
            "triggerWorkflow"
        ]
    ],
    "update_worksheet": [
        "PATCH",
        "/worksheet",
        [],
        [
            "worksheetId",
            "name",
            "alias",
            "remark",
            "sectionId",
            "addFields",
            "editFields",
            "removeFields"
        ]
    ]
}

class MingdaoDynamicAction(Action):
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
            raise ValueError(f"Mingdao API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class MingdaoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="mingdao",
            display_name="Mingdao",
            category="Project Management",
            auth_types=["api_key", "custom_credential"],
            description="Mingdao HAP enterprise no-code application platform records, worksheets, and workflows with 47 actions."
        )
        for act in get_provider_actions("mingdao"):
            self.register_action(MingdaoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.mingdao.com/v3/app"
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
            raise ValueError(f"Mingdao connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Mingdao credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Mingdao validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Mingdao Account"
        }

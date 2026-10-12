"""
n8n Provider for ConnectorHub.
Loads and registers 36 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "{instanceUrl}/api/v1"

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

    auth_mode = "n8n_header"
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
    "activate_workflow": [
        "POST",
        "/workflows/{encodeURIComponent}/activate",
        [
            "encodeURIComponent"
        ],
        [
            "workflowId",
            "versionId",
            "name",
            "description"
        ]
    ],
    "archive_workflow": [
        "POST",
        "/executions",
        [],
        [
            "workflowId"
        ]
    ],
    "create_data_table": [
        "POST",
        "/data-tables",
        [],
        [
            "name",
            "columns",
            "projectId"
        ]
    ],
    "create_data_table_column": [
        "POST",
        "/data-tables/{encodeURIComponent}/columns",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "name",
            "type",
            "index"
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
    "create_variable": [
        "POST",
        "/variables",
        [],
        [
            "key",
            "value",
            "projectId"
        ]
    ],
    "deactivate_workflow": [
        "POST",
        "/executions",
        [],
        [
            "workflowId"
        ]
    ],
    "delete_data_table": [
        "DELETE",
        "/data-tables/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId"
        ]
    ],
    "delete_data_table_column": [
        "DELETE",
        "/data-tables/{encodeURIComponent}/columns/{encodeURIComponent}",
        [
            "encodeURIComponent",
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "columnId"
        ]
    ],
    "delete_tag": [
        "DELETE",
        "/tags/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "tagId"
        ]
    ],
    "delete_variable": [
        "DELETE",
        "/variables/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "variableId"
        ]
    ],
    "get_data_table": [
        "PATCH",
        "/data-tables/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId"
        ]
    ],
    "get_execution": [
        "POST",
        "/executions/{executionId}",
        [
            "executionId"
        ],
        [
            "includeData",
            "redactExecutionData"
        ]
    ],
    "get_execution_tags": [
        "PUT",
        "/executions/{executionId}/tags",
        [
            "executionId"
        ],
        []
    ],
    "get_insights_summary": [
        "GET",
        "/insights/summary",
        [],
        [
            "startDate",
            "endDate",
            "projectId"
        ]
    ],
    "get_workflow": [
        "POST",
        "/workflows/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "workflowId",
            "excludePinnedData"
        ]
    ],
    "get_workflow_tags": [
        "PUT",
        "/workflows/{encodeURIComponent}/tags",
        [
            "encodeURIComponent"
        ],
        [
            "workflowId"
        ]
    ],
    "insert_data_table_rows": [
        "POST",
        "/data-tables/{encodeURIComponent}/rows",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "data",
            "returnType"
        ]
    ],
    "list_data_table_columns": [
        "POST",
        "/data-tables/{encodeURIComponent}/columns",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId"
        ]
    ],
    "list_data_table_rows": [
        "POST",
        "/data-tables/{encodeURIComponent}/rows",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "filter",
            "sortBy",
            "search",
            "limit",
            "cursor"
        ]
    ],
    "list_data_tables": [
        "POST",
        "/data-tables",
        [],
        [
            "filter",
            "sortBy",
            "limit",
            "cursor"
        ]
    ],
    "list_executions": [
        "POST",
        "/executions",
        [],
        [
            "includeData",
            "redactExecutionData",
            "status",
            "workflowId",
            "projectId",
            "limit",
            "cursor"
        ]
    ],
    "list_tags": [
        "POST",
        "/tags",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_variables": [
        "POST",
        "/variables",
        [],
        [
            "projectId",
            "state",
            "limit",
            "cursor"
        ]
    ],
    "list_workflows": [
        "POST",
        "/workflows",
        [],
        [
            "active",
            "tags",
            "name",
            "projectId",
            "excludePinnedData",
            "limit",
            "cursor"
        ]
    ],
    "retry_execution": [
        "POST",
        "/executions/{executionId}/retry",
        [
            "executionId"
        ],
        [
            "loadWorkflow"
        ]
    ],
    "stop_execution": [
        "POST",
        "/executions/{executionId}/stop",
        [
            "executionId"
        ],
        []
    ],
    "unarchive_workflow": [
        "POST",
        "/executions",
        [],
        [
            "workflowId"
        ]
    ],
    "update_data_table": [
        "PATCH",
        "/data-tables/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "name"
        ]
    ],
    "update_data_table_column": [
        "PATCH",
        "/data-tables/{encodeURIComponent}/columns/{encodeURIComponent}",
        [
            "encodeURIComponent",
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "columnId",
            "name",
            "index"
        ]
    ],
    "update_data_table_rows": [
        "PATCH",
        "/data-tables/{encodeURIComponent}/rows/update",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "filter",
            "data",
            "returnData",
            "dryRun"
        ]
    ],
    "update_execution_tags": [
        "PUT",
        "/executions/{executionId}/tags",
        [
            "executionId"
        ],
        [
            "tagIds"
        ]
    ],
    "update_tag": [
        "PUT",
        "/tags/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "tagId",
            "name"
        ]
    ],
    "update_variable": [
        "PUT",
        "/variables/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "variableId",
            "key",
            "value"
        ]
    ],
    "update_workflow_tags": [
        "PUT",
        "/workflows/{encodeURIComponent}/tags",
        [
            "encodeURIComponent"
        ],
        [
            "workflowId",
            "tagIds"
        ]
    ],
    "upsert_data_table_row": [
        "POST",
        "/data-tables/{encodeURIComponent}/rows/upsert",
        [
            "encodeURIComponent"
        ],
        [
            "dataTableId",
            "filter",
            "data",
            "returnData",
            "dryRun"
        ]
    ]
}

class N8nDynamicAction(Action):
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
            raise ValueError(f"n8n API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class N8nProvider(Provider):
    def __init__(self):
        super().__init__(
            service="n8n",
            display_name="n8n",
            category="Project Management",
            auth_types=["api_key"],
            description="n8n fair-code workflow automation, workflows, executions, data tables, and variables with 36 actions."
        )
        for act in get_provider_actions("n8n"):
            self.register_action(N8nDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "{instanceUrl}/api/v1/workflows?limit=1"
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
            raise ValueError(f"n8n connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid n8n credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"n8n validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"n8n Account"
        }

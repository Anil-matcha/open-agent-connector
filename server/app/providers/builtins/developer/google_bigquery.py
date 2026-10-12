"""
Google BigQuery Provider for ConnectorHub.
Loads and registers 32 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://bigquery.googleapis.com/bigquery/v2"

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
    "cancel_job": [
        "POST",
        "/projects/{projectId}/job",
        [
            "projectId"
        ],
        [
            "jobId",
            "location"
        ]
    ],
    "create_dataset": [
        "POST",
        "/projects/{projectId}/dataset",
        [
            "projectId"
        ],
        [
            "datasetId",
            "location",
            "friendlyName",
            "description",
            "labels",
            "defaultTableExpirationMs",
            "defaultPartitionExpirationMs",
            "updateMode"
        ]
    ],
    "create_routine": [
        "POST",
        "/projects/{projectId}/routine",
        [
            "projectId"
        ],
        [
            "datasetId",
            "routineId",
            "routineType",
            "language",
            "definitionBody",
            "description",
            "arguments",
            "returnType",
            "importedLibraries",
            "determinismLevel"
        ]
    ],
    "create_table": [
        "POST",
        "/projects/{projectId}/table",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "schema",
            "friendlyName",
            "description",
            "labels",
            "timePartitioning",
            "rangePartitioning",
            "clustering",
            "view",
            "materializedView",
            "externalDataConfiguration",
            "encryptionConfiguration"
        ]
    ],
    "delete_dataset": [
        "POST",
        "/projects/{projectId}/dataset",
        [
            "projectId"
        ],
        [
            "datasetId",
            "deleteContents"
        ]
    ],
    "delete_model": [
        "DELETE",
        "/projects/{projectId}/model",
        [
            "projectId"
        ],
        [
            "datasetId",
            "modelId"
        ]
    ],
    "delete_routine": [
        "DELETE",
        "/projects/{projectId}/routine",
        [
            "projectId"
        ],
        [
            "datasetId",
            "routineId"
        ]
    ],
    "delete_table": [
        "DELETE",
        "/projects/{projectId}/table",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId"
        ]
    ],
    "get_dataset": [
        "POST",
        "/projects/{projectId}/dataset",
        [
            "projectId"
        ],
        [
            "datasetId",
            "selectedFields"
        ]
    ],
    "get_job": [
        "GET",
        "/projects/{projectId}/job",
        [
            "projectId"
        ],
        [
            "jobId",
            "location"
        ]
    ],
    "get_model": [
        "GET",
        "/projects/{projectId}/model",
        [
            "projectId"
        ],
        [
            "datasetId",
            "modelId"
        ]
    ],
    "get_query_results": [
        "GET",
        "/projects/{projectId}/query_results",
        [
            "projectId"
        ],
        [
            "jobId",
            "location",
            "maxResults",
            "pageToken",
            "startIndex",
            "timeoutMs"
        ]
    ],
    "get_routine": [
        "GET",
        "/projects/{projectId}/routine",
        [
            "projectId"
        ],
        [
            "datasetId",
            "routineId",
            "readMask"
        ]
    ],
    "get_table": [
        "GET",
        "/projects/{projectId}/table",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "selectedFields"
        ]
    ],
    "insert_all": [
        "GET",
        "/projects/{projectId}/insert_all",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "rows",
            "skipInvalidRows",
            "ignoreUnknownValues",
            "templateSuffix"
        ]
    ],
    "list_datasets": [
        "POST",
        "/projects/{projectId}/datasets",
        [
            "projectId"
        ],
        [
            "all",
            "filter",
            "maxResults",
            "pageToken"
        ]
    ],
    "list_jobs": [
        "GET",
        "/projects/{projectId}/jobs",
        [
            "projectId"
        ],
        [
            "allUsers",
            "maxResults",
            "pageToken",
            "projection",
            "stateFilter",
            "minCreationTime",
            "maxCreationTime"
        ]
    ],
    "list_models": [
        "GET",
        "/projects/{projectId}/models",
        [
            "projectId"
        ],
        [
            "datasetId",
            "maxResults",
            "pageToken"
        ]
    ],
    "list_projects": [
        "GET",
        "/projects/{projectId}/projects",
        [
            "projectId"
        ],
        [
            "maxResults",
            "pageToken"
        ]
    ],
    "list_routines": [
        "GET",
        "/projects/{projectId}/routines",
        [
            "projectId"
        ],
        [
            "datasetId",
            "maxResults",
            "pageToken",
            "readMask"
        ]
    ],
    "list_table_data": [
        "GET",
        "/projects/{projectId}/table_data",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "maxResults",
            "pageToken",
            "startIndex",
            "selectedFields"
        ]
    ],
    "list_tables": [
        "GET",
        "/projects/{projectId}/tables",
        [
            "projectId"
        ],
        [
            "datasetId",
            "maxResults",
            "pageToken"
        ]
    ],
    "patch_dataset": [
        "POST",
        "/projects/{projectId}/patch_dataset",
        [
            "projectId"
        ],
        [
            "datasetId",
            "location",
            "friendlyName",
            "description",
            "labels",
            "defaultTableExpirationMs",
            "defaultPartitionExpirationMs",
            "updateMode"
        ]
    ],
    "patch_model": [
        "PATCH",
        "/projects/{projectId}/patch_model",
        [
            "projectId"
        ],
        [
            "datasetId",
            "modelId",
            "friendlyName",
            "description",
            "labels"
        ]
    ],
    "patch_table": [
        "PATCH",
        "/projects/{projectId}/patch_table",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "schema",
            "friendlyName",
            "description",
            "labels",
            "timePartitioning",
            "rangePartitioning",
            "clustering",
            "view",
            "materializedView",
            "externalDataConfiguration",
            "encryptionConfiguration"
        ]
    ],
    "query": [
        "POST",
        "/projects/{projectId}/query",
        [
            "projectId"
        ],
        [
            "query",
            "location",
            "maxResults",
            "dryRun",
            "useLegacySql",
            "timeoutMs",
            "parameterMode",
            "queryParameters"
        ]
    ],
    "start_extract_job_to_gcs": [
        "GET",
        "/projects/{projectId}/start_extract_job_to_gcs",
        [
            "projectId"
        ],
        [
            "sourceTable",
            "destinationUris",
            "location",
            "jobId",
            "destinationFormat",
            "compression",
            "fieldDelimiter",
            "printHeader",
            "useAvroLogicalTypes",
            "labels"
        ]
    ],
    "start_load_job_from_gcs": [
        "GET",
        "/projects/{projectId}/start_load_job_from_gcs",
        [
            "projectId"
        ],
        [
            "sourceUris",
            "destinationTable",
            "location",
            "jobId",
            "sourceFormat",
            "schema",
            "writeDisposition",
            "createDisposition",
            "skipLeadingRows",
            "fieldDelimiter",
            "allowQuotedNewlines",
            "allowJaggedRows",
            "ignoreUnknownValues",
            "maxBadRecords",
            "autodetect",
            "nullMarker",
            "encoding",
            "timePartitioning",
            "rangePartitioning",
            "clustering",
            "labels"
        ]
    ],
    "start_query_job": [
        "GET",
        "/projects/{projectId}/start_query_job",
        [
            "projectId"
        ],
        [
            "query",
            "location",
            "jobId",
            "dryRun",
            "useLegacySql",
            "destinationTable",
            "defaultDataset",
            "writeDisposition",
            "createDisposition",
            "priority",
            "maximumBytesBilled",
            "parameterMode",
            "queryParameters",
            "labels"
        ]
    ],
    "update_dataset": [
        "POST",
        "/projects/{projectId}/dataset",
        [
            "projectId"
        ],
        [
            "datasetId",
            "location",
            "friendlyName",
            "description",
            "labels",
            "defaultTableExpirationMs",
            "defaultPartitionExpirationMs",
            "updateMode"
        ]
    ],
    "update_routine": [
        "PATCH",
        "/projects/{projectId}/routine",
        [
            "projectId"
        ],
        [
            "datasetId",
            "routineId",
            "routineType",
            "language",
            "definitionBody",
            "description",
            "arguments",
            "returnType",
            "importedLibraries",
            "determinismLevel"
        ]
    ],
    "update_table": [
        "PATCH",
        "/projects/{projectId}/table",
        [
            "projectId"
        ],
        [
            "datasetId",
            "tableId",
            "schema",
            "friendlyName",
            "description",
            "labels",
            "timePartitioning",
            "rangePartitioning",
            "clustering",
            "view",
            "materializedView",
            "externalDataConfiguration",
            "encryptionConfiguration"
        ]
    ]
}

class GoogleBigQueryDynamicAction(Action):
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
            raise ValueError(f"Google BigQuery API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class GoogleBigQueryProvider(Provider):
    def __init__(self):
        super().__init__(
            service="google_bigquery",
            display_name="Google BigQuery",
            category="Developer Tools",
            auth_types=["oauth2", "custom_credential"],
            description="Google BigQuery serverless enterprise data warehouse and SQL analytics with 32 actions."
        )
        for act in get_provider_actions("google_bigquery"):
            self.register_action(GoogleBigQueryDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://bigquery.googleapis.com/bigquery/v2/projects"
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
            raise ValueError(f"Google BigQuery connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Google BigQuery credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Google BigQuery validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Google BigQuery Account"
        }

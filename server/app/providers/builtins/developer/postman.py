"""
Postman Provider for ConnectorHub.
Loads and registers 135 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://api.getpostman.com"

def _headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    return {
        "X-Api-Key": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "userKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Postman credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "postman" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "get_authenticated_user": [
        "GET",
        "/me",
        [],
        []
    ],
    "get_accounts": [
        "GET",
        "/accounts",
        [],
        []
    ],
    "list_account_invoices": [
        "GET",
        "/accounts/{accountId}/invoices",
        [
            "account_id"
        ],
        [
            "status"
        ]
    ],
    "get_all_team_users": [
        "GET",
        "/users",
        [],
        []
    ],
    "get_a_team_user": [
        "GET",
        "/users/{userId}",
        [
            "user_id"
        ],
        []
    ],
    "get_all_groups": [
        "GET",
        "/groups",
        [],
        []
    ],
    "get_resource_types": [
        "GET",
        "/scim/v2/ResourceTypes",
        [],
        []
    ],
    "get_service_provider_configuration": [
        "GET",
        "/scim/v2/ServiceProviderConfig",
        [],
        []
    ],
    "create_a_workspace": [
        "POST",
        "/workspaces",
        [],
        []
    ],
    "get_all_workspaces": [
        "GET",
        "/workspaces",
        [],
        [
            "type"
        ]
    ],
    "get_a_workspace": [
        "GET",
        "/workspaces/{workspaceId}",
        [
            "workspace_id"
        ],
        []
    ],
    "update_a_workspace": [
        "PUT",
        "/workspaces/{workspaceId}",
        [
            "workspace_id"
        ],
        []
    ],
    "delete_a_workspace": [
        "DELETE",
        "/workspaces/{workspaceId}",
        [
            "workspace_id"
        ],
        []
    ],
    "get_global_variables": [
        "GET",
        "/workspaces/{workspaceId}/globals",
        [
            "workspace_id"
        ],
        []
    ],
    "update_global_variables": [
        "PUT",
        "/workspaces/{workspaceId}/globals",
        [
            "workspace_id"
        ],
        []
    ],
    "get_a_workspaces_activity_feed": [
        "GET",
        "/workspaces/{workspaceId}/activities",
        [
            "workspace_id"
        ],
        [
            "limit",
            "cursor"
        ]
    ],
    "get_a_workspaces_roles": [
        "GET",
        "/workspaces/{workspaceId}/roles",
        [
            "workspace_id"
        ],
        []
    ],
    "create_a_collection": [
        "POST",
        "/collections",
        [],
        [
            "workspace"
        ]
    ],
    "get_all_collections2": [
        "GET",
        "/collections",
        [],
        [
            "workspace"
        ]
    ],
    "delete_a_collection": [
        "DELETE",
        "/collections/{collectionId}",
        [
            "collection_id"
        ],
        []
    ],
    "duplicate_a_collection": [
        "POST",
        "/collections/{collectionId}/duplicates",
        [
            "collection_id"
        ],
        [
            "workspace"
        ]
    ],
    "get_duplication_task_status": [
        "GET",
        "/collections/duplicates/{taskId}",
        [
            "task_id"
        ],
        []
    ],
    "replace_collections_data_asynchronously": [
        "PUT",
        "/collections/{collectionId}",
        [
            "collection_id"
        ],
        []
    ],
    "get_async_collection_update_status": [
        "GET",
        "/collections/tasks/{taskId}",
        [
            "task_id"
        ],
        []
    ],
    "update_part_of_a_collection": [
        "PATCH",
        "/collections/{collectionId}",
        [
            "collection_id"
        ],
        []
    ],
    "get_all_forked_collections": [
        "GET",
        "/collections/forks",
        [],
        []
    ],
    "get_a_collections_forks": [
        "GET",
        "/collections/{collectionId}/forks",
        [
            "collection_id"
        ],
        []
    ],
    "fork_collection": [
        "POST",
        "/collections/fork/{collectionId}",
        [
            "collection_id"
        ],
        [
            "workspace"
        ]
    ],
    "merge_a_fork": [
        "POST",
        "/collections/merge/{destination}",
        [
            "destination"
        ],
        []
    ],
    "get_source_collections_status": [
        "GET",
        "/collections/{collectionId}/fork",
        [
            "collection_id"
        ],
        []
    ],
    "pull_source_changes2": [
        "POST",
        "/collections/{collectionId}/pull-changes",
        [
            "collection_id"
        ],
        []
    ],
    "get_collection_access_keys": [
        "GET",
        "/collections/access-keys",
        [],
        []
    ],
    "get_a_collections_pull_requests": [
        "GET",
        "/collections/{collectionUid}/pull-requests",
        [
            "collection_uid"
        ],
        []
    ],
    "create_a_pull_request": [
        "POST",
        "/collections/{collectionUid}/pull-requests",
        [
            "collection_uid"
        ],
        []
    ],
    "update_a_pull_request": [
        "PUT",
        "/pull-requests/{pullRequestId}",
        [
            "pull_request_id"
        ],
        []
    ],
    "review_a_pull_request": [
        "PUT",
        "/pull-requests/{pullRequestId}/review",
        [
            "pull_request_id"
        ],
        []
    ],
    "get_a_collections_roles": [
        "GET",
        "/collections/{collectionId}/roles",
        [
            "collection_id"
        ],
        []
    ],
    "create_a_folder": [
        "POST",
        "/collections/{collectionId}/folders",
        [
            "collection_id"
        ],
        []
    ],
    "get_a_folder": [
        "GET",
        "/collections/{collectionId}/folders/{folderId}",
        [
            "collection_id",
            "folder_id"
        ],
        []
    ],
    "update_a_folder": [
        "PUT",
        "/collections/{collectionId}/folders/{folderId}",
        [
            "collection_id",
            "folder_id"
        ],
        []
    ],
    "delete_a_folder": [
        "DELETE",
        "/collections/{collectionId}/folders/{folderId}",
        [
            "collection_id",
            "folder_id"
        ],
        []
    ],
    "transfer_folders": [
        "POST",
        "/collection-folders-transfers",
        [],
        []
    ],
    "create_a_request": [
        "POST",
        "/collections/{collectionId}/requests",
        [
            "collection_id"
        ],
        []
    ],
    "get_a_request": [
        "GET",
        "/collections/{collectionId}/requests/{requestId}",
        [
            "collection_id",
            "request_id"
        ],
        []
    ],
    "update_a_request": [
        "PUT",
        "/collections/{collectionId}/requests/{requestId}",
        [
            "collection_id",
            "request_id"
        ],
        []
    ],
    "create_a_response": [
        "POST",
        "/collections/{collectionId}/responses",
        [
            "collection_id"
        ],
        [
            "parent_request_id"
        ]
    ],
    "get_a_response": [
        "GET",
        "/collections/{collectionId}/responses/{responseId}",
        [
            "collection_id",
            "response_id"
        ],
        []
    ],
    "update_a_response": [
        "PUT",
        "/collections/{collectionId}/responses/{responseId}",
        [
            "collection_id",
            "response_id"
        ],
        []
    ],
    "delete_a_response": [
        "DELETE",
        "/collections/{collectionId}/responses/{responseId}",
        [
            "collection_id",
            "response_id"
        ],
        []
    ],
    "create_a_folder_comment": [
        "POST",
        "/collections/{collectionUid}/folders/{folderUid}/comments",
        [
            "collection_uid",
            "folder_uid"
        ],
        []
    ],
    "get_a_folders_comments": [
        "GET",
        "/collections/{collectionUid}/folders/{folderUid}/comments",
        [
            "collection_uid",
            "folder_uid"
        ],
        []
    ],
    "update_a_folders_comment": [
        "PUT",
        "/collections/{collectionUid}/folders/{folderUid}/comments/{commentId}",
        [
            "collection_uid",
            "folder_uid",
            "comment_id"
        ],
        []
    ],
    "delete_a_folders_comment": [
        "DELETE",
        "/collections/{collectionUid}/folders/{folderUid}/comments/{commentId}",
        [
            "collection_uid",
            "folder_uid",
            "comment_id"
        ],
        []
    ],
    "create_a_request_comment": [
        "POST",
        "/collections/{collectionUid}/requests/{requestUid}/comments",
        [
            "collection_uid",
            "request_uid"
        ],
        []
    ],
    "get_a_requests_comments": [
        "GET",
        "/collections/{collectionUid}/requests/{requestUid}/comments",
        [
            "collection_uid",
            "request_uid"
        ],
        []
    ],
    "update_a_requests_comment": [
        "PUT",
        "/collections/{collectionUid}/requests/{requestUid}/comments/{commentId}",
        [
            "collection_uid",
            "request_uid",
            "comment_id"
        ],
        []
    ],
    "delete_a_requests_comment": [
        "DELETE",
        "/collections/{collectionUid}/requests/{requestUid}/comments/{commentId}",
        [
            "collection_uid",
            "request_uid",
            "comment_id"
        ],
        []
    ],
    "create_a_response_comment": [
        "POST",
        "/collections/{collectionUid}/responses/{responseUid}/comments",
        [
            "collection_uid",
            "response_uid"
        ],
        []
    ],
    "get_a_responses_comments": [
        "GET",
        "/collections/{collectionUid}/responses/{responseUid}/comments",
        [
            "collection_uid",
            "response_uid"
        ],
        []
    ],
    "update_a_responses_comment": [
        "PUT",
        "/collections/{collectionUid}/responses/{responseUid}/comments/{commentId}",
        [
            "collection_uid",
            "response_uid",
            "comment_id"
        ],
        []
    ],
    "delete_a_responses_comment": [
        "DELETE",
        "/collections/{collectionUid}/responses/{responseUid}/comments/{commentId}",
        [
            "collection_uid",
            "response_uid",
            "comment_id"
        ],
        []
    ],
    "resolve_a_comment_thread": [
        "PUT",
        "/comments/{threadId}/resolve",
        [
            "thread_id"
        ],
        []
    ],
    "create_an_environment": [
        "POST",
        "/environments",
        [],
        [
            "workspace_id"
        ]
    ],
    "get_all_environments": [
        "GET",
        "/environments",
        [],
        [
            "workspace"
        ]
    ],
    "get_an_environment": [
        "GET",
        "/environments/{environmentId}",
        [
            "environment_id"
        ],
        []
    ],
    "update_an_environment": [
        "PATCH",
        "/environments/{environmentId}",
        [
            "environment_id"
        ],
        []
    ],
    "replace_an_environments_data": [
        "PUT",
        "/environments/{environmentId}",
        [
            "environment_id"
        ],
        []
    ],
    "delete_an_environment": [
        "DELETE",
        "/environments/{environmentId}",
        [
            "environment_id"
        ],
        []
    ],
    "create_a_fork2": [
        "POST",
        "/environments/{environmentUid}/forks",
        [
            "environment_uid"
        ],
        [
            "workspace"
        ]
    ],
    "get_an_environments_forks": [
        "GET",
        "/environments/{environmentUid}/forks",
        [
            "environment_uid"
        ],
        []
    ],
    "merge_a_fork2": [
        "POST",
        "/environments/{environmentUid}/merge",
        [
            "environment_uid"
        ],
        []
    ],
    "get_all_api_releases": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/releases",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_an_apis_comments": [
        "GET",
        "/apis/{apiId}/comments",
        [
            "api_id"
        ],
        []
    ],
    "update_an_apis_comment": [
        "PUT",
        "/apis/{apiId}/comments/{commentId}",
        [
            "api_id",
            "comment_id"
        ],
        []
    ],
    "delete_an_apis_comment": [
        "DELETE",
        "/apis/{apiId}/comments/{commentId}",
        [
            "api_id",
            "comment_id"
        ],
        []
    ],
    "create_a_collection_comment": [
        "POST",
        "/apis/{apiId}/collections/{collectionId}/comments",
        [
            "api_id",
            "collection_id"
        ],
        []
    ],
    "get_a_collections_comments": [
        "GET",
        "/apis/{apiId}/collections/{collectionId}/comments",
        [
            "api_id",
            "collection_id"
        ],
        []
    ],
    "delete_a_collections_comment": [
        "DELETE",
        "/apis/{apiId}/collections/{collectionId}/comments/{commentId}",
        [
            "api_id",
            "collection_id",
            "comment_id"
        ],
        []
    ],
    "create_relations": [
        "POST",
        "/apis/{apiId}/versions/{apiVersionId}/relations",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_all_linked_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_all_test_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/test",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_contract_test_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/contracttest",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_documentation_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/documentation",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_environment_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/environment",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_integration_test_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/integrationtest",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_test_suite_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/testsuite",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "get_unclassified_relations": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}/relations/unclassified",
        [
            "api_id",
            "api_version_id"
        ],
        []
    ],
    "create_a_schema": [
        "POST",
        "/apis/{apiId}/schemas",
        [
            "api_id"
        ],
        []
    ],
    "get_a_schema": [
        "GET",
        "/apis/{apiId}/schemas/{schemaId}",
        [
            "api_id",
            "schema_id"
        ],
        [
            "version_id"
        ]
    ],
    "get_schema_files": [
        "GET",
        "/apis/{apiId}/schemas/{schemaId}/files",
        [
            "api_id",
            "schema_id"
        ],
        [
            "version_id"
        ]
    ],
    "get_schema_file_contents": [
        "GET",
        "/apis/{apiId}/schemas/{schemaId}/files/{filePath}",
        [
            "api_id",
            "schema_id",
            "file_path"
        ],
        [
            "version_id"
        ]
    ],
    "create_or_update_a_schema_file": [
        "PUT",
        "/apis/{apiId}/schemas/{schemaId}/files/{filePath}",
        [
            "api_id",
            "schema_id",
            "file_path"
        ],
        []
    ],
    "delete_a_schema_file": [
        "DELETE",
        "/apis/{apiId}/schemas/{schemaId}/files/{filePath}",
        [
            "api_id",
            "schema_id",
            "file_path"
        ],
        []
    ],
    "create_a_collection_from_a_schema": [
        "POST",
        "/apis/{apiId}/versions/{apiVersionId}/schemas/{schemaId}/collections",
        [
            "api_id",
            "api_version_id",
            "schema_id"
        ],
        [
            "workspace"
        ]
    ],
    "sync_collection_with_schema": [
        "POST",
        "/apis/{apiId}/collections/{collectionUid}/sync",
        [
            "api_id",
            "collection_uid"
        ],
        []
    ],
    "create_a_spec": [
        "POST",
        "/specs",
        [],
        [
            "workspace_id"
        ]
    ],
    "get_all_specs": [
        "GET",
        "/specs",
        [],
        [
            "workspace_id"
        ]
    ],
    "get_a_spec": [
        "GET",
        "/specs/{specId}",
        [
            "spec_id"
        ],
        []
    ],
    "update_a_specs_properties": [
        "PATCH",
        "/specs/{specId}",
        [
            "spec_id"
        ],
        []
    ],
    "delete_a_spec": [
        "DELETE",
        "/specs/{specId}",
        [
            "spec_id"
        ],
        []
    ],
    "get_a_specs_definition": [
        "GET",
        "/specs/{specId}/definition",
        [
            "spec_id"
        ],
        []
    ],
    "get_a_specs_files": [
        "GET",
        "/specs/{specId}/files",
        [
            "spec_id"
        ],
        []
    ],
    "get_a_spec_file": [
        "GET",
        "/specs/{specId}/files/{filePath}",
        [
            "spec_id",
            "file_path"
        ],
        []
    ],
    "create_a_spec_file": [
        "POST",
        "/specs/{specId}/files",
        [
            "spec_id"
        ],
        []
    ],
    "update_a_spec_file": [
        "PUT",
        "/specs/{specId}/files/{filePath}",
        [
            "spec_id",
            "file_path"
        ],
        []
    ],
    "delete_a_spec_file": [
        "DELETE",
        "/specs/{specId}/files/{filePath}",
        [
            "spec_id",
            "file_path"
        ],
        []
    ],
    "get_a_specs_generated_collections": [
        "GET",
        "/specs/{specId}/generations/collection",
        [
            "spec_id"
        ],
        []
    ],
    "generate_a_collection_from_spec": [
        "POST",
        "/specs/{specId}/generations/collection",
        [
            "spec_id"
        ],
        []
    ],
    "sync_collection_with_spec": [
        "PUT",
        "/collections/{collectionUid}/synchronizations",
        [
            "collection_uid"
        ],
        [
            "spec_id"
        ]
    ],
    "sync_spec_with_collection": [
        "PUT",
        "/specs/{specId}/synchronizations",
        [
            "spec_id"
        ],
        [
            "collection_uid"
        ]
    ],
    "generate_spec_from_collection": [
        "POST",
        "/collections/{collectionUid}/generations/spec",
        [
            "collection_uid"
        ],
        []
    ],
    "get_generated_spec": [
        "GET",
        "/collections/{collectionUid}/generations/spec",
        [
            "collection_uid"
        ],
        []
    ],
    "import_openapi": [
        "POST",
        "/import/openapi",
        [],
        [
            "workspace"
        ]
    ],
    "transform_collection_to_openapi": [
        "POST",
        "/collections/{collectionId}/transformations",
        [
            "collection_id"
        ],
        []
    ],
    "create_a_mock_server": [
        "POST",
        "/mocks",
        [],
        [
            "workspace"
        ]
    ],
    "get_all_mock_servers": [
        "GET",
        "/mocks",
        [],
        [
            "workspace"
        ]
    ],
    "update_a_mock_server": [
        "PUT",
        "/mocks/{mockId}",
        [
            "mock_id"
        ],
        []
    ],
    "publish_a_mock_server": [
        "POST",
        "/mocks/{mockId}/publish",
        [
            "mock_id"
        ],
        []
    ],
    "create_a_server_response": [
        "POST",
        "/mocks/{mockId}/server-responses",
        [
            "mock_id"
        ],
        []
    ],
    "update_a_server_response": [
        "PUT",
        "/mocks/{mockId}/server-responses/{serverResponseId}",
        [
            "mock_id",
            "server_response_id"
        ],
        []
    ],
    "delete_a_server_response": [
        "DELETE",
        "/mocks/{mockId}/server-responses/{serverResponseId}",
        [
            "mock_id",
            "server_response_id"
        ],
        []
    ],
    "create_a_monitor": [
        "POST",
        "/monitors",
        [],
        [
            "workspace"
        ]
    ],
    "get_all_monitors": [
        "GET",
        "/monitors",
        [],
        [
            "workspace"
        ]
    ],
    "get_a_monitor": [
        "GET",
        "/monitors/{monitorId}",
        [
            "monitor_id"
        ],
        []
    ],
    "update_a_monitor": [
        "PUT",
        "/monitors/{monitorId}",
        [
            "monitor_id"
        ],
        []
    ],
    "delete_monitor": [
        "DELETE",
        "/monitors/{monitorId}",
        [
            "monitor_id"
        ],
        []
    ],
    "run_a_monitor": [
        "POST",
        "/monitors/{monitorId}/run",
        [
            "monitor_id"
        ],
        []
    ],
    "create_a_webhook": [
        "POST",
        "/webhooks",
        [],
        [
            "workspace"
        ]
    ],
    "create_an_api": [
        "POST",
        "/apis",
        [],
        []
    ],
    "get_all_apis": [
        "GET",
        "/apis",
        [],
        [
            "workspace"
        ]
    ],
    "get_an_api": [
        "GET",
        "/apis/{apiId}",
        [
            "apiId"
        ],
        []
    ],
    "update_an_api": [
        "PUT",
        "/apis/{apiId}",
        [
            "apiId"
        ],
        []
    ],
    "delete_an_api": [
        "DELETE",
        "/apis/{apiId}",
        [
            "apiId"
        ],
        []
    ],
    "get_all_versions": [
        "GET",
        "/apis/{apiId}/versions",
        [
            "apiId"
        ],
        []
    ],
    "get_an_api_version": [
        "GET",
        "/apis/{apiId}/versions/{apiVersionId}",
        [
            "apiId",
            "apiVersionId"
        ],
        []
    ]
}

class PostmanDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Developer Tools"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        self.action_meta = action_meta
        act_name = action_meta["name"]
        route_info = ROUTES.get(act_name) or [
            action_meta.get("method", "GET"),
            action_meta.get("endpoint", ""),
            action_meta.get("pathParams", []),
            action_meta.get("queryParams", [])
        ]
        self.method = route_info[0]
        self.endpoint_template = route_info[1]
        self.path_params = route_info[2]
        self.query_params = set(route_info[3])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        inputs = dict(input_data or {})
        headers = _headers(token, credential)

        path = self.endpoint_template
        # Replace path variables (supporting camelCase, snake_case, and kebab-case)
        path_matches = re.findall(r"\{([^\}]+)\}", path)
        for var in path_matches:
            val = None
            candidates = [
                var,
                "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_"),
                var.replace("-", "_"),
                "id",
                "name"
            ]
            for cand in candidates:
                if cand in inputs:
                    val = inputs.pop(cand)
                    break
            if val is not None:
                path = path.replace(chr(123) + var + chr(125), urllib.parse.quote(str(val), safe=""))

        # Special endpoints overriding base URL
        if "postman" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "postman" == "new_relic" and path.startswith("/graphql"):
            base_url = "https://api.newrelic.com"

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        params = {}
        body = {}

        for k, v in inputs.items():
            if v is None or v == "":
                continue
            if req_method in ["GET", "DELETE"] or k in self.query_params or k in ["limit", "offset", "cursor", "page", "per_page"]:
                params[k] = v
            else:
                body[k] = v

        # Payload wraps / transforms if required
        if "postman" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "postman" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "postman" == "pagerduty" and self.name == "resolve_incident":
            body = {"incident": {"type": "incident_reference", "status": "resolved"}}

        json_body = body if (req_method in ["POST", "PUT", "PATCH"] and body) else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=json_body
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("detail") or resp.text
            raise ValueError(f"Postman API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PostmanProvider(Provider):
    def __init__(self):
        super().__init__(
            service="postman",
            display_name="Postman",
            category="Developer Tools",
            auth_types=["api_key"] if "postman" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="Postman integration suite for ConnectorHub."
        )
        for act in get_provider_actions("postman"):
            self.register_action(PostmanDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/me"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Postman credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Postman validation failed: {resp.status_code} {resp.text}")

        try:
            res_data = resp.json()
        except Exception:
            res_data = {}

        acc_id = None
        disp_name = None
        for key in ["id", "user_id", "userId", "username", "login", "email", "name", "account_id"]:
            if isinstance(res_data, dict):
                if key in res_data:
                    acc_id = str(res_data[key])
                    break
                user_obj = res_data.get("user") or res_data.get("data")
                if isinstance(user_obj, dict) and key in user_obj:
                    acc_id = str(user_obj[key])
                    disp_name = str(user_obj.get("name") or user_obj.get("username") or acc_id)
                    break

        return {
            "account_id": acc_id or "connected_account",
            "display_name": disp_name or f"Postman ({acc_id or 'verified'})"
        }

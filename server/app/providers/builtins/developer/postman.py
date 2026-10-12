"""
Postman Provider for ConnectorHub.
Loads and registers 135 actions from 'actions_catalog.json'.
Collaborative API development, collections, environments, mocks, monitors, workspaces, and APIs.
"""
import json
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

POSTMAN_API_BASE = "https://api.getpostman.com"

def _postman_headers(token: str) -> Dict[str, str]:
    return {
        "X-Api-Key": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Postman API Key required. Please connect your Postman account first.")
    return str(token).strip()

def _resolve_postman_route(name: str) -> tuple[str, str]:
    n = name.lower()
    if n.startswith("delete_"):
        method = "DELETE"
    elif n.startswith("update_") or n.startswith("edit_") or n.startswith("replace_"):
        method = "PUT"
    elif n.startswith("create_") or n.startswith("add_") or n.startswith("import_") or n.startswith("run_") or n.startswith("publish_") or n.startswith("sync_") or n.startswith("transfer_"):
        method = "POST"
    else:
        method = "GET"

    if n in ["get_authenticated_user", "get_me", "user", "me"] or n.endswith("_user") or n.endswith("_users"):
        endpoint = "/me" if n in ["get_authenticated_user", "get_me", "me"] else "/users"
    elif "pull_request" in n:
        endpoint = "/pull-requests/{pull_request_id}" if method in ["PUT", "DELETE"] else "/pull-requests"
    elif "folder" in n and "comment" not in n:
        endpoint = "/collections/{collection_id}/folders/{folder_id}" if method in ["PUT", "DELETE"] else "/collections/{collection_id}/folders"
    elif "request" in n and "comment" not in n and "pull_request" not in n:
        endpoint = "/collections/{collection_id}/requests/{request_id}" if method in ["PUT", "DELETE"] else "/collections/{collection_id}/requests"
    elif "response" in n and "comment" not in n and "server_response" not in n:
        endpoint = "/collections/{collection_id}/responses/{response_id}" if method in ["PUT", "DELETE"] else "/collections/{collection_id}/responses"
    elif "comment" in n:
        endpoint = "/collections/{collection_id}/comments"
    elif "collection" in n:
        endpoint = "/collections/{collectionId}" if (method in ["PUT", "DELETE"] or ("a_collection" in n and "create" not in n and "all" not in n and "from" not in n)) else "/collections"
    elif "workspace" in n:
        endpoint = "/workspaces/{workspaceId}" if (method in ["PUT", "DELETE"] or ("a_workspace" in n and "create" not in n and "all" not in n)) else "/workspaces"
    elif "environment" in n:
        endpoint = "/environments/{environmentId}" if (method in ["PUT", "DELETE"] or ("an_environment" in n and "create" not in n and "all" not in n)) else "/environments"
    elif "monitor" in n:
        endpoint = "/monitors/{monitorId}" if (method in ["PUT", "DELETE"] or ("a_monitor" in n and "create" not in n and "all" not in n)) else "/monitors"
    elif "mock" in n:
        endpoint = "/mocks/{mockId}" if (method in ["PUT", "DELETE"] or ("a_mock" in n and "create" not in n and "all" not in n)) else "/mocks"
    elif "api" in n:
        endpoint = "/apis/{apiId}" if (method in ["PUT", "DELETE"] or ("an_api" in n and "create" not in n and "all" not in n)) else "/apis"
    else:
        endpoint = "/collections"

    return method, endpoint

class PostmanDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Developer Tools"),
            required_scopes=action_meta.get("requiredScopes") or action_meta.get("required_scopes", []),
            input_schema=action_meta.get("inputSchema") or action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("outputSchema") or action_meta.get("output_schema", {"type": "object"})
        )
        self.method, self.endpoint_template = _resolve_postman_route(action_meta["name"])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _postman_headers(token)

        # Path variable substitution
        path = self.endpoint_template
        for var in [
            "collectionId", "collection_id", "collection_uid",
            "workspaceId", "workspace_id", "workspace_uid",
            "environmentId", "environment_id", "environment_uid",
            "monitorId", "monitor_id", "mockId", "mock_id",
            "apiId", "api_id", "schemaId", "schema_id", "api_version_id",
            "threadId", "thread_id", "folderId", "folder_id", "folder_uid",
            "requestId", "request_id", "responseId", "response_id",
            "pull_request_id", "id"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{POSTMAN_API_BASE}{path}"
        assert_public_url(url)

        req_method = self.method
        params = {}

        if req_method == "GET":
            params = {k: v for k, v in inputs.items() if v is not None}
            json_body = None
        else:
            # Query parameter workspace if provided
            if "workspace" in inputs:
                ws = inputs.pop("workspace")
                if ws and str(ws).strip():
                    params["workspace"] = str(ws).strip()

            # Collection payload normalization
            if self.id == "postman.create_a_collection":
                coll = inputs.get("collection")
                if isinstance(coll, str):
                    try:
                        inputs["collection"] = json.loads(coll)
                    except Exception:
                        inputs["collection"] = {"info": {"name": coll}}
                elif not coll:
                    col_name = inputs.pop("name", None) or "New Collection"
                    col_desc = inputs.pop("description", "")
                    inputs["collection"] = {
                        "info": {
                            "name": str(col_name),
                            "description": str(col_desc) if col_desc else "",
                            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
                        },
                        "item": inputs.pop("item", [])
                    }
                elif isinstance(inputs["collection"], dict) and "info" not in inputs["collection"]:
                    col_name = inputs["collection"].get("name", "New Collection")
                    col_desc = inputs["collection"].get("description", "")
                    inputs["collection"] = {
                        "info": {
                            "name": str(col_name),
                            "description": str(col_desc) if col_desc else "",
                            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
                        },
                        "item": inputs["collection"].get("item", [])
                    }

            # Workspace payload normalization
            elif "workspace" in self.id and "create" in self.id:
                ws = inputs.get("workspace")
                if isinstance(ws, str):
                    try:
                        inputs["workspace"] = json.loads(ws)
                    except Exception:
                        inputs["workspace"] = {"name": ws, "type": "personal"}
                elif not ws:
                    ws_name = inputs.pop("name", "New Workspace")
                    ws_type = inputs.pop("type", "personal")
                    inputs["workspace"] = {"name": str(ws_name), "type": str(ws_type)}

            json_body = inputs

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params if params else None
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            err_msg = str(data)
            if isinstance(data, dict):
                err_msg = data.get("error", {}).get("message") or data.get("message") or str(data)
            raise ValueError(f"Postman API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class PostmanProvider(Provider):
    def __init__(self):
        super().__init__(
            service="postman",
            display_name="Postman",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Collaborative API development, collections, environments, mocking, and automated API monitoring.",
            homepage_url="https://www.postman.com",
            base_url=POSTMAN_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Postman API Key",
                    "placeholder": "PMAK-...",
                    "description": "Postman API Key generated from Postman Account Settings.",
                    "docs_url": "https://learning.postman.com/docs/developer/postman-api/authentication/",
                    "docs_label": "Postman API Key Docs",
                    "setup_guide": {
                        "title": "Postman API Key Setup",
                        "docs_url": "https://web.postman.co/settings/me/api-keys",
                        "docs_label": "Postman API Keys Dashboard",
                        "instructions": [
                            "1. Open Postman Account Settings (web.postman.co/settings/me/api-keys).",
                            "2. Click 'Generate API Key', give it a label (e.g. 'ConnectorHub').",
                            "3. Copy the key (starts with 'PMAK-') and paste below."
                        ],
                        "scopes": ["all"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "PMAK-...",
                            "description": "Postman API key."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("postman"):
            self.register_action(PostmanDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Postman API key via GET /me."""
        token = _extract_token(credential)
        headers = _postman_headers(token)
        url = f"{POSTMAN_API_BASE}/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Postman API: {str(e)}")

        if resp.status_code in [401, 403]:
            raise ValueError("Invalid Postman API key. Postman returned 401 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Postman credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        user = resp.json().get("user", {})
        username = user.get("username") or user.get("email") or "Postman User"
        uid = str(user.get("id") or "postman-account")

        return {
            "account_id": uid,
            "display_name": f"Postman ({username})",
            "granted_scopes": ["all"],
            "avatar_url": user.get("avatar")
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{POSTMAN_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_postman_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }

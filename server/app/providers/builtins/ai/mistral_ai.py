"""
Mistral AI Provider for ConnectorHub.
Loads and registers 54 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://api.mistral.ai"

def _headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "userKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Mistral AI credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "mistral_ai" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "list_models": [
        "GET",
        "/v1/models",
        [],
        []
    ],
    "get_model": [
        "GET",
        "/v1/models/{model_id}",
        [
            "model_id"
        ],
        []
    ],
    "list_conversations": [
        "GET",
        "/v1/conversations",
        [],
        []
    ],
    "start_conversation": [
        "POST",
        "/v1/conversations",
        [],
        []
    ],
    "get_conversation": [
        "GET",
        "/v1/conversations/{conversation_id}",
        [
            "conversation_id"
        ],
        []
    ],
    "delete_conversation": [
        "DELETE",
        "/v1/conversations/{conversation_id}",
        [
            "conversation_id"
        ],
        []
    ],
    "append_to_conversation": [
        "POST",
        "/v1/conversations/{conversation_id}",
        [
            "conversation_id"
        ],
        []
    ],
    "get_conversation_history": [
        "GET",
        "/v1/conversations/{conversation_id}/history",
        [
            "conversation_id"
        ],
        []
    ],
    "get_conversation_messages": [
        "GET",
        "/v1/conversations/{conversation_id}/messages",
        [
            "conversation_id"
        ],
        []
    ],
    "restart_conversation": [
        "POST",
        "/v1/conversations/{conversation_id}/restart",
        [
            "conversation_id"
        ],
        []
    ],
    "list_agents": [
        "GET",
        "/v1/agents",
        [],
        []
    ],
    "create_agent": [
        "POST",
        "/v1/agents",
        [],
        []
    ],
    "get_agent": [
        "GET",
        "/v1/agents/{agent_id}",
        [
            "agent_id"
        ],
        []
    ],
    "update_agent": [
        "PATCH",
        "/v1/agents/{agent_id}",
        [
            "agent_id"
        ],
        []
    ],
    "delete_agent": [
        "DELETE",
        "/v1/agents/{agent_id}",
        [
            "agent_id"
        ],
        []
    ],
    "update_agent_version": [
        "PATCH",
        "/v1/agents/{agent_id}/version",
        [
            "agent_id"
        ],
        [
            "version"
        ]
    ],
    "list_agent_versions": [
        "GET",
        "/v1/agents/{agent_id}/versions",
        [
            "agent_id"
        ],
        []
    ],
    "get_agent_version": [
        "GET",
        "/v1/agents/{agent_id}/versions/{version}",
        [
            "agent_id",
            "version"
        ],
        []
    ],
    "create_or_update_agent_alias": [
        "PUT",
        "/v1/agents/{agent_id}/aliases",
        [
            "agent_id"
        ],
        [
            "alias",
            "version"
        ]
    ],
    "list_agent_aliases": [
        "GET",
        "/v1/agents/{agent_id}/aliases",
        [
            "agent_id"
        ],
        []
    ],
    "create_chat_completion": [
        "POST",
        "/v1/chat/completions",
        [],
        []
    ],
    "create_fim_completion": [
        "POST",
        "/v1/fim/completions",
        [],
        []
    ],
    "create_agents_completion": [
        "POST",
        "/v1/agents/completions",
        [],
        []
    ],
    "create_embeddings": [
        "POST",
        "/v1/embeddings",
        [],
        []
    ],
    "create_moderation": [
        "POST",
        "/v1/moderations",
        [],
        []
    ],
    "create_chat_moderation": [
        "POST",
        "/v1/chat/moderations",
        [],
        []
    ],
    "create_ocr": [
        "POST",
        "/v1/ocr",
        [],
        []
    ],
    "create_audio_transcription": [
        "POST",
        "/v1/audio/transcriptions",
        [],
        []
    ],
    "list_files": [
        "GET",
        "/v1/files",
        [],
        []
    ],
    "upload_file": [
        "POST",
        "/v1/files",
        [],
        []
    ],
    "retrieve_file": [
        "GET",
        "/v1/files/{file_id}",
        [
            "file_id"
        ],
        []
    ],
    "delete_file": [
        "DELETE",
        "/v1/files/{file_id}",
        [
            "file_id"
        ],
        []
    ],
    "download_file": [
        "GET",
        "/v1/files/{file_id}/content",
        [
            "file_id"
        ],
        []
    ],
    "get_file_signed_url": [
        "GET",
        "/v1/files/{file_id}/url",
        [
            "file_id"
        ],
        []
    ],
    "get_fine_tuning_jobs": [
        "GET",
        "/v1/fine_tuning/jobs",
        [],
        []
    ],
    "list_batch_jobs": [
        "GET",
        "/v1/batch/jobs",
        [],
        []
    ],
    "list_libraries": [
        "GET",
        "/v1/libraries",
        [],
        []
    ],
    "create_library": [
        "POST",
        "/v1/libraries",
        [],
        []
    ],
    "get_library": [
        "GET",
        "/v1/libraries/{library_id}",
        [
            "library_id"
        ],
        []
    ],
    "update_library": [
        "PUT",
        "/v1/libraries/{library_id}",
        [
            "library_id"
        ],
        []
    ],
    "delete_library": [
        "DELETE",
        "/v1/libraries/{library_id}",
        [
            "library_id"
        ],
        []
    ],
    "list_library_documents": [
        "GET",
        "/v1/libraries/{library_id}/documents",
        [
            "library_id"
        ],
        []
    ],
    "upload_library_document": [
        "POST",
        "/v1/libraries/{library_id}/documents",
        [
            "library_id"
        ],
        []
    ],
    "get_library_document": [
        "GET",
        "/v1/libraries/{library_id}/documents/{document_id}",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "update_library_document": [
        "PUT",
        "/v1/libraries/{library_id}/documents/{document_id}",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "delete_library_document": [
        "DELETE",
        "/v1/libraries/{library_id}/documents/{document_id}",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "get_document_text_content": [
        "GET",
        "/v1/libraries/{library_id}/documents/{document_id}/text_content",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "get_document_status": [
        "GET",
        "/v1/libraries/{library_id}/documents/{document_id}/status",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "get_document_signed_url": [
        "GET",
        "/v1/libraries/{library_id}/documents/{document_id}/signed-url",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "get_document_extracted_text_url": [
        "GET",
        "/v1/libraries/{library_id}/documents/{document_id}/extracted-text-signed-url",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "reprocess_document": [
        "POST",
        "/v1/libraries/{library_id}/documents/{document_id}/reprocess",
        [
            "library_id",
            "document_id"
        ],
        []
    ],
    "list_library_shares": [
        "GET",
        "/v1/libraries/{library_id}/share",
        [
            "library_id"
        ],
        []
    ],
    "create_library_share": [
        "PUT",
        "/v1/libraries/{library_id}/share",
        [
            "library_id"
        ],
        []
    ],
    "delete_library_share": [
        "DELETE",
        "/v1/libraries/{library_id}/share",
        [
            "library_id"
        ],
        []
    ]
}

class MistralAIDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Modern AI & Vector DBs"),
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
        if "mistral_ai" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "mistral_ai" == "new_relic" and path.startswith("/graphql"):
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
        if "mistral_ai" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "mistral_ai" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "mistral_ai" == "pagerduty" and self.name == "resolve_incident":
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
            raise ValueError(f"Mistral AI API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class MistralAIProvider(Provider):
    def __init__(self):
        super().__init__(
            service="mistral_ai",
            display_name="Mistral AI",
            category="Modern AI & Vector DBs",
            auth_types=["api_key"] if "mistral_ai" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="Mistral AI integration suite for ConnectorHub."
        )
        for act in get_provider_actions("mistral_ai"):
            self.register_action(MistralAIDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/v1/models"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Mistral AI credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Mistral AI validation failed: {resp.status_code} {resp.text}")

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
            "display_name": disp_name or f"Mistral AI ({acc_id or 'verified'})"
        }

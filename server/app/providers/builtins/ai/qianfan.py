"""
Baidu Qianfan Provider for ConnectorHub.
Loads and registers 25 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://qianfan.baidubce.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "deployKey", "accessKeyId"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    if "qianfan" == "elasticsearch":
        val = str(cred.get("baseUrl") or cred.get("host") or "").strip()
        if val:
            if not val.startswith("http://") and not val.startswith("https://"):
                val = f"https://{val}"
            return val.rstrip("/")
        return "https://localhost:9200"

    if "qianfan" == "nocodb":
        val = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        return val.rstrip("/")

    if "qianfan" == "algolia":
        app_id = str(cred.get("applicationId") or cred.get("appId") or "application").strip()
        return f"https://{app_id}-dsn.algolia.net"

    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base.rstrip("/")

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
    elif auth_mode == "xc_token":
        if token:
            headers["xc-token"] = token
    elif auth_mode == "x_api_key":
        if token:
            headers["x-api-key"] = token
    elif auth_mode == "anthropic_admin":
        if token:
            headers["x-api-key"] = token
            headers["anthropic-version"] = "2023-06-01"
    elif auth_mode == "planetscale_token":
        token_id = cred.get("serviceTokenId") or cred.get("service_token_id")
        if token:
            headers["Authorization"] = f"Bearer {token}" if not token_id else token
            if token_id:
                headers["Service-Token-Id"] = str(token_id).strip()
    elif auth_mode == "algolia":
        app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
        if token:
            headers["X-Algolia-API-Key"] = token
        if app_id:
            headers["X-Algolia-Application-Id"] = app_id
    elif auth_mode == "elasticsearch_auth":
        username = cred.get("username")
        password = cred.get("password")
        if username and password:
            pair = f"{username}:{password}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
        elif token:
            headers["Authorization"] = f"ApiKey {token}"
    elif auth_mode == "volcengine":
        ak = cred.get("accessKeyId") or token
        sk = cred.get("secretAccessKey") or ""
        if ak:
            headers["X-Access-Key"] = str(ak).strip()
        if sk:
            headers["X-Secret-Key"] = str(sk).strip()
        if cred.get("sessionToken"):
            headers["X-Security-Token"] = str(cred["sessionToken"]).strip()

    return headers

ROUTES: Dict[str, List[Any]] = {
    "cancel_batch": [
        "POST",
        "/v2/batches/{batchId}/cancel",
        [
            "batchId"
        ],
        [
            "batch_id"
        ]
    ],
    "cancel_video_generation_task": [
        "POST",
        "/video/generations/{taskId}/cancel",
        [
            "taskId"
        ],
        [
            "task_id"
        ]
    ],
    "create_ai_search_completion": [
        "POST",
        "/v2/ai_search/chat/completions",
        [],
        [
            "model",
            "messages",
            "stream"
        ]
    ],
    "create_air_image_generation": [
        "POST",
        "/v2/musesteamer/images/generations",
        [],
        [
            "model",
            "prompt",
            "n",
            "seed",
            "size",
            "response_format"
        ]
    ],
    "create_batch": [
        "POST",
        "/v2/batches",
        [],
        [
            "input_file_id",
            "endpoint",
            "completion_window",
            "metadata",
            "replace"
        ]
    ],
    "create_chat_completion": [
        "POST",
        "/v2/chat/completions",
        [],
        [
            "model",
            "messages",
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "stream",
            "stream_options",
            "response_format",
            "tools",
            "tool_choice",
            "user"
        ]
    ],
    "create_completion": [
        "POST",
        "/v2/completions",
        [],
        [
            "model",
            "prompt",
            "suffix",
            "max_tokens",
            "temperature",
            "top_p",
            "stop",
            "stream",
            "stream_options",
            "user_id"
        ]
    ],
    "create_embeddings": [
        "POST",
        "/v2/embeddings",
        [],
        [
            "model",
            "input",
            "encoding_format",
            "dimensions",
            "user"
        ]
    ],
    "create_image_generation": [
        "POST",
        "/v2/images/generations",
        [],
        [
            "model",
            "prompt",
            "n",
            "seed",
            "size",
            "response_format"
        ]
    ],
    "create_response": [
        "POST",
        "/v2/responses",
        [],
        [
            "model",
            "input",
            "instructions",
            "stream"
        ]
    ],
    "create_video_generation_task": [
        "POST",
        "/video/generations",
        [],
        [
            "model",
            "content",
            "duration",
            "prompt_extend",
            "watermark"
        ]
    ],
    "delete_response": [
        "DELETE",
        "/v2/responses/{responseId}",
        [
            "responseId"
        ],
        [
            "response_id"
        ]
    ],
    "get_batch": [
        "GET",
        "/v2/batches/{batchId}",
        [
            "batchId"
        ],
        [
            "batch_id"
        ]
    ],
    "get_file_content": [
        "GET",
        "/get_file_content",
        [],
        [
            "file_id"
        ]
    ],
    "get_response": [
        "GET",
        "/v2/responses/{responseId}",
        [
            "responseId"
        ],
        [
            "response_id"
        ]
    ],
    "get_video_generation_task": [
        "GET",
        "/video/generations/{taskId}",
        [
            "taskId"
        ],
        [
            "task_id"
        ]
    ],
    "list_batches": [
        "GET",
        "/v2/batches",
        [],
        [
            "after",
            "limit"
        ]
    ],
    "list_files": [
        "GET",
        "/v2/files",
        [],
        [
            "after",
            "limit",
            "order",
            "purpose"
        ]
    ],
    "list_models": [
        "GET",
        "/v2/models",
        [],
        []
    ],
    "list_response_input_items": [
        "GET",
        "/list_response_input_items",
        [],
        [
            "response_id",
            "after",
            "before",
            "limit",
            "order"
        ]
    ],
    "list_video_generation_tasks": [
        "GET",
        "/list_video_generation_tasks",
        [],
        [
            "page_num",
            "page_size",
            "status",
            "task_ids",
            "model_name",
            "start_time",
            "end_time"
        ]
    ],
    "rerank": [
        "POST",
        "/v2/rerank",
        [],
        [
            "model",
            "query",
            "documents",
            "top_n",
            "return_documents",
            "max_chunks_per_doc",
            "user"
        ]
    ],
    "run_paddleocr_vl": [
        "GET",
        "/run_paddleocr_vl",
        [],
        [
            "file",
            "model",
            "fileType"
        ]
    ],
    "run_pp_structure_v3": [
        "GET",
        "/run_pp_structure_v3",
        [],
        [
            "file",
            "model",
            "fileType"
        ]
    ],
    "upload_file": [
        "POST",
        "/v2/files",
        [],
        [
            "file",
            "purpose"
        ]
    ]
}

class QianfanDynamicAction(Action):
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

        base_url = _resolve_base_url(cred)
        path = path_template

        # Fill path parameters
        for p_name in path_param_names:
            val = params.get(p_name)
            if val is not None:
                path = path.replace(" + p_name + ", urllib.parse.quote(str(val), safe=""))
            else:
                path = path.replace(" + p_name + ", "")

        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        assert_public_url(full_url)

        headers = _build_headers(cred)
        req_params = {}
        req_json = None

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
            raise ValueError(f"Baidu Qianfan API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class QianfanProvider(Provider):
    def __init__(self):
        super().__init__(
            service="qianfan",
            display_name="Baidu Qianfan",
            category="AI & Machine Learning",
            auth_types=['api_key'],
            description="Baidu Qianfan enterprise AI platform with 25 actions for LLM chat completions, embeddings, images, video, batches, and models."
        )
        for act in get_provider_actions("qianfan"):
            self.register_action(QianfanDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "qianfan" != "elasticsearch":
            raise ValueError("API token or key is required for Baidu Qianfan.")

        if "qianfan" == "elasticsearch":
            base_url = str(cred.get("baseUrl") or cred.get("host") or "").strip()
            if not base_url:
                raise ValueError("Elasticsearch baseUrl is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/_cluster/health"
        elif "qianfan" == "nocodb":
            base_url = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/meta/bases"
        elif "qianfan" == "algolia":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Algolia applicationId is required in credentials.")
            val_url = f"https://{app_id}-dsn.algolia.net/1/indexes"
        elif "qianfan" == "jimeng_ai":
            ak = str(cred.get("accessKeyId") or token or "").strip()
            sk = str(cred.get("secretAccessKey") or "").strip()
            if not ak or not sk:
                raise ValueError("Jimeng AI accessKeyId and secretAccessKey are required in credentials.")
            val_url = "https://visual.volcengineapi.com/"
        else:
            val_url = "https://qianfan.baidubce.com/v2/models"
            for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
                if "{" + key + "}" in val_url:
                    val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))
            if "{token}" in val_url:
                val_url = val_url.replace("{token}", token or "invalid-token")

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
            raise ValueError(f"Baidu Qianfan connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Baidu Qianfan credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Baidu Qianfan validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                code = body.get("code")
                if "qianfan" == "sunoapi" and code is not None and code not in [200, 0]:
                    raise ValueError(f"Invalid Baidu Qianfan credentials: {body.get('msg') or resp.text}")
                elif "qianfan" == "jimeng_ai" and body.get("ResponseMetadata", {}).get("Error"):
                    err = body["ResponseMetadata"]["Error"]
                    raise ValueError(f"Invalid Baidu Qianfan credentials: {err.get('Message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Baidu Qianfan Account"
        }

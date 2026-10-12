"""
Jimeng AI Provider for ConnectorHub.
Loads and registers 28 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://visual.volcengineapi.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "deployKey", "accessKeyId"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    if "jimeng_ai" == "elasticsearch":
        val = str(cred.get("baseUrl") or cred.get("host") or "").strip()
        if val:
            if not val.startswith("http://") and not val.startswith("https://"):
                val = f"https://{val}"
            return val.rstrip("/")
        return "https://localhost:9200"

    if "jimeng_ai" == "nocodb":
        val = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        return val.rstrip("/")

    if "jimeng_ai" == "algolia":
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

    auth_mode = "volcengine"
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
    "get_image_generation_4_0_result": [
        "POST",
        "/api/v1/get_image_generation_4_0_result",
        [],
        [
            "task_id",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "get_image_generation_4_6_result": [
        "POST",
        "/api/v1/get_image_generation_4_6_result",
        [],
        [
            "task_id",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "get_marketing_video_agent_result": [
        "POST",
        "/api/v1/get_marketing_video_agent_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_smart_upscale_result": [
        "POST",
        "/api/v1/get_smart_upscale_result",
        [],
        [
            "task_id",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "get_smart_video_agent_1_0_result": [
        "POST",
        "/api/v1/get_smart_video_agent_1_0_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_smart_video_agent_2_0_with_reference_result": [
        "POST",
        "/api/v1/get_smart_video_agent_2_0_with_reference_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_smart_video_agent_2_0_without_reference_result": [
        "POST",
        "/api/v1/get_smart_video_agent_2_0_without_reference_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_text_to_image_3_0_result": [
        "POST",
        "/api/v1/get_text_to_image_3_0_result",
        [],
        [
            "task_id",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "get_text_to_image_3_1_result": [
        "POST",
        "/api/v1/get_text_to_image_3_1_result",
        [],
        [
            "task_id",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "get_video_generation_3_0_1080p_result": [
        "POST",
        "/api/v1/get_video_generation_3_0_1080p_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_video_generation_3_0_720p_result": [
        "POST",
        "/api/v1/get_video_generation_3_0_720p_result",
        [],
        [
            "task_id"
        ]
    ],
    "get_video_generation_3_0_pro_result": [
        "POST",
        "/api/v1/get_video_generation_3_0_pro_result",
        [],
        [
            "task_id"
        ]
    ],
    "submit_image_generation_4_0": [
        "POST",
        "/api/v1/submit_image_generation_4_0",
        [],
        [
            "image_urls",
            "prompt",
            "size",
            "width",
            "height",
            "scale",
            "force_single",
            "min_ratio",
            "max_ratio",
            "callback_url",
            "return_url",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "submit_image_generation_4_6": [
        "POST",
        "/api/v1/submit_image_generation_4_6",
        [],
        [
            "image_urls",
            "prompt",
            "size",
            "width",
            "height",
            "scale",
            "force_single",
            "min_ratio",
            "max_ratio",
            "callback_url",
            "return_url",
            "logo_info",
            "aigc_meta"
        ]
    ],
    "submit_image_to_video_first_frame_3_0_1080p": [
        "POST",
        "/api/v1/submit_image_to_video_first_frame_3_0_1080p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio",
            "image_urls"
        ]
    ],
    "submit_image_to_video_first_frame_3_0_720p": [
        "POST",
        "/api/v1/submit_image_to_video_first_frame_3_0_720p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio",
            "image_urls"
        ]
    ],
    "submit_image_to_video_first_tail_frame_3_0_1080p": [
        "POST",
        "/api/v1/submit_image_to_video_first_tail_frame_3_0_1080p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio",
            "image_urls"
        ]
    ],
    "submit_image_to_video_first_tail_frame_3_0_720p": [
        "POST",
        "/api/v1/submit_image_to_video_first_tail_frame_3_0_720p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio",
            "image_urls"
        ]
    ],
    "submit_marketing_video_agent": [
        "POST",
        "/api/v1/submit_marketing_video_agent",
        [],
        [
            "product_name",
            "product_img_url_list",
            "model_img_url_list"
        ]
    ],
    "submit_smart_upscale": [
        "POST",
        "/api/v1/submit_smart_upscale",
        [],
        [
            "image_url",
            "resolution",
            "scale"
        ]
    ],
    "submit_smart_video_agent_1_0": [
        "POST",
        "/api/v1/submit_smart_video_agent_1_0",
        [],
        [
            "prompt",
            "img_url_list",
            "video_url_list",
            "duration",
            "ratio",
            "language"
        ]
    ],
    "submit_smart_video_agent_2_0_with_reference": [
        "POST",
        "/api/v1/submit_smart_video_agent_2_0_with_reference",
        [],
        [
            "prompt",
            "img_url_list",
            "video_url_list",
            "duration",
            "ratio",
            "language"
        ]
    ],
    "submit_smart_video_agent_2_0_without_reference": [
        "POST",
        "/api/v1/submit_smart_video_agent_2_0_without_reference",
        [],
        [
            "prompt",
            "img_url_list",
            "duration",
            "ratio",
            "language"
        ]
    ],
    "submit_text_to_image_3_0": [
        "POST",
        "/api/v1/submit_text_to_image_3_0",
        [],
        [
            "prompt",
            "use_pre_llm",
            "seed",
            "width",
            "height"
        ]
    ],
    "submit_text_to_image_3_1": [
        "POST",
        "/api/v1/submit_text_to_image_3_1",
        [],
        [
            "prompt",
            "use_pre_llm",
            "seed",
            "width",
            "height"
        ]
    ],
    "submit_video_generation_3_0_1080p": [
        "POST",
        "/api/v1/submit_video_generation_3_0_1080p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio"
        ]
    ],
    "submit_video_generation_3_0_720p": [
        "POST",
        "/api/v1/submit_video_generation_3_0_720p",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio"
        ]
    ],
    "submit_video_generation_3_0_pro": [
        "POST",
        "/api/v1/submit_video_generation_3_0_pro",
        [],
        [
            "prompt",
            "seed",
            "frames",
            "aspect_ratio",
            "image_urls"
        ]
    ]
}

class JimengAiDynamicAction(Action):
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
            raise ValueError(f"Jimeng AI API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class JimengAiProvider(Provider):
    def __init__(self):
        super().__init__(
            service="jimeng_ai",
            display_name="Jimeng AI",
            category="AI & Machine Learning",
            auth_types=['custom_credential'],
            description="Jimeng AI Volcengine multimodal generative suite with 28 actions for text-to-image, video generation, and AI agents."
        )
        for act in get_provider_actions("jimeng_ai"):
            self.register_action(JimengAiDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "jimeng_ai" != "elasticsearch":
            raise ValueError("API token or key is required for Jimeng AI.")

        if "jimeng_ai" == "elasticsearch":
            base_url = str(cred.get("baseUrl") or cred.get("host") or "").strip()
            if not base_url:
                raise ValueError("Elasticsearch baseUrl is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/_cluster/health"
        elif "jimeng_ai" == "nocodb":
            base_url = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/meta/bases"
        elif "jimeng_ai" == "algolia":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Algolia applicationId is required in credentials.")
            val_url = f"https://{app_id}-dsn.algolia.net/1/indexes"
        elif "jimeng_ai" == "jimeng_ai":
            ak = str(cred.get("accessKeyId") or token or "").strip()
            sk = str(cred.get("secretAccessKey") or "").strip()
            if not ak or not sk:
                raise ValueError("Jimeng AI accessKeyId and secretAccessKey are required in credentials.")
            val_url = "https://visual.volcengineapi.com/"
        else:
            val_url = "https://visual.volcengineapi.com/"
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
            raise ValueError(f"Jimeng AI connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Jimeng AI credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Jimeng AI validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                code = body.get("code")
                if "jimeng_ai" == "sunoapi" and code is not None and code not in [200, 0]:
                    raise ValueError(f"Invalid Jimeng AI credentials: {body.get('msg') or resp.text}")
                elif "jimeng_ai" == "jimeng_ai" and body.get("ResponseMetadata", {}).get("Error"):
                    err = body["ResponseMetadata"]["Error"]
                    raise ValueError(f"Invalid Jimeng AI credentials: {err.get('Message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Jimeng AI Account"
        }

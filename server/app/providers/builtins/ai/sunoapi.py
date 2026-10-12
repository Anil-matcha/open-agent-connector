"""
SunoAPI Provider for ConnectorHub.
Loads and registers 26 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.sunoapi.org"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "deployKey", "accessKeyId"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    if "sunoapi" == "elasticsearch":
        val = str(cred.get("baseUrl") or cred.get("host") or "").strip()
        if val:
            if not val.startswith("http://") and not val.startswith("https://"):
                val = f"https://{val}"
            return val.rstrip("/")
        return "https://localhost:9200"

    if "sunoapi" == "nocodb":
        val = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        return val.rstrip("/")

    if "sunoapi" == "algolia":
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
    "add_instrumental": [
        "POST",
        "/api/v1/generate/add-instrumental",
        [],
        [
            "uploadUrl",
            "title",
            "negativeTags",
            "tags",
            "callBackUrl",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "model"
        ]
    ],
    "add_vocals": [
        "POST",
        "/api/v1/generate/add-vocals",
        [],
        [
            "uploadUrl",
            "callBackUrl",
            "prompt",
            "title",
            "negativeTags",
            "style",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "model"
        ]
    ],
    "boost_music_style": [
        "POST",
        "/api/v1/style/generate",
        [],
        [
            "content"
        ]
    ],
    "convert_to_wav_format": [
        "POST",
        "/api/v1/wav/generate",
        [],
        [
            "taskId",
            "audioId",
            "callBackUrl"
        ]
    ],
    "create_music_video": [
        "POST",
        "/api/v1/mp4/generate",
        [],
        [
            "taskId",
            "audioId",
            "callBackUrl",
            "author",
            "domainName"
        ]
    ],
    "extend_music": [
        "POST",
        "/api/v1/generate/extend",
        [],
        [
            "defaultParamFlag",
            "audioId",
            "continueAt",
            "prompt",
            "style",
            "title",
            "instrumental",
            "personaId",
            "personaModel",
            "model",
            "negativeTags",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "callBackUrl"
        ]
    ],
    "generate_lyrics": [
        "POST",
        "/api/v1/lyrics",
        [],
        [
            "prompt",
            "callBackUrl"
        ]
    ],
    "generate_mashup": [
        "POST",
        "/api/v1/generate/mashup",
        [],
        [
            "uploadUrlList",
            "customMode",
            "prompt",
            "style",
            "title",
            "instrumental",
            "model",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "callBackUrl"
        ]
    ],
    "generate_midi": [
        "POST",
        "/api/v1/midi/generate",
        [],
        [
            "taskId",
            "callBackUrl",
            "audioId"
        ]
    ],
    "generate_music": [
        "POST",
        "/api/v1/generate",
        [],
        [
            "prompt",
            "style",
            "title",
            "instrumental",
            "personaId",
            "personaModel",
            "model",
            "negativeTags",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "callBackUrl",
            "customMode",
            "duration"
        ]
    ],
    "generate_music_cover": [
        "POST",
        "/api/v1/suno/cover/generate",
        [],
        [
            "taskId",
            "callBackUrl"
        ]
    ],
    "generate_persona": [
        "POST",
        "/api/v1/generate/generate-persona",
        [],
        [
            "taskId",
            "audioId",
            "name",
            "description",
            "vocalStart",
            "vocalEnd",
            "style"
        ]
    ],
    "generate_sounds": [
        "POST",
        "/api/v1/generate/sounds",
        [],
        [
            "prompt",
            "model",
            "soundLoop",
            "soundTempo",
            "soundKey",
            "grabLyrics",
            "callBackUrl"
        ]
    ],
    "get_lyrics_generation_details": [
        "GET",
        "/api/v1/lyrics/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_midi_generation_details": [
        "GET",
        "/api/v1/midi/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_music_cover_details": [
        "GET",
        "/api/v1/suno/cover/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_music_generation_details": [
        "GET",
        "/api/v1/generate/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_music_video_details": [
        "GET",
        "/api/v1/mp4/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_remaining_credits": [
        "GET",
        "/api/v1/generate/credit",
        [],
        []
    ],
    "get_timestamped_lyrics": [
        "POST",
        "/api/v1/generate/get-timestamped-lyrics",
        [],
        [
            "taskId",
            "audioId"
        ]
    ],
    "get_vocal_separation_details": [
        "GET",
        "/api/v1/vocal-removal/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "get_wav_conversion_details": [
        "GET",
        "/api/v1/wav/record-info",
        [],
        [
            "taskId"
        ]
    ],
    "replace_music_section": [
        "POST",
        "/api/v1/generate/replace-section",
        [],
        [
            "taskId",
            "audioId",
            "prompt",
            "tags",
            "title",
            "infillStartS",
            "infillEndS",
            "negativeTags",
            "callBackUrl"
        ]
    ],
    "separate_vocals_from_music": [
        "POST",
        "/api/v1/vocal-removal/generate",
        [],
        [
            "taskId",
            "audioId",
            "type",
            "callBackUrl"
        ]
    ],
    "upload_and_cover_audio": [
        "POST",
        "/api/v1/generate/upload-cover",
        [],
        [
            "uploadUrl",
            "prompt",
            "style",
            "title",
            "instrumental",
            "personaId",
            "personaModel",
            "model",
            "negativeTags",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "callBackUrl",
            "customMode",
            "duration"
        ]
    ],
    "upload_and_extend_audio": [
        "POST",
        "/api/v1/generate/upload-extend",
        [],
        [
            "uploadUrl",
            "defaultParamFlag",
            "prompt",
            "style",
            "title",
            "instrumental",
            "personaId",
            "personaModel",
            "model",
            "negativeTags",
            "vocalGender",
            "styleWeight",
            "weirdnessConstraint",
            "audioWeight",
            "callBackUrl",
            "continueAt"
        ]
    ]
}

class SunoapiDynamicAction(Action):
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
            raise ValueError(f"SunoAPI API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class SunoapiProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sunoapi",
            display_name="SunoAPI",
            category="AI & Machine Learning",
            auth_types=['api_key'],
            description="SunoAPI AI music generation service with 26 actions for songs, lyrics, stems, extensions, and audio conversion."
        )
        for act in get_provider_actions("sunoapi"):
            self.register_action(SunoapiDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        if not token and "sunoapi" != "elasticsearch":
            raise ValueError("API token or key is required for SunoAPI.")

        if "sunoapi" == "elasticsearch":
            base_url = str(cred.get("baseUrl") or cred.get("host") or "").strip()
            if not base_url:
                raise ValueError("Elasticsearch baseUrl is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/_cluster/health"
        elif "sunoapi" == "nocodb":
            base_url = str(cred.get("baseUrl") or "https://app.nocodb.com").strip()
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/v2/meta/bases"
        elif "sunoapi" == "algolia":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Algolia applicationId is required in credentials.")
            val_url = f"https://{app_id}-dsn.algolia.net/1/indexes"
        elif "sunoapi" == "jimeng_ai":
            ak = str(cred.get("accessKeyId") or token or "").strip()
            sk = str(cred.get("secretAccessKey") or "").strip()
            if not ak or not sk:
                raise ValueError("Jimeng AI accessKeyId and secretAccessKey are required in credentials.")
            val_url = "https://visual.volcengineapi.com/"
        else:
            val_url = "https://api.sunoapi.org/api/v1/generate/credit"
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
            raise ValueError(f"SunoAPI connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid SunoAPI credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"SunoAPI validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                code = body.get("code")
                if "sunoapi" == "sunoapi" and code is not None and code not in [200, 0]:
                    raise ValueError(f"Invalid SunoAPI credentials: {body.get('msg') or resp.text}")
                elif "sunoapi" == "jimeng_ai" and body.get("ResponseMetadata", {}).get("Error"):
                    err = body["ResponseMetadata"]["Error"]
                    raise ValueError(f"Invalid SunoAPI credentials: {err.get('Message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"SunoAPI Account"
        }

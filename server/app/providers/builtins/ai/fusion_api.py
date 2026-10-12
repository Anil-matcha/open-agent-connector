"""
OOMOL Fusion API Provider for ConnectorHub.
Loads and registers 82 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://fusion-api.oomol.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
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
    elif auth_mode in ["recurly_basic", "chargebee_basic"]:
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "voiceflow_key":
        if token:
            headers["Authorization"] = token
    elif auth_mode in ["alpha_vantage", "fmp"]:
        if token:
            headers["apikey"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "cosyvoice_tts_generate": [
        "POST",
        "/cosyvoice_tts_generate",
        [],
        [
            "model",
            "text",
            "voice",
            "format",
            "sampleRate",
            "volume",
            "rate",
            "bitRate",
            "pitch",
            "enableSSML",
            "wordTimestampEnabled",
            "seed",
            "languageHints",
            "instruction",
            "enableAIGCTag",
            "AIGCPropagator",
            "AIGCPropagateID",
            "hotFix",
            "enableMarkdownFilter"
        ]
    ],
    "cphone_nano_banana_result": [
        "GET",
        "/cphone_nano_banana_result",
        [],
        [
            "sessionID"
        ]
    ],
    "cphone_nano_banana_state": [
        "GET",
        "/cphone_nano_banana_state",
        [],
        [
            "sessionID"
        ]
    ],
    "cphone_nano_banana_submit": [
        "POST",
        "/cphone_nano_banana_submit",
        [],
        [
            "prompt",
            "model",
            "aspectRatio",
            "imageURLs",
            "imageSize"
        ]
    ],
    "deepseek_ocr_recognize": [
        "GET",
        "/deepseek_ocr_recognize",
        [],
        [
            "imageURL",
            "prompt",
            "oomolApiKey"
        ]
    ],
    "doubao_stt_result": [
        "GET",
        "/doubao_stt_result",
        [],
        [
            "sessionID"
        ]
    ],
    "doubao_stt_state": [
        "GET",
        "/doubao_stt_state",
        [],
        [
            "sessionID"
        ]
    ],
    "doubao_stt_submit": [
        "POST",
        "/doubao_stt_submit",
        [],
        [
            "audioURL",
            "format"
        ]
    ],
    "doubao_text_to_image_seedream_generate": [
        "POST",
        "/doubao_text_to_image_seedream_generate",
        [],
        [
            "prompt",
            "image",
            "size",
            "multiple",
            "maxCount",
            "watermark",
            "optionsnew"
        ]
    ],
    "doubao_tts_result": [
        "GET",
        "/doubao_tts_result",
        [],
        [
            "sessionID"
        ]
    ],
    "doubao_tts_state": [
        "GET",
        "/doubao_tts_state",
        [],
        [
            "sessionID"
        ]
    ],
    "doubao_tts_submit": [
        "POST",
        "/doubao_tts_submit",
        [],
        [
            "text",
            "voice"
        ]
    ],
    "fal_aura_sr_result": [
        "GET",
        "/fal_aura_sr_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_aura_sr_state": [
        "GET",
        "/fal_aura_sr_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_aura_sr_submit": [
        "POST",
        "/fal_aura_sr_submit",
        [],
        [
            "imageURL"
        ]
    ],
    "fal_nano_banana_2_result": [
        "GET",
        "/fal_nano_banana_2_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_2_state": [
        "GET",
        "/fal_nano_banana_2_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_2_submit": [
        "POST",
        "/fal_nano_banana_2_submit",
        [],
        [
            "prompt",
            "imageURLs",
            "numImages",
            "aspectRatio",
            "outputFormat",
            "safetyTolerance",
            "seed",
            "resolution",
            "limitGenerations",
            "enableWebSearch"
        ]
    ],
    "fal_nano_banana_pro_result": [
        "GET",
        "/fal_nano_banana_pro_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_pro_state": [
        "GET",
        "/fal_nano_banana_pro_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_pro_submit": [
        "POST",
        "/fal_nano_banana_pro_submit",
        [],
        [
            "prompt",
            "imageUrls",
            "aspectRatio",
            "outputFormat",
            "resolution",
            "numImages"
        ]
    ],
    "fal_nano_banana_result": [
        "GET",
        "/fal_nano_banana_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_state": [
        "GET",
        "/fal_nano_banana_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_nano_banana_submit": [
        "POST",
        "/fal_nano_banana_submit",
        [],
        [
            "prompt",
            "imageURLs",
            "numImages",
            "outputFormat",
            "aspectRatio"
        ]
    ],
    "fal_qwen_image_layered_result": [
        "GET",
        "/fal_qwen_image_layered_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_qwen_image_layered_state": [
        "GET",
        "/fal_qwen_image_layered_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_qwen_image_layered_submit": [
        "POST",
        "/fal_qwen_image_layered_submit",
        [],
        [
            "imageURL",
            "prompt",
            "negativePrompt",
            "numInferenceSteps",
            "guidanceScale",
            "seed",
            "numLayers",
            "enableSafetyChecker",
            "outputFormat",
            "acceleration"
        ]
    ],
    "fal_remove_background_result": [
        "DELETE",
        "/fal_remove_background_result",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_remove_background_state": [
        "DELETE",
        "/fal_remove_background_state",
        [],
        [
            "sessionID"
        ]
    ],
    "fal_remove_background_submit": [
        "POST",
        "/fal_remove_background_submit",
        [],
        [
            "imageURL"
        ]
    ],
    "file_upload_abort_multipart_upload": [
        "POST",
        "/file_upload_abort_multipart_upload",
        [],
        [
            "uploadID",
            "key"
        ]
    ],
    "file_upload_complete_multipart_upload": [
        "POST",
        "/file_upload_complete_multipart_upload",
        [],
        [
            "uploadID",
            "key",
            "parts"
        ]
    ],
    "file_upload_create_multipart_upload": [
        "POST",
        "/file_upload_create_multipart_upload",
        [],
        [
            "fileSuffix",
            "filename",
            "fileSize"
        ]
    ],
    "file_upload_generate_presigned_url": [
        "POST",
        "/file_upload_generate_presigned_url",
        [],
        [
            "fileSuffix",
            "filename"
        ]
    ],
    "file_upload_generate_presigned_urls": [
        "POST",
        "/file_upload_generate_presigned_urls",
        [],
        [
            "uploadID",
            "key",
            "partNumbers"
        ]
    ],
    "jina_reader_read": [
        "GET",
        "/jina_reader_read",
        [],
        [
            "URL",
            "format",
            "engine",
            "jsonResponse",
            "timeout",
            "tokenLimit",
            "useReaderLMV2",
            "selectorOnly",
            "selectorWait",
            "selectorNone",
            "removeAllImages",
            "withLinkSummary",
            "withImageSummary"
        ]
    ],
    "jina_reader_search": [
        "GET",
        "/jina_reader_search",
        [],
        [
            "content",
            "engine",
            "jsonResponse",
            "withFavicons",
            "googleLocal",
            "hostLanguage",
            "pageIndex",
            "noCache"
        ]
    ],
    "openai_image_async_result": [
        "GET",
        "/openai_image_async_result",
        [],
        [
            "sessionID"
        ]
    ],
    "openai_image_async_submit": [
        "POST",
        "/openai_image_async_submit",
        [],
        [
            "prompt",
            "model",
            "background",
            "moderation",
            "n",
            "output_compression",
            "output_format",
            "partial_images",
            "quality",
            "size",
            "user"
        ]
    ],
    "openai_image_edit_async_result": [
        "PATCH",
        "/openai_image_edit_async_result",
        [],
        [
            "sessionID"
        ]
    ],
    "openai_image_edit_async_submit": [
        "POST",
        "/openai_image_edit_async_submit",
        [],
        [
            "prompt",
            "model",
            "background",
            "n",
            "output_compression",
            "output_format",
            "partial_images",
            "quality",
            "size",
            "user",
            "images",
            "mask"
        ]
    ],
    "pdf_transform_epub_result": [
        "GET",
        "/pdf_transform_epub_result",
        [],
        [
            "sessionID"
        ]
    ],
    "pdf_transform_epub_state": [
        "GET",
        "/pdf_transform_epub_state",
        [],
        [
            "sessionID"
        ]
    ],
    "pdf_transform_epub_submit": [
        "POST",
        "/pdf_transform_epub_submit",
        [],
        [
            "pdfURL",
            "model",
            "includesFootnotes",
            "ignorePdfErrors",
            "ignoreOcrErrors",
            "ocrWorkers",
            "inlineLatex",
            "oomolApiKey",
            "filename"
        ]
    ],
    "pdf_transform_markdown_result": [
        "GET",
        "/pdf_transform_markdown_result",
        [],
        [
            "sessionID"
        ]
    ],
    "pdf_transform_markdown_state": [
        "GET",
        "/pdf_transform_markdown_state",
        [],
        [
            "sessionID"
        ]
    ],
    "pdf_transform_markdown_submit": [
        "POST",
        "/pdf_transform_markdown_submit",
        [],
        [
            "pdfURL",
            "model",
            "includesFootnotes",
            "ignorePdfErrors",
            "ignoreOcrErrors",
            "ocrWorkers",
            "oomolApiKey",
            "inlineLatex",
            "filename"
        ]
    ],
    "qwen_asr_filetrans_result": [
        "GET",
        "/qwen_asr_filetrans_result",
        [],
        [
            "sessionID"
        ]
    ],
    "qwen_asr_filetrans_state": [
        "GET",
        "/qwen_asr_filetrans_state",
        [],
        [
            "sessionID"
        ]
    ],
    "qwen_asr_filetrans_submit": [
        "POST",
        "/qwen_asr_filetrans_submit",
        [],
        [
            "fileURL",
            "language",
            "enableITN",
            "enableWords",
            "channelID"
        ]
    ],
    "qwen_doc_turbo_analyze": [
        "GET",
        "/qwen_doc_turbo_analyze",
        [],
        [
            "docURLs",
            "instruction",
            "text",
            "systemPrompt",
            "fileParsingStrategy"
        ]
    ],
    "qwen_image_edit_plus_edit": [
        "PATCH",
        "/qwen_image_edit_plus_edit",
        [],
        [
            "model",
            "imageURLs",
            "prompt",
            "generateImageCount",
            "negativePrompt",
            "size",
            "promptExtend",
            "watermark",
            "seed"
        ]
    ],
    "qwen_image_generate": [
        "POST",
        "/qwen_image_generate",
        [],
        [
            "model",
            "prompt",
            "negativePrompt",
            "size",
            "n",
            "promptExtend",
            "watermark",
            "seed"
        ]
    ],
    "qwen_mt_image_result": [
        "GET",
        "/qwen_mt_image_result",
        [],
        [
            "sessionID"
        ]
    ],
    "qwen_mt_image_state": [
        "GET",
        "/qwen_mt_image_state",
        [],
        [
            "sessionID"
        ]
    ],
    "qwen_mt_image_submit": [
        "POST",
        "/qwen_mt_image_submit",
        [],
        [
            "imageURL",
            "sourceLang",
            "targetLang",
            "domainHint",
            "sensitivities",
            "terminologies",
            "skipImgSegment"
        ]
    ],
    "qwen_tts_generate": [
        "POST",
        "/qwen_tts_generate",
        [],
        [
            "model",
            "text",
            "voice",
            "languageType",
            "instructions",
            "optimizeInstructions"
        ]
    ],
    "qwen_voice_cloning_create": [
        "POST",
        "/qwen_voice_cloning_create",
        [],
        [
            "targetModel",
            "preferredName",
            "audioData",
            "text",
            "previewText",
            "language"
        ]
    ],
    "qwen_voice_design_create": [
        "POST",
        "/qwen_voice_design_create",
        [],
        [
            "targetModel",
            "voicePrompt",
            "previewText",
            "preferredName",
            "language",
            "sampleRate",
            "responseFormat"
        ]
    ],
    "qwen_voice_design_delete": [
        "DELETE",
        "/qwen_voice_design_delete",
        [],
        [
            "voice"
        ]
    ],
    "qwen_voice_design_generate": [
        "POST",
        "/qwen_voice_design_generate",
        [],
        [
            "text",
            "voice",
            "model"
        ]
    ],
    "qwen_voice_design_list": [
        "GET",
        "/qwen_voice_design_list",
        [],
        [
            "pageIndex",
            "pageSize"
        ]
    ],
    "qwen_voice_design_query": [
        "GET",
        "/qwen_voice_design_query",
        [],
        [
            "voice"
        ]
    ],
    "seedance_video_result": [
        "GET",
        "/seedance_video_result",
        [],
        [
            "sessionID"
        ]
    ],
    "seedance_video_state": [
        "GET",
        "/seedance_video_state",
        [],
        [
            "sessionID"
        ]
    ],
    "seedance_video_submit": [
        "POST",
        "/seedance_video_submit",
        [],
        [
            "model",
            "prompt",
            "omniReferenceTaskType",
            "outputFormat",
            "images",
            "videos",
            "audios",
            "returnLastFrame",
            "executionExpiresAfter",
            "generateAudio",
            "tools",
            "safetyIdentifier",
            "resolution",
            "ratio",
            "duration",
            "seed",
            "watermark"
        ]
    ],
    "tinify_png_shrink_compress": [
        "GET",
        "/tinify_png_shrink_compress",
        [],
        [
            "imageURL"
        ]
    ],
    "wanx_i2v_video_result": [
        "GET",
        "/wanx_i2v_video_result",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_i2v_video_state": [
        "GET",
        "/wanx_i2v_video_state",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_i2v_video_submit": [
        "POST",
        "/wanx_i2v_video_submit",
        [],
        [
            "model",
            "prompt",
            "imageURL",
            "negativePrompt",
            "audio",
            "audioURL",
            "duration",
            "resolution",
            "promptExtend",
            "shotType",
            "watermark",
            "seed"
        ]
    ],
    "wanx_image_result": [
        "GET",
        "/wanx_image_result",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_image_state": [
        "GET",
        "/wanx_image_state",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_image_submit": [
        "POST",
        "/wanx_image_submit",
        [],
        [
            "model",
            "mode",
            "prompt",
            "imageURLs",
            "negativePrompt",
            "size",
            "n",
            "maxImages",
            "promptExtend",
            "watermark",
            "seed"
        ]
    ],
    "wanx_kf2v_video_result": [
        "GET",
        "/wanx_kf2v_video_result",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_kf2v_video_state": [
        "GET",
        "/wanx_kf2v_video_state",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_kf2v_video_submit": [
        "POST",
        "/wanx_kf2v_video_submit",
        [],
        [
            "model",
            "prompt",
            "firstFrameURL",
            "lastFrameURL",
            "negativePrompt",
            "template",
            "resolution",
            "promptExtend",
            "watermark",
            "seed"
        ]
    ],
    "wanx_r2v_video_result": [
        "GET",
        "/wanx_r2v_video_result",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_r2v_video_state": [
        "GET",
        "/wanx_r2v_video_state",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_r2v_video_submit": [
        "POST",
        "/wanx_r2v_video_submit",
        [],
        [
            "model",
            "prompt",
            "referenceURLs",
            "negativePrompt",
            "size",
            "duration",
            "shotType",
            "audio",
            "watermark",
            "seed"
        ]
    ],
    "wanx_t2v_video_result": [
        "GET",
        "/wanx_t2v_video_result",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_t2v_video_state": [
        "GET",
        "/wanx_t2v_video_state",
        [],
        [
            "sessionID"
        ]
    ],
    "wanx_t2v_video_submit": [
        "POST",
        "/wanx_t2v_video_submit",
        [],
        [
            "prompt",
            "negativePrompt",
            "audioURL",
            "size",
            "duration",
            "promptExtend",
            "shotType",
            "watermark",
            "seed"
        ]
    ]
}

class FusionApiDynamicAction(Action):
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

        token = _extract_token(cred)
        if "Bearer" in ["alpha_vantage", "fmp"] and token:
            req_params["apikey"] = token

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
            raise ValueError(f"OOMOL Fusion API API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class FusionApiProvider(Provider):
    def __init__(self):
        super().__init__(
            service="fusion-api",
            display_name="OOMOL Fusion API",
            category="AI & Machine Learning",
            auth_types=["api_key"],
            description="OOMOL Fusion API multimodal AI, speech, OCR, and image generation with 82 actions."
        )
        for act in get_provider_actions("fusion-api"):
            self.register_action(FusionApiDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://fusion-api.oomol.com/openapi/qwen-image?hideTaskStateAPI=true"
        for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        token = _extract_token(cred)
        if "Bearer" in ["alpha_vantage", "fmp"] and token:
            req_params["apikey"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"OOMOL Fusion API connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid OOMOL Fusion API credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"OOMOL Fusion API validation failed: {resp.status_code} {resp.text}")

        # For Alpha Vantage, invalid API key returns 200 with 'Information' or 'Error Message'
        if "Bearer" == "alpha_vantage":
            try:
                j = resp.json()
                if "Error Message" in j or "Information" in j:
                    raise ValueError(f"Invalid Alpha Vantage credentials: {resp.text}")
            except Exception as e:
                if "Invalid Alpha Vantage" in str(e):
                    raise

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"OOMOL Fusion API Account"
        }

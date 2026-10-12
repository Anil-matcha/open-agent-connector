"""
PixelLab Provider for ConnectorHub.
Loads and registers 56 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.pixellab.ai/v2"

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
    "animate_with_skeleton": [
        "POST",
        "/animate-with-skeleton",
        [],
        [
            "imageSize",
            "referenceImage",
            "skeletonKeypoints",
            "guidanceScale",
            "view",
            "direction",
            "isometric",
            "obliqueProjection",
            "seed"
        ]
    ],
    "animate_with_text_legacy": [
        "POST",
        "/animate-with-text",
        [],
        [
            "imageSize",
            "description",
            "action",
            "referenceImage",
            "textGuidanceScale",
            "imageGuidanceScale",
            "frameCount",
            "startFrameIndex",
            "view",
            "direction",
            "colorImage",
            "seed"
        ]
    ],
    "convert_to_pixel_art": [
        "POST",
        "/image-to-pixelart",
        [],
        [
            "image",
            "imageSize",
            "outputSize",
            "textGuidanceScale",
            "seed"
        ]
    ],
    "create_pixen_image": [
        "POST",
        "/create-image-pixen",
        [],
        [
            "description",
            "imageSize",
            "outline",
            "detail",
            "view",
            "direction",
            "noBackground",
            "backgroundRemovalTask",
            "seed",
            "enhancePrompt"
        ]
    ],
    "create_pixflux_image": [
        "POST",
        "/create-image-pixflux",
        [],
        [
            "description",
            "imageSize",
            "textGuidanceScale",
            "outline",
            "shading",
            "detail",
            "view",
            "direction",
            "isometric",
            "noBackground",
            "backgroundRemovalTask",
            "initImage",
            "initImageStrength",
            "colorImage",
            "seed"
        ]
    ],
    "delete_character": [
        "DELETE",
        "/characters/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "characterId"
        ]
    ],
    "delete_object": [
        "DELETE",
        "/objects/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "objectId"
        ]
    ],
    "delete_ui_asset": [
        "DELETE",
        "/ui-assets/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "uiAssetId"
        ]
    ],
    "dismiss_object_review": [
        "POST",
        "/objects/{encodeURIComponent}/dismiss-review",
        [
            "encodeURIComponent"
        ],
        [
            "objectId"
        ]
    ],
    "download_character_zip": [
        "PATCH",
        "/characters/{encodeURIComponent}/zip",
        [
            "encodeURIComponent"
        ],
        [
            "characterId"
        ]
    ],
    "enhance_animation_prompt": [
        "POST",
        "/enhance-animation-v3-prompt",
        [],
        [
            "firstFrame",
            "lastFrame",
            "action"
        ]
    ],
    "enhance_character_prompt": [
        "POST",
        "/enhance-character-v3-prompt",
        [],
        [
            "description",
            "imageSize",
            "view",
            "outline",
            "detail"
        ]
    ],
    "enhance_pixen_prompt": [
        "POST",
        "/enhance-pixen-prompt",
        [],
        [
            "description",
            "imageSize",
            "outline",
            "detail",
            "view",
            "direction",
            "noBackground"
        ]
    ],
    "estimate_skeleton": [
        "POST",
        "/estimate-skeleton",
        [],
        [
            "image"
        ]
    ],
    "get_background_job": [
        "POST",
        "/background-jobs/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "jobId"
        ]
    ],
    "get_balance": [
        "POST",
        "/balance",
        [],
        []
    ],
    "get_character": [
        "DELETE",
        "/characters/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "characterId"
        ]
    ],
    "get_object": [
        "DELETE",
        "/objects/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "objectId"
        ]
    ],
    "get_ui_asset": [
        "DELETE",
        "/ui-assets/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "uiAssetId"
        ]
    ],
    "inpaint_image_legacy": [
        "POST",
        "/inpaint",
        [],
        [
            "description",
            "imageSize",
            "inpaintingImage",
            "maskImage",
            "textGuidanceScale",
            "outline",
            "shading",
            "detail",
            "view",
            "direction",
            "isometric",
            "obliqueProjection",
            "noBackground",
            "initImage",
            "initImageStrength",
            "colorImage",
            "seed"
        ]
    ],
    "list_characters": [
        "DELETE",
        "/characters",
        [],
        [
            "limit",
            "offset"
        ]
    ],
    "list_objects": [
        "DELETE",
        "/objects",
        [],
        [
            "limit",
            "offset"
        ]
    ],
    "list_ui_assets": [
        "DELETE",
        "/ui-assets",
        [],
        [
            "limit",
            "offset"
        ]
    ],
    "remove_background": [
        "POST",
        "/remove-background",
        [],
        [
            "image",
            "imageSize",
            "backgroundRemovalTask",
            "text",
            "seed"
        ]
    ],
    "resize_image": [
        "POST",
        "/resize",
        [],
        [
            "description",
            "referenceImage",
            "referenceImageSize",
            "targetSize",
            "view",
            "direction",
            "isometric",
            "obliqueProjection",
            "noBackground",
            "colorImage",
            "initImage",
            "initImageStrength",
            "seed"
        ]
    ],
    "rotate_image": [
        "POST",
        "/rotate",
        [],
        [
            "imageSize",
            "fromImage",
            "imageGuidanceScale",
            "viewChange",
            "directionChange",
            "fromView",
            "toView",
            "fromDirection",
            "toDirection",
            "isometric",
            "obliqueProjection",
            "initImage",
            "initImageStrength",
            "maskImage",
            "colorImage",
            "seed"
        ]
    ],
    "select_object_frames": [
        "POST",
        "/objects/{encodeURIComponent}/select-frames",
        [
            "encodeURIComponent"
        ],
        [
            "objectId",
            "indices",
            "commonTag"
        ]
    ],
    "start_animate_object": [
        "POST",
        "/start_animate_object",
        [],
        [
            "objectId",
            "mode",
            "animationDescription",
            "directions",
            "animationGroupId",
            "displayName",
            "frameCount",
            "replaceExisting",
            "customStartFrame",
            "endFrame",
            "keepFirstFrame",
            "enhancePrompt"
        ]
    ],
    "start_convert_to_pixel_art_pro": [
        "POST",
        "/image-to-pixelart-pro",
        [],
        [
            "image",
            "description",
            "seed"
        ]
    ],
    "start_create_character_4_directions": [
        "POST",
        "/create-character-with-4-directions",
        [],
        [
            "description",
            "imageSize",
            "textGuidanceScale",
            "outline",
            "shading",
            "detail",
            "view",
            "isometric",
            "colorImage",
            "forceColors",
            "templateId",
            "seed"
        ]
    ],
    "start_create_character_8_directions": [
        "POST",
        "/create-character-with-8-directions",
        [],
        [
            "description",
            "imageSize",
            "mode",
            "textGuidanceScale",
            "outline",
            "shading",
            "detail",
            "view",
            "isometric",
            "colorImage",
            "forceColors",
            "templateId",
            "seed"
        ]
    ],
    "start_create_character_animation": [
        "POST",
        "/characters/animations",
        [],
        [
            "characterId",
            "animationName",
            "description",
            "actionDescription",
            "mode",
            "templateAnimationId",
            "frameCount",
            "customStartFrame",
            "endFrame",
            "keepFirstFrame",
            "directions",
            "seed",
            "enhancePrompt"
        ]
    ],
    "start_create_character_pro": [
        "POST",
        "/create-character-pro",
        [],
        [
            "description",
            "imageSize",
            "method",
            "view",
            "templateId",
            "conceptImage",
            "referenceImage",
            "styleDescription",
            "seed",
            "noBackground"
        ]
    ],
    "start_create_character_state": [
        "POST",
        "/create-character-state",
        [],
        [
            "characterId",
            "editDescription",
            "noBackground",
            "seed",
            "useColorPaletteFromReference"
        ]
    ],
    "start_create_character_v3": [
        "POST",
        "/create-character-v3",
        [],
        [
            "description",
            "referenceImage",
            "imageSize",
            "view",
            "templateId",
            "name",
            "seed",
            "noBackground",
            "outline",
            "detail",
            "enhancePrompt"
        ]
    ],
    "start_create_object_1_direction": [
        "POST",
        "/create-1-direction-object",
        [],
        [
            "description",
            "size",
            "view",
            "styleImages",
            "itemDescriptions"
        ]
    ],
    "start_create_object_8_directions": [
        "POST",
        "/create-8-direction-object",
        [],
        [
            "description",
            "size",
            "view",
            "referenceImage",
            "styleImage"
        ]
    ],
    "start_create_object_state": [
        "POST",
        "/objects/{encodeURIComponent}/states",
        [
            "encodeURIComponent"
        ],
        [
            "objectId",
            "editDescription",
            "seed"
        ]
    ],
    "start_create_ui_asset": [
        "POST",
        "/create-ui-asset",
        [],
        [
            "description",
            "imageSize",
            "pieces",
            "elements",
            "styleImage",
            "colorPalette",
            "noBackground",
            "seed",
            "name",
            "projectId"
        ]
    ],
    "start_edit_animation": [
        "POST",
        "/edit-animation-v2",
        [],
        [
            "description",
            "frames",
            "imageSize",
            "seed",
            "noBackground"
        ]
    ],
    "start_edit_image_legacy": [
        "POST",
        "/edit-image",
        [],
        [
            "image",
            "imageSize",
            "description",
            "width",
            "height",
            "seed",
            "noBackground",
            "textGuidanceScale",
            "colorImage"
        ]
    ],
    "start_edit_images": [
        "POST",
        "/edit-images-v2",
        [],
        [
            "method",
            "editImages",
            "imageSize",
            "description",
            "referenceImage",
            "seed",
            "noBackground"
        ]
    ],
    "start_generate_image": [
        "POST",
        "/generate-image-v2",
        [],
        [
            "description",
            "imageSize",
            "seed",
            "noBackground",
            "referenceImages",
            "styleImage",
            "styleOptions"
        ]
    ],
    "start_generate_rotations": [
        "POST",
        "/generate-8-rotations-v3",
        [],
        [
            "firstFrame",
            "noBackground",
            "seed"
        ]
    ],
    "start_generate_rotations_pro": [
        "POST",
        "/generate-8-rotations-v2",
        [],
        [
            "method",
            "imageSize",
            "referenceImage",
            "conceptImage",
            "description",
            "styleDescription",
            "view",
            "seed",
            "noBackground"
        ]
    ],
    "start_generate_ui": [
        "POST",
        "/generate-ui-v2",
        [],
        [
            "description",
            "imageSize",
            "seed",
            "noBackground",
            "conceptImage",
            "colorPalette"
        ]
    ],
    "start_generate_with_style": [
        "POST",
        "/generate-with-style-v2",
        [],
        [
            "styleImages",
            "description",
            "imageSize",
            "styleDescription",
            "seed",
            "noBackground"
        ]
    ],
    "start_inpaint": [
        "POST",
        "/inpaint-v3",
        [],
        [
            "description",
            "image",
            "maskImage",
            "imageSize",
            "seed",
            "noBackground",
            "cropToMask"
        ]
    ],
    "start_interpolation": [
        "POST",
        "/interpolation-v2",
        [],
        [
            "startImage",
            "endImage",
            "action",
            "imageSize",
            "seed",
            "noBackground"
        ]
    ],
    "start_pixflux_background": [
        "POST",
        "/create-image-pixflux-background",
        [],
        [
            "description",
            "imageSize",
            "textGuidanceScale",
            "outline",
            "shading",
            "detail",
            "view",
            "direction",
            "isometric",
            "noBackground",
            "backgroundRemovalTask",
            "initImage",
            "initImageStrength",
            "colorImage",
            "seed"
        ]
    ],
    "start_portrait_character_conversion": [
        "POST",
        "/portrait-character-pro",
        [],
        [
            "direction",
            "image",
            "view",
            "resultSize",
            "seed"
        ]
    ],
    "start_text_animation": [
        "POST",
        "/animate-with-text-v3",
        [],
        [
            "firstFrame",
            "action",
            "lastFrame",
            "frameCount",
            "seed",
            "noBackground",
            "enhancePrompt"
        ]
    ],
    "start_text_animation_pro": [
        "POST",
        "/animate-with-text-v2",
        [],
        [
            "referenceImage",
            "referenceImageSize",
            "action",
            "imageSize",
            "seed",
            "noBackground",
            "view",
            "direction"
        ]
    ],
    "start_transfer_outfit": [
        "POST",
        "/transfer-outfit-v2",
        [],
        [
            "referenceImage",
            "frames",
            "imageSize",
            "seed",
            "noBackground",
            "additionalInstructions"
        ]
    ],
    "update_character_tags": [
        "PATCH",
        "/characters/{encodeURIComponent}/tags",
        [
            "encodeURIComponent"
        ],
        [
            "characterId",
            "tags"
        ]
    ],
    "update_object_tags": [
        "PATCH",
        "/objects/{encodeURIComponent}/tags",
        [
            "encodeURIComponent"
        ],
        [
            "objectId",
            "tags"
        ]
    ]
}

class PixelLabDynamicAction(Action):
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
            raise ValueError(f"PixelLab API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PixelLabProvider(Provider):
    def __init__(self):
        super().__init__(
            service="pixellab",
            display_name="PixelLab",
            category="AI & Machine Learning",
            auth_types=["api_key"],
            description="PixelLab AI sprite generation, pixel art, and skeleton animation with 56 actions."
        )
        for act in get_provider_actions("pixellab"):
            self.register_action(PixelLabDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.pixellab.ai/v2/characters?limit=1&offset=0"
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
            raise ValueError(f"PixelLab connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid PixelLab credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"PixelLab validation failed: {resp.status_code} {resp.text}")

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
            "display_name": f"PixelLab Account"
        }

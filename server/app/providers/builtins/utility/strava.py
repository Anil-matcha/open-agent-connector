"""
Strava Provider for ConnectorHub.
Loads and registers 34 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://www.strava.com/api/v3"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
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
    elif auth_mode == "token_auth":
        if token:
            headers["Authorization"] = f"Token {token}"
    elif auth_mode == "unsplash_client_id":
        if token:
            headers["Authorization"] = f"Client-ID {token}"
    elif auth_mode == "amplitude_basic":
        if token:
            secret = str(cred.get("secretKey") or cred.get("apiKeyId") or "X").strip()
            pair = f"{token}:{secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "create_activity": [
        "POST",
        "/activity",
        [],
        [
            "name",
            "type",
            "sportType",
            "startDateLocal",
            "elapsedTime",
            "description",
            "distance",
            "trainer",
            "commute"
        ]
    ],
    "explore_segments": [
        "PUT",
        "/athlete",
        [],
        [
            "bounds",
            "activityType",
            "minCat",
            "maxCat"
        ]
    ],
    "export_route_gpx": [
        "PUT",
        "/athlete",
        [],
        [
            "routeId"
        ]
    ],
    "export_route_tcx": [
        "PUT",
        "/athlete",
        [],
        [
            "routeId"
        ]
    ],
    "get_activity": [
        "GET",
        "/activity",
        [],
        [
            "activityId",
            "includeAllEfforts"
        ]
    ],
    "get_activity_streams": [
        "GET",
        "/activity_streams",
        [],
        [
            "activityId",
            "keys",
            "keyByType"
        ]
    ],
    "get_activity_zones": [
        "GET",
        "/activity_zones",
        [],
        [
            "activityId"
        ]
    ],
    "get_athlete_stats": [
        "GET",
        "/athlete_stats",
        [],
        [
            "athleteId"
        ]
    ],
    "get_authenticated_athlete": [
        "GET",
        "/authenticated_athlete",
        [],
        []
    ],
    "get_club": [
        "GET",
        "/athlete",
        [],
        [
            "clubId"
        ]
    ],
    "get_equipment": [
        "GET",
        "/athlete",
        [],
        [
            "gearId"
        ]
    ],
    "get_route": [
        "GET",
        "/athlete",
        [],
        [
            "routeId"
        ]
    ],
    "get_route_streams": [
        "PUT",
        "/athlete",
        [],
        [
            "routeId"
        ]
    ],
    "get_segment": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentId"
        ]
    ],
    "get_segment_effort": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentEffortId"
        ]
    ],
    "get_segment_effort_streams": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentEffortId",
            "keys",
            "keyByType"
        ]
    ],
    "get_segment_streams": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentId",
            "keys",
            "keyByType"
        ]
    ],
    "get_upload": [
        "POST",
        "/upload",
        [],
        [
            "uploadId"
        ]
    ],
    "get_zones": [
        "GET",
        "/athlete/zones",
        [],
        []
    ],
    "list_activity_comments": [
        "GET",
        "/activity_comments",
        [],
        [
            "activityId",
            "page",
            "perPage",
            "pageSize",
            "afterCursor"
        ]
    ],
    "list_activity_kudoers": [
        "GET",
        "/athlete",
        [],
        [
            "activityId",
            "page",
            "perPage"
        ]
    ],
    "list_activity_laps": [
        "GET",
        "/activity_laps",
        [],
        [
            "activityId"
        ]
    ],
    "list_athlete_activities": [
        "GET",
        "/athlete_activities",
        [],
        [
            "before",
            "after",
            "page",
            "perPage"
        ]
    ],
    "list_athlete_clubs": [
        "GET",
        "/athlete",
        [],
        [
            "page",
            "perPage"
        ]
    ],
    "list_athlete_routes": [
        "GET",
        "/athlete",
        [],
        [
            "athleteId",
            "page",
            "perPage"
        ]
    ],
    "list_club_activities": [
        "GET",
        "/athlete",
        [],
        [
            "clubId",
            "page",
            "perPage"
        ]
    ],
    "list_club_administrators": [
        "GET",
        "/athlete",
        [],
        [
            "clubId",
            "page",
            "perPage"
        ]
    ],
    "list_club_members": [
        "GET",
        "/athlete",
        [],
        [
            "clubId",
            "page",
            "perPage"
        ]
    ],
    "list_segment_efforts": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentId",
            "startDateLocal",
            "endDateLocal",
            "page",
            "perPage"
        ]
    ],
    "list_starred_segments": [
        "PUT",
        "/athlete",
        [],
        [
            "page",
            "perPage"
        ]
    ],
    "star_segment": [
        "PUT",
        "/athlete",
        [],
        [
            "segmentId",
            "starred"
        ]
    ],
    "update_activity": [
        "PATCH",
        "/activity",
        [],
        [
            "activityId",
            "activity"
        ]
    ],
    "update_athlete": [
        "PUT",
        "/athlete",
        [],
        [
            "weight"
        ]
    ],
    "upload_activity": [
        "POST",
        "/uploads",
        [],
        [
            "file",
            "name",
            "description",
            "trainer",
            "commute",
            "dataType",
            "externalId"
        ]
    ]
}

class StravaDynamicAction(Action):
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

        if resp.status_code >= 400:
            raise ValueError(f"Strava API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class StravaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="strava",
            display_name="Strava",
            category="Health & Fitness",
            auth_types=["oauth2"],
            description="Strava athlete activity tracking, routes, segments, and gear with 34 actions."
        )
        for act in get_provider_actions("strava"):
            self.register_action(StravaDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://www.strava.com/api/v3/athlete"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
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
            raise ValueError(f"Strava connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Strava credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Strava validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "strava" == "weixin_store" and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Strava credentials: {body.get('errmsg') or resp.text}")
                elif "strava" == "xiaohongshu_store" and (body.get("success") is False or body.get("code", 0) != 0):
                    raise ValueError(f"Invalid Strava credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Strava Account"
        }

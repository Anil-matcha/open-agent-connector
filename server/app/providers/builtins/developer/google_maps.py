"""
Google Maps Provider for ConnectorHub.
Loads and registers 8 actions for geocoding, reverse geocoding, places autocomplete, search, and routing.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://maps.googleapis.com/maps/api"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

ROUTES: Dict[str, List[Any]] = {
    "geocode_address": ["GET", "/geocode/json", [], ["address", "bounds", "components", "language", "region"]],
    "reverse_geocode": ["GET", "/geocode/json", [], ["latitude", "longitude", "resultTypes", "locationTypes", "language", "region"]],
    "autocomplete_places": ["GET", "/place/autocomplete/json", [], ["input", "sessionToken", "languageCode", "regionCode"]],
    "get_place": ["GET", "/place/details/json", [], ["placeId", "fieldMask", "languageCode", "regionCode"]],
    "search_places": ["GET", "/place/textsearch/json", [], ["textQuery", "fieldMask", "pageSize", "pageToken", "languageCode", "regionCode"]],
    "search_nearby_places": ["GET", "/place/nearbysearch/json", [], ["latitude", "longitude", "radiusMeters", "fieldMask", "includedTypes", "excludedTypes", "languageCode", "regionCode"]],
    "compute_routes": ["POST", "https://routes.googleapis.com/directions/v2:computeRoutes", [], []],
    "compute_route_matrix": ["POST", "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix", [], []],
}

class GoogleMapsDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Location"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["GET", f"/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        api_key = _extract_token(cred)
        req_method, path_or_url, path_vars, query_keys = self.route_info

        if path_or_url.startswith("http"):
            target_url = path_or_url
        else:
            target_url = f"{DEFAULT_API_BASE}{path_or_url}"

        assert_public_url(target_url)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }

        params: Dict[str, Any] = {}
        if api_key:
            if "routes.googleapis.com" in target_url:
                headers["X-Goog-Api-Key"] = api_key
                field_mask = input_data.get("fieldMask", "*")
                headers["X-Goog-FieldMask"] = str(field_mask)
            else:
                params["key"] = api_key

        body: Dict[str, Any] = {}

        # Handle reverse geocode lat/lon mapping
        if self.action_name == "reverse_geocode" and "latitude" in input_data and "longitude" in input_data:
            params["latlng"] = f"{input_data['latitude']},{input_data['longitude']}"

        # Handle nearby search location mapping
        if self.action_name == "search_nearby_places" and "latitude" in input_data and "longitude" in input_data:
            params["location"] = f"{input_data['latitude']},{input_data['longitude']}"
            if "radiusMeters" in input_data:
                params["radius"] = input_data["radiusMeters"]

        # Handle places details mapping
        if self.action_name == "get_place" and "placeId" in input_data:
            params["place_id"] = input_data["placeId"]

        # Handle text search query mapping
        if self.action_name == "search_places" and "textQuery" in input_data:
            params["query"] = input_data["textQuery"]

        # Handle autocomplete input mapping
        if self.action_name == "autocomplete_places" and "input" in input_data:
            params["input"] = input_data["input"]

        for k, v in input_data.items():
            if k in ["fieldMask"]:
                continue
            if req_method == "GET" or k in query_keys:
                if k not in ["latitude", "longitude", "radiusMeters", "placeId", "textQuery", "input"]:
                    params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        if resp.status_code >= 400:
            err_msg = resp.text[:400]
            try:
                err_json = resp.json()
                err_msg = err_json.get("error_message") or err_json.get("error") or err_msg
            except Exception:
                pass
            raise ValueError(f"Google Maps API error ({resp.status_code}): {err_msg}")

        data = resp.json()
        if isinstance(data, dict) and data.get("status") in ["REQUEST_DENIED", "OVER_QUERY_LIMIT"]:
            raise ValueError(f"Google Maps error: {data.get('status')} - {data.get('error_message')}")

        return data

class GoogleMapsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="google_maps",
            display_name="Google Maps",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Geocoding, reverse geocoding, places autocomplete, search, and route computation with 8 actions.",
            homepage_url="https://developers.google.com/maps",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Google Maps API Key",
                    "placeholder": "AIzaSy...",
                    "description": "Your Google Maps Platform API key from Google Cloud Console.",
                    "docs_url": "https://developers.google.com/maps/documentation",
                    "docs_label": "Google Maps Platform Docs",
                    "setup_guide": {
                        "title": "Google Maps API Key Setup Guide",
                        "docs_url": "https://console.cloud.google.com/google/maps-apis/credentials",
                        "docs_label": "Google Cloud Maps Credentials",
                        "instructions": [
                            "1. Go to Google Cloud Console > APIs & Services > Credentials.",
                            "2. Click '+ CREATE CREDENTIALS' and select 'API key'.",
                            "3. Ensure the Geocoding API, Places API, and Routes API are enabled.",
                            "4. Copy your API Key (starts with AIzaSy...) and paste it below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "AIzaSy..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("google_maps"):
            self.register_action(GoogleMapsDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        if not api_key:
            raise ValueError("Google Maps API key is required.")

        val_url = f"{DEFAULT_API_BASE}/geocode/json"
        assert_public_url(val_url)
        params = {"address": "1600 Amphitheatre Parkway, Mountain View, CA", "key": api_key}

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, params=params)
        except Exception as e:
            raise ValueError(f"Google Maps connection error: {e}")

        if resp.status_code >= 400:
            raise ValueError(f"Google Maps validation failed: {resp.status_code} {resp.text}")

        data = resp.json() if resp.status_code == 200 else {}
        status = data.get("status")
        if status in ["REQUEST_DENIED", "OVER_QUERY_LIMIT"]:
            err_msg = data.get("error_message") or "API key invalid or Geocoding API not enabled."
            raise ValueError(f"Invalid Google Maps credentials: {status} - {err_msg}")

        return {
            "account_id": f"gmaps_{api_key[:8]}...",
            "display_name": "Google Maps Platform"
        }

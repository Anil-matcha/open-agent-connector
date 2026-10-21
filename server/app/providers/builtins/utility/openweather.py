"""
OpenWeather Provider for ConnectorHub.
Loads and registers 21 actions for current weather, forecasts, air pollution, geocoding, and stations.
"""
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.openweathermap.org/data/2.5"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "appid", "api_key"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

ROUTES: Dict[str, List[Any]] = {
    "get_current_weather": ["GET", "https://api.openweathermap.org/data/2.5/weather", [], ["q", "id", "zip", "lat", "lon", "units", "lang"]],
    "get_5_day_forecast": ["GET", "https://api.openweathermap.org/data/2.5/forecast", [], ["q", "id", "zip", "lat", "lon", "mode", "units", "lang"]],
    "get_air_pollution_current": ["GET", "https://api.openweathermap.org/data/2.5/air_pollution", [], ["lat", "lon"]],
    "get_air_pollution_forecast": ["GET", "https://api.openweathermap.org/data/2.5/air_pollution/forecast", [], ["lat", "lon"]],
    "get_air_pollution_history": ["GET", "https://api.openweathermap.org/data/2.5/air_pollution/history", [], ["lat", "lon", "start", "end"]],
    "get_uv_index": ["GET", "https://api.openweathermap.org/data/2.5/uvi", [], ["lat", "lon", "units", "lang"]],
    "get_uv_index_forecast": ["GET", "https://api.openweathermap.org/data/2.5/uvi/forecast", [], ["lat", "lon", "cnt", "units", "lang"]],
    "get_uv_index_history": ["GET", "https://api.openweathermap.org/data/2.5/uvi/history", [], ["lat", "lon", "start", "end", "units", "lang"]],
    "get_circle_city_weather": ["GET", "https://api.openweathermap.org/data/2.5/find", [], ["lat", "lon", "cnt", "mode", "units", "lang"]],
    "get_weather_map_tile": ["GET", "https://tile.openweathermap.org/map/{layer}/{z}/{x}/{y}.png", ["layer", "z", "x", "y"], ["palette", "opacity", "color", "fill", "fill_bound", "scale", "format"]],
    "get_geocoding_direct": ["GET", "https://api.openweathermap.org/geo/1.0/direct", [], ["q", "limit"]],
    "get_geocoding_reverse": ["GET", "https://api.openweathermap.org/geo/1.0/reverse", [], ["lat", "lon", "limit"]],
    "get_geocoding_by_zip": ["GET", "https://api.openweathermap.org/geo/1.0/zip", [], ["zip"]],
    "list_weather_stations": ["GET", "https://api.openweathermap.org/data/3.0/stations", [], []],
    "get_weather_station": ["GET", "https://api.openweathermap.org/data/3.0/stations/{station_id}", ["station_id"], []],
    "add_weather_station": ["POST", "https://api.openweathermap.org/data/3.0/stations", [], []],
    "update_weather_station": ["PUT", "https://api.openweathermap.org/data/3.0/stations/{station_id}", ["station_id"], []],
    "delete_weather_station": ["DELETE", "https://api.openweathermap.org/data/3.0/stations/{station_id}", ["station_id"], []],
    "submit_station_measurements": ["POST", "https://api.openweathermap.org/data/3.0/measurements", [], []],
    "get_station_measurements": ["GET", "https://api.openweathermap.org/data/3.0/measurements", [], ["station_id", "type", "limit", "from", "to"]],
    "get_weather_triggers": ["GET", "https://api.openweathermap.org/data/3.0/triggers", [], ["triggers"]],
}

class OpenWeatherDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        act_id = action_meta["id"]
        act_name = act_id.split(".", 1)[-1] if "." in act_id else act_id
        super().__init__(
            id=act_id,
            name=action_meta.get("name", act_name.replace("_", " ").title()),
            description=action_meta.get("description", ""),
            category=action_meta.get("category", "Data"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema", {"type": "object"})
        )
        self.action_name = act_name
        self.route_info = ROUTES.get(act_name, ["GET", f"{DEFAULT_API_BASE}/{act_name}", [], []])

    async def execute(self, credential: Optional[Dict[str, Any]], input_data: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)
        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        target_url = path
        assert_public_url(target_url)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ConnectorHub/1.0"
        }

        params: Dict[str, Any] = {}
        if token:
            params["appid"] = token

        body: Dict[str, Any] = {}

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if req_method == "GET" or k in query_keys:
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
                err_msg = err_json.get("message") or err_json.get("error") or err_msg
            except Exception:
                pass
            raise ValueError(f"OpenWeather API error ({resp.status_code}): {err_msg}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class OpenWeatherProvider(Provider):
    def __init__(self):
        super().__init__(
            service="openweather_api",
            display_name="OpenWeather",
            category="Data & Analytics",
            auth_types=["api_key"],
            description="Global real-time weather, 5-day forecasts, air pollution, geocoding, and stations with 21 actions.",
            homepage_url="https://openweathermap.org",
            base_url=DEFAULT_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "OpenWeather API Key",
                    "placeholder": "9a8b7c...",
                    "description": "Your OpenWeatherMap App ID (API key).",
                    "docs_url": "https://openweathermap.org/api",
                    "docs_label": "OpenWeather API Docs",
                    "setup_guide": {
                        "title": "OpenWeather API Key Setup Guide",
                        "docs_url": "https://home.openweathermap.org/api_keys",
                        "docs_label": "OpenWeather API Keys",
                        "instructions": [
                            "1. Sign up or log in at openweathermap.org.",
                            "2. Navigate to your Account > 'API keys' tab.",
                            "3. Generate a key or copy the Default key.",
                            "4. Paste your API key below."
                        ],
                        "scopes": []
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key (App ID)",
                            "type": "password",
                            "required": True,
                            "placeholder": "Paste OpenWeather API key..."
                        }
                    ]
                }
            ]
        )
        for act in get_provider_actions("openweather_api"):
            self.register_action(OpenWeatherDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        if not token:
            raise ValueError("OpenWeather API key is required.")

        val_url = f"{DEFAULT_API_BASE}/weather"
        assert_public_url(val_url)
        params = {"q": "London", "appid": token}

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=val_url, params=params)
        except Exception as e:
            raise ValueError(f"OpenWeather connection error: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid OpenWeather credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"OpenWeather validation failed: {resp.status_code} {resp.text}")

        return {
            "account_id": f"owm_{token[:8]}...",
            "display_name": "OpenWeather Account"
        }

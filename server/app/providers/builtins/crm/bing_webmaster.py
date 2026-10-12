"""
Bing Webmaster Tools Provider for ConnectorHub.
Loads and registers 54 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "botToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["domain", "subdomain", "site", "host", "tenant", "region"]:
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

    auth_mode = "bing_webmaster"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "discord_bot":
        if token:
            headers["Authorization"] = f"Bot {token}"
    elif auth_mode == "freshdesk_basic":
        if token:
            pair = f"{token}:X"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "x_api_key":
        if token:
            headers["X-API-Key"] = token
            headers["X-Api-Key"] = token

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_blocked_url": [
        "POST",
        "/blocked_url",
        [],
        [
            "siteUrl",
            "blockedUrl"
        ]
    ],
    "add_connected_page": [
        "POST",
        "/connected_page",
        [],
        [
            "siteUrl",
            "masterUrl"
        ]
    ],
    "add_country_region_settings": [
        "POST",
        "/country_region_settings",
        [],
        [
            "siteUrl",
            "settings"
        ]
    ],
    "add_deep_link_block": [
        "POST",
        "/deep_link_block",
        [],
        [
            "siteUrl",
            "market",
            "searchUrl",
            "deepLinkUrl"
        ]
    ],
    "add_query_parameter": [
        "POST",
        "/query_parameter",
        [],
        [
            "siteUrl",
            "queryParameter"
        ]
    ],
    "add_site": [
        "POST",
        "/site",
        [],
        [
            "siteUrl"
        ]
    ],
    "add_site_roles": [
        "POST",
        "/site_roles",
        [],
        [
            "siteUrl",
            "delegatedUrl",
            "userEmail",
            "authenticationCode",
            "isAdministrator",
            "isReadOnly"
        ]
    ],
    "get_content_submission_quota": [
        "GET",
        "/content_submission_quota",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_crawl_issues": [
        "GET",
        "/crawl_issues",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_crawl_settings": [
        "POST",
        "/crawl_settings",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_crawl_stats": [
        "GET",
        "/crawl_stats",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_fetched_url_details": [
        "GET",
        "/fetched_url_details",
        [],
        [
            "siteUrl",
            "url"
        ]
    ],
    "get_keyword_stats": [
        "GET",
        "/keyword_stats",
        [],
        [
            "q",
            "country",
            "language"
        ]
    ],
    "get_page_query_stats": [
        "GET",
        "/page_query_stats",
        [],
        [
            "siteUrl",
            "page"
        ]
    ],
    "get_page_stats": [
        "GET",
        "/page_stats",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_query_page_detail_stats": [
        "GET",
        "/query_page_detail_stats",
        [],
        [
            "siteUrl",
            "query",
            "page"
        ]
    ],
    "get_query_page_stats": [
        "GET",
        "/query_page_stats",
        [],
        [
            "siteUrl",
            "query"
        ]
    ],
    "get_query_stats": [
        "GET",
        "/query_stats",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_query_traffic_stats": [
        "GET",
        "/query_traffic_stats",
        [],
        [
            "siteUrl",
            "query"
        ]
    ],
    "get_rank_and_traffic_stats": [
        "GET",
        "/rank_and_traffic_stats",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_sitemap_details": [
        "GET",
        "/sitemap_details",
        [],
        [
            "siteUrl",
            "feedUrl"
        ]
    ],
    "get_url_info": [
        "GET",
        "/url_info",
        [],
        [
            "siteUrl",
            "url"
        ]
    ],
    "get_url_submission_quota": [
        "GET",
        "/url_submission_quota",
        [],
        [
            "siteUrl"
        ]
    ],
    "get_url_traffic_info": [
        "GET",
        "/url_traffic_info",
        [],
        [
            "siteUrl",
            "url"
        ]
    ],
    "list_blocked_urls": [
        "GET",
        "/blocked_urls",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_child_url_info": [
        "GET",
        "/child_url_info",
        [],
        [
            "siteUrl",
            "url",
            "page",
            "filterProperties"
        ]
    ],
    "list_child_url_traffic_info": [
        "GET",
        "/child_url_traffic_info",
        [],
        [
            "siteUrl",
            "url",
            "page"
        ]
    ],
    "list_connected_pages": [
        "GET",
        "/connected_pages",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_country_region_settings": [
        "POST",
        "/country_region_settings",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_deep_link_blocks": [
        "GET",
        "/deep_link_blocks",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_fetched_urls": [
        "GET",
        "/fetched_urls",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_link_counts": [
        "GET",
        "/link_counts",
        [],
        [
            "siteUrl",
            "page"
        ]
    ],
    "list_page_preview_blocks": [
        "GET",
        "/page_preview_blocks",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_query_parameters": [
        "GET",
        "/query_parameters",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_site_moves": [
        "GET",
        "/site_moves",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_site_roles": [
        "GET",
        "/site_roles",
        [],
        [
            "siteUrl",
            "includeAllSubdomains"
        ]
    ],
    "list_sitemaps": [
        "GET",
        "/sitemaps",
        [],
        [
            "siteUrl"
        ]
    ],
    "list_sites": [
        "GET",
        "/sites",
        [],
        []
    ],
    "list_url_links": [
        "GET",
        "/url_links",
        [],
        [
            "siteUrl",
            "link",
            "page"
        ]
    ],
    "remove_blocked_url": [
        "DELETE",
        "/blocked_url",
        [],
        [
            "siteUrl",
            "blockedUrl"
        ]
    ],
    "remove_country_region_settings": [
        "POST",
        "/country_region_settings",
        [],
        [
            "siteUrl",
            "settings"
        ]
    ],
    "remove_deep_link_block": [
        "DELETE",
        "/deep_link_block",
        [],
        [
            "siteUrl",
            "market",
            "searchUrl",
            "deepLinkUrl"
        ]
    ],
    "remove_page_preview_block": [
        "DELETE",
        "/page_preview_block",
        [],
        [
            "siteUrl",
            "url"
        ]
    ],
    "remove_query_parameter": [
        "DELETE",
        "/query_parameter",
        [],
        [
            "siteUrl",
            "queryParameter"
        ]
    ],
    "remove_site": [
        "DELETE",
        "/site",
        [],
        [
            "siteUrl"
        ]
    ],
    "remove_site_role": [
        "DELETE",
        "/site_role",
        [],
        [
            "siteUrl",
            "siteRole"
        ]
    ],
    "remove_sitemap": [
        "DELETE",
        "/sitemap",
        [],
        [
            "siteUrl",
            "feedUrl"
        ]
    ],
    "save_crawl_settings": [
        "POST",
        "/save_crawl_settings",
        [],
        [
            "siteUrl",
            "crawlSettings"
        ]
    ],
    "set_query_parameter_enabled": [
        "POST",
        "/set_query_parameter_enabled",
        [],
        [
            "siteUrl",
            "queryParameter",
            "isEnabled"
        ]
    ],
    "submit_site_move": [
        "POST",
        "/submit_site_move",
        [],
        [
            "siteUrl",
            "settings"
        ]
    ],
    "submit_sitemap": [
        "POST",
        "/submit_sitemap",
        [],
        [
            "siteUrl",
            "feedUrl"
        ]
    ],
    "submit_url": [
        "POST",
        "/submit_url",
        [],
        [
            "siteUrl",
            "url"
        ]
    ],
    "submit_url_batch": [
        "POST",
        "/submit_url_batch",
        [],
        [
            "siteUrl",
            "urlList"
        ]
    ],
    "verify_site": [
        "GET",
        "/verify_site",
        [],
        [
            "siteUrl"
        ]
    ]
}

class BingWebmasterDynamicAction(Action):
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
        if "bing_webmaster" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "bing_webmaster" == "pushover_token" and token:
            req_params["token"] = token

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
            raise ValueError(f"Bing Webmaster Tools API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class BingWebmasterProvider(Provider):
    def __init__(self):
        super().__init__(
            service="bing_webmaster",
            display_name="Bing Webmaster Tools",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="Bing Webmaster Tools search performance, crawl stats, sitemaps, and URL submission API with 54 actions."
        )
        for act in get_provider_actions("bing_webmaster"):
            self.register_action(BingWebmasterDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://ssl.bing.com/webmaster/api.svc/json/GetUserSites"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "bing_webmaster" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "bing_webmaster" == "pushover_token" and token:
            req_params["token"] = token

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers,
                params=req_params if req_params else None
            )
        except Exception as e:
            raise ValueError(f"Bing Webmaster Tools connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Bing Webmaster Tools credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Bing Webmaster Tools validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "bing_webmaster" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Bing Webmaster Tools credentials: {body.get('msg') or resp.text}")
                elif "bing_webmaster" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Bing Webmaster Tools credentials: {body.get('errmsg') or resp.text}")
                elif "bing_webmaster" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Bing Webmaster Tools credentials: {body.get('error_msg') or resp.text}")
                elif "bing_webmaster" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Bing Webmaster Tools credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Bing Webmaster Tools Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Bing Webmaster Tools Account"
        }

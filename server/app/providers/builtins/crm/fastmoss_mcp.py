"""
FastMoss MCP Provider for ConnectorHub.
Loads and registers 57 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://mcp.fastmoss.com"

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

    auth_mode = "Bearer"
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
    "ad_data_overview": [
        "GET",
        "/ad_data_overview",
        [],
        [
            "filter"
        ]
    ],
    "ad_search": [
        "GET",
        "/ad_search",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "agency_creator_analysis": [
        "GET",
        "/agency_creator_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "agency_product_analysis": [
        "GET",
        "/agency_product_analysis",
        [],
        [
            "filter"
        ]
    ],
    "agency_product_list": [
        "GET",
        "/agency_product_list",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "agency_profile_overview": [
        "GET",
        "/agency_profile_overview",
        [],
        [
            "filter"
        ]
    ],
    "agency_rank_top": [
        "GET",
        "/agency_rank_top",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "agency_search": [
        "GET",
        "/agency_search",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "agency_shop_analysis": [
        "GET",
        "/agency_shop_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "call_tool": [
        "GET",
        "/call_tool",
        [],
        [
            "toolName",
            "arguments"
        ]
    ],
    "creator_cargo_summary": [
        "GET",
        "/creator_cargo_summary",
        [],
        [
            "filter"
        ]
    ],
    "creator_data_trends": [
        "GET",
        "/creator_data_trends",
        [],
        [
            "filter"
        ]
    ],
    "creator_fans_distribution": [
        "GET",
        "/creator_fans_distribution",
        [],
        [
            "filter"
        ]
    ],
    "creator_product_list": [
        "GET",
        "/creator_product_list",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "creator_profile_overview": [
        "GET",
        "/creator_profile_overview",
        [],
        [
            "filter"
        ]
    ],
    "creator_rank_top_ecommerce": [
        "GET",
        "/creator_rank_top_ecommerce",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "creator_rank_top_growth": [
        "GET",
        "/creator_rank_top_growth",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "creator_rank_top_potential": [
        "GET",
        "/creator_rank_top_potential",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "creator_search": [
        "GET",
        "/creator_search",
        [],
        [
            "filter",
            "keywords",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "creator_video_analysis": [
        "GET",
        "/creator_video_analysis",
        [],
        [
            "filter"
        ]
    ],
    "credit_usage_summary": [
        "PATCH",
        "/credit_usage_summary",
        [],
        []
    ],
    "fastmoss_detail_url_examples": [
        "GET",
        "/fastmoss_detail_url_examples",
        [],
        []
    ],
    "list_tools": [
        "GET",
        "/tools",
        [],
        []
    ],
    "live_detail_analysis": [
        "GET",
        "/live_detail_analysis",
        [],
        [
            "filter",
            "lang"
        ]
    ],
    "live_products_list": [
        "GET",
        "/live_products_list",
        [],
        [
            "filter",
            "lang",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "live_search": [
        "GET",
        "/live_search",
        [],
        [
            "filter",
            "keywords",
            "lang",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "market_category_analysis": [
        "GET",
        "/market_category_analysis",
        [],
        [
            "analysis_type",
            "filter",
            "lang"
        ]
    ],
    "market_category_author_sales_matrix": [
        "GET",
        "/market_category_author_sales_matrix",
        [],
        [
            "filter",
            "lang"
        ]
    ],
    "market_category_ranking": [
        "GET",
        "/market_category_ranking",
        [],
        [
            "filter",
            "lang",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_category_info": [
        "GET",
        "/product_category_info",
        [],
        []
    ],
    "product_creator_analysis": [
        "GET",
        "/product_creator_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_detail_info": [
        "GET",
        "/product_detail_info",
        [],
        [
            "filter"
        ]
    ],
    "product_investment": [
        "GET",
        "/product_investment",
        [],
        [
            "filter"
        ]
    ],
    "product_overview": [
        "GET",
        "/product_overview",
        [],
        [
            "filter"
        ]
    ],
    "product_rank_new_listed": [
        "GET",
        "/product_rank_new_listed",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_rank_top_selling": [
        "GET",
        "/product_rank_top_selling",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_review_list": [
        "GET",
        "/product_review_list",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_sales_trend": [
        "GET",
        "/product_sales_trend",
        [],
        [
            "filter"
        ]
    ],
    "product_search": [
        "GET",
        "/product_search",
        [],
        [
            "filter",
            "keywords",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "product_sku": [
        "GET",
        "/product_sku",
        [],
        [
            "filter"
        ]
    ],
    "product_video_list": [
        "GET",
        "/product_video_list",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "search_category_by_words": [
        "GET",
        "/search_category_by_words",
        [],
        [
            "max_total_results",
            "query",
            "top_k"
        ]
    ],
    "search_fastmoss_documents": [
        "GET",
        "/search_fastmoss_documents",
        [],
        [
            "query",
            "source_file",
            "top_k"
        ]
    ],
    "shop_base_info": [
        "GET",
        "/shop_base_info",
        [],
        [
            "filter"
        ]
    ],
    "shop_creator_analysis": [
        "GET",
        "/shop_creator_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "shop_data_trends": [
        "GET",
        "/shop_data_trends",
        [],
        [
            "filter"
        ]
    ],
    "shop_investment_analysis": [
        "GET",
        "/shop_investment_analysis",
        [],
        [
            "filter"
        ]
    ],
    "shop_live_analysis": [
        "GET",
        "/shop_live_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "shop_product_analysis": [
        "GET",
        "/shop_product_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "shop_rank_top_selling": [
        "GET",
        "/shop_rank_top_selling",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "shop_sale_analysis": [
        "GET",
        "/shop_sale_analysis",
        [],
        [
            "filter"
        ]
    ],
    "shop_search": [
        "GET",
        "/shop_search",
        [],
        [
            "filter",
            "keywords",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "shop_video_analysis": [
        "GET",
        "/shop_video_analysis",
        [],
        [
            "filter",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "video_data_trends": [
        "GET",
        "/video_data_trends",
        [],
        [
            "filter"
        ]
    ],
    "video_detail_analysis": [
        "GET",
        "/video_detail_analysis",
        [],
        [
            "filter",
            "lang",
            "orderby",
            "page",
            "pagesize"
        ]
    ],
    "video_script_info": [
        "GET",
        "/video_script_info",
        [],
        [
            "video_id"
        ]
    ],
    "video_search": [
        "GET",
        "/video_search",
        [],
        [
            "filter",
            "keywords",
            "lang",
            "orderby",
            "page",
            "pagesize"
        ]
    ]
}

class FastmossMcpDynamicAction(Action):
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
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
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
            raise ValueError(f"FastMoss MCP API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class FastmossMcpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="fastmoss_mcp",
            display_name="FastMoss MCP",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="FastMoss TikTok ecommerce data intelligence and creator analytics MCP API with 57 actions."
        )
        for act in get_provider_actions("fastmoss_mcp"):
            self.register_action(FastmossMcpDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://mcp.fastmoss.com/api/v1/user/info"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "Bearer" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "Bearer" == "pushover_token" and token:
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
            raise ValueError(f"FastMoss MCP connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid FastMoss MCP credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"FastMoss MCP validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "fastmoss_mcp" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid FastMoss MCP credentials: {body.get('msg') or resp.text}")
                elif "fastmoss_mcp" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid FastMoss MCP credentials: {body.get('errmsg') or resp.text}")
                elif "fastmoss_mcp" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid FastMoss MCP credentials: {body.get('error_msg') or resp.text}")
                elif "fastmoss_mcp" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid FastMoss MCP credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"FastMoss MCP Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"FastMoss MCP Account"
        }

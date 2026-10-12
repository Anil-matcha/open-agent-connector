"""
Longbridge Provider for ConnectorHub.
Loads and registers 80 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://openapi.longbridge.com"

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
    "ah_premium": [
        "GET",
        "/ah_premium",
        [],
        [
            "symbol",
            "period",
            "count"
        ]
    ],
    "ah_premium_intraday": [
        "GET",
        "/ah_premium_intraday",
        [],
        [
            "symbol"
        ]
    ],
    "anomaly": [
        "GET",
        "/anomaly",
        [],
        [
            "market",
            "size",
            "symbol"
        ]
    ],
    "broker_holding": [
        "GET",
        "/broker_holding",
        [],
        [
            "symbol",
            "period"
        ]
    ],
    "broker_holding_daily": [
        "GET",
        "/broker_holding_daily",
        [],
        [
            "symbol",
            "brokerId"
        ]
    ],
    "broker_holding_detail": [
        "GET",
        "/broker_holding_detail",
        [],
        [
            "symbol"
        ]
    ],
    "business_segments": [
        "GET",
        "/business_segments",
        [],
        [
            "symbol"
        ]
    ],
    "business_segments_history": [
        "GET",
        "/business_segments_history",
        [],
        [
            "symbol",
            "report",
            "category"
        ]
    ],
    "buyback": [
        "GET",
        "/buyback",
        [],
        [
            "symbol"
        ]
    ],
    "company": [
        "GET",
        "/company",
        [],
        [
            "symbol"
        ]
    ],
    "consensus": [
        "GET",
        "/consensus",
        [],
        [
            "symbol"
        ]
    ],
    "constituent": [
        "GET",
        "/constituent",
        [],
        [
            "symbol"
        ]
    ],
    "corp_action": [
        "GET",
        "/corp_action",
        [],
        [
            "symbol"
        ]
    ],
    "dividend": [
        "GET",
        "/dividend",
        [],
        [
            "symbol",
            "page",
            "size",
            "year"
        ]
    ],
    "dividend_detail": [
        "GET",
        "/dividend_detail",
        [],
        [
            "symbol"
        ]
    ],
    "estimate_max_buy_quantity": [
        "GET",
        "/v1/trade/estimate/buy_limit",
        [],
        [
            "symbol",
            "orderType",
            "side",
            "price",
            "currency",
            "market",
            "fractionalShares",
            "orderId"
        ]
    ],
    "exchange_rate": [
        "GET",
        "/exchange_rate",
        [],
        []
    ],
    "executive": [
        "GET",
        "/executive",
        [],
        [
            "symbol"
        ]
    ],
    "finance_calendar": [
        "GET",
        "/finance_calendar",
        [],
        [
            "startDate",
            "endDate",
            "categories",
            "symbols",
            "market",
            "count",
            "star"
        ]
    ],
    "financial_report": [
        "GET",
        "/financial_report",
        [],
        [
            "symbol",
            "kind",
            "period"
        ]
    ],
    "financial_report_latest": [
        "GET",
        "/financial_report_latest",
        [],
        [
            "symbol"
        ]
    ],
    "financial_report_snapshot": [
        "GET",
        "/financial_report_snapshot",
        [],
        [
            "symbol",
            "report",
            "fiscalYear",
            "fiscalPeriod"
        ]
    ],
    "financial_statement": [
        "GET",
        "/financial_statement",
        [],
        [
            "symbol",
            "kind",
            "period"
        ]
    ],
    "forecast_eps": [
        "GET",
        "/forecast_eps",
        [],
        [
            "symbol"
        ]
    ],
    "fund_holder": [
        "GET",
        "/fund_holder",
        [],
        [
            "symbol",
            "limit"
        ]
    ],
    "get_market_temperature": [
        "GET",
        "/v1/quote/market_temperature",
        [],
        [
            "market"
        ]
    ],
    "get_order_detail": [
        "GET",
        "/v1/trade/order",
        [],
        [
            "orderId"
        ]
    ],
    "industry_peers": [
        "GET",
        "/industry_peers",
        [],
        [
            "symbol",
            "market"
        ]
    ],
    "industry_valuation": [
        "GET",
        "/industry_valuation",
        [],
        [
            "symbol",
            "currency"
        ]
    ],
    "industry_valuation_dist": [
        "GET",
        "/industry_valuation_dist",
        [],
        [
            "symbol"
        ]
    ],
    "institution_rating": [
        "GET",
        "/institution_rating",
        [],
        [
            "symbol"
        ]
    ],
    "institution_rating_detail": [
        "GET",
        "/institution_rating_detail",
        [],
        [
            "symbol"
        ]
    ],
    "institution_rating_history": [
        "GET",
        "/institution_rating_history",
        [],
        [
            "symbol"
        ]
    ],
    "institution_rating_industry_rank": [
        "GET",
        "/institution_rating_industry_rank",
        [],
        [
            "symbol",
            "page",
            "size"
        ]
    ],
    "institutional_views": [
        "GET",
        "/institutional_views",
        [],
        [
            "symbol"
        ]
    ],
    "invest_relation": [
        "GET",
        "/invest_relation",
        [],
        [
            "symbol",
            "count"
        ]
    ],
    "list_account_cash": [
        "GET",
        "/v1/asset/account",
        [],
        [
            "currency"
        ]
    ],
    "list_cash_flow": [
        "GET",
        "/v1/asset/cashflow",
        [],
        [
            "startTime",
            "endTime",
            "businessType",
            "symbols",
            "page",
            "size"
        ]
    ],
    "list_filings": [
        "GET",
        "/v1/quote/filings",
        [],
        [
            "symbol"
        ]
    ],
    "list_fund_positions": [
        "GET",
        "/v1/asset/fund",
        [],
        [
            "symbols"
        ]
    ],
    "list_history_executions": [
        "GET",
        "/v1/trade/execution/history",
        [],
        [
            "startAt",
            "endAt",
            "orderId",
            "symbol",
            "page"
        ]
    ],
    "list_history_orders": [
        "GET",
        "/v1/trade/order/history",
        [],
        [
            "startAt",
            "endAt",
            "symbol",
            "market",
            "side",
            "statuses",
            "page",
            "size"
        ]
    ],
    "list_market_temperature": [
        "GET",
        "/v1/quote/history_market_temperature",
        [],
        [
            "market",
            "startDate",
            "endDate"
        ]
    ],
    "list_news": [
        "GET",
        "/v1/content/{encodePathSegment}/news",
        [
            "encodePathSegment"
        ],
        [
            "symbol"
        ]
    ],
    "list_securities": [
        "GET",
        "/v1/quote/get_security_list",
        [],
        [
            "market",
            "category"
        ]
    ],
    "list_stock_positions": [
        "GET",
        "/v1/asset/stock",
        [],
        [
            "symbols"
        ]
    ],
    "list_today_executions": [
        "GET",
        "/v1/trade/execution/today",
        [],
        [
            "orderId",
            "symbol"
        ]
    ],
    "list_today_orders": [
        "GET",
        "/v1/trade/order/today",
        [],
        [
            "symbol",
            "market",
            "side",
            "statuses",
            "orderId",
            "page",
            "size"
        ]
    ],
    "list_watchlist_groups": [
        "GET",
        "/v1/watchlist/groups",
        [],
        []
    ],
    "market_status": [
        "GET",
        "/market_status",
        [],
        []
    ],
    "market_stock_events": [
        "GET",
        "/market_stock_events",
        [],
        [
            "markets",
            "limit",
            "sort",
            "date"
        ]
    ],
    "news": [
        "GET",
        "/news",
        [],
        [
            "symbol"
        ]
    ],
    "operating": [
        "GET",
        "/operating",
        [],
        [
            "symbol",
            "report"
        ]
    ],
    "option_volume": [
        "GET",
        "/option_volume",
        [],
        [
            "symbol"
        ]
    ],
    "option_volume_daily": [
        "GET",
        "/option_volume_daily",
        [],
        [
            "symbol",
            "timestamp",
            "count"
        ]
    ],
    "profit_analysis": [
        "GET",
        "/profit_analysis",
        [],
        [
            "startDate",
            "endDate"
        ]
    ],
    "profit_analysis_by_market": [
        "GET",
        "/profit_analysis_by_market",
        [],
        [
            "market",
            "startDate",
            "endDate",
            "currency",
            "page",
            "size"
        ]
    ],
    "profit_analysis_detail": [
        "GET",
        "/profit_analysis_detail",
        [],
        [
            "symbol",
            "startDate",
            "endDate"
        ]
    ],
    "profit_analysis_flows": [
        "GET",
        "/profit_analysis_flows",
        [],
        [
            "symbol",
            "page",
            "size",
            "derivative",
            "startDate",
            "endDate"
        ]
    ],
    "profit_analysis_sublist": [
        "GET",
        "/profit_analysis_sublist",
        [],
        [
            "profitOrLoss",
            "startDate",
            "endDate"
        ]
    ],
    "rank_categories": [
        "GET",
        "/rank_categories",
        [],
        []
    ],
    "rank_list": [
        "GET",
        "/rank_list",
        [],
        [
            "key",
            "needArticle",
            "market",
            "size"
        ]
    ],
    "screener_indicators": [
        "GET",
        "/screener_indicators",
        [],
        []
    ],
    "screener_recommend_strategies": [
        "GET",
        "/screener_recommend_strategies",
        [],
        [
            "market"
        ]
    ],
    "screener_search": [
        "GET",
        "/screener_search",
        [],
        [
            "market",
            "filters",
            "conditions",
            "returns",
            "extraReturns",
            "page",
            "size",
            "sortByKey",
            "sortBy",
            "sortOrder"
        ]
    ],
    "screener_strategy": [
        "GET",
        "/screener_strategy",
        [],
        [
            "id"
        ]
    ],
    "screener_user_strategies": [
        "GET",
        "/screener_user_strategies",
        [],
        [
            "market"
        ]
    ],
    "shareholder": [
        "GET",
        "/shareholder",
        [],
        [
            "symbol",
            "range",
            "sortField",
            "sortOrder"
        ]
    ],
    "shareholder_detail": [
        "GET",
        "/shareholder_detail",
        [],
        [
            "symbol",
            "objectId"
        ]
    ],
    "shareholder_top": [
        "GET",
        "/shareholder_top",
        [],
        [
            "symbol"
        ]
    ],
    "short_margin": [
        "GET",
        "/short_margin",
        [],
        []
    ],
    "short_positions": [
        "GET",
        "/short_positions",
        [],
        [
            "symbol",
            "lastTimestamp",
            "count"
        ]
    ],
    "short_trades": [
        "GET",
        "/short_trades",
        [],
        [
            "symbol",
            "lastTimestamp",
            "count"
        ]
    ],
    "stock_rating_history": [
        "GET",
        "/stock_rating_history",
        [],
        [
            "symbol"
        ]
    ],
    "stock_ratings": [
        "GET",
        "/stock_ratings",
        [],
        [
            "symbol"
        ]
    ],
    "trade_stats": [
        "GET",
        "/trade_stats",
        [],
        [
            "symbol"
        ]
    ],
    "valuation": [
        "GET",
        "/valuation",
        [],
        [
            "symbol",
            "indicator",
            "range"
        ]
    ],
    "valuation_comparison": [
        "GET",
        "/valuation_comparison",
        [],
        [
            "symbol",
            "currency",
            "comparisonSymbols"
        ]
    ],
    "valuation_history": [
        "GET",
        "/valuation_history",
        [],
        [
            "symbol",
            "indicator"
        ]
    ],
    "valuation_rank": [
        "GET",
        "/valuation_rank",
        [],
        [
            "symbol",
            "startDate",
            "endDate"
        ]
    ]
}

class LongbridgeDynamicAction(Action):
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
            raise ValueError(f"Longbridge API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class LongbridgeProvider(Provider):
    def __init__(self):
        super().__init__(
            service="longbridge",
            display_name="Longbridge",
            category="Finance & Accounting",
            auth_types=["oauth2"],
            description="Longbridge securities brokerage, market data, and portfolio intelligence with 80 actions."
        )
        for act in get_provider_actions("longbridge"):
            self.register_action(LongbridgeDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://openapi.longbridge.com/v1/user/me"
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
            raise ValueError(f"Longbridge connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Longbridge credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Longbridge validation failed: {resp.status_code} {resp.text}")

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
            "display_name": f"Longbridge Account"
        }

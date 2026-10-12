"""
Alpha Vantage Provider for ConnectorHub.
Loads and registers 44 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://www.alphavantage.co"

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

    auth_mode = "alpha_vantage"
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
    "call_official_function": [
        "GET",
        "/query",
        [],
        [
            "functionName",
            "parameters",
            "responseFormat"
        ]
    ],
    "get_balance_sheet": [
        "GET",
        "/balance_sheet",
        [],
        [
            "symbol"
        ]
    ],
    "get_cash_flow": [
        "GET",
        "/cash_flow",
        [],
        [
            "symbol"
        ]
    ],
    "get_commodity_data": [
        "GET",
        "/commodity_data",
        [],
        [
            "commodity",
            "interval",
            "datatype"
        ]
    ],
    "get_company_overview": [
        "GET",
        "/company_overview",
        [],
        [
            "symbol"
        ]
    ],
    "get_crypto_intraday": [
        "GET",
        "/crypto_intraday",
        [],
        [
            "symbol",
            "market",
            "interval"
        ]
    ],
    "get_currency_exchange_rate": [
        "GET",
        "/currency_exchange_rate",
        [],
        [
            "fromSymbol",
            "toSymbol"
        ]
    ],
    "get_daily_adjusted_time_series": [
        "GET",
        "/daily_adjusted_time_series",
        [],
        [
            "symbol",
            "outputSize",
            "datatype"
        ]
    ],
    "get_daily_time_series": [
        "GET",
        "/daily_time_series",
        [],
        [
            "symbol",
            "outputSize"
        ]
    ],
    "get_digital_currency_daily": [
        "GET",
        "/digital_currency_daily",
        [],
        [
            "symbol",
            "market"
        ]
    ],
    "get_digital_currency_monthly": [
        "GET",
        "/digital_currency_monthly",
        [],
        [
            "symbol",
            "market"
        ]
    ],
    "get_digital_currency_weekly": [
        "GET",
        "/digital_currency_weekly",
        [],
        [
            "symbol",
            "market"
        ]
    ],
    "get_dividends": [
        "GET",
        "/dividends",
        [],
        [
            "symbol"
        ]
    ],
    "get_earnings": [
        "GET",
        "/earnings",
        [],
        [
            "symbol"
        ]
    ],
    "get_earnings_calendar": [
        "GET",
        "/earnings_calendar",
        [],
        [
            "symbol",
            "horizon"
        ]
    ],
    "get_earnings_call_transcript": [
        "GET",
        "/earnings_call_transcript",
        [],
        [
            "symbol",
            "quarter",
            "fiscalYear"
        ]
    ],
    "get_earnings_estimates": [
        "GET",
        "/earnings_estimates",
        [],
        [
            "symbol"
        ]
    ],
    "get_etf_profile": [
        "GET",
        "/etf_profile",
        [],
        [
            "symbol"
        ]
    ],
    "get_fx_daily": [
        "GET",
        "/fx_daily",
        [],
        [
            "fromSymbol",
            "toSymbol",
            "outputSize",
            "datatype"
        ]
    ],
    "get_fx_intraday": [
        "GET",
        "/fx_intraday",
        [],
        [
            "fromSymbol",
            "toSymbol",
            "interval",
            "outputSize",
            "datatype"
        ]
    ],
    "get_fx_monthly": [
        "GET",
        "/fx_monthly",
        [],
        [
            "fromSymbol",
            "toSymbol"
        ]
    ],
    "get_fx_weekly": [
        "GET",
        "/fx_weekly",
        [],
        [
            "fromSymbol",
            "toSymbol"
        ]
    ],
    "get_global_quote": [
        "GET",
        "/global_quote",
        [],
        [
            "symbol"
        ]
    ],
    "get_historical_options": [
        "GET",
        "/historical_options",
        [],
        [
            "symbol",
            "date"
        ]
    ],
    "get_income_statement": [
        "GET",
        "/income_statement",
        [],
        [
            "symbol"
        ]
    ],
    "get_insider_transactions": [
        "GET",
        "/insider_transactions",
        [],
        [
            "symbol"
        ]
    ],
    "get_institutional_holdings": [
        "GET",
        "/institutional_holdings",
        [],
        [
            "symbol"
        ]
    ],
    "get_intraday_time_series": [
        "GET",
        "/intraday_time_series",
        [],
        [
            "symbol",
            "interval",
            "adjusted",
            "extendedHours",
            "month",
            "outputSize",
            "datatype"
        ]
    ],
    "get_ipo_calendar": [
        "GET",
        "/ipo_calendar",
        [],
        []
    ],
    "get_listing_status": [
        "GET",
        "/listing_status",
        [],
        [
            "date",
            "state"
        ]
    ],
    "get_macro_indicator": [
        "GET",
        "/macro_indicator",
        [],
        [
            "indicator",
            "interval",
            "maturity",
            "datatype"
        ]
    ],
    "get_market_status": [
        "GET",
        "/market_status",
        [],
        []
    ],
    "get_monthly_adjusted_time_series": [
        "GET",
        "/monthly_adjusted_time_series",
        [],
        [
            "symbol"
        ]
    ],
    "get_monthly_time_series": [
        "GET",
        "/monthly_time_series",
        [],
        [
            "symbol"
        ]
    ],
    "get_news_sentiment": [
        "GET",
        "/news_sentiment",
        [],
        [
            "tickers",
            "topics",
            "timeFrom",
            "timeTo",
            "sort",
            "limit"
        ]
    ],
    "get_realtime_bulk_quotes": [
        "GET",
        "/realtime_bulk_quotes",
        [],
        [
            "symbols"
        ]
    ],
    "get_realtime_options": [
        "GET",
        "/realtime_options",
        [],
        [
            "symbol",
            "requireGreeks",
            "contract"
        ]
    ],
    "get_sector_performance": [
        "GET",
        "/sector_performance",
        [],
        []
    ],
    "get_splits": [
        "GET",
        "/splits",
        [],
        [
            "symbol"
        ]
    ],
    "get_technical_indicator": [
        "GET",
        "/technical_indicator",
        [],
        [
            "indicator",
            "symbol",
            "interval",
            "timePeriod",
            "seriesType",
            "month",
            "fastPeriod",
            "slowPeriod",
            "signalPeriod",
            "fastKPeriod",
            "slowKPeriod",
            "slowDPeriod",
            "slowKMatype",
            "slowDMatype",
            "fastDPeriod",
            "fastDMatype",
            "fastMatype",
            "slowMatype",
            "signalMatype",
            "matype",
            "nbdevup",
            "nbdevdn",
            "acceleration",
            "maximum",
            "datatype"
        ]
    ],
    "get_top_gainers_losers": [
        "GET",
        "/top_gainers_losers",
        [],
        []
    ],
    "get_weekly_adjusted_time_series": [
        "GET",
        "/weekly_adjusted_time_series",
        [],
        [
            "symbol"
        ]
    ],
    "get_weekly_time_series": [
        "GET",
        "/weekly_time_series",
        [],
        [
            "symbol"
        ]
    ],
    "search_symbols": [
        "GET",
        "/search_symbols",
        [],
        [
            "keywords"
        ]
    ]
}

class AlphaVantageDynamicAction(Action):
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
        if "alpha_vantage" in ["alpha_vantage", "fmp"] and token:
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
            raise ValueError(f"Alpha Vantage API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class AlphaVantageProvider(Provider):
    def __init__(self):
        super().__init__(
            service="alpha_vantage",
            display_name="Alpha Vantage",
            category="Finance & Accounting",
            auth_types=["api_key"],
            description="Alpha Vantage real-time and historical financial market data, crypto, and technical indicators with 44 actions."
        )
        for act in get_provider_actions("alpha_vantage"):
            self.register_action(AlphaVantageDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM"
        for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        token = _extract_token(cred)
        if "alpha_vantage" in ["alpha_vantage", "fmp"] and token:
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
            raise ValueError(f"Alpha Vantage connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Alpha Vantage credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Alpha Vantage validation failed: {resp.status_code} {resp.text}")

        # For Alpha Vantage, invalid API key returns 200 with 'Information' or 'Error Message'
        if "alpha_vantage" == "alpha_vantage":
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
            "display_name": f"Alpha Vantage Account"
        }

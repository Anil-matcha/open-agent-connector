"""
Polygon.io Provider for ConnectorHub.
Loads and registers 40 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.polygon.io"

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
    "get_aggregate_bars": [
        "GET",
        "/v2/aggs/ticker/{encodeURIComponent}/range/{multiplier}/{encodeURIComponent}/{encodeURIComponent}/{encodeURIComponent}",
        [
            "encodeURIComponent",
            "multiplier",
            "encodeURIComponent",
            "encodeURIComponent",
            "encodeURIComponent"
        ],
        [
            "ticker",
            "timespan",
            "from",
            "to",
            "adjusted",
            "sort",
            "limit"
        ]
    ],
    "get_daily_open_close": [
        "GET",
        "/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}",
        [
            "ticker"
        ],
        [
            "date",
            "adjusted"
        ]
    ],
    "get_ema": [
        "GET",
        "/v1/indicators/ema/{ticker}",
        [
            "ticker"
        ],
        [
            "timespan",
            "window",
            "adjusted",
            "expandUnderlying",
            "seriesType",
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "get_last_stock_quote": [
        "GET",
        "/v2/last/nbbo/{ticker}",
        [
            "ticker"
        ],
        []
    ],
    "get_last_stock_trade": [
        "GET",
        "/v2/last/trade/{ticker}",
        [
            "ticker"
        ],
        []
    ],
    "get_macd": [
        "GET",
        "/v1/indicators/macd/{ticker}",
        [
            "ticker"
        ],
        [
            "timespan",
            "shortWindow",
            "longWindow",
            "signalWindow",
            "adjusted",
            "expandUnderlying",
            "seriesType",
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "get_market_status": [
        "GET",
        "/v1/marketstatus/now",
        [],
        []
    ],
    "get_option_chain_snapshot": [
        "GET",
        "/v3/snapshot/options/{underlyingTicker}",
        [
            "underlyingTicker"
        ],
        [
            "contractType",
            "expirationDate",
            "expirationDateGte",
            "expirationDateLte",
            "strikePrice",
            "strikePriceGte",
            "strikePriceLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "get_option_contract": [
        "GET",
        "/v3/reference/options/contracts/{optionsTicker}",
        [
            "optionsTicker"
        ],
        [
            "asOf"
        ]
    ],
    "get_option_contract_snapshot": [
        "GET",
        "/v3/snapshot/options/{underlyingTicker}/{optionsTicker}",
        [
            "underlyingTicker",
            "optionsTicker"
        ],
        []
    ],
    "get_previous_day_bar": [
        "GET",
        "/v2/aggs/ticker/{encodeURIComponent}/prev",
        [
            "encodeURIComponent"
        ],
        [
            "ticker",
            "adjusted"
        ]
    ],
    "get_rsi": [
        "GET",
        "/v1/indicators/rsi/{ticker}",
        [
            "ticker"
        ],
        [
            "timespan",
            "window",
            "adjusted",
            "expandUnderlying",
            "seriesType",
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "get_sma": [
        "GET",
        "/v1/indicators/sma/{ticker}",
        [
            "ticker"
        ],
        [
            "timespan",
            "window",
            "adjusted",
            "expandUnderlying",
            "seriesType",
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "get_stock_movers": [
        "GET",
        "/v3/trades/{ticker}",
        [
            "ticker"
        ],
        [
            "direction"
        ]
    ],
    "get_stock_snapshot": [
        "GET",
        "/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}",
        [
            "ticker"
        ],
        []
    ],
    "get_ticker_details": [
        "GET",
        "/v3/reference/tickers/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "ticker",
            "date"
        ]
    ],
    "get_unified_snapshot": [
        "GET",
        "/v3/snapshot",
        [],
        [
            "tickers",
            "assetType",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_balance_sheets": [
        "GET",
        "/stocks/financials/v1/balance-sheets",
        [],
        [
            "tickers",
            "cik",
            "timeframe",
            "fiscalYear",
            "fiscalQuarter",
            "periodEnd",
            "periodEndGte",
            "periodEndLte",
            "filingDateGte",
            "filingDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_cash_flow_statements": [
        "GET",
        "/stocks/financials/v1/cash-flow-statements",
        [],
        [
            "tickers",
            "cik",
            "timeframe",
            "fiscalYear",
            "fiscalQuarter",
            "periodEnd",
            "periodEndGte",
            "periodEndLte",
            "filingDateGte",
            "filingDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_condition_codes": [
        "GET",
        "/v3/reference/conditions",
        [],
        [
            "assetClass",
            "dataType",
            "id",
            "sipMapping"
        ]
    ],
    "list_dividends": [
        "GET",
        "/stocks/v1/dividends",
        [],
        [
            "ticker",
            "exDividendDate",
            "exDividendDateGte",
            "exDividendDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_exchanges": [
        "GET",
        "/v3/reference/exchanges",
        [],
        [
            "assetClass",
            "locale"
        ]
    ],
    "list_financial_ratios": [
        "GET",
        "/stocks/financials/v1/ratios",
        [],
        [
            "tickers",
            "cik",
            "timeframe",
            "fiscalYear",
            "fiscalQuarter",
            "periodEnd",
            "periodEndGte",
            "periodEndLte",
            "filingDateGte",
            "filingDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_funding_conditions": [
        "GET",
        "/fed/v1/funding-conditions",
        [],
        [
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_income_statements": [
        "GET",
        "/stocks/financials/v1/income-statements",
        [],
        [
            "tickers",
            "cik",
            "timeframe",
            "fiscalYear",
            "fiscalQuarter",
            "periodEnd",
            "periodEndGte",
            "periodEndLte",
            "filingDateGte",
            "filingDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_inflation": [
        "GET",
        "/fed/v1/inflation",
        [],
        [
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_inflation_expectations": [
        "GET",
        "/fed/v1/inflation-expectations",
        [],
        [
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_labor_market": [
        "GET",
        "/fed/v1/labor-market",
        [],
        [
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_market_holidays": [
        "GET",
        "/v1/marketstatus/upcoming",
        [],
        []
    ],
    "list_option_contracts": [
        "GET",
        "/v3/reference/options/contracts",
        [],
        [
            "underlyingTicker",
            "contractType",
            "expirationDate",
            "expirationDateGte",
            "expirationDateLte",
            "strikePrice",
            "expired",
            "asOf",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_quotes": [
        "GET",
        "/v3/quotes/{ticker}",
        [
            "ticker"
        ],
        [
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_related_tickers": [
        "GET",
        "/v1/related-companies/{ticker}",
        [
            "ticker"
        ],
        []
    ],
    "list_short_interest": [
        "GET",
        "/stocks/v1/short-interest",
        [],
        [
            "ticker",
            "settlementDate",
            "settlementDateGte",
            "settlementDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_short_volume": [
        "GET",
        "/stocks/v1/short-volume",
        [],
        [
            "ticker",
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_splits": [
        "GET",
        "/stocks/v1/splits",
        [],
        [
            "ticker",
            "executionDate",
            "executionDateGte",
            "executionDateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_ticker_news": [
        "GET",
        "/v2/reference/news",
        [],
        [
            "ticker",
            "publishedUtcGte",
            "publishedUtcLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_ticker_types": [
        "GET",
        "/v3/reference/tickers/types",
        [],
        [
            "assetClass",
            "locale"
        ]
    ],
    "list_tickers": [
        "GET",
        "/v3/reference/tickers",
        [],
        [
            "ticker",
            "type",
            "market",
            "exchange",
            "cusip",
            "cik",
            "date",
            "search",
            "active",
            "tickerGte",
            "tickerGt",
            "tickerLte",
            "tickerLt",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_trades": [
        "GET",
        "/v3/trades/{ticker}",
        [
            "ticker"
        ],
        [
            "timestamp",
            "timestampGte",
            "timestampLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ],
    "list_treasury_yields": [
        "GET",
        "/fed/v1/treasury-yields",
        [],
        [
            "date",
            "dateGte",
            "dateLte",
            "order",
            "limit",
            "sort",
            "cursor"
        ]
    ]
}

class PolygonIoDynamicAction(Action):
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
            raise ValueError(f"Polygon.io API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PolygonIoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="polygon_io",
            display_name="Polygon.io",
            category="Finance & Accounting",
            auth_types=["api_key"],
            description="Polygon.io financial market data APIs for stocks, options, forex, and crypto with 40 actions."
        )
        for act in get_provider_actions("polygon_io"):
            self.register_action(PolygonIoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.polygon.io/v3/reference/tickers?limit=1"
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
            raise ValueError(f"Polygon.io connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Polygon.io credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Polygon.io validation failed: {resp.status_code} {resp.text}")

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
            "display_name": f"Polygon.io Account"
        }

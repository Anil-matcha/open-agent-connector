"""
Financial Modeling Prep Provider for ConnectorHub.
Loads and registers 37 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://financialmodelingprep.com/stable"

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

    auth_mode = "fmp"
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
    "get_analyst_estimates": [
        "GET",
        "/analyst-estimates",
        [],
        [
            "symbol",
            "period",
            "page",
            "limit"
        ]
    ],
    "get_asset_quote": [
        "POST",
        "/batch-commodity-quotes",
        [],
        [
            "assetType",
            "symbol"
        ]
    ],
    "get_balance_sheet_statement": [
        "GET",
        "/balance-sheet-statement",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_calendar": [
        "GET",
        "/earnings-calendar",
        [],
        [
            "type",
            "from",
            "to"
        ]
    ],
    "get_cash_flow_statement": [
        "GET",
        "/cash-flow-statement",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_company_executives": [
        "GET",
        "/key-executives",
        [],
        [
            "symbol"
        ]
    ],
    "get_company_notes": [
        "GET",
        "/company-notes",
        [],
        [
            "symbol"
        ]
    ],
    "get_company_peers": [
        "GET",
        "/stock-peers",
        [],
        [
            "symbol"
        ]
    ],
    "get_company_profile": [
        "GET",
        "/profile",
        [],
        [
            "symbol"
        ]
    ],
    "get_company_profile_by_cik": [
        "GET",
        "/profile-cik",
        [],
        [
            "cik"
        ]
    ],
    "get_congressional_trades": [
        "GET",
        "/{chamber}-latest",
        [
            "chamber"
        ],
        [
            "symbol",
            "name",
            "page",
            "limit"
        ]
    ],
    "get_dcf": [
        "GET",
        "/discounted-cash-flow",
        [],
        [
            "symbol"
        ]
    ],
    "get_economic_indicators": [
        "GET",
        "/economic-indicators",
        [],
        [
            "name",
            "from",
            "to"
        ]
    ],
    "get_enterprise_values": [
        "GET",
        "/enterprise-values",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_etf_holdings": [
        "GET",
        "/etf/holdings",
        [],
        [
            "symbol"
        ]
    ],
    "get_financial_ratios": [
        "GET",
        "/ratios",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_financial_scores": [
        "GET",
        "/financial-scores",
        [],
        [
            "symbol"
        ]
    ],
    "get_financial_statement_growth": [
        "GET",
        "/income-statement-growth",
        [],
        [
            "statementType",
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_historical_prices": [
        "GET",
        "/historical-price-eod/full",
        [],
        [
            "symbol",
            "from",
            "to"
        ]
    ],
    "get_income_statement": [
        "GET",
        "/income-statement",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_insider_trades": [
        "GET",
        "/insider-trading/latest",
        [],
        [
            "symbol",
            "reportingCik",
            "transactionType",
            "page",
            "limit"
        ]
    ],
    "get_intraday_prices": [
        "GET",
        "/historical-chart/1min",
        [],
        [
            "symbol",
            "interval",
            "from",
            "to"
        ]
    ],
    "get_key_metrics": [
        "GET",
        "/key-metrics",
        [],
        [
            "symbol",
            "period",
            "limit"
        ]
    ],
    "get_market_cap": [
        "GET",
        "/market-capitalization",
        [],
        [
            "symbol"
        ]
    ],
    "get_market_movers": [
        "GET",
        "/biggest-gainers",
        [],
        [
            "type"
        ]
    ],
    "get_market_performance": [
        "GET",
        "/sector-performance-snapshot",
        [],
        [
            "type"
        ]
    ],
    "get_news": [
        "GET",
        "/news/general-latest",
        [],
        [
            "type",
            "symbols",
            "page",
            "limit"
        ]
    ],
    "get_quote": [
        "GET",
        "/quote-short",
        [],
        [
            "symbol"
        ]
    ],
    "get_quote_short": [
        "GET",
        "/quote-short",
        [],
        [
            "symbol"
        ]
    ],
    "get_ratings": [
        "GET",
        "/ratings-snapshot",
        [],
        [
            "type",
            "symbol",
            "limit"
        ]
    ],
    "get_sec_filings": [
        "GET",
        "/latest-filings",
        [],
        [
            "symbol",
            "cik",
            "formType",
            "from",
            "to",
            "page",
            "limit"
        ]
    ],
    "get_shares_float": [
        "GET",
        "/shares-float",
        [],
        [
            "symbol"
        ]
    ],
    "get_technical_indicator": [
        "GET",
        "/technical-indicators/{indicator}",
        [
            "indicator"
        ],
        [
            "symbol",
            "periodLength",
            "timeframe",
            "from",
            "to"
        ]
    ],
    "list_directory": [
        "GET",
        "/stock-list",
        [],
        [
            "type"
        ]
    ],
    "search_company_screener": [
        "GET",
        "/company-screener",
        [],
        [
            "marketCapMoreThan",
            "marketCapLowerThan",
            "priceMoreThan",
            "priceLowerThan",
            "betaMoreThan",
            "betaLowerThan",
            "volumeMoreThan",
            "volumeLowerThan",
            "dividendMoreThan",
            "dividendLowerThan",
            "isEtf",
            "isFund",
            "sector",
            "industry",
            "country",
            "exchange",
            "limit"
        ]
    ],
    "search_names": [
        "GET",
        "/search-name",
        [],
        [
            "query",
            "limit",
            "exchange"
        ]
    ],
    "search_symbols": [
        "GET",
        "/search-symbol",
        [],
        [
            "query",
            "limit",
            "exchange"
        ]
    ]
}

class FinancialModelingPrepDynamicAction(Action):
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
        if "fmp" in ["alpha_vantage", "fmp"] and token:
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
            raise ValueError(f"Financial Modeling Prep API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class FinancialModelingPrepProvider(Provider):
    def __init__(self):
        super().__init__(
            service="financial_modeling_prep",
            display_name="Financial Modeling Prep",
            category="Finance & Accounting",
            auth_types=["api_key"],
            description="Financial Modeling Prep stock market data, financial statements, valuation, and analytics with 37 actions."
        )
        for act in get_provider_actions("financial_modeling_prep"):
            self.register_action(FinancialModelingPrepDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://financialmodelingprep.com/stable/profile?symbol=AAPL"
        for key in ["site", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        token = _extract_token(cred)
        if "fmp" in ["alpha_vantage", "fmp"] and token:
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
            raise ValueError(f"Financial Modeling Prep connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Financial Modeling Prep credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Financial Modeling Prep validation failed: {resp.status_code} {resp.text}")

        # For Alpha Vantage, invalid API key returns 200 with 'Information' or 'Error Message'
        if "fmp" == "alpha_vantage":
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
            "display_name": f"Financial Modeling Prep Account"
        }

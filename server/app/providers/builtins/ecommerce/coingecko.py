"""
CoinGecko Provider for ConnectorHub.
Loads and registers 25 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.coingecko.com/api/v3"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "coingecko" in ["shopify_admin", "shopify_storefront"]:
        shop = str(cred.get("shopDomain") or cred.get("shop") or "default.myshopify.com").strip()
        shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
        return base.replace("{shopDomain}", shop).rstrip("/")

    if "coingecko" == "shopify_partner":
        org_id = str(cred.get("organizationId") or cred.get("orgId") or "1").strip()
        return base.replace("{organizationId}", org_id).rstrip("/")

    if "coingecko" == "sendbird":
        app_id = str(cred.get("applicationId") or cred.get("appId") or "default").strip()
        return base.replace("{applicationId}", app_id).rstrip("/")

    if "coingecko" == "listmonk":
        val = str(cred.get("baseUrl") or "https://listmonk.example.com").strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = f"https://{val}"
        return val.rstrip("/")

    for key in ["domain", "subdomain", "site", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base.rstrip("/")

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "coingecko"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "shopify_admin":
        if token:
            headers["X-Shopify-Access-Token"] = token
    elif auth_mode == "shopify_storefront":
        if token:
            headers["X-Shopify-Storefront-Access-Token"] = token
    elif auth_mode == "coingecko":
        if token:
            is_pro = str(cred.get("plan") or "").lower() == "pro"
            header_name = "x-cg-pro-api-key" if is_pro else "x-cg-demo-api-key"
            headers[header_name] = token
    elif auth_mode == "sendbird":
        if token:
            headers["Api-Token"] = token
    elif auth_mode == "listmonk":
        user = str(cred.get("apiUser") or cred.get("username") or "").strip()
        if user and token:
            pair = f"{user}:{token}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mailgun":
        if token:
            pair = f"api:{token}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "flexmail":
        acc_id = str(cred.get("accountId") or "").strip()
        pat = token or str(cred.get("personalAccessToken") or "").strip()
        if acc_id and pat:
            pair = f"{acc_id}:{pat}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "crisp":
        token_id = str(cred.get("tokenIdentifier") or "").strip()
        token_key = token or str(cred.get("tokenKey") or "").strip()
        if token_id and token_key:
            pair = f"{token_id}:{token_key}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
        if cred.get("tokenTier"):
            headers["X-Crisp-Tier"] = str(cred["tokenTier"]).strip()
    elif auth_mode == "vonage":
        api_key = str(cred.get("apiKey") or token or "").strip()
        api_secret = str(cred.get("apiSecret") or "").strip()
        if api_key and api_secret:
            pair = f"{api_key}:{api_secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "onesignal":
        if token:
            headers["Authorization"] = f"Key {token}"

    return headers

ROUTES: Dict[str, List[Any]] = {
    "get_coin": [
        "GET",
        "/get/coin",
        [],
        [
            "id",
            "localization",
            "tickers",
            "market_data",
            "sparkline",
            "include_categories_details",
            "dex_pair_format"
        ]
    ],
    "get_coin_by_contract": [
        "GET",
        "/get/coin/by/contract",
        [],
        [
            "asset_platform_id",
            "contract_address"
        ]
    ],
    "get_coin_history": [
        "GET",
        "/get/coin/history",
        [],
        [
            "id",
            "date",
            "localization"
        ]
    ],
    "get_coin_ohlc": [
        "GET",
        "/get/coin/ohlc",
        [],
        [
            "id",
            "vs_currency",
            "days",
            "interval",
            "precision"
        ]
    ],
    "get_global_market_data": [
        "PATCH",
        "/get/global/market/data",
        [],
        []
    ],
    "get_market_chart": [
        "PATCH",
        "/get/market/chart",
        [],
        [
            "id",
            "vs_currency",
            "days",
            "interval",
            "precision"
        ]
    ],
    "get_market_chart_range": [
        "PATCH",
        "/get/market/chart/range",
        [],
        [
            "id",
            "vs_currency",
            "from",
            "to",
            "interval",
            "precision"
        ]
    ],
    "get_onchain_pool": [
        "GET",
        "/get/onchain/pool",
        [],
        [
            "network",
            "pool_address",
            "include",
            "include_volume_breakdown",
            "include_composition"
        ]
    ],
    "get_onchain_token": [
        "GET",
        "/get/onchain/token",
        [],
        [
            "network",
            "token_address",
            "include",
            "include_composition",
            "include_inactive_source"
        ]
    ],
    "get_onchain_token_info": [
        "GET",
        "/get/onchain/token/info",
        [],
        [
            "network",
            "token_address"
        ]
    ],
    "get_pool_ohlcv": [
        "GET",
        "/get/pool/ohlcv",
        [],
        [
            "network",
            "pool_address",
            "timeframe",
            "aggregate",
            "before_timestamp",
            "limit",
            "currency",
            "token",
            "include_empty_intervals"
        ]
    ],
    "get_prices": [
        "GET",
        "/get/prices",
        [],
        [
            "vs_currencies",
            "ids",
            "names",
            "symbols",
            "include_tokens",
            "include_market_cap",
            "include_24hr_vol",
            "include_24hr_change",
            "include_last_updated_at",
            "precision"
        ]
    ],
    "get_token_prices": [
        "GET",
        "/get/token/prices",
        [],
        [
            "asset_platform_id",
            "contract_addresses",
            "vs_currencies",
            "include_market_cap",
            "include_24hr_vol",
            "include_24hr_change",
            "include_last_updated_at",
            "precision"
        ]
    ],
    "get_trending": [
        "GET",
        "/get/trending",
        [],
        [
            "show_max"
        ]
    ],
    "list_asset_platforms": [
        "POST",
        "/list/asset/platforms",
        [],
        [
            "filter"
        ]
    ],
    "list_category_markets": [
        "PATCH",
        "/list/category/markets",
        [],
        [
            "order"
        ]
    ],
    "list_coin_markets": [
        "PATCH",
        "/list/coin/markets",
        [],
        [
            "vs_currency",
            "ids",
            "names",
            "symbols",
            "include_tokens",
            "category",
            "order",
            "per_page",
            "page",
            "sparkline",
            "price_change_percentage",
            "locale",
            "precision",
            "include_rehypothecated"
        ]
    ],
    "list_coin_tickers": [
        "GET",
        "/list/coin/tickers",
        [],
        [
            "id",
            "exchange_ids",
            "include_exchange_logo",
            "page",
            "order",
            "depth",
            "dex_pair_format"
        ]
    ],
    "list_coins": [
        "GET",
        "/list/coins",
        [],
        [
            "include_platform",
            "status"
        ]
    ],
    "list_onchain_networks": [
        "GET",
        "/list/onchain/networks",
        [],
        [
            "page"
        ]
    ],
    "list_pool_trades": [
        "GET",
        "/list/pool/trades",
        [],
        [
            "network",
            "pool_address",
            "trade_volume_in_usd_greater_than",
            "token"
        ]
    ],
    "list_supported_currencies": [
        "GET",
        "/list/supported/currencies",
        [],
        []
    ],
    "list_token_pools": [
        "GET",
        "/list/token/pools",
        [],
        [
            "network",
            "token_address",
            "include",
            "include_inactive_source",
            "page",
            "sort",
            "include_gt_community_data"
        ]
    ],
    "search": [
        "GET",
        "/search",
        [],
        [
            "query"
        ]
    ],
    "search_onchain_pools": [
        "GET",
        "/search/onchain/pools",
        [],
        [
            "query",
            "network",
            "include",
            "page"
        ]
    ]
}

class CoinGeckoDynamicAction(Action):
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

        base_url = _resolve_base_url(cred)
        path = path_template

        # Fill path parameters
        for p_name in path_param_names:
            val = params.get(p_name)
            if val is not None:
                path = path.replace(" + p_name + ", urllib.parse.quote(str(val), safe=""))
            else:
                path = path.replace(" + p_name + ", "")

        full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        assert_public_url(full_url)

        headers = _build_headers(cred)
        req_params = {}
        req_json = None

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
            raise ValueError(f"CoinGecko API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class CoinGeckoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="coingecko",
            display_name="CoinGecko",
            category="Finance & Accounting",
            auth_types=['api_key'],
            description="CoinGecko cryptocurrency data API with 25 actions for coins, markets, OHLCV, and onchain pools."
        )
        for act in get_provider_actions("coingecko"):
            self.register_action(CoinGeckoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)

        if "coingecko" in ["shopify_admin", "shopify_storefront"]:
            shop = str(cred.get("shopDomain") or cred.get("shop") or "").strip()
            if not shop:
                raise ValueError("Shopify shopDomain is required in credentials.")
            shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
            val_url = "https://api.coingecko.com/api/v3/ping".replace("{shopDomain}", shop)
        elif "coingecko" == "shopify_partner":
            org_id = str(cred.get("organizationId") or cred.get("orgId") or "").strip()
            if not org_id:
                raise ValueError("Shopify Partner organizationId is required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping".replace("{organizationId}", org_id)
        elif "coingecko" == "sendbird":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Sendbird applicationId is required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping".replace("{applicationId}", app_id)
        elif "coingecko" == "listmonk":
            base_url = str(cred.get("baseUrl") or "").strip()
            user = str(cred.get("apiUser") or cred.get("username") or "").strip()
            if not base_url:
                raise ValueError("Listmonk baseUrl is required in credentials.")
            if not user:
                raise ValueError("Listmonk apiUser is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/subscribers?per_page=1"
        elif "coingecko" == "flexmail":
            acc_id = str(cred.get("accountId") or "").strip()
            pat = token or str(cred.get("personalAccessToken") or "").strip()
            if not acc_id or not pat:
                raise ValueError("Flexmail accountId and personalAccessToken are required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping"
        elif "coingecko" == "crisp":
            token_id = str(cred.get("tokenIdentifier") or "").strip()
            token_key = token or str(cred.get("tokenKey") or "").strip()
            if not token_id or not token_key:
                raise ValueError("Crisp tokenIdentifier and tokenKey are required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping"
        elif "coingecko" == "vonage":
            api_key = str(cred.get("apiKey") or token or "").strip()
            api_secret = str(cred.get("apiSecret") or "").strip()
            if not api_key or not api_secret:
                raise ValueError("Vonage apiKey and apiSecret are required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping"
        elif "coingecko" == "onesignal_rest_api":
            app_id = str(cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("OneSignal appId is required in credentials.")
            val_url = "https://api.coingecko.com/api/v3/ping"
        else:
            if not token:
                raise ValueError("API token or key is required for CoinGecko.")
            val_url = "https://api.coingecko.com/api/v3/ping"
            for key in ["site", "domain", "subdomain", "host", "tenant", "region", "instanceUrl", "baseUrl"]:
                if "{" + key + "}" in val_url:
                    val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))
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
            raise ValueError(f"CoinGecko connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid CoinGecko credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"CoinGecko validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "coingecko" == "shopee" and body.get("error"):
                    raise ValueError(f"Invalid CoinGecko credentials: {body.get('message') or resp.text}")
                elif "coingecko" == "coingecko" and body.get("error"):
                    raise ValueError(f"Invalid CoinGecko credentials: {body.get('error')}")
                elif "coingecko" == "sendbird" and body.get("error") is True:
                    raise ValueError(f"Invalid CoinGecko credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"CoinGecko Account"
        }

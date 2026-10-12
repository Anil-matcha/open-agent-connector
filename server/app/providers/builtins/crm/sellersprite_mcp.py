"""
SellerSprite MCP Provider for ConnectorHub.
Loads and registers 47 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://mcp.sellersprite.com"

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
    "aba_research_monthly": [
        "GET",
        "/aba_research_monthly",
        [],
        [
            "marketplace",
            "date",
            "departments",
            "excludeKeywords",
            "includeKeywords",
            "exactFlag",
            "minRankGrowthRate",
            "maxRankGrowthRate",
            "minSearchRank",
            "maxSearchRank",
            "minSearches",
            "maxSearches",
            "minMonopolyClickRate",
            "maxMonopolyClickRate",
            "minConversionRate",
            "maxConversionRate",
            "minWordCount",
            "maxWordCount",
            "minSPR",
            "maxSPR",
            "minTitleDensity",
            "maxTitleDensity",
            "minClicks",
            "maxClicks",
            "minImpressions",
            "maxImpressions",
            "searchModel",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "aba_research_trend": [
        "GET",
        "/aba_research_trend",
        [],
        [
            "marketplace",
            "keyword",
            "timeGranularity",
            "returnFields"
        ]
    ],
    "aba_research_weekly": [
        "GET",
        "/aba_research_weekly",
        [],
        [
            "marketplace",
            "date",
            "departments",
            "excludeKeywords",
            "includeKeywords",
            "exactFlag",
            "rankGrowthValue",
            "rankGrowthRate",
            "minRankGrowthRate",
            "maxRankGrowthRate",
            "minSearchRank",
            "maxSearchRank",
            "minSearches",
            "maxSearches",
            "minMonopolyClickRate",
            "maxMonopolyClickRate",
            "minConversionRate",
            "maxConversionRate",
            "minWordCount",
            "maxWordCount",
            "minSPR",
            "maxSPR",
            "minTitleDensity",
            "maxTitleDensity",
            "minClicks",
            "maxClicks",
            "minImpressions",
            "maxImpressions",
            "searchModel",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "asin_competitor": [
        "GET",
        "/asin_competitor",
        [],
        [
            "marketplace",
            "asin",
            "size",
            "returnFields"
        ]
    ],
    "asin_coupon_trend": [
        "GET",
        "/asin_coupon_trend",
        [],
        [
            "marketplace",
            "asin",
            "returnFields"
        ]
    ],
    "asin_detail": [
        "GET",
        "/asin_detail",
        [],
        [
            "marketplace",
            "asin",
            "returnFields"
        ]
    ],
    "asin_detail_with_coupon_trend": [
        "GET",
        "/asin_detail_with_coupon_trend",
        [],
        [
            "marketplace",
            "asin",
            "returnFields"
        ]
    ],
    "asin_prediction": [
        "GET",
        "/asin_prediction",
        [],
        [
            "marketplace",
            "asin",
            "returnFields"
        ]
    ],
    "asin_sales_trend": [
        "GET",
        "/asin_sales_trend",
        [],
        [
            "marketplace",
            "asin",
            "returnFields"
        ]
    ],
    "bsr_prediction": [
        "GET",
        "/bsr_prediction",
        [],
        [
            "marketplace",
            "bsr",
            "categoryId",
            "returnFields"
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
    "competitor_lookup": [
        "GET",
        "/competitor_lookup",
        [],
        [
            "marketplace",
            "month",
            "brand",
            "sellerName",
            "asins",
            "nodeIdPath",
            "nodeIdPathEqual",
            "keyword",
            "matchType",
            "variation",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "google_trend": [
        "GET",
        "/google_trend",
        [],
        [
            "marketplace",
            "keyword",
            "googleProp",
            "monthly",
            "returnFields"
        ]
    ],
    "keepa_info": [
        "GET",
        "/keepa_info",
        [],
        [
            "marketplace",
            "asin",
            "startTimestamp",
            "endTimestamp",
            "dailyLatest",
            "returnFields"
        ]
    ],
    "keyword_conversion": [
        "GET",
        "/keyword_conversion",
        [],
        [
            "marketplace",
            "keyword",
            "timeType",
            "minSearches",
            "maxSearches",
            "minClicks",
            "maxClicks",
            "minPurchases",
            "maxPurchases",
            "minSearchConvRate",
            "maxSearchConvRate",
            "minClickConvRate",
            "maxClickConvRate",
            "minPpc",
            "maxPpc",
            "minCpa",
            "maxCpa",
            "minProductPrice",
            "maxProductPrice",
            "minAcos",
            "maxAcos",
            "minClickingRate",
            "maxClickingRate",
            "minConversionRate",
            "maxConversionRate",
            "minPhraseCount",
            "maxPhraseCount",
            "minBudget",
            "maxBudget",
            "matchType",
            "includeKeywords",
            "excludeKeywords",
            "customAvgProductPrice",
            "returnFields"
        ]
    ],
    "keyword_miner": [
        "GET",
        "/keyword_miner",
        [],
        [
            "marketplace",
            "historyDate",
            "keyword",
            "keywordList",
            "minSearch",
            "maxSearch",
            "minPurchases",
            "maxPurchases",
            "minPurchasesRate",
            "maxPurchasesRate",
            "minSPR",
            "maxSPR",
            "minTitleDensity",
            "maxTitleDensity",
            "minRelevancy",
            "maxRelevancy",
            "minSearchRank",
            "maxSearchRank",
            "minProducts",
            "maxProducts",
            "minSupplyDemandRatio",
            "maxSupplyDemandRatio",
            "minAdProducts",
            "maxAdProducts",
            "minWordCount",
            "maxWordCount",
            "minMonopolyClickRate",
            "maxMonopolyClickRate",
            "minBid",
            "maxBid",
            "minPrice",
            "maxPrice",
            "minRatings",
            "maxRatings",
            "minRating",
            "maxRating",
            "amazonChoice",
            "filterRootWord",
            "matchType",
            "includeKeywords",
            "excludeKeywords",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "keyword_order": [
        "GET",
        "/keyword_order",
        [],
        [
            "marketplace",
            "asins",
            "reverseType",
            "date",
            "conversionType",
            "variation",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "keyword_research": [
        "GET",
        "/keyword_research",
        [],
        [
            "marketplace",
            "month",
            "departments",
            "keywords",
            "excludeKeywords",
            "minSearches",
            "maxSearches",
            "minSearchesCr",
            "maxSearchesCr",
            "minProducts",
            "maxProducts",
            "minPurchases",
            "maxPurchases",
            "minPurchaseRate",
            "maxPurchaseRate",
            "withYearlyGrowth",
            "minSearchMonthCv",
            "maxSearchMonthCv",
            "minSearchMonthCr",
            "maxSearchMonthCr",
            "minSearchNearlyCv",
            "maxSearchNearlyCv",
            "minSearchNearlyCr",
            "maxSearchNearlyCr",
            "marketPeriod",
            "minAvgPrice",
            "maxAvgPrice",
            "minRatings",
            "maxRatings",
            "minRating",
            "maxRating",
            "minBid",
            "maxBid",
            "minAraClickRate",
            "maxAraClickRate",
            "minGoodsValue",
            "maxGoodsValue",
            "minSupplyDemandRatio",
            "maxSupplyDemandRatio",
            "minWordCount",
            "maxWordCount",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "keyword_research_trends": [
        "GET",
        "/keyword_research_trends",
        [],
        [
            "marketplace",
            "keyword",
            "returnFields"
        ]
    ],
    "list_tools": [
        "GET",
        "/tools",
        [],
        []
    ],
    "market_brand_concentration": [
        "GET",
        "/market_brand_concentration",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_ebc_distribution": [
        "GET",
        "/market_ebc_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_listing_date_distribution": [
        "GET",
        "/market_listing_date_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_listing_trend_distribution": [
        "GET",
        "/market_listing_trend_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_price_distribution": [
        "GET",
        "/market_price_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_product_concentration": [
        "GET",
        "/market_product_concentration",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "asins",
            "returnFields"
        ]
    ],
    "market_product_demand_trend": [
        "GET",
        "/market_product_demand_trend",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_rating_distribution": [
        "GET",
        "/market_rating_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_ratings_count_distribution": [
        "GET",
        "/market_ratings_count_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_research": [
        "GET",
        "/market_research",
        [],
        [
            "marketplace",
            "month",
            "topNum",
            "newProduct",
            "nodeIdPath",
            "departmentKeyword",
            "minAvgUnits",
            "maxAvgUnits",
            "minAvgRevenue",
            "maxAvgRevenue",
            "minAvgRatings",
            "maxAvgRatings",
            "minAvgRating",
            "maxAvgRating",
            "minAvgBsr",
            "maxAvgBsr",
            "minAvgPrice",
            "maxAvgPrice",
            "minWeight",
            "maxWeight",
            "minVolume",
            "maxVolume",
            "minAvgProfit",
            "maxAvgProfit",
            "minTopAvgUnits",
            "maxTopAvgUnits",
            "minTopAvgRevenue",
            "maxTopAvgRevenue",
            "minTopAvgBsr",
            "maxTopAvgBsr",
            "minGoodsCount",
            "maxGoodsCount",
            "minBrands",
            "maxBrands",
            "minSellers",
            "maxSellers",
            "minAvgSellers",
            "maxAvgSellers",
            "minGoodsCrn",
            "maxGoodsCrn",
            "minBrandCrn",
            "maxBrandCrn",
            "maxSellerCrn",
            "minSellerCrn",
            "minEbcProportion",
            "maxEbcProportion",
            "minFbaProportion",
            "maxFbaProportion",
            "minFbmProportion",
            "maxFbmProportion",
            "minAmazonSelfProportion",
            "maxAmazonSelfProportion",
            "sellerLocation",
            "minNewProportion",
            "maxNewProportion",
            "minNewCount",
            "maxNewCount",
            "minNewAvgRatings",
            "maxNewAvgRatings",
            "minNewAvgPrice",
            "maxNewAvgPrice",
            "minNewAvgRating",
            "maxNewAvgRating",
            "minNewAvgUnits",
            "maxNewAvgUnits",
            "minNewAvgRevenue",
            "maxNewAvgRevenue",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "market_research_statistics": [
        "GET",
        "/market_research_statistics",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_seller_concentration": [
        "GET",
        "/market_seller_concentration",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_seller_country_distribution": [
        "GET",
        "/market_seller_country_distribution",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "market_seller_type_concentration": [
        "GET",
        "/market_seller_type_concentration",
        [],
        [
            "marketplace",
            "month",
            "topN",
            "newProduct",
            "nodeIdPath",
            "returnFields"
        ]
    ],
    "product_node": [
        "GET",
        "/product_node",
        [],
        [
            "marketplace",
            "nodeIdPath",
            "keyword",
            "month",
            "returnFields"
        ]
    ],
    "product_research": [
        "GET",
        "/product_research",
        [],
        [
            "marketplace",
            "month",
            "keyword",
            "includeSellers",
            "excludeSellers",
            "matchType",
            "excludeKeywords",
            "minPrice",
            "maxPrice",
            "minRating",
            "maxRating",
            "minRatings",
            "maxRatings",
            "minRatingsCv",
            "maxRatingsCv",
            "minSellers",
            "maxSellers",
            "minProfit",
            "maxProfit",
            "minBsr",
            "maxBsr",
            "minBsrCv",
            "maxBsrCv",
            "minBsrCr",
            "maxBsrCr",
            "minUnits",
            "maxUnits",
            "minAmzUnit",
            "maxAmzUnit",
            "minRevenue",
            "maxRevenue",
            "minRevenueCr",
            "maxRevenueCr",
            "minUnitsCr",
            "maxUnitsCr",
            "weightUnit",
            "minWeights",
            "maxWeights",
            "minVariations",
            "maxVariations",
            "filterSub",
            "minSubBsrRank",
            "maxSubBsrRank",
            "includeBrands",
            "excludeBrands",
            "nodeIdPaths",
            "nodeIdPathEqual",
            "availableMonth",
            "dimensionType",
            "minFba",
            "maxFba",
            "minLqs",
            "maxLqs",
            "sellerNation",
            "badgeBS",
            "badgeAC",
            "badgeNR",
            "fulfillment",
            "variation",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "review": [
        "GET",
        "/review",
        [],
        [
            "marketplace",
            "asin",
            "starList",
            "typeList",
            "page",
            "size",
            "returnFields"
        ]
    ],
    "trademark_country_list": [
        "GET",
        "/trademark_country_list",
        [],
        [
            "returnFields"
        ]
    ],
    "trademark_detail": [
        "GET",
        "/trademark_detail",
        [],
        [
            "office",
            "brandId",
            "returnFields"
        ]
    ],
    "trademark_list": [
        "GET",
        "/trademark_list",
        [],
        [
            "office",
            "text",
            "brandName",
            "status",
            "applicant",
            "niceClass",
            "applicationYear",
            "expiryYear",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "trademark_stats": [
        "GET",
        "/trademark_stats",
        [],
        [
            "office",
            "text",
            "returnFields"
        ]
    ],
    "traffic_extend": [
        "GET",
        "/traffic_extend",
        [],
        [
            "marketplace",
            "historyDate",
            "asinList",
            "queryType",
            "minSearches",
            "maxSearches",
            "minSearchRank",
            "maxSearchRank",
            "minPurchases",
            "maxPurchases",
            "minPurchaseRate",
            "maxPurchaseRate",
            "minProducts",
            "maxProducts",
            "minSupplyDemandRatio",
            "maxSupplyDemandRatio",
            "minBid",
            "maxBid",
            "minAdProducts",
            "maxAdProducts",
            "minAvgPrice",
            "maxAvgPrice",
            "minWordCount",
            "maxWordCount",
            "includeKeywords",
            "excludeKeywords",
            "minSPR",
            "maxSPR",
            "minTitleDensity",
            "maxTitleDensity",
            "minMonopolyClickRate",
            "maxMonopolyClickRate",
            "minTrafficPercentage",
            "maxTrafficPercentage",
            "minConversionRate",
            "maxConversionRate",
            "minCompetitors",
            "maxCompetitors",
            "amazonChoice",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "traffic_keyword": [
        "GET",
        "/traffic_keyword",
        [],
        [
            "marketplace",
            "asin",
            "keyword",
            "month",
            "badges",
            "trafficKeywordTypes",
            "conversionKeywordTypes",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "traffic_keyword_stat": [
        "GET",
        "/traffic_keyword_stat",
        [],
        [
            "marketplace",
            "asin",
            "month",
            "returnFields"
        ]
    ],
    "traffic_listing": [
        "GET",
        "/traffic_listing",
        [],
        [
            "marketplace",
            "asinList",
            "relations",
            "variations",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ],
    "traffic_listing_stat": [
        "GET",
        "/traffic_listing_stat",
        [],
        [
            "marketplace",
            "asinList",
            "returnFields"
        ]
    ],
    "traffic_source": [
        "GET",
        "/traffic_source",
        [],
        [
            "marketplace",
            "q",
            "month",
            "page",
            "size",
            "order",
            "returnFields"
        ]
    ]
}

class SellerspriteMcpDynamicAction(Action):
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
            raise ValueError(f"SellerSprite MCP API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class SellerspriteMcpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sellersprite_mcp",
            display_name="SellerSprite MCP",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="SellerSprite Amazon seller product research, keyword trends, and competitor lookup MCP API with 47 actions."
        )
        for act in get_provider_actions("sellersprite_mcp"):
            self.register_action(SellerspriteMcpDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://mcp.sellersprite.com/api/v1/user"
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
            raise ValueError(f"SellerSprite MCP connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid SellerSprite MCP credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"SellerSprite MCP validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "sellersprite_mcp" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid SellerSprite MCP credentials: {body.get('msg') or resp.text}")
                elif "sellersprite_mcp" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid SellerSprite MCP credentials: {body.get('errmsg') or resp.text}")
                elif "sellersprite_mcp" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid SellerSprite MCP credentials: {body.get('error_msg') or resp.text}")
                elif "sellersprite_mcp" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid SellerSprite MCP credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"SellerSprite MCP Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"SellerSprite MCP Account"
        }

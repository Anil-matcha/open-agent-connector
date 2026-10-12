"""
Apple Ads Provider for ConnectorHub.
Loads and registers 98 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.ads.apple.com"

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
    "apply_daily_budget_recommendations": [
        "POST",
        "{dailyBudgetRecommendationsPath}/apply",
        [
            "dailyBudgetRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "recommendations"
        ]
    ],
    "apply_target_cpa_recommendations": [
        "GET",
        "{targetCpaRecommendationsPath}/apply",
        [
            "targetCpaRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "recommendations"
        ]
    ],
    "bulk_create_keywords": [
        "POST",
        "{keywordsPath}/{suffix}",
        [
            "keywordsPath",
            "suffix"
        ],
        [
            "adAccountId",
            "keywords",
            "allowPartialSuccess"
        ]
    ],
    "bulk_create_negative_keywords": [
        "POST",
        "{negativeKeywordsPath}/{operation}",
        [
            "negativeKeywordsPath",
            "operation"
        ],
        [
            "adAccountId",
            "negativeKeywords",
            "allowPartialSuccess"
        ]
    ],
    "bulk_update_keywords": [
        "POST",
        "{keywordsPath}/{suffix}",
        [
            "keywordsPath",
            "suffix"
        ],
        [
            "adAccountId",
            "keywords",
            "allowPartialSuccess"
        ]
    ],
    "bulk_update_negative_keywords": [
        "POST",
        "{negativeKeywordsPath}/{operation}",
        [
            "negativeKeywordsPath",
            "operation"
        ],
        [
            "adAccountId",
            "negativeKeywords",
            "allowPartialSuccess"
        ]
    ],
    "create_ad": [
        "POST",
        "{creativesPath}/query",
        [
            "creativesPath"
        ],
        [
            "adAccountId",
            "adGroupId",
            "creativeId",
            "name",
            "status"
        ]
    ],
    "create_ad_account": [
        "POST",
        "/ad_account",
        [],
        [
            "name",
            "productFeatures",
            "delegations"
        ]
    ],
    "create_ad_group": [
        "POST",
        "/ad_group",
        [],
        [
            "adAccountId",
            "campaignId",
            "name",
            "pricingModel",
            "startTime",
            "endTime",
            "status",
            "automatedKeywordsOptIn",
            "automatedKeywordsRequired",
            "bidStrategy",
            "targeting",
            "cpaCap"
        ]
    ],
    "create_budget_order": [
        "POST",
        "/budget_order",
        [],
        [
            "adAccountId",
            "name",
            "startTime",
            "endTime",
            "value",
            "invoiceDetail"
        ]
    ],
    "create_campaign": [
        "POST",
        "/campaign",
        [],
        [
            "adAccountId",
            "name",
            "promotedObjectType",
            "promotedObjectId",
            "billingEvent",
            "dailyBudget",
            "targeting",
            "bidStrategy",
            "startTime",
            "endTime",
            "status",
            "sharedBudgets",
            "invoiceDetail",
            "regulationResponses"
        ]
    ],
    "create_creative": [
        "POST",
        "/creative",
        [],
        [
            "adAccountId",
            "name",
            "creativeType",
            "creativeSpec",
            "destination"
        ]
    ],
    "create_keyword": [
        "POST",
        "/keyword",
        [],
        [
            "adAccountId",
            "adGroupId",
            "text",
            "matchType",
            "bid",
            "status"
        ]
    ],
    "create_location_group": [
        "POST",
        "{locationGroupsPath}/query",
        [
            "locationGroupsPath"
        ],
        [
            "adAccountId",
            "name",
            "brandId",
            "groupType",
            "rules",
            "locationIds",
            "description"
        ]
    ],
    "create_negative_keyword": [
        "POST",
        "/negative_keyword",
        [],
        [
            "adAccountId",
            "campaignId",
            "adGroupId",
            "text",
            "matchType",
            "status"
        ]
    ],
    "delete_ad": [
        "DELETE",
        "{creativesPath}/query",
        [
            "creativesPath"
        ],
        [
            "adId",
            "adAccountId"
        ]
    ],
    "delete_ad_group": [
        "DELETE",
        "/ad_group",
        [],
        [
            "adGroupId",
            "adAccountId"
        ]
    ],
    "delete_asset": [
        "POST",
        "{productPagesPath}/query",
        [
            "productPagesPath"
        ],
        [
            "assetId",
            "adAccountId"
        ]
    ],
    "delete_budget_order": [
        "DELETE",
        "/budget_order",
        [],
        [
            "budgetOrderId",
            "adAccountId"
        ]
    ],
    "delete_campaign": [
        "DELETE",
        "/campaign",
        [],
        [
            "campaignId",
            "adAccountId"
        ]
    ],
    "delete_creative": [
        "DELETE",
        "/creative",
        [],
        [
            "creativeId",
            "adAccountId"
        ]
    ],
    "delete_keyword": [
        "POST",
        "{keywordsPath}/{suffix}",
        [
            "keywordsPath",
            "suffix"
        ],
        [
            "keywordId",
            "adAccountId"
        ]
    ],
    "delete_location_group": [
        "DELETE",
        "/location_group",
        [],
        [
            "locationGroupId",
            "adAccountId"
        ]
    ],
    "delete_negative_keyword": [
        "POST",
        "{negativeKeywordsPath}/{operation}",
        [
            "negativeKeywordsPath",
            "operation"
        ],
        [
            "negativeKeywordId",
            "adAccountId"
        ]
    ],
    "dismiss_daily_budget_recommendations": [
        "POST",
        "{dailyBudgetRecommendationsPath}/dismiss",
        [
            "dailyBudgetRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "recommendations"
        ]
    ],
    "dismiss_target_cpa_recommendations": [
        "GET",
        "{targetCpaRecommendationsPath}/dismiss",
        [
            "targetCpaRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "recommendations"
        ]
    ],
    "get_ad": [
        "GET",
        "{creativesPath}/query",
        [
            "creativesPath"
        ],
        [
            "adId",
            "adAccountId"
        ]
    ],
    "get_ad_account": [
        "GET",
        "/ad_account",
        [],
        [
            "adAccountId"
        ]
    ],
    "get_ad_group": [
        "GET",
        "/ad_group",
        [],
        [
            "adGroupId",
            "adAccountId"
        ]
    ],
    "get_ad_group_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_ad_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_advertiser_resources": [
        "GET",
        "/advertiser_resources",
        [],
        [
            "resourceType"
        ]
    ],
    "get_app": [
        "GET",
        "{rejectionReasonsPath}/query",
        [
            "rejectionReasonsPath"
        ],
        [
            "adamId",
            "adAccountId"
        ]
    ],
    "get_app_rejection_reasons": [
        "GET",
        "/app_rejection_reasons",
        [],
        [
            "rejectionReasonId",
            "adAccountId"
        ]
    ],
    "get_asset": [
        "POST",
        "{productPagesPath}/query",
        [
            "productPagesPath"
        ],
        [
            "assetId",
            "adAccountId"
        ]
    ],
    "get_brand": [
        "GET",
        "{businessCategoriesPath}/query",
        [
            "businessCategoriesPath"
        ],
        [
            "brandId",
            "adAccountId"
        ]
    ],
    "get_brand_ad_group_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_brand_ad_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_brand_campaign_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_brand_keyword_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_brand_search_term_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_budget_order": [
        "GET",
        "/budget_order",
        [],
        [
            "budgetOrderId",
            "adAccountId"
        ]
    ],
    "get_business_category": [
        "GET",
        "{brandRejectionReasonsPath}/query",
        [
            "brandRejectionReasonsPath"
        ],
        [
            "businessCategoryId",
            "adAccountId"
        ]
    ],
    "get_campaign": [
        "GET",
        "/campaign",
        [],
        [
            "campaignId",
            "adAccountId"
        ]
    ],
    "get_campaign_limited_status_details": [
        "GET",
        "/campaign_limited_status_details",
        [],
        [
            "campaignId",
            "adAccountId"
        ]
    ],
    "get_campaign_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_change_history_detail": [
        "GET",
        "/change_history_detail",
        [],
        [
            "detailId",
            "adAccountId",
            "limit",
            "offset"
        ]
    ],
    "get_creative": [
        "GET",
        "/creative",
        [],
        [
            "creativeId",
            "adAccountId"
        ]
    ],
    "get_keyword": [
        "GET",
        "/keyword",
        [],
        [
            "keywordId",
            "adAccountId"
        ]
    ],
    "get_keyword_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_location": [
        "GET",
        "{locationGroupsPath}/query",
        [
            "locationGroupsPath"
        ],
        [
            "locationId",
            "adAccountId"
        ]
    ],
    "get_location_group": [
        "GET",
        "/location_group",
        [],
        [
            "locationGroupId",
            "adAccountId"
        ]
    ],
    "get_me": [
        "GET",
        "/me",
        [],
        []
    ],
    "get_negative_keyword": [
        "GET",
        "/negative_keyword",
        [],
        [
            "negativeKeywordId",
            "adAccountId"
        ]
    ],
    "get_org": [
        "GET",
        "/org",
        [],
        [
            "orgId"
        ]
    ],
    "get_product_page": [
        "GET",
        "{productPagesPath}/locale-details/query",
        [
            "productPagesPath"
        ],
        [
            "productPageId",
            "adAccountId"
        ]
    ],
    "get_search_term_report": [
        "POST",
        "{reportsPath}/{request}/{request}/query",
        [
            "reportsPath",
            "request",
            "request"
        ],
        [
            "adAccountId",
            "timeRange",
            "filters",
            "sorting",
            "fields",
            "groupBy",
            "includeRows",
            "offset",
            "pageSize"
        ]
    ],
    "get_user_acls": [
        "GET",
        "/user_acls",
        [],
        []
    ],
    "query_ad_groups": [
        "GET",
        "{adGroupsPath}/query",
        [
            "adGroupsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_ads": [
        "GET",
        "{adsPath}/query",
        [
            "adsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_app_eligibilities": [
        "GET",
        "{rejectionReasonsPath}/query",
        [
            "rejectionReasonsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_app_locale_details": [
        "GET",
        "/query_app_locale_details",
        [],
        [
            "adamId",
            "adAccountId",
            "filters",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_app_rejection_reasons": [
        "GET",
        "{rejectionReasonsPath}/query",
        [
            "rejectionReasonsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_assets": [
        "POST",
        "{assetsPath}/query",
        [
            "assetsPath"
        ],
        [
            "adAccountId",
            "filters",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_brand_rejection_reasons": [
        "GET",
        "{brandRejectionReasonsPath}/query",
        [
            "brandRejectionReasonsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_brands": [
        "GET",
        "{brandsPath}/query",
        [
            "brandsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_budget_orders": [
        "GET",
        "{budgetOrdersPath}/query",
        [
            "budgetOrdersPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_business_categories": [
        "GET",
        "{businessCategoriesPath}/query",
        [
            "businessCategoriesPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_campaigns": [
        "GET",
        "{campaignsPath}/query",
        [
            "campaignsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_category_suggestions": [
        "POST",
        "/query_category_suggestions",
        [],
        [
            "adAccountId",
            "queryType",
            "promotedObjectId",
            "promotedObjectType",
            "categories",
            "categoryLike",
            "ignoreCase",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_change_history": [
        "POST",
        "{changeHistoryPath}/query",
        [
            "changeHistoryPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "needTotals",
            "timeZone",
            "metadata"
        ]
    ],
    "query_creatives": [
        "GET",
        "{creativesPath}/query",
        [
            "creativesPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_daily_budget_recommendations": [
        "GET",
        "{dailyBudgetRecommendationsPath}/query",
        [
            "dailyBudgetRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "state",
            "campaignIds",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_geo_locations": [
        "POST",
        "{locationsPath}/query",
        [
            "locationsPath"
        ],
        [
            "adAccountId",
            "geoRequest",
            "supplySource",
            "offset",
            "pageSize"
        ]
    ],
    "query_impression_share": [
        "POST",
        "{targetCpaRecommendationsPath}/query",
        [
            "targetCpaRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "countryOrRegion",
            "timeRange",
            "impressionShareReportType",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_keyword_suggestions": [
        "POST",
        "/query_keyword_suggestions",
        [],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "terms",
            "countriesOrRegions",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_keywords": [
        "GET",
        "{keywordsPath}/query",
        [
            "keywordsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_location_groups": [
        "GET",
        "{locationGroupsPath}/query",
        [
            "locationGroupsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_locations": [
        "GET",
        "{locationsPath}/query",
        [
            "locationsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_negative_keywords": [
        "GET",
        "{negativeKeywordsPath}/query",
        [
            "negativeKeywordsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_phrase_suggestions": [
        "POST",
        "/query_phrase_suggestions",
        [],
        [
            "adAccountId",
            "queryType",
            "promotedObjectId",
            "promotedObjectType",
            "phrases",
            "phraseLike",
            "ignoreCase",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_product_page_locale_details": [
        "GET",
        "{productPagesPath}/locale-details/query",
        [
            "productPagesPath"
        ],
        [
            "adAccountId",
            "filters",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_product_pages": [
        "GET",
        "{productPagesPath}/query",
        [
            "productPagesPath"
        ],
        [
            "adAccountId",
            "filters",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_search_term_popularity": [
        "POST",
        "{targetCpaRecommendationsPath}/query",
        [
            "targetCpaRecommendationsPath"
        ],
        [
            "adAccountId",
            "timeRange",
            "fields",
            "filters",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_supported_app_languages": [
        "GET",
        "{rejectionReasonsPath}/query",
        [
            "rejectionReasonsPath"
        ],
        [
            "adAccountId",
            "filters",
            "sorting",
            "offset",
            "pageSize",
            "fetchTotalCount"
        ]
    ],
    "query_target_cpa_recommendations": [
        "GET",
        "{targetCpaRecommendationsPath}/query",
        [
            "targetCpaRecommendationsPath"
        ],
        [
            "adAccountId",
            "promotedObjectId",
            "promotedObjectType",
            "state",
            "sorting",
            "offset",
            "pageSize"
        ]
    ],
    "query_target_cpa_suggestion": [
        "POST",
        "/query_target_cpa_suggestion",
        [],
        [
            "adAccountId",
            "promotedObjectId",
            "countryOrRegion"
        ]
    ],
    "search_apps": [
        "GET",
        "{rejectionReasonsPath}/query",
        [
            "rejectionReasonsPath"
        ],
        [
            "adAccountId",
            "query",
            "returnOwnedApps",
            "cpids",
            "storeFronts",
            "offset",
            "limit"
        ]
    ],
    "search_geo_locations": [
        "GET",
        "{locationsPath}/query",
        [
            "locationsPath"
        ],
        [
            "adAccountId",
            "supplySource",
            "query",
            "entity",
            "countryCode",
            "eligible",
            "offset",
            "pageSize"
        ]
    ],
    "update_ad": [
        "PATCH",
        "{creativesPath}/query",
        [
            "creativesPath"
        ],
        [
            "adId",
            "adAccountId",
            "name",
            "status"
        ]
    ],
    "update_ad_account": [
        "PATCH",
        "/ad_account",
        [],
        [
            "adAccountId",
            "name",
            "delegations"
        ]
    ],
    "update_ad_group": [
        "PATCH",
        "/ad_group",
        [],
        [
            "adGroupId",
            "adAccountId",
            "name",
            "status",
            "startTime",
            "endTime",
            "automatedKeywordsOptIn",
            "bidStrategy",
            "targeting",
            "cpaCap"
        ]
    ],
    "update_budget_order": [
        "PATCH",
        "/budget_order",
        [],
        [
            "budgetOrderId",
            "adAccountId",
            "name",
            "startTime",
            "endTime",
            "value",
            "adAccountIds",
            "invoiceDetail"
        ]
    ],
    "update_campaign": [
        "PATCH",
        "/campaign",
        [],
        [
            "campaignId",
            "adAccountId",
            "name",
            "status",
            "startTime",
            "endTime",
            "dailyBudget",
            "targeting",
            "bidStrategy",
            "sharedBudgets",
            "invoiceDetail",
            "regulationResponses"
        ]
    ],
    "update_creative": [
        "PATCH",
        "/creative",
        [],
        [
            "creativeId",
            "adAccountId",
            "name",
            "creativeSpec"
        ]
    ],
    "update_keyword": [
        "POST",
        "{keywordsPath}/{suffix}",
        [
            "keywordsPath",
            "suffix"
        ],
        [
            "keywordId",
            "adAccountId",
            "bid",
            "status"
        ]
    ],
    "update_location_group": [
        "PATCH",
        "/location_group",
        [],
        [
            "locationGroupId",
            "adAccountId",
            "name",
            "groupType",
            "rules",
            "locationIds",
            "description"
        ]
    ],
    "update_negative_keyword": [
        "PATCH",
        "/negative_keyword",
        [],
        [
            "negativeKeywordId",
            "adAccountId",
            "status"
        ]
    ]
}

class AppleAdsDynamicAction(Action):
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
            raise ValueError(f"Apple Ads API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class AppleAdsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="apple_ads",
            display_name="Apple Ads",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="Apple Search Ads Campaign Management API with 98 actions for campaigns, ad groups, keywords, budget orders, and reporting."
        )
        for act in get_provider_actions("apple_ads"):
            self.register_action(AppleAdsDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.ads.apple.com/api/v5/me"
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
            raise ValueError(f"Apple Ads connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Apple Ads credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Apple Ads validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "apple_ads" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Apple Ads credentials: {body.get('msg') or resp.text}")
                elif "apple_ads" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Apple Ads credentials: {body.get('errmsg') or resp.text}")
                elif "apple_ads" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Apple Ads credentials: {body.get('error_msg') or resp.text}")
                elif "apple_ads" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Apple Ads credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Apple Ads Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Apple Ads Account"
        }

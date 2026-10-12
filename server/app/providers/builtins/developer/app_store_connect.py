"""
App Store Connect Provider for ConnectorHub.
Loads and registers 653 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.appstoreconnect.apple.com/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    if base.startswith("{instanceUrl}"):
        inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
        base = base.replace("{instanceUrl}", inst)
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
    elif auth_mode == "gitea_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "zerotier_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "n8n_header":
        if token:
            headers["X-N8N-API-KEY"] = token
    elif auth_mode == "readme_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mingdao_auth":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cred.get("appKey"):
            headers["X-App-Key"] = str(cred["appKey"])
        if cred.get("sign"):
            headers["X-Sign"] = str(cred["sign"])

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_achievements_to_game_center_activity": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId",
            "gameCenterAchievementIds"
        ]
    ],
    "add_beta_testers_to_group": [
        "POST",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId",
            "betaTesterIds"
        ]
    ],
    "add_build_to_beta_groups": [
        "POST",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "buildId",
            "betaGroupIds"
        ]
    ],
    "add_builds_to_beta_group": [
        "POST",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId",
            "buildIds"
        ]
    ],
    "add_compatibility_versions_to_game_center_app_version": [
        "POST",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterAppVersionId",
            "compatibilityVersionIds"
        ]
    ],
    "add_individual_testers_to_build": [
        "POST",
        "/v1/builds",
        [],
        [
            "buildId",
            "betaTesterIds"
        ]
    ],
    "add_leaderboards_to_game_center_activity": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "add_leaderboards_to_game_center_leaderboard_set": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "add_review_submission_item": [
        "POST",
        "/v1/reviewSubmissionItems",
        [],
        [
            "reviewSubmissionId",
            "appStoreVersionId",
            "appCustomProductPageVersionId",
            "appStoreVersionExperimentId",
            "appStoreVersionExperimentV2Id",
            "appEventId"
        ]
    ],
    "add_visible_apps_to_user": [
        "POST",
        "/v1/users",
        [],
        [
            "userId",
            "appIds"
        ]
    ],
    "cancel_review_submission": [
        "POST",
        "/v1/reviewSubmissionItems",
        [],
        [
            "reviewSubmissionId"
        ]
    ],
    "cancel_user_invitation": [
        "POST",
        "/v1/actors",
        [],
        [
            "userInvitationId"
        ]
    ],
    "clear_sandbox_tester_purchase_history": [
        "GET",
        "/v2/sandboxTestersClearPurchaseHistoryRequest",
        [],
        [
            "sandboxTesterIds"
        ]
    ],
    "create_accessibility_declaration": [
        "POST",
        "/v1/accessibilityDeclarations",
        [],
        [
            "appId",
            "deviceFamily",
            "supportsAudioDescriptions",
            "supportsCaptions",
            "supportsDarkInterface",
            "supportsDifferentiateWithoutColorAlone",
            "supportsLargerText",
            "supportsReducedMotion",
            "supportsSufficientContrast",
            "supportsVoiceControl",
            "supportsVoiceover"
        ]
    ],
    "create_alternative_distribution_domain": [
        "POST",
        "/v1/alternativeDistributionDomains",
        [],
        [
            "domain",
            "referenceName"
        ]
    ],
    "create_alternative_distribution_key": [
        "POST",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "publicKey",
            "appId"
        ]
    ],
    "create_alternative_distribution_package": [
        "POST",
        "/v1/alternativeDistributionPackages",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "create_analytics_report_request": [
        "POST",
        "/v1/analyticsReportRequests",
        [],
        [
            "appId",
            "accessType"
        ]
    ],
    "create_android_to_ios_app_mapping_detail": [
        "POST",
        "/v1/androidToIosAppMappingDetails",
        [],
        [
            "appId",
            "packageName",
            "appSigningKeyPublicCertificateSha256Fingerprints"
        ]
    ],
    "create_app_availability": [
        "POST",
        "/v2/appAvailabilities",
        [],
        [
            "appId",
            "availableInNewTerritories",
            "territoryAvailabilities"
        ]
    ],
    "create_app_clip_advanced_experience": [
        "POST",
        "/v1/appClipAdvancedExperiences",
        [],
        [
            "appClipId",
            "headerImageId",
            "link",
            "defaultLanguage",
            "isPoweredBy",
            "action",
            "businessCategory",
            "place",
            "localizations"
        ]
    ],
    "create_app_clip_app_store_review_detail": [
        "POST",
        "/v1/appClipAppStoreReviewDetails",
        [],
        [
            "appClipDefaultExperienceId",
            "invocationUrls"
        ]
    ],
    "create_app_clip_default_experience": [
        "POST",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipId",
            "action",
            "releaseWithAppStoreVersionId",
            "appClipDefaultExperienceTemplateId"
        ]
    ],
    "create_app_clip_default_experience_localization": [
        "POST",
        "/v1/appClipDefaultExperienceLocalizations",
        [],
        [
            "appClipDefaultExperienceId",
            "locale",
            "subtitle"
        ]
    ],
    "create_app_custom_product_page": [
        "POST",
        "/v1/appCustomProductPages",
        [],
        [
            "appId",
            "name",
            "appStoreVersionTemplateId",
            "customProductPageTemplateId",
            "deepLink",
            "localizations"
        ]
    ],
    "create_app_custom_product_page_localization": [
        "POST",
        "/v1/appCustomProductPageLocalizations",
        [],
        [
            "appCustomProductPageVersionId",
            "locale",
            "promotionalText"
        ]
    ],
    "create_app_custom_product_page_version": [
        "POST",
        "/v1/appCustomProductPageVersions",
        [],
        [
            "appCustomProductPageId",
            "deepLink"
        ]
    ],
    "create_app_encryption_declaration": [
        "POST",
        "/v1/appEncryptionDeclarations",
        [],
        [
            "appId",
            "appDescription",
            "containsProprietaryCryptography",
            "containsThirdPartyCryptography",
            "availableOnFrenchStore"
        ]
    ],
    "create_app_event": [
        "POST",
        "/v1/appEvents",
        [],
        [
            "appId",
            "referenceName",
            "deepLink",
            "badge",
            "purchaseRequirement",
            "primaryLocale",
            "priority",
            "purpose",
            "territorySchedules"
        ]
    ],
    "create_app_event_localization": [
        "POST",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventId",
            "locale",
            "name",
            "shortDescription",
            "longDescription"
        ]
    ],
    "create_app_info_localization": [
        "POST",
        "/v1/appInfoLocalizations",
        [],
        [
            "appInfoId",
            "locale",
            "name",
            "subtitle",
            "privacyPolicyUrl",
            "privacyChoicesUrl",
            "privacyPolicyText"
        ]
    ],
    "create_app_price_schedule": [
        "POST",
        "/v1/appPriceSchedules",
        [],
        [
            "appId",
            "baseTerritoryId",
            "manualPrices"
        ]
    ],
    "create_app_store_review_detail": [
        "POST",
        "/v1/appStoreReviewDetails",
        [],
        [
            "appStoreVersionId",
            "contactFirstName",
            "contactLastName",
            "contactPhone",
            "contactEmail",
            "demoAccountName",
            "demoAccountPassword",
            "demoAccountRequired",
            "notes"
        ]
    ],
    "create_app_store_version": [
        "POST",
        "/v1/appStoreVersions",
        [],
        [
            "appId",
            "platform",
            "versionString",
            "copyright",
            "reviewType",
            "releaseType",
            "earliestReleaseDate",
            "buildId"
        ]
    ],
    "create_app_store_version_experiment": [
        "POST",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appId",
            "name",
            "platform",
            "trafficProportion"
        ]
    ],
    "create_app_store_version_experiment_treatment": [
        "POST",
        "/v1/appStoreVersionExperimentTreatments",
        [],
        [
            "appStoreVersionExperimentId",
            "name",
            "appIconName"
        ]
    ],
    "create_app_store_version_experiment_treatment_localization": [
        "POST",
        "/v1/appStoreVersionExperimentTreatmentLocalizations",
        [],
        [
            "appStoreVersionExperimentTreatmentId",
            "locale"
        ]
    ],
    "create_app_store_version_localization": [
        "POST",
        "/v1/appStoreVersionLocalizations",
        [],
        [
            "appStoreVersionId",
            "locale",
            "description",
            "keywords",
            "marketingUrl",
            "promotionalText",
            "supportUrl",
            "whatsNew"
        ]
    ],
    "create_app_store_version_phased_release": [
        "POST",
        "/v1/appStoreVersionPhasedReleases",
        [],
        [
            "appStoreVersionId",
            "phasedReleaseState"
        ]
    ],
    "create_app_store_version_promotion": [
        "POST",
        "/v1/appStoreVersionPromotions",
        [],
        [
            "appStoreVersionId",
            "appStoreVersionExperimentTreatmentId"
        ]
    ],
    "create_background_asset": [
        "POST",
        "/v1/backgroundAssets",
        [],
        [
            "appId",
            "assetPackIdentifier"
        ]
    ],
    "create_background_asset_version": [
        "POST",
        "/v1/backgroundAssetVersions",
        [],
        [
            "backgroundAssetId"
        ]
    ],
    "create_beta_app_clip_invocation": [
        "POST",
        "/v1/betaAppClipInvocations",
        [],
        [
            "buildBundleId",
            "url",
            "betaAppClipInvocationLocalizations"
        ]
    ],
    "create_beta_app_clip_invocation_localization": [
        "POST",
        "/v1/betaAppClipInvocationLocalizations",
        [],
        [
            "betaAppClipInvocationId",
            "title",
            "locale"
        ]
    ],
    "create_beta_app_localization": [
        "POST",
        "/v1/betaAppLocalizations",
        [],
        [
            "appId",
            "locale",
            "description",
            "feedbackEmail",
            "marketingUrl",
            "privacyPolicyUrl",
            "tvOsPrivacyPolicy"
        ]
    ],
    "create_beta_build_localization": [
        "POST",
        "/v1/betaBuildLocalizations",
        [],
        [
            "buildId",
            "locale",
            "whatsNew"
        ]
    ],
    "create_beta_group": [
        "POST",
        "/v1/betaGroups",
        [],
        [
            "appId",
            "name",
            "publicLinkEnabled",
            "publicLinkLimitEnabled",
            "publicLinkLimit",
            "feedbackEnabled",
            "hasAccessToAllBuilds"
        ]
    ],
    "create_beta_recruitment_criterion": [
        "POST",
        "/v1/betaRecruitmentCriteria",
        [],
        [
            "betaGroupId",
            "deviceFamilyOsVersionFilters"
        ]
    ],
    "create_beta_tester": [
        "POST",
        "/v1/betaTesters",
        [],
        [
            "email",
            "firstName",
            "lastName",
            "betaGroupIds",
            "buildIds"
        ]
    ],
    "create_bundle_id": [
        "POST",
        "/v1/bundleIds",
        [],
        [
            "identifier",
            "name",
            "platform",
            "seedId"
        ]
    ],
    "create_certificate": [
        "POST",
        "/v1/certificates",
        [],
        [
            "csrContent",
            "certificateType",
            "merchantIdId",
            "passTypeIdId"
        ]
    ],
    "create_ci_workflow": [
        "POST",
        "/v1/ciWorkflows",
        [],
        [
            "ciProductId",
            "scmRepositoryId",
            "ciXcodeVersionId",
            "ciMacOsVersionId",
            "name",
            "description",
            "branchStartCondition",
            "tagStartCondition",
            "pullRequestStartCondition",
            "scheduledStartCondition",
            "manualBranchStartCondition",
            "manualTagStartCondition",
            "manualPullRequestStartCondition",
            "actions",
            "isEnabled",
            "isLockedForEditing",
            "clean",
            "containerFilePath"
        ]
    ],
    "create_end_app_availability_pre_order": [
        "POST",
        "/v1/endAppAvailabilityPreOrders",
        [],
        [
            "territoryAvailabilityIds"
        ]
    ],
    "create_end_user_license_agreement": [
        "POST",
        "/v1/endUserLicenseAgreements",
        [],
        [
            "appId",
            "agreementText",
            "territoryIds"
        ]
    ],
    "create_game_center_achievement": [
        "POST",
        "/v2/gameCenterAchievements",
        [],
        [
            "referenceName",
            "vendorIdentifier",
            "points",
            "showBeforeEarned",
            "repeatable",
            "activityProperties",
            "gameCenterDetailId",
            "gameCenterGroupId"
        ]
    ],
    "create_game_center_achievement_localization": [
        "POST",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementVersionId",
            "locale",
            "name",
            "beforeEarnedDescription",
            "afterEarnedDescription"
        ]
    ],
    "create_game_center_achievement_version": [
        "POST",
        "/v2/gameCenterAchievementVersions",
        [],
        [
            "gameCenterAchievementId"
        ]
    ],
    "create_game_center_activity": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "referenceName",
            "vendorIdentifier",
            "playStyle",
            "minimumPlayersCount",
            "maximumPlayersCount",
            "supportsPartyCode",
            "properties",
            "gameCenterDetailId",
            "gameCenterGroupId",
            "fallbackUrl"
        ]
    ],
    "create_game_center_activity_localization": [
        "POST",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityVersionId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_game_center_activity_version": [
        "POST",
        "/v1/gameCenterActivityVersions",
        [],
        [
            "gameCenterActivityId",
            "fallbackUrl"
        ]
    ],
    "create_game_center_app_version": [
        "POST",
        "/v1/gameCenterAppVersions",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "create_game_center_challenge": [
        "POST",
        "/v1/gameCenterChallenges",
        [],
        [
            "referenceName",
            "vendorIdentifier",
            "challengeType",
            "repeatable",
            "gameCenterDetailId",
            "gameCenterGroupId",
            "gameCenterLeaderboardId"
        ]
    ],
    "create_game_center_challenge_localization": [
        "POST",
        "/v1/gameCenterChallengeLocalizations",
        [],
        [
            "gameCenterChallengeVersionId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_game_center_challenge_version": [
        "POST",
        "/v1/gameCenterChallengeVersions",
        [],
        [
            "gameCenterChallengeId"
        ]
    ],
    "create_game_center_detail": [
        "POST",
        "/v1/gameCenterDetails",
        [],
        [
            "appId"
        ]
    ],
    "create_game_center_group": [
        "POST",
        "/v1/gameCenterGroups",
        [],
        [
            "referenceName"
        ]
    ],
    "create_game_center_leaderboard": [
        "POST",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "referenceName",
            "vendorIdentifier",
            "defaultFormatter",
            "submissionType",
            "scoreSortType",
            "scoreRangeStart",
            "scoreRangeEnd",
            "recurrenceStartDate",
            "recurrenceDuration",
            "recurrenceRule",
            "activityProperties",
            "visibility",
            "gameCenterDetailId",
            "gameCenterGroupId",
            "gameCenterLeaderboardSetIds"
        ]
    ],
    "create_game_center_leaderboard_localization": [
        "POST",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardVersionId",
            "locale",
            "name",
            "formatterOverride",
            "formatterSuffix",
            "formatterSuffixSingular",
            "description"
        ]
    ],
    "create_game_center_leaderboard_set": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "referenceName",
            "vendorIdentifier",
            "gameCenterDetailId",
            "gameCenterGroupId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "create_game_center_leaderboard_set_localization": [
        "POST",
        "/v2/gameCenterLeaderboardSetLocalizations",
        [],
        [
            "gameCenterLeaderboardSetVersionId",
            "locale",
            "name"
        ]
    ],
    "create_game_center_leaderboard_set_member_localization": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetId",
            "gameCenterLeaderboardId",
            "locale",
            "name"
        ]
    ],
    "create_game_center_leaderboard_set_version": [
        "POST",
        "/v2/gameCenterLeaderboardSetVersions",
        [],
        [
            "gameCenterLeaderboardSetId"
        ]
    ],
    "create_game_center_leaderboard_version": [
        "POST",
        "/v2/gameCenterLeaderboardVersions",
        [],
        [
            "gameCenterLeaderboardId"
        ]
    ],
    "create_game_center_matchmaking_queue": [
        "POST",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "referenceName",
            "classicMatchmakingBundleIds",
            "gameCenterMatchmakingRuleSetId",
            "experimentRuleSetId"
        ]
    ],
    "create_game_center_matchmaking_rule": [
        "POST",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "referenceName",
            "description",
            "type",
            "expression",
            "weight"
        ]
    ],
    "create_game_center_matchmaking_rule_set": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "referenceName",
            "ruleLanguageVersion",
            "minPlayers",
            "maxPlayers"
        ]
    ],
    "create_game_center_matchmaking_team": [
        "POST",
        "/v1/gameCenterMatchmakingTeams",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "referenceName",
            "minPlayers",
            "maxPlayers"
        ]
    ],
    "create_in_app_purchase": [
        "POST",
        "/v2/inAppPurchases",
        [],
        [
            "appId",
            "name",
            "productId",
            "inAppPurchaseType",
            "reviewNote",
            "familySharable"
        ]
    ],
    "create_in_app_purchase_availability": [
        "POST",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchaseId",
            "availableInNewTerritories",
            "availableTerritories"
        ]
    ],
    "create_in_app_purchase_localization": [
        "POST",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_in_app_purchase_offer_code": [
        "POST",
        "/v1/inAppPurchaseOfferCodes",
        [],
        [
            "inAppPurchaseId",
            "name",
            "customerEligibilities",
            "prices"
        ]
    ],
    "create_in_app_purchase_offer_code_custom_code": [
        "POST",
        "/v1/inAppPurchaseOfferCodeCustomCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "customCode",
            "numberOfCodes",
            "expirationDate"
        ]
    ],
    "create_in_app_purchase_offer_code_one_time_use_code": [
        "POST",
        "/v1/inAppPurchaseOfferCodeOneTimeUseCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "numberOfCodes",
            "expirationDate",
            "environment"
        ]
    ],
    "create_in_app_purchase_price_schedule": [
        "POST",
        "/v1/inAppPurchasePriceSchedules",
        [],
        [
            "inAppPurchaseId",
            "baseTerritory",
            "manualPrices"
        ]
    ],
    "create_in_app_purchase_version": [
        "POST",
        "/v1/inAppPurchaseVersions",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "create_in_app_purchase_version_localization": [
        "POST",
        "/v2/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseVersionId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_marketplace_search_detail": [
        "POST",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "appId",
            "catalogUrl"
        ]
    ],
    "create_merchant_id": [
        "POST",
        "/v1/merchantIds",
        [],
        [
            "name",
            "identifier"
        ]
    ],
    "create_nomination": [
        "POST",
        "/v1/nominations",
        [],
        [
            "relatedAppIds",
            "name",
            "type",
            "description",
            "submitted",
            "publishStartDate",
            "publishEndDate",
            "notes",
            "deviceFamilies",
            "locales",
            "supplementalMaterialsUris",
            "hasInAppEvents",
            "launchInSelectMarketsFirst",
            "preOrderEnabled",
            "inAppEventIds",
            "supportedTerritoryIds"
        ]
    ],
    "create_pass_type_id": [
        "POST",
        "/v1/passTypeIds",
        [],
        [
            "name",
            "identifier"
        ]
    ],
    "create_profile": [
        "POST",
        "/v1/profiles",
        [],
        [
            "name",
            "profileType",
            "bundleIdId",
            "certificateIds",
            "deviceIds"
        ]
    ],
    "create_promoted_purchase": [
        "POST",
        "/v1/promotedPurchases",
        [],
        [
            "appId",
            "inAppPurchaseId",
            "subscriptionId",
            "visibleForAllUsers",
            "enabled"
        ]
    ],
    "create_review_submission": [
        "POST",
        "/v1/reviewSubmissions",
        [],
        [
            "appId",
            "platform"
        ]
    ],
    "create_subscription": [
        "POST",
        "/v1/subscriptions",
        [],
        [
            "subscriptionGroupId",
            "name",
            "productId",
            "subscriptionPeriod",
            "familySharable",
            "reviewNote",
            "groupLevel"
        ]
    ],
    "create_subscription_group": [
        "POST",
        "/v1/subscriptionGroups",
        [],
        [
            "appId",
            "referenceName"
        ]
    ],
    "create_subscription_group_localization": [
        "POST",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupId",
            "locale",
            "name",
            "customAppName"
        ]
    ],
    "create_subscription_group_version": [
        "POST",
        "/v1/subscriptionGroupVersions",
        [],
        [
            "subscriptionGroupId"
        ]
    ],
    "create_subscription_group_version_localization": [
        "POST",
        "/v2/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupVersionId",
            "locale",
            "name",
            "customAppName"
        ]
    ],
    "create_subscription_introductory_offer": [
        "POST",
        "/v1/subscriptionIntroductoryOffers",
        [],
        [
            "subscriptionId",
            "duration",
            "offerMode",
            "numberOfPeriods",
            "startDate",
            "endDate",
            "territoryId",
            "subscriptionPricePointId",
            "targetSubscriptionPlanType"
        ]
    ],
    "create_subscription_localization": [
        "POST",
        "/v1/subscriptionLocalizations",
        [],
        [
            "subscriptionId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_subscription_offer_code": [
        "POST",
        "/v1/subscriptionOfferCodes",
        [],
        [
            "subscriptionId",
            "name",
            "customerEligibilities",
            "offerEligibility",
            "duration",
            "offerMode",
            "numberOfPeriods",
            "autoRenewEnabled",
            "targetSubscriptionPlanType",
            "prices"
        ]
    ],
    "create_subscription_offer_code_custom_code": [
        "POST",
        "/v1/subscriptionOfferCodeCustomCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "customCode",
            "numberOfCodes",
            "expirationDate"
        ]
    ],
    "create_subscription_offer_code_one_time_use_code": [
        "POST",
        "/v1/subscriptionOfferCodeOneTimeUseCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "numberOfCodes",
            "expirationDate",
            "environment"
        ]
    ],
    "create_subscription_plan_availability": [
        "POST",
        "/v1/subscriptionPlanAvailabilities",
        [],
        [
            "subscriptionId",
            "planType",
            "availableTerritoryIds",
            "availableInNewTerritories"
        ]
    ],
    "create_subscription_price": [
        "POST",
        "/v1/subscriptionPrices",
        [],
        [
            "subscriptionId",
            "subscriptionPricePointId",
            "territoryId",
            "startDate",
            "preserveCurrentPrice",
            "planType"
        ]
    ],
    "create_subscription_promotional_offer": [
        "POST",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionId",
            "name",
            "offerCode",
            "duration",
            "offerMode",
            "numberOfPeriods",
            "targetSubscriptionPlanType",
            "prices"
        ]
    ],
    "create_subscription_version": [
        "POST",
        "/v1/subscriptionVersions",
        [],
        [
            "subscriptionId"
        ]
    ],
    "create_subscription_version_localization": [
        "POST",
        "/v2/subscriptionLocalizations",
        [],
        [
            "subscriptionVersionId",
            "locale",
            "name",
            "description"
        ]
    ],
    "create_webhook": [
        "POST",
        "/v1/webhooks",
        [],
        [
            "appId",
            "name",
            "url",
            "secret",
            "eventTypes",
            "enabled"
        ]
    ],
    "create_win_back_offer": [
        "POST",
        "/v1/winBackOffers",
        [],
        [
            "subscriptionId",
            "referenceName",
            "offerId",
            "duration",
            "offerMode",
            "periodCount",
            "customerEligibilityPaidSubscriptionDurationInMonths",
            "customerEligibilityTimeSinceLastSubscribedInMonths",
            "customerEligibilityWaitBetweenOffersInMonths",
            "startDate",
            "endDate",
            "priority",
            "promotionIntent",
            "targetSubscriptionPlanType",
            "prices"
        ]
    ],
    "delete_accessibility_declaration": [
        "DELETE",
        "/v1/accessibilityDeclarations",
        [],
        [
            "accessibilityDeclarationId"
        ]
    ],
    "delete_alternative_distribution_domain": [
        "DELETE",
        "/v1/alternativeDistributionDomains",
        [],
        [
            "alternativeDistributionDomainId"
        ]
    ],
    "delete_alternative_distribution_key": [
        "DELETE",
        "/v1/alternativeDistributionDomains",
        [],
        [
            "alternativeDistributionKeyId"
        ]
    ],
    "delete_analytics_report_request": [
        "DELETE",
        "/v1/analyticsReportRequests",
        [],
        [
            "analyticsReportRequestId"
        ]
    ],
    "delete_android_to_ios_app_mapping_detail": [
        "DELETE",
        "/v1/androidToIosAppMappingDetails",
        [],
        [
            "androidToIosAppMappingDetailId"
        ]
    ],
    "delete_app_clip_advanced_experience": [
        "DELETE",
        "/v1/nominations",
        [],
        [
            "appClipAdvancedExperienceId"
        ]
    ],
    "delete_app_clip_default_experience": [
        "PATCH",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipDefaultExperienceId"
        ]
    ],
    "delete_app_clip_default_experience_localization": [
        "DELETE",
        "/v1/appClipAppStoreReviewDetails",
        [],
        [
            "appClipDefaultExperienceLocalizationId"
        ]
    ],
    "delete_app_custom_product_page": [
        "DELETE",
        "/v1/appCustomProductPages",
        [],
        [
            "appCustomProductPageId"
        ]
    ],
    "delete_app_custom_product_page_localization": [
        "DELETE",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appCustomProductPageLocalizationId"
        ]
    ],
    "delete_app_event": [
        "DELETE",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventId"
        ]
    ],
    "delete_app_event_localization": [
        "DELETE",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventLocalizationId"
        ]
    ],
    "delete_app_info_localization": [
        "DELETE",
        "/v1/appCategories",
        [],
        [
            "appInfoLocalizationId"
        ]
    ],
    "delete_app_store_version": [
        "PATCH",
        "/v1/appStoreVersions",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "delete_app_store_version_experiment": [
        "DELETE",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appStoreVersionExperimentId"
        ]
    ],
    "delete_app_store_version_experiment_treatment": [
        "DELETE",
        "/v1/appStoreVersionExperimentTreatments",
        [],
        [
            "appStoreVersionExperimentTreatmentId"
        ]
    ],
    "delete_app_store_version_experiment_treatment_localization": [
        "DELETE",
        "/v1/appStoreVersionPromotions",
        [],
        [
            "appStoreVersionExperimentTreatmentLocalizationId"
        ]
    ],
    "delete_app_store_version_localization": [
        "DELETE",
        "/v1/appStoreVersionPhasedReleases",
        [],
        [
            "appStoreVersionLocalizationId"
        ]
    ],
    "delete_app_store_version_phased_release": [
        "POST",
        "/v1/appStoreVersionReleaseRequests",
        [],
        [
            "appStoreVersionPhasedReleaseId"
        ]
    ],
    "delete_beta_app_clip_invocation": [
        "DELETE",
        "/v1/betaAppClipInvocationLocalizations",
        [],
        [
            "betaAppClipInvocationId"
        ]
    ],
    "delete_beta_app_clip_invocation_localization": [
        "DELETE",
        "/v1/betaAppClipInvocationLocalizations",
        [],
        [
            "betaAppClipInvocationLocalizationId"
        ]
    ],
    "delete_beta_app_localization": [
        "DELETE",
        "/v1/betaAppLocalizations",
        [],
        [
            "betaAppLocalizationId"
        ]
    ],
    "delete_beta_build_localization": [
        "DELETE",
        "/v1/betaBuildLocalizations",
        [],
        [
            "betaBuildLocalizationId"
        ]
    ],
    "delete_beta_feedback_crash_submission": [
        "DELETE",
        "/v1/betaRecruitmentCriteria",
        [],
        [
            "betaFeedbackCrashSubmissionId"
        ]
    ],
    "delete_beta_feedback_screenshot_submission": [
        "DELETE",
        "/v1/betaFeedbackScreenshotSubmissions",
        [],
        [
            "betaFeedbackScreenshotSubmissionId"
        ]
    ],
    "delete_beta_group": [
        "DELETE",
        "/v1/betaTesters",
        [],
        [
            "betaGroupId"
        ]
    ],
    "delete_beta_recruitment_criterion": [
        "DELETE",
        "/v1/betaRecruitmentCriterionOptions",
        [],
        [
            "betaRecruitmentCriterionId"
        ]
    ],
    "delete_beta_tester": [
        "POST",
        "/v1/betaTesters",
        [],
        [
            "betaTesterId"
        ]
    ],
    "delete_bundle_id": [
        "DELETE",
        "/v1/bundleIds",
        [],
        [
            "bundleIdId"
        ]
    ],
    "delete_ci_product": [
        "DELETE",
        "/v1/ciProducts",
        [],
        [
            "ciProductId"
        ]
    ],
    "delete_ci_workflow": [
        "DELETE",
        "/v1/ciWorkflows",
        [],
        [
            "ciWorkflowId"
        ]
    ],
    "delete_customer_review_response": [
        "DELETE",
        "/v1/customerReviewResponses",
        [],
        [
            "customerReviewResponseId"
        ]
    ],
    "delete_end_user_license_agreement": [
        "DELETE",
        "/v1/territories",
        [],
        [
            "endUserLicenseAgreementId"
        ]
    ],
    "delete_game_center_achievement": [
        "PATCH",
        "/v2/gameCenterAchievements",
        [],
        [
            "gameCenterAchievementId"
        ]
    ],
    "delete_game_center_achievement_localization": [
        "DELETE",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementLocalizationId"
        ]
    ],
    "delete_game_center_activity": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId"
        ]
    ],
    "delete_game_center_activity_localization": [
        "DELETE",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityLocalizationId"
        ]
    ],
    "delete_game_center_challenge": [
        "PATCH",
        "/v1/gameCenterChallenges",
        [],
        [
            "gameCenterChallengeId"
        ]
    ],
    "delete_game_center_challenge_localization": [
        "DELETE",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterChallengeLocalizationId"
        ]
    ],
    "delete_game_center_group": [
        "DELETE",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId"
        ]
    ],
    "delete_game_center_leaderboard": [
        "PATCH",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterLeaderboardId"
        ]
    ],
    "delete_game_center_leaderboard_localization": [
        "DELETE",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardLocalizationId"
        ]
    ],
    "delete_game_center_leaderboard_set": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId"
        ]
    ],
    "delete_game_center_leaderboard_set_localization": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetLocalizationId"
        ]
    ],
    "delete_game_center_leaderboard_set_member_localization": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetMemberLocalizationId"
        ]
    ],
    "delete_game_center_matchmaking_queue": [
        "DELETE",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "gameCenterMatchmakingQueueId"
        ]
    ],
    "delete_game_center_matchmaking_rule": [
        "DELETE",
        "/v1/gameCenterMatchmakingTeams",
        [],
        [
            "gameCenterMatchmakingRuleId"
        ]
    ],
    "delete_game_center_matchmaking_rule_set": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "gameCenterMatchmakingRuleSetId"
        ]
    ],
    "delete_game_center_matchmaking_team": [
        "DELETE",
        "/v1/gameCenterMatchmakingTeams",
        [],
        [
            "gameCenterMatchmakingTeamId"
        ]
    ],
    "delete_in_app_purchase": [
        "DELETE",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "delete_in_app_purchase_localization": [
        "DELETE",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseLocalizationId"
        ]
    ],
    "delete_in_app_purchase_version_localization": [
        "DELETE",
        "/v1/inAppPurchaseSubmissions",
        [],
        [
            "inAppPurchaseVersionLocalizationId"
        ]
    ],
    "delete_marketplace_search_detail": [
        "DELETE",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "marketplaceSearchDetailId"
        ]
    ],
    "delete_merchant_id": [
        "DELETE",
        "/v1/passTypeIds",
        [],
        [
            "merchantIdId"
        ]
    ],
    "delete_nomination": [
        "DELETE",
        "/v1/nominations",
        [],
        [
            "nominationId"
        ]
    ],
    "delete_pass_type_id": [
        "DELETE",
        "/v1/passTypeIds",
        [],
        [
            "passTypeIdId"
        ]
    ],
    "delete_profile": [
        "DELETE",
        "/v1/devices",
        [],
        [
            "profileId"
        ]
    ],
    "delete_promoted_purchase": [
        "PATCH",
        "/v1/promotedPurchases",
        [],
        [
            "promotedPurchaseId"
        ]
    ],
    "delete_review_submission_item": [
        "PATCH",
        "/v1/reviewSubmissionItems",
        [],
        [
            "reviewSubmissionItemId"
        ]
    ],
    "delete_subscription": [
        "DELETE",
        "/v1/subscriptionLocalizations",
        [],
        [
            "subscriptionId"
        ]
    ],
    "delete_subscription_group": [
        "DELETE",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupId"
        ]
    ],
    "delete_subscription_group_localization": [
        "DELETE",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId"
        ]
    ],
    "delete_subscription_group_version_localization": [
        "DELETE",
        "/v2/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId"
        ]
    ],
    "delete_subscription_introductory_offer": [
        "DELETE",
        "/v1/subscriptionIntroductoryOffers",
        [],
        [
            "subscriptionIntroductoryOfferId"
        ]
    ],
    "delete_subscription_localization": [
        "POST",
        "/v1/subscriptionPrices",
        [],
        [
            "subscriptionLocalizationId"
        ]
    ],
    "delete_subscription_price": [
        "DELETE",
        "/v1/subscriptionPrices",
        [],
        [
            "subscriptionPriceId"
        ]
    ],
    "delete_subscription_promotional_offer": [
        "DELETE",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionPromotionalOfferId"
        ]
    ],
    "delete_subscription_version_localization": [
        "DELETE",
        "/v1/subscriptionGroupVersions",
        [],
        [
            "subscriptionLocalizationId"
        ]
    ],
    "delete_user": [
        "POST",
        "/v1/users",
        [],
        [
            "userId"
        ]
    ],
    "delete_webhook": [
        "POST",
        "/v1/webhookDeliveries",
        [],
        [
            "webhookId"
        ]
    ],
    "delete_win_back_offer": [
        "POST",
        "/v1/winBackOffers",
        [],
        [
            "winBackOfferId"
        ]
    ],
    "disable_bundle_id_capability": [
        "GET",
        "/v1/certificates",
        [],
        [
            "bundleIdCapabilityId"
        ]
    ],
    "enable_bundle_id_capability": [
        "GET",
        "/v1/bundleIdCapabilities",
        [],
        [
            "bundleIdId",
            "capabilityType",
            "settings"
        ]
    ],
    "get_accessibility_declaration": [
        "GET",
        "/v1/accessibilityDeclarations",
        [],
        [
            "accessibilityDeclarationId"
        ]
    ],
    "get_actor": [
        "GET",
        "/v2/sandboxTesters",
        [],
        [
            "actorId"
        ]
    ],
    "get_age_rating_declaration": [
        "GET",
        "/v1/appInfos",
        [],
        [
            "appInfoId"
        ]
    ],
    "get_alternative_distribution_domain": [
        "GET",
        "/v1/alternativeDistributionDomains",
        [],
        [
            "alternativeDistributionDomainId"
        ]
    ],
    "get_alternative_distribution_key": [
        "GET",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "alternativeDistributionKeyId"
        ]
    ],
    "get_alternative_distribution_package": [
        "GET",
        "/v1/alternativeDistributionPackages",
        [],
        [
            "alternativeDistributionPackageId"
        ]
    ],
    "get_alternative_distribution_package_delta": [
        "GET",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "alternativeDistributionPackageDeltaId"
        ]
    ],
    "get_alternative_distribution_package_variant": [
        "GET",
        "/v1/alternativeDistributionPackageVariants",
        [],
        [
            "alternativeDistributionPackageVariantId"
        ]
    ],
    "get_alternative_distribution_package_version": [
        "GET",
        "/v1/alternativeDistributionPackageVersions",
        [],
        [
            "alternativeDistributionPackageVersionId"
        ]
    ],
    "get_analytics_report": [
        "GET",
        "/v1/analyticsReports",
        [],
        [
            "analyticsReportId"
        ]
    ],
    "get_analytics_report_instance": [
        "GET",
        "/v1/analyticsReportInstances",
        [],
        [
            "analyticsReportInstanceId"
        ]
    ],
    "get_analytics_report_request": [
        "GET",
        "/v1/analyticsReportRequests",
        [],
        [
            "analyticsReportRequestId"
        ]
    ],
    "get_android_to_ios_app_mapping_detail": [
        "GET",
        "/v1/androidToIosAppMappingDetails",
        [],
        [
            "androidToIosAppMappingDetailId"
        ]
    ],
    "get_app": [
        "GET",
        "/v1/builds",
        [],
        [
            "appId"
        ]
    ],
    "get_app_alternative_distribution_key": [
        "GET",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "appId"
        ]
    ],
    "get_app_availability": [
        "POST",
        "/v2/appAvailabilities",
        [],
        [
            "appId"
        ]
    ],
    "get_app_beta_tester_usages": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "period",
            "groupByBetaTester",
            "betaTesterId",
            "limit",
            "cursor"
        ]
    ],
    "get_app_category": [
        "GET",
        "/v1/appCategories",
        [],
        [
            "appCategoryId"
        ]
    ],
    "get_app_clip": [
        "GET",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipId"
        ]
    ],
    "get_app_clip_advanced_experience": [
        "POST",
        "/v1/appClipAdvancedExperiences",
        [],
        [
            "appClipAdvancedExperienceId"
        ]
    ],
    "get_app_clip_default_experience": [
        "GET",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipDefaultExperienceId"
        ]
    ],
    "get_app_clip_default_experience_localization": [
        "GET",
        "/v1/appClipDefaultExperienceLocalizations",
        [],
        [
            "appClipDefaultExperienceLocalizationId"
        ]
    ],
    "get_app_clip_default_experience_review_detail": [
        "GET",
        "/v1/appClipAppStoreReviewDetails",
        [],
        [
            "appClipDefaultExperienceId"
        ]
    ],
    "get_app_custom_product_page": [
        "POST",
        "/v1/appCustomProductPages",
        [],
        [
            "appCustomProductPageId"
        ]
    ],
    "get_app_custom_product_page_localization": [
        "GET",
        "/v1/appCustomProductPageLocalizations",
        [],
        [
            "appCustomProductPageLocalizationId"
        ]
    ],
    "get_app_custom_product_page_version": [
        "GET",
        "/v1/appCustomProductPageVersions",
        [],
        [
            "appCustomProductPageVersionId"
        ]
    ],
    "get_app_encryption_declaration": [
        "GET",
        "/v1/appEncryptionDeclarations",
        [],
        [
            "appEncryptionDeclarationId"
        ]
    ],
    "get_app_event": [
        "GET",
        "/v1/appEvents",
        [],
        [
            "appEventId"
        ]
    ],
    "get_app_event_localization": [
        "GET",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventLocalizationId"
        ]
    ],
    "get_app_game_center_detail": [
        "POST",
        "/v1/gameCenterDetails",
        [],
        [
            "appId"
        ]
    ],
    "get_app_info": [
        "GET",
        "/v1/appInfos",
        [],
        [
            "appInfoId"
        ]
    ],
    "get_app_info_localization": [
        "GET",
        "/v1/appInfoLocalizations",
        [],
        [
            "appInfoLocalizationId"
        ]
    ],
    "get_app_perf_power_metrics": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "platform",
            "metricTypes",
            "deviceTypes"
        ]
    ],
    "get_app_price_point": [
        "GET",
        "/v3/appPricePoints",
        [],
        [
            "appPricePointId"
        ]
    ],
    "get_app_price_schedule": [
        "POST",
        "/v1/appPriceSchedules",
        [],
        [
            "appId"
        ]
    ],
    "get_app_price_schedule_base_territory": [
        "GET",
        "/v1/appPriceSchedules",
        [],
        [
            "appPriceScheduleId"
        ]
    ],
    "get_app_store_review_detail": [
        "GET",
        "/v1/appStoreReviewDetails",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_app_store_version": [
        "GET",
        "/v1/appStoreVersions",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_app_store_version_alternative_distribution_package": [
        "GET",
        "/v1/alternativeDistributionPackages",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_app_store_version_build": [
        "GET",
        "/v1/appStoreVersionLocalizations",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_app_store_version_experiment": [
        "GET",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appStoreVersionExperimentId"
        ]
    ],
    "get_app_store_version_experiment_treatment": [
        "GET",
        "/v1/appStoreVersionExperimentTreatments",
        [],
        [
            "appStoreVersionExperimentTreatmentId"
        ]
    ],
    "get_app_store_version_experiment_treatment_localization": [
        "GET",
        "/v1/appStoreVersionExperimentTreatmentLocalizations",
        [],
        [
            "appStoreVersionExperimentTreatmentLocalizationId"
        ]
    ],
    "get_app_store_version_game_center_app_version": [
        "GET",
        "/v1/gameCenterLeaderboardEntrySubmissions",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_app_store_version_localization": [
        "GET",
        "/v1/appStoreVersionLocalizations",
        [],
        [
            "appStoreVersionLocalizationId"
        ]
    ],
    "get_app_store_version_phased_release": [
        "GET",
        "/v1/appStoreVersionPhasedReleases",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "get_background_asset": [
        "POST",
        "/v1/backgroundAssets",
        [],
        [
            "backgroundAssetId"
        ]
    ],
    "get_background_asset_version": [
        "POST",
        "/v1/backgroundAssetVersions",
        [],
        [
            "backgroundAssetVersionId"
        ]
    ],
    "get_background_asset_version_app_store_release": [
        "POST",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "backgroundAssetVersionAppStoreReleaseId"
        ]
    ],
    "get_background_asset_version_external_beta_release": [
        "POST",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "backgroundAssetVersionExternalBetaReleaseId"
        ]
    ],
    "get_background_asset_version_internal_beta_release": [
        "POST",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "backgroundAssetVersionInternalBetaReleaseId"
        ]
    ],
    "get_beta_app_clip_invocation": [
        "POST",
        "/v1/betaAppClipInvocations",
        [],
        [
            "betaAppClipInvocationId"
        ]
    ],
    "get_beta_app_localization": [
        "GET",
        "/v1/betaAppLocalizations",
        [],
        [
            "betaAppLocalizationId"
        ]
    ],
    "get_beta_app_review_detail": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId"
        ]
    ],
    "get_beta_app_review_submission": [
        "GET",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "betaAppReviewSubmissionId"
        ]
    ],
    "get_beta_build_localization": [
        "GET",
        "/v1/betaBuildLocalizations",
        [],
        [
            "betaBuildLocalizationId"
        ]
    ],
    "get_beta_feedback_crash_log": [
        "GET",
        "/v1/betaRecruitmentCriteria",
        [],
        [
            "betaFeedbackCrashSubmissionId"
        ]
    ],
    "get_beta_feedback_crash_submission": [
        "GET",
        "/v1/betaFeedbackCrashSubmissions",
        [],
        [
            "betaFeedbackCrashSubmissionId"
        ]
    ],
    "get_beta_feedback_screenshot_submission": [
        "GET",
        "/v1/betaFeedbackScreenshotSubmissions",
        [],
        [
            "betaFeedbackScreenshotSubmissionId"
        ]
    ],
    "get_beta_group": [
        "GET",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId"
        ]
    ],
    "get_beta_group_beta_tester_usages": [
        "GET",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId",
            "period",
            "groupByBetaTester",
            "betaTesterId",
            "limit",
            "cursor"
        ]
    ],
    "get_beta_license_agreement": [
        "GET",
        "/v1/betaTesterInvitations",
        [],
        [
            "appId"
        ]
    ],
    "get_beta_recruitment_criterion": [
        "GET",
        "/v1/betaRecruitmentCriteria",
        [],
        [
            "betaGroupId"
        ]
    ],
    "get_beta_recruitment_criterion_compatible_build_check": [
        "GET",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId"
        ]
    ],
    "get_beta_tester": [
        "DELETE",
        "/v1/betaTesters",
        [],
        [
            "betaTesterId"
        ]
    ],
    "get_beta_tester_usages": [
        "GET",
        "/v1/betaTesters",
        [],
        [
            "betaTesterId",
            "appId",
            "period",
            "limit",
            "cursor"
        ]
    ],
    "get_build": [
        "GET",
        "/v1/preReleaseVersions",
        [],
        [
            "buildId"
        ]
    ],
    "get_build_beta_build_usages": [
        "GET",
        "/v1/builds",
        [],
        [
            "buildId"
        ]
    ],
    "get_build_beta_detail": [
        "GET",
        "/v1/buildBetaNotifications",
        [],
        [
            "buildId"
        ]
    ],
    "get_build_bundle_app_clip_domain_cache_status": [
        "GET",
        "/v1/buildBundles",
        [],
        [
            "buildBundleId"
        ]
    ],
    "get_build_bundle_app_clip_domain_debug_status": [
        "GET",
        "/v1/buildBundles",
        [],
        [
            "buildBundleId"
        ]
    ],
    "get_build_perf_power_metrics": [
        "GET",
        "/v1/builds",
        [],
        [
            "buildId",
            "platform",
            "metricTypes",
            "deviceTypes"
        ]
    ],
    "get_bundle_id": [
        "GET",
        "/v1/bundleIds",
        [],
        [
            "bundleIdId"
        ]
    ],
    "get_bundle_id_app": [
        "GET",
        "/v1/bundleIdCapabilities",
        [],
        [
            "bundleIdId"
        ]
    ],
    "get_certificate": [
        "GET",
        "/v1/certificates",
        [],
        [
            "certificateId"
        ]
    ],
    "get_ci_artifact": [
        "GET",
        "/v1/ciMacOsVersions",
        [],
        [
            "ciArtifactId"
        ]
    ],
    "get_ci_build_action": [
        "GET",
        "/v1/ciBuildActions",
        [],
        [
            "ciBuildActionId"
        ]
    ],
    "get_ci_build_action_build_run": [
        "POST",
        "/v1/ciMacOsVersions",
        [],
        [
            "ciBuildActionId"
        ]
    ],
    "get_ci_build_run": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciBuildRunId"
        ]
    ],
    "get_ci_issue": [
        "GET",
        "/v1/ciMacOsVersions",
        [],
        [
            "ciIssueId"
        ]
    ],
    "get_ci_mac_os_version": [
        "GET",
        "/v1/ciXcodeVersions",
        [],
        [
            "ciMacOsVersionId"
        ]
    ],
    "get_ci_product": [
        "GET",
        "/v1/ciProducts",
        [],
        [
            "ciProductId"
        ]
    ],
    "get_ci_test_result": [
        "GET",
        "/v1/ciMacOsVersions",
        [],
        [
            "ciTestResultId"
        ]
    ],
    "get_ci_workflow": [
        "POST",
        "/v1/ciWorkflows",
        [],
        [
            "ciWorkflowId"
        ]
    ],
    "get_ci_workflow_repository": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciWorkflowId"
        ]
    ],
    "get_ci_xcode_version": [
        "GET",
        "/v1/scmProviders",
        [],
        [
            "ciXcodeVersionId"
        ]
    ],
    "get_customer_review": [
        "POST",
        "/v1/customerReviewResponses",
        [],
        [
            "customerReviewId"
        ]
    ],
    "get_device": [
        "GET",
        "/v1/devices",
        [],
        [
            "deviceId"
        ]
    ],
    "get_diagnostic_signature_logs": [
        "GET",
        "/v1/diagnosticSignatures",
        [],
        [
            "diagnosticSignatureId",
            "limit"
        ]
    ],
    "get_end_user_license_agreement": [
        "GET",
        "/v1/endUserLicenseAgreements",
        [],
        [
            "appId"
        ]
    ],
    "get_game_center_achievement": [
        "GET",
        "/v2/gameCenterAchievements",
        [],
        [
            "gameCenterAchievementId"
        ]
    ],
    "get_game_center_achievement_localization": [
        "GET",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementLocalizationId"
        ]
    ],
    "get_game_center_achievement_localization_image": [
        "POST",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterAchievementLocalizationId"
        ]
    ],
    "get_game_center_achievement_version": [
        "GET",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementVersionId"
        ]
    ],
    "get_game_center_activity": [
        "GET",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId"
        ]
    ],
    "get_game_center_activity_localization": [
        "GET",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityLocalizationId"
        ]
    ],
    "get_game_center_activity_localization_image": [
        "GET",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityLocalizationId"
        ]
    ],
    "get_game_center_activity_version": [
        "GET",
        "/v1/gameCenterActivityVersions",
        [],
        [
            "gameCenterActivityVersionId"
        ]
    ],
    "get_game_center_activity_version_default_image": [
        "GET",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityVersionId"
        ]
    ],
    "get_game_center_app_version": [
        "GET",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterAppVersionId"
        ]
    ],
    "get_game_center_app_version_app_store_version": [
        "POST",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterAppVersionId"
        ]
    ],
    "get_game_center_challenge": [
        "GET",
        "/v1/gameCenterChallenges",
        [],
        [
            "gameCenterChallengeId"
        ]
    ],
    "get_game_center_challenge_localization": [
        "GET",
        "/v1/gameCenterChallengeLocalizations",
        [],
        [
            "gameCenterChallengeLocalizationId"
        ]
    ],
    "get_game_center_challenge_localization_image": [
        "POST",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterChallengeLocalizationId"
        ]
    ],
    "get_game_center_challenge_version": [
        "GET",
        "/v1/gameCenterChallengeVersions",
        [],
        [
            "gameCenterChallengeVersionId"
        ]
    ],
    "get_game_center_challenge_version_default_image": [
        "GET",
        "/v1/gameCenterChallengeLocalizations",
        [],
        [
            "gameCenterChallengeVersionId"
        ]
    ],
    "get_game_center_classic_matchmaking_request_metrics": [
        "GET",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "groupBy",
            "result",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_detail": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId"
        ]
    ],
    "get_game_center_detail_group": [
        "GET",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId"
        ]
    ],
    "get_game_center_group": [
        "GET",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId"
        ]
    ],
    "get_game_center_leaderboard": [
        "GET",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterLeaderboardId"
        ]
    ],
    "get_game_center_leaderboard_localization": [
        "GET",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardLocalizationId"
        ]
    ],
    "get_game_center_leaderboard_localization_image": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardLocalizationId"
        ]
    ],
    "get_game_center_leaderboard_set": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId"
        ]
    ],
    "get_game_center_leaderboard_set_localization": [
        "POST",
        "/v2/gameCenterLeaderboardSetLocalizations",
        [],
        [
            "gameCenterLeaderboardSetLocalizationId"
        ]
    ],
    "get_game_center_leaderboard_set_localization_image": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetLocalizationId"
        ]
    ],
    "get_game_center_leaderboard_set_version": [
        "POST",
        "/v2/gameCenterLeaderboardSetLocalizations",
        [],
        [
            "gameCenterLeaderboardSetVersionId"
        ]
    ],
    "get_game_center_leaderboard_version": [
        "GET",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardVersionId"
        ]
    ],
    "get_game_center_matchmaking_queue": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId"
        ]
    ],
    "get_game_center_matchmaking_queue_experiment_request_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "groupBy",
            "result",
            "gameCenterDetailId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_queue_experiment_size_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_queue_request_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "groupBy",
            "result",
            "gameCenterDetailId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_queue_session_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_queue_size_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_rule_boolean_result_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleId",
            "groupBy",
            "result",
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_rule_error_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleId",
            "groupBy",
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_rule_number_result_metrics": [
        "GET",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleId",
            "groupBy",
            "gameCenterMatchmakingQueueId",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_game_center_matchmaking_rule_set": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "gameCenterMatchmakingRuleSetId"
        ]
    ],
    "get_game_center_rule_based_matchmaking_request_metrics": [
        "GET",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "groupBy",
            "result",
            "granularity",
            "limit",
            "cursor"
        ]
    ],
    "get_in_app_purchase": [
        "GET",
        "/v2/inAppPurchases",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "get_in_app_purchase_availability": [
        "GET",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "get_in_app_purchase_content": [
        "GET",
        "/v1/inAppPurchaseVersions",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "get_in_app_purchase_localization": [
        "GET",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseLocalizationId"
        ]
    ],
    "get_in_app_purchase_offer_code": [
        "POST",
        "/v1/inAppPurchaseOfferCodes",
        [],
        [
            "inAppPurchaseOfferCodeId"
        ]
    ],
    "get_in_app_purchase_price_schedule": [
        "POST",
        "/v1/inAppPurchasePriceSchedules",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "get_in_app_purchase_price_schedule_base_territory": [
        "GET",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchasePriceScheduleId"
        ]
    ],
    "get_in_app_purchase_version": [
        "GET",
        "/v1/inAppPurchaseVersions",
        [],
        [
            "inAppPurchaseVersionId"
        ]
    ],
    "get_in_app_purchase_version_localization": [
        "GET",
        "/v2/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseVersionLocalizationId"
        ]
    ],
    "get_marketplace_search_detail": [
        "GET",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "appId"
        ]
    ],
    "get_merchant_id": [
        "GET",
        "/v1/merchantIds",
        [],
        [
            "merchantIdId"
        ]
    ],
    "get_nomination": [
        "GET",
        "/v1/nominations",
        [],
        [
            "nominationId"
        ]
    ],
    "get_pass_type_id": [
        "GET",
        "/v1/passTypeIds",
        [],
        [
            "passTypeIdId"
        ]
    ],
    "get_pre_release_version": [
        "GET",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "preReleaseVersionId"
        ]
    ],
    "get_profile": [
        "GET",
        "/v1/profiles",
        [],
        [
            "profileId"
        ]
    ],
    "get_profile_bundle_id": [
        "GET",
        "/v1/devices",
        [],
        [
            "profileId"
        ]
    ],
    "get_promoted_purchase": [
        "POST",
        "/v1/promotedPurchases",
        [],
        [
            "promotedPurchaseId"
        ]
    ],
    "get_review_submission": [
        "POST",
        "/v1/reviewSubmissions",
        [],
        [
            "reviewSubmissionId"
        ]
    ],
    "get_scm_git_reference": [
        "GET",
        "/v1/scmGitReferences",
        [],
        [
            "scmGitReferenceId"
        ]
    ],
    "get_scm_provider": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmProviderId"
        ]
    ],
    "get_scm_pull_request": [
        "GET",
        "/v1/scmPullRequests",
        [],
        [
            "scmPullRequestId"
        ]
    ],
    "get_scm_repository": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmRepositoryId"
        ]
    ],
    "get_subscription": [
        "POST",
        "/v1/subscriptions",
        [],
        [
            "subscriptionId"
        ]
    ],
    "get_subscription_grace_period": [
        "GET",
        "/v1/subscriptionGracePeriods",
        [],
        [
            "appId",
            "subscriptionGracePeriodId"
        ]
    ],
    "get_subscription_group": [
        "GET",
        "/v1/subscriptionGroups",
        [],
        [
            "subscriptionGroupId"
        ]
    ],
    "get_subscription_group_localization": [
        "GET",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId"
        ]
    ],
    "get_subscription_group_version": [
        "GET",
        "/v1/subscriptionGroupVersions",
        [],
        [
            "subscriptionGroupVersionId"
        ]
    ],
    "get_subscription_group_version_localization": [
        "GET",
        "/v2/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId"
        ]
    ],
    "get_subscription_localization": [
        "GET",
        "/v1/subscriptionLocalizations",
        [],
        [
            "subscriptionLocalizationId"
        ]
    ],
    "get_subscription_offer_code": [
        "POST",
        "/v1/subscriptionOfferCodes",
        [],
        [
            "subscriptionOfferCodeId"
        ]
    ],
    "get_subscription_offer_code_custom_code": [
        "GET",
        "/v1/subscriptionOfferCodeCustomCodes",
        [],
        [
            "subscriptionOfferCodeCustomCodeId"
        ]
    ],
    "get_subscription_offer_code_one_time_use_code": [
        "GET",
        "/v1/subscriptionOfferCodeOneTimeUseCodes",
        [],
        [
            "subscriptionOfferCodeOneTimeUseCodeId"
        ]
    ],
    "get_subscription_plan_availability": [
        "GET",
        "/v1/subscriptionPlanAvailabilities",
        [],
        [
            "subscriptionPlanAvailabilityId"
        ]
    ],
    "get_subscription_price_point": [
        "GET",
        "/v1/subscriptionPricePoints",
        [],
        [
            "subscriptionPricePointId"
        ]
    ],
    "get_subscription_promotional_offer": [
        "POST",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionPromotionalOfferId"
        ]
    ],
    "get_subscription_version": [
        "GET",
        "/v1/subscriptionVersions",
        [],
        [
            "subscriptionVersionId"
        ]
    ],
    "get_subscription_version_localization": [
        "GET",
        "/v2/subscriptionLocalizations",
        [],
        [
            "subscriptionLocalizationId"
        ]
    ],
    "get_user": [
        "GET",
        "/v1/users",
        [],
        [
            "userId"
        ]
    ],
    "get_user_invitation": [
        "GET",
        "/v1/userInvitations",
        [],
        [
            "userInvitationId"
        ]
    ],
    "get_webhook": [
        "GET",
        "/v1/webhooks",
        [],
        [
            "webhookId"
        ]
    ],
    "get_win_back_offer": [
        "POST",
        "/v1/winBackOffers",
        [],
        [
            "winBackOfferId"
        ]
    ],
    "invite_user": [
        "POST",
        "/v1/userInvitations",
        [],
        [
            "email",
            "firstName",
            "lastName",
            "roles",
            "allAppsVisible",
            "provisioningAllowed",
            "visibleAppIds"
        ]
    ],
    "list_accessibility_declarations": [
        "GET",
        "/v1/accessibilityDeclarations",
        [],
        [
            "appId",
            "deviceFamilies",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_actors": [
        "GET",
        "/v1/actors",
        [],
        [
            "actorIds",
            "limit",
            "cursor"
        ]
    ],
    "list_alternative_distribution_domains": [
        "GET",
        "/v1/alternativeDistributionDomains",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_alternative_distribution_keys": [
        "GET",
        "/v1/alternativeDistributionKeys",
        [],
        [
            "hasApp",
            "limit",
            "cursor"
        ]
    ],
    "list_alternative_distribution_package_version_deltas": [
        "GET",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "alternativeDistributionPackageVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_alternative_distribution_package_version_variants": [
        "GET",
        "/v1/alternativeDistributionPackageVersions",
        [],
        [
            "alternativeDistributionPackageVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_alternative_distribution_package_versions": [
        "GET",
        "/v1/alternativeDistributionPackages",
        [],
        [
            "alternativeDistributionPackageId",
            "state",
            "limit",
            "cursor"
        ]
    ],
    "list_analytics_report_instances": [
        "GET",
        "/v1/analyticsReports",
        [],
        [
            "analyticsReportId",
            "granularity",
            "processingDate",
            "limit",
            "cursor"
        ]
    ],
    "list_analytics_report_requests": [
        "GET",
        "/v1/analyticsReportRequests",
        [],
        [
            "appId",
            "accessType",
            "limit",
            "cursor"
        ]
    ],
    "list_analytics_report_segments": [
        "GET",
        "/v1/analyticsReportInstances",
        [],
        [
            "analyticsReportInstanceId",
            "limit",
            "cursor"
        ]
    ],
    "list_analytics_reports": [
        "GET",
        "/v1/analyticsReportRequests",
        [],
        [
            "analyticsReportRequestId",
            "category",
            "name",
            "limit",
            "cursor"
        ]
    ],
    "list_android_to_ios_app_mapping_details": [
        "GET",
        "/v1/androidToIosAppMappingDetails",
        [],
        [
            "appId",
            "limit",
            "cursor"
        ]
    ],
    "list_app_categories": [
        "GET",
        "/v1/appCategories",
        [],
        [
            "platforms",
            "hasParent",
            "limit",
            "cursor"
        ]
    ],
    "list_app_clip_advanced_experiences": [
        "POST",
        "/v1/appClipAdvancedExperiences",
        [],
        [
            "appClipId",
            "statuses",
            "placeStatuses",
            "actions",
            "limit",
            "cursor"
        ]
    ],
    "list_app_clip_default_experience_localizations": [
        "GET",
        "/v1/appClipDefaultExperienceLocalizations",
        [],
        [
            "appClipDefaultExperienceId",
            "locales",
            "limit",
            "cursor"
        ]
    ],
    "list_app_clip_default_experiences": [
        "GET",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipId",
            "hasReleaseVersion",
            "limit",
            "cursor"
        ]
    ],
    "list_app_clips": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "bundleIds",
            "limit",
            "cursor"
        ]
    ],
    "list_app_custom_product_page_localizations": [
        "GET",
        "/v1/appCustomProductPageLocalizations",
        [],
        [
            "appCustomProductPageVersionId",
            "locales",
            "limit",
            "cursor"
        ]
    ],
    "list_app_custom_product_page_versions": [
        "GET",
        "/v1/appCustomProductPageVersions",
        [],
        [
            "appCustomProductPageId",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_app_custom_product_pages": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "visible",
            "limit",
            "cursor"
        ]
    ],
    "list_app_encryption_declarations": [
        "GET",
        "/v1/appEncryptionDeclarations",
        [],
        [
            "appId",
            "platforms",
            "buildIds",
            "limit",
            "cursor"
        ]
    ],
    "list_app_event_localizations": [
        "GET",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventId",
            "limit",
            "cursor"
        ]
    ],
    "list_app_events": [
        "GET",
        "/v1/appEvents",
        [],
        [
            "appId",
            "eventStates",
            "appEventIds",
            "limit",
            "cursor"
        ]
    ],
    "list_app_info_localizations": [
        "GET",
        "/v1/appInfoLocalizations",
        [],
        [
            "appInfoId",
            "locales",
            "limit",
            "cursor"
        ]
    ],
    "list_app_infos": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "limit",
            "cursor"
        ]
    ],
    "list_app_price_point_equalizations": [
        "GET",
        "/v3/appPricePoints",
        [],
        [
            "appPricePointId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_app_price_points": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_app_price_schedule_automatic_prices": [
        "GET",
        "/v1/appPriceSchedules",
        [],
        [
            "appPriceScheduleId",
            "territoryIds",
            "startDate",
            "endDate",
            "limit",
            "cursor"
        ]
    ],
    "list_app_price_schedule_manual_prices": [
        "GET",
        "/v1/appPriceSchedules",
        [],
        [
            "appPriceScheduleId",
            "territoryIds",
            "startDate",
            "endDate",
            "limit",
            "cursor"
        ]
    ],
    "list_app_store_version_experiment_treatment_localizations": [
        "GET",
        "/v1/appStoreVersionExperimentTreatmentLocalizations",
        [],
        [
            "appStoreVersionExperimentTreatmentId",
            "locales",
            "limit",
            "cursor"
        ]
    ],
    "list_app_store_version_experiment_treatments": [
        "GET",
        "/v1/appStoreVersionExperimentTreatments",
        [],
        [
            "appStoreVersionExperimentId",
            "limit",
            "cursor"
        ]
    ],
    "list_app_store_version_experiments": [
        "GET",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appId",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_app_store_version_localizations": [
        "GET",
        "/v1/appStoreVersionLocalizations",
        [],
        [
            "appStoreVersionId",
            "locales",
            "limit",
            "cursor"
        ]
    ],
    "list_app_store_versions": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "platform",
            "versionString",
            "appVersionState",
            "limit",
            "cursor"
        ]
    ],
    "list_app_tags": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "visibleInAppStore",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_apps": [
        "GET",
        "/v1/apps",
        [],
        [
            "bundleId",
            "name",
            "sku",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_background_asset_versions": [
        "POST",
        "/v1/backgroundAssets",
        [],
        [
            "backgroundAssetId",
            "version",
            "state",
            "locale",
            "platform",
            "internalBetaReleaseState",
            "externalBetaReleaseState",
            "appStoreReleaseState",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_background_assets": [
        "POST",
        "/v1/backgroundAssets",
        [],
        [
            "appId",
            "assetPackIdentifier",
            "archived",
            "versionLocale",
            "versionPlatform",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_app_clip_invocations": [
        "POST",
        "/v1/betaAppClipInvocations",
        [],
        [
            "buildBundleId",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_app_localizations": [
        "GET",
        "/v1/betaAppLocalizations",
        [],
        [
            "appId",
            "locale",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_app_review_submissions": [
        "GET",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "buildId",
            "betaReviewState",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_build_localizations": [
        "GET",
        "/v1/betaBuildLocalizations",
        [],
        [
            "buildId",
            "locale",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_feedback_crash_submissions": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "buildIds",
            "preReleaseVersionIds",
            "betaTesterIds",
            "deviceModels",
            "osVersions",
            "appPlatforms",
            "devicePlatforms",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_feedback_screenshot_submissions": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "buildIds",
            "preReleaseVersionIds",
            "betaTesterIds",
            "deviceModels",
            "osVersions",
            "appPlatforms",
            "devicePlatforms",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_group_builds": [
        "POST",
        "/v1/builds",
        [],
        [
            "betaGroupId",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_groups": [
        "GET",
        "/v1/betaGroups",
        [],
        [
            "appId",
            "name",
            "isInternalGroup",
            "publicLinkEnabled",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_recruitment_criterion_options": [
        "GET",
        "/v1/betaRecruitmentCriterionOptions",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_beta_tester_apps": [
        "DELETE",
        "/v1/betaTesters",
        [],
        [
            "betaTesterId",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_tester_beta_groups": [
        "GET",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "betaTesterId",
            "limit",
            "cursor"
        ]
    ],
    "list_beta_testers": [
        "GET",
        "/v1/betaTesters",
        [],
        [
            "email",
            "firstName",
            "lastName",
            "inviteType",
            "appId",
            "betaGroupId",
            "buildId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_build_beta_groups": [
        "GET",
        "/v1/betaGroups",
        [],
        [
            "buildId",
            "limit",
            "cursor"
        ]
    ],
    "list_build_bundle_file_sizes": [
        "GET",
        "/v1/buildBundles",
        [],
        [
            "buildBundleId",
            "limit",
            "cursor"
        ]
    ],
    "list_build_bundles": [
        "GET",
        "/v1/builds",
        [],
        [
            "buildId"
        ]
    ],
    "list_build_individual_testers": [
        "POST",
        "/v1/builds",
        [],
        [
            "buildId",
            "limit",
            "cursor"
        ]
    ],
    "list_builds": [
        "GET",
        "/v1/builds",
        [],
        [
            "appId",
            "version",
            "preReleaseVersion",
            "platform",
            "processingState",
            "betaReviewState",
            "expired",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_bundle_id_capabilities": [
        "GET",
        "/v1/bundleIdCapabilities",
        [],
        [
            "bundleIdId",
            "limit",
            "cursor"
        ]
    ],
    "list_bundle_id_profiles": [
        "GET",
        "/v1/bundleIdCapabilities",
        [],
        [
            "bundleIdId",
            "limit",
            "cursor"
        ]
    ],
    "list_bundle_ids": [
        "GET",
        "/v1/bundleIds",
        [],
        [
            "identifier",
            "name",
            "platform",
            "seedId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_certificates": [
        "GET",
        "/v1/certificates",
        [],
        [
            "displayName",
            "certificateType",
            "serialNumber",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_build_action_artifacts": [
        "GET",
        "/v1/ciArtifacts",
        [],
        [
            "ciBuildActionId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_build_action_issues": [
        "GET",
        "/v1/ciArtifacts",
        [],
        [
            "ciBuildActionId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_build_action_test_results": [
        "GET",
        "/v1/ciArtifacts",
        [],
        [
            "ciBuildActionId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_build_run_actions": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciBuildRunId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_build_run_builds": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciBuildRunId",
            "version",
            "preReleaseVersion",
            "platform",
            "processingState",
            "betaReviewState",
            "expired",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_mac_os_version_xcode_versions": [
        "GET",
        "/v1/ciXcodeVersions",
        [],
        [
            "ciMacOsVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_mac_os_versions": [
        "GET",
        "/v1/ciMacOsVersions",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_ci_product_additional_repositories": [
        "POST",
        "/v1/ciWorkflows",
        [],
        [
            "ciProductId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_product_build_runs": [
        "POST",
        "/v1/ciWorkflows",
        [],
        [
            "ciProductId",
            "buildId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_product_primary_repositories": [
        "POST",
        "/v1/ciWorkflows",
        [],
        [
            "ciProductId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_product_workflows": [
        "GET",
        "/v1/ciProducts",
        [],
        [
            "ciProductId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_products": [
        "GET",
        "/v1/ciProducts",
        [],
        [
            "appId",
            "productType",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_workflow_build_runs": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciWorkflowId",
            "buildId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_xcode_version_mac_os_versions": [
        "GET",
        "/v1/scmProviders",
        [],
        [
            "ciXcodeVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_ci_xcode_versions": [
        "GET",
        "/v1/ciXcodeVersions",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_customer_reviews": [
        "GET",
        "/v1/apps",
        [],
        [
            "appId",
            "rating",
            "territory",
            "hasResponse",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_devices": [
        "GET",
        "/v1/devices",
        [],
        [
            "name",
            "platform",
            "udid",
            "status",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_diagnostic_signatures": [
        "GET",
        "/v1/builds",
        [],
        [
            "buildId",
            "diagnosticType",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_achievement_version_localizations": [
        "GET",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_achievement_versions": [
        "PATCH",
        "/v2/gameCenterAchievementVersions",
        [],
        [
            "gameCenterAchievementId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_activity_version_localizations": [
        "GET",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_activity_versions": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_app_version_compatibility_versions": [
        "POST",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterAppVersionId",
            "enabled",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_challenge_version_localizations": [
        "GET",
        "/v1/gameCenterChallengeLocalizations",
        [],
        [
            "gameCenterChallengeVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_challenge_versions": [
        "PATCH",
        "/v1/gameCenterChallengeVersions",
        [],
        [
            "gameCenterChallengeId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_achievements": [
        "GET",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "referenceNames",
            "archived",
            "gameCenterAchievementIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_activities": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterDetailId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_app_versions": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "enabled",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_challenges": [
        "GET",
        "/v1/gameCenterChallenges",
        [],
        [
            "gameCenterDetailId",
            "referenceNames",
            "archived",
            "gameCenterChallengeIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_leaderboard_sets": [
        "POST",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "referenceNames",
            "gameCenterLeaderboardSetIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_detail_leaderboards": [
        "GET",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "referenceNames",
            "archived",
            "gameCenterLeaderboardIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_achievements": [
        "GET",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "referenceNames",
            "archived",
            "gameCenterAchievementIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_activities": [
        "POST",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterGroupId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_challenges": [
        "GET",
        "/v1/gameCenterChallenges",
        [],
        [
            "gameCenterGroupId",
            "referenceNames",
            "archived",
            "gameCenterChallengeIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_details": [
        "GET",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "appVersionsEnabled",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_leaderboard_sets": [
        "PATCH",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "referenceNames",
            "gameCenterLeaderboardSetIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_group_leaderboards": [
        "GET",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "referenceNames",
            "archived",
            "gameCenterLeaderboardIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_groups": [
        "GET",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterDetailIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_set_leaderboards": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId",
            "referenceNames",
            "archived",
            "gameCenterLeaderboardIds",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_set_member_localizations": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetId",
            "gameCenterLeaderboardId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_set_version_localizations": [
        "POST",
        "/v2/gameCenterLeaderboardSetLocalizations",
        [],
        [
            "gameCenterLeaderboardSetVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_set_versions": [
        "POST",
        "/v2/gameCenterLeaderboardSetVersions",
        [],
        [
            "gameCenterLeaderboardSetId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_version_localizations": [
        "GET",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_leaderboard_versions": [
        "PATCH",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterLeaderboardId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_matchmaking_queues": [
        "POST",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_matchmaking_rule_set_queues": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_matchmaking_rule_set_rules": [
        "POST",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_matchmaking_rule_set_teams": [
        "POST",
        "/v1/gameCenterMatchmakingRules",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "limit",
            "cursor"
        ]
    ],
    "list_game_center_matchmaking_rule_sets": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_available_territories": [
        "GET",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchaseAvailabilityId",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_localizations": [
        "GET",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseId",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_offer_code_custom_codes": [
        "GET",
        "/v1/inAppPurchaseOfferCodeCustomCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_offer_code_one_time_use_codes": [
        "GET",
        "/v1/inAppPurchaseOfferCodeOneTimeUseCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_offer_code_prices": [
        "GET",
        "/v1/inAppPurchaseOfferCodeCustomCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_offer_codes": [
        "POST",
        "/v1/inAppPurchaseOfferCodes",
        [],
        [
            "inAppPurchaseId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_price_point_equalizations": [
        "GET",
        "/v1/inAppPurchasePricePoints",
        [],
        [
            "inAppPurchasePricePointId",
            "inAppPurchaseId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_price_points": [
        "GET",
        "/v1/inAppPurchasePricePoints",
        [],
        [
            "inAppPurchaseId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_price_schedule_automatic_prices": [
        "GET",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchasePriceScheduleId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_price_schedule_manual_prices": [
        "GET",
        "/v1/inAppPurchaseAvailabilities",
        [],
        [
            "inAppPurchasePriceScheduleId",
            "territory",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_version_localizations": [
        "GET",
        "/v2/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchase_versions": [
        "GET",
        "/v1/inAppPurchaseVersions",
        [],
        [
            "inAppPurchaseId",
            "state",
            "limit",
            "cursor"
        ]
    ],
    "list_in_app_purchases": [
        "GET",
        "/v2/inAppPurchases",
        [],
        [
            "appId",
            "inAppPurchaseType",
            "state",
            "name",
            "productId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_merchant_id_certificates": [
        "GET",
        "/v1/passTypeIds",
        [],
        [
            "merchantIdId",
            "displayName",
            "certificateType",
            "serialNumber",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_merchant_ids": [
        "GET",
        "/v1/merchantIds",
        [],
        [
            "name",
            "identifier",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_nominations": [
        "GET",
        "/v1/nominations",
        [],
        [
            "states",
            "types",
            "relatedAppIds",
            "hasInAppEvents",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_pass_type_id_certificates": [
        "GET",
        "/v1/passTypeIds",
        [],
        [
            "passTypeIdId",
            "displayName",
            "certificateType",
            "serialNumber",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_pass_type_ids": [
        "GET",
        "/v1/passTypeIds",
        [],
        [
            "name",
            "identifier",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_pre_release_versions": [
        "GET",
        "/v1/preReleaseVersions",
        [],
        [
            "appId",
            "platform",
            "version",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_profile_certificates": [
        "GET",
        "/v1/devices",
        [],
        [
            "profileId",
            "limit",
            "cursor"
        ]
    ],
    "list_profile_devices": [
        "GET",
        "/v1/devices",
        [],
        [
            "profileId",
            "limit",
            "cursor"
        ]
    ],
    "list_profiles": [
        "GET",
        "/v1/profiles",
        [],
        [
            "name",
            "profileType",
            "profileState",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_promoted_purchases": [
        "POST",
        "/v1/promotedPurchases",
        [],
        [
            "appId",
            "limit",
            "cursor"
        ]
    ],
    "list_review_submission_items": [
        "POST",
        "/v1/reviewSubmissionItems",
        [],
        [
            "reviewSubmissionId",
            "limit",
            "cursor"
        ]
    ],
    "list_review_submissions": [
        "POST",
        "/v1/reviewSubmissions",
        [],
        [
            "appId",
            "platform",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_sandbox_testers": [
        "GET",
        "/v2/sandboxTesters",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_scm_provider_repositories": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmProviderId",
            "limit",
            "cursor"
        ]
    ],
    "list_scm_providers": [
        "GET",
        "/v1/scmProviders",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_scm_repositories": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmRepositoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_scm_repository_git_references": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmRepositoryId",
            "limit",
            "cursor"
        ]
    ],
    "list_scm_repository_pull_requests": [
        "GET",
        "/v1/scmRepositories",
        [],
        [
            "scmRepositoryId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_group_localizations": [
        "GET",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_group_version_localizations": [
        "GET",
        "/v2/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_group_versions": [
        "GET",
        "/v1/subscriptionGroupVersions",
        [],
        [
            "subscriptionGroupId",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_groups": [
        "GET",
        "/v1/subscriptionGroups",
        [],
        [
            "appId",
            "referenceName",
            "subscriptionStates",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_introductory_offers": [
        "POST",
        "/v1/subscriptionIntroductoryOffers",
        [],
        [
            "subscriptionId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_localizations": [
        "GET",
        "/v1/subscriptionLocalizations",
        [],
        [
            "subscriptionId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_offer_code_custom_codes": [
        "GET",
        "/v1/subscriptionOfferCodeCustomCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_offer_code_one_time_use_codes": [
        "GET",
        "/v1/subscriptionOfferCodeOneTimeUseCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_offer_code_prices": [
        "GET",
        "/v1/subscriptionOfferCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_offer_codes": [
        "POST",
        "/v1/subscriptionOfferCodes",
        [],
        [
            "subscriptionId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_plan_availabilities": [
        "GET",
        "/v1/subscriptionPlanAvailabilities",
        [],
        [
            "subscriptionId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_plan_availability_territories": [
        "GET",
        "/v1/subscriptionVersions",
        [],
        [
            "subscriptionPlanAvailabilityId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_price_point_adjusted_equalizations": [
        "GET",
        "/v1/subscriptionPricePoints",
        [],
        [
            "subscriptionPricePointId",
            "territory",
            "subscriptionId",
            "planType",
            "upfrontPricePointId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_price_point_equalizations": [
        "GET",
        "/v1/subscriptionPricePoints",
        [],
        [
            "subscriptionPricePointId",
            "territory",
            "subscriptionId",
            "planType",
            "upfrontPricePointId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_price_points": [
        "GET",
        "/v1/subscriptions",
        [],
        [
            "subscriptionId",
            "territory",
            "planType",
            "upfrontPricePointId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_prices": [
        "POST",
        "/v1/subscriptionPrices",
        [],
        [
            "subscriptionId",
            "territory",
            "planType",
            "subscriptionPricePointId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_promotional_offer_prices": [
        "GET",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionPromotionalOfferId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_promotional_offers": [
        "POST",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_version_localizations": [
        "GET",
        "/v2/subscriptionLocalizations",
        [],
        [
            "subscriptionVersionId",
            "limit",
            "cursor"
        ]
    ],
    "list_subscription_versions": [
        "GET",
        "/v1/subscriptionVersions",
        [],
        [
            "subscriptionId",
            "states",
            "limit",
            "cursor"
        ]
    ],
    "list_subscriptions": [
        "POST",
        "/v1/subscriptions",
        [],
        [
            "subscriptionGroupId",
            "name",
            "productId",
            "states",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_territories": [
        "GET",
        "/v1/territories",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "list_territory_availabilities": [
        "PATCH",
        "/v2/appAvailabilities",
        [],
        [
            "appAvailabilityId",
            "limit",
            "cursor"
        ]
    ],
    "list_user_invitation_visible_apps": [
        "GET",
        "/v1/actors",
        [],
        [
            "userInvitationId",
            "limit",
            "cursor"
        ]
    ],
    "list_user_invitations": [
        "GET",
        "/v1/userInvitations",
        [],
        [
            "email",
            "roles",
            "visibleAppId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_user_visible_apps": [
        "POST",
        "/v1/users",
        [],
        [
            "userId",
            "limit",
            "cursor"
        ]
    ],
    "list_users": [
        "GET",
        "/v1/users",
        [],
        [
            "roles",
            "username",
            "visibleAppId",
            "sort",
            "limit",
            "cursor"
        ]
    ],
    "list_webhook_deliveries": [
        "POST",
        "/v1/webhookDeliveries",
        [],
        [
            "webhookId",
            "deliveryStates",
            "createdSince",
            "createdBefore",
            "limit",
            "cursor"
        ]
    ],
    "list_webhooks": [
        "GET",
        "/v1/webhooks",
        [],
        [
            "appId",
            "limit",
            "cursor"
        ]
    ],
    "list_win_back_offer_prices": [
        "POST",
        "/v1/winBackOffers",
        [],
        [
            "winBackOfferId",
            "territoryIds",
            "limit",
            "cursor"
        ]
    ],
    "list_win_back_offers": [
        "POST",
        "/v1/winBackOffers",
        [],
        [
            "subscriptionId",
            "limit",
            "cursor"
        ]
    ],
    "notify_build_testers": [
        "GET",
        "/v1/buildBetaNotifications",
        [],
        [
            "buildId"
        ]
    ],
    "ping_webhook": [
        "POST",
        "/v1/webhookPings",
        [],
        [
            "webhookId"
        ]
    ],
    "redeliver_webhook_delivery": [
        "POST",
        "/v1/webhookDeliveries",
        [],
        [
            "webhookDeliveryId"
        ]
    ],
    "register_device": [
        "GET",
        "/v1/devices",
        [],
        [
            "name",
            "platform",
            "udid"
        ]
    ],
    "release_app_store_version": [
        "POST",
        "/v1/appStoreVersionReleaseRequests",
        [],
        [
            "appStoreVersionId"
        ]
    ],
    "remove_achievements_from_game_center_activity": [
        "DELETE",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId",
            "gameCenterAchievementIds"
        ]
    ],
    "remove_beta_tester_from_apps": [
        "DELETE",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "betaTesterId",
            "appIds"
        ]
    ],
    "remove_beta_testers_from_group": [
        "DELETE",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "betaGroupId",
            "betaTesterIds"
        ]
    ],
    "remove_build_from_beta_groups": [
        "DELETE",
        "/v1/betaGroups",
        [],
        [
            "buildId",
            "betaGroupIds"
        ]
    ],
    "remove_builds_from_beta_group": [
        "DELETE",
        "/v1/betaGroups",
        [],
        [
            "betaGroupId",
            "buildIds"
        ]
    ],
    "remove_compatibility_versions_from_game_center_app_version": [
        "DELETE",
        "/v1/gameCenterLeaderboardEntrySubmissions",
        [],
        [
            "gameCenterAppVersionId",
            "compatibilityVersionIds"
        ]
    ],
    "remove_individual_testers_from_build": [
        "DELETE",
        "/v1/betaGroups",
        [],
        [
            "buildId",
            "betaTesterIds"
        ]
    ],
    "remove_leaderboards_from_game_center_activity": [
        "DELETE",
        "/v1/gameCenterActivityVersions",
        [],
        [
            "gameCenterActivityId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "remove_leaderboards_from_game_center_leaderboard_set": [
        "DELETE",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "remove_visible_apps_from_user": [
        "DELETE",
        "/v1/userInvitations",
        [],
        [
            "userId",
            "appIds"
        ]
    ],
    "reorder_promoted_purchases": [
        "PATCH",
        "/v1/apps",
        [],
        [
            "appId",
            "promotedPurchaseIds"
        ]
    ],
    "replace_game_center_detail_achievements": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "gameCenterAchievementIds"
        ]
    ],
    "replace_game_center_detail_challenges_minimum_platform_versions": [
        "PATCH",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterDetailId",
            "appStoreVersionIds"
        ]
    ],
    "replace_game_center_detail_leaderboard_sets": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "gameCenterLeaderboardSetIds"
        ]
    ],
    "replace_game_center_detail_leaderboards": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "replace_game_center_group_achievements": [
        "PATCH",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "gameCenterAchievementIds"
        ]
    ],
    "replace_game_center_group_leaderboard_sets": [
        "PATCH",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterGroupId",
            "gameCenterLeaderboardSetIds"
        ]
    ],
    "replace_game_center_group_leaderboards": [
        "PATCH",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "replace_game_center_leaderboard_set_leaderboards": [
        "PATCH",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId",
            "gameCenterLeaderboardIds"
        ]
    ],
    "replace_user_visible_apps": [
        "PATCH",
        "/v1/userInvitations",
        [],
        [
            "userId",
            "appIds"
        ]
    ],
    "resend_beta_tester_invitation": [
        "POST",
        "/v1/betaTesterInvitations",
        [],
        [
            "appId",
            "betaTesterId"
        ]
    ],
    "respond_to_customer_review": [
        "POST",
        "/v1/customerReviewResponses",
        [],
        [
            "customerReviewId",
            "responseBody"
        ]
    ],
    "revoke_certificate": [
        "DELETE",
        "/v1/profiles",
        [],
        [
            "certificateId"
        ]
    ],
    "set_app_clip_default_experience_release_version": [
        "PATCH",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipDefaultExperienceId",
            "appStoreVersionId"
        ]
    ],
    "set_app_store_version_build": [
        "PATCH",
        "/v1/appStoreVersions",
        [],
        [
            "appStoreVersionId",
            "buildId"
        ]
    ],
    "set_game_center_achievement_activity": [
        "PATCH",
        "/v2/gameCenterAchievementVersions",
        [],
        [
            "gameCenterAchievementId",
            "gameCenterActivityId"
        ]
    ],
    "set_game_center_challenge_leaderboard": [
        "PATCH",
        "/v1/gameCenterChallengeVersions",
        [],
        [
            "gameCenterChallengeId",
            "gameCenterLeaderboardId"
        ]
    ],
    "set_game_center_leaderboard_activity": [
        "PATCH",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterLeaderboardId",
            "gameCenterActivityId"
        ]
    ],
    "set_game_center_leaderboard_challenge": [
        "PATCH",
        "/v2/gameCenterLeaderboardVersions",
        [],
        [
            "gameCenterLeaderboardId",
            "gameCenterChallengeId"
        ]
    ],
    "start_ci_build_run": [
        "POST",
        "/v1/ciBuildRuns",
        [],
        [
            "ciWorkflowId",
            "sourceBranchOrTagId",
            "scmPullRequestId",
            "clean"
        ]
    ],
    "submit_build_for_beta_review": [
        "POST",
        "/v1/betaAppReviewSubmissions",
        [],
        [
            "buildId"
        ]
    ],
    "submit_game_center_leaderboard_entry": [
        "POST",
        "/v1/gameCenterLeaderboardEntrySubmissions",
        [],
        [
            "bundleId",
            "scopedPlayerId",
            "challengeIds",
            "submittedDate",
            "preReleased",
            "vendorIdentifier",
            "score",
            "context"
        ]
    ],
    "submit_game_center_player_achievement": [
        "POST",
        "/v1/gameCenterPlayerAchievementSubmissions",
        [],
        [
            "bundleId",
            "scopedPlayerId",
            "challengeIds",
            "submittedDate",
            "preReleased",
            "vendorIdentifier",
            "percentageAchieved"
        ]
    ],
    "submit_in_app_purchase_for_review": [
        "POST",
        "/v1/inAppPurchaseSubmissions",
        [],
        [
            "inAppPurchaseId"
        ]
    ],
    "submit_review_submission": [
        "GET",
        "/v1/reviewSubmissions",
        [],
        [
            "reviewSubmissionId"
        ]
    ],
    "test_game_center_matchmaking_rule_set": [
        "POST",
        "/test_game_center_matchmaking_rule_set",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "requests"
        ]
    ],
    "update_accessibility_declaration": [
        "PATCH",
        "/v1/accessibilityDeclarations",
        [],
        [
            "accessibilityDeclarationId",
            "publish",
            "supportsAudioDescriptions",
            "supportsCaptions",
            "supportsDarkInterface",
            "supportsDifferentiateWithoutColorAlone",
            "supportsLargerText",
            "supportsReducedMotion",
            "supportsSufficientContrast",
            "supportsVoiceControl",
            "supportsVoiceover"
        ]
    ],
    "update_age_rating_declaration": [
        "PATCH",
        "/v1/ageRatingDeclarations",
        [],
        [
            "ageRatingDeclarationId",
            "advertising",
            "ageAssurance",
            "alcoholTobaccoOrDrugUseOrReferences",
            "contests",
            "gambling",
            "gamblingSimulated",
            "gunsOrOtherWeapons",
            "healthOrWellnessTopics",
            "horrorOrFearThemes",
            "kidsAgeBand",
            "lootBox",
            "matureOrSuggestiveThemes",
            "medicalOrTreatmentInformation",
            "messagingAndChat",
            "parentalControls",
            "profanityOrCrudeHumor",
            "sexualContentGraphicAndNudity",
            "sexualContentOrNudity",
            "socialMedia",
            "socialMediaAgeRestricted",
            "unrestrictedWebAccess",
            "userGeneratedContent",
            "violenceCartoonOrFantasy",
            "violenceRealistic",
            "violenceRealisticProlongedGraphicOrSadistic",
            "ageRatingOverrideV2",
            "koreaAgeRatingOverride",
            "developerAgeRatingInfoUrl"
        ]
    ],
    "update_android_to_ios_app_mapping_detail": [
        "PATCH",
        "/v1/androidToIosAppMappingDetails",
        [],
        [
            "androidToIosAppMappingDetailId",
            "packageName",
            "appSigningKeyPublicCertificateSha256Fingerprints"
        ]
    ],
    "update_app": [
        "PATCH",
        "/v1/apps",
        [],
        [
            "appId",
            "primaryLocale",
            "bundleId",
            "contentRightsDeclaration",
            "subscriptionStatusUrl",
            "subscriptionStatusUrlVersion",
            "subscriptionStatusUrlForSandbox",
            "subscriptionStatusUrlVersionForSandbox",
            "streamlinedPurchasingEnabled",
            "accessibilityUrl"
        ]
    ],
    "update_app_clip_advanced_experience": [
        "PATCH",
        "/v1/appClipAdvancedExperiences",
        [],
        [
            "appClipAdvancedExperienceId",
            "headerImageId",
            "defaultLanguage",
            "isPoweredBy",
            "action",
            "businessCategory",
            "place",
            "localizations"
        ]
    ],
    "update_app_clip_app_store_review_detail": [
        "PATCH",
        "/v1/appClipAppStoreReviewDetails",
        [],
        [
            "appClipAppStoreReviewDetailId",
            "invocationUrls"
        ]
    ],
    "update_app_clip_default_experience": [
        "PATCH",
        "/v1/appClipDefaultExperiences",
        [],
        [
            "appClipDefaultExperienceId",
            "action",
            "releaseWithAppStoreVersionId"
        ]
    ],
    "update_app_clip_default_experience_localization": [
        "PATCH",
        "/v1/appClipDefaultExperienceLocalizations",
        [],
        [
            "appClipDefaultExperienceLocalizationId",
            "subtitle"
        ]
    ],
    "update_app_custom_product_page": [
        "PATCH",
        "/v1/appCustomProductPages",
        [],
        [
            "appCustomProductPageId",
            "name",
            "visible"
        ]
    ],
    "update_app_custom_product_page_localization": [
        "PATCH",
        "/v1/appCustomProductPageLocalizations",
        [],
        [
            "appCustomProductPageLocalizationId",
            "promotionalText"
        ]
    ],
    "update_app_custom_product_page_version": [
        "PATCH",
        "/v1/appCustomProductPageVersions",
        [],
        [
            "appCustomProductPageVersionId",
            "deepLink"
        ]
    ],
    "update_app_event": [
        "PATCH",
        "/v1/appEvents",
        [],
        [
            "appEventId",
            "referenceName",
            "deepLink",
            "badge",
            "purchaseRequirement",
            "primaryLocale",
            "priority",
            "purpose",
            "territorySchedules"
        ]
    ],
    "update_app_event_localization": [
        "PATCH",
        "/v1/appEventLocalizations",
        [],
        [
            "appEventLocalizationId",
            "name",
            "shortDescription",
            "longDescription"
        ]
    ],
    "update_app_info": [
        "PATCH",
        "/v1/appInfos",
        [],
        [
            "appInfoId",
            "primaryCategoryId",
            "primarySubcategoryOneId",
            "primarySubcategoryTwoId",
            "secondaryCategoryId",
            "secondarySubcategoryOneId",
            "secondarySubcategoryTwoId"
        ]
    ],
    "update_app_info_localization": [
        "PATCH",
        "/v1/appCategories",
        [],
        [
            "appInfoLocalizationId",
            "name",
            "subtitle",
            "privacyPolicyUrl",
            "privacyChoicesUrl",
            "privacyPolicyText"
        ]
    ],
    "update_app_store_review_detail": [
        "PATCH",
        "/v1/reviewSubmissions",
        [],
        [
            "appStoreReviewDetailId",
            "contactFirstName",
            "contactLastName",
            "contactPhone",
            "contactEmail",
            "demoAccountName",
            "demoAccountPassword",
            "demoAccountRequired",
            "notes"
        ]
    ],
    "update_app_store_version": [
        "PATCH",
        "/v1/appStoreVersions",
        [],
        [
            "appStoreVersionId",
            "versionString",
            "copyright",
            "reviewType",
            "releaseType",
            "earliestReleaseDate",
            "downloadable",
            "buildId"
        ]
    ],
    "update_app_store_version_experiment": [
        "PATCH",
        "/v2/appStoreVersionExperiments",
        [],
        [
            "appStoreVersionExperimentId",
            "name",
            "trafficProportion",
            "started"
        ]
    ],
    "update_app_store_version_experiment_treatment": [
        "PATCH",
        "/v1/appStoreVersionExperimentTreatments",
        [],
        [
            "appStoreVersionExperimentTreatmentId",
            "name",
            "appIconName"
        ]
    ],
    "update_app_store_version_localization": [
        "PATCH",
        "/v1/appStoreVersionLocalizations",
        [],
        [
            "appStoreVersionLocalizationId",
            "description",
            "keywords",
            "marketingUrl",
            "promotionalText",
            "supportUrl",
            "whatsNew"
        ]
    ],
    "update_app_store_version_phased_release": [
        "POST",
        "/v1/appStoreVersionReleaseRequests",
        [],
        [
            "appStoreVersionPhasedReleaseId",
            "phasedReleaseState"
        ]
    ],
    "update_background_asset": [
        "PATCH",
        "/v1/backgroundAssets",
        [],
        [
            "backgroundAssetId",
            "archived"
        ]
    ],
    "update_beta_app_clip_invocation": [
        "PATCH",
        "/v1/betaAppClipInvocationLocalizations",
        [],
        [
            "betaAppClipInvocationId",
            "url"
        ]
    ],
    "update_beta_app_clip_invocation_localization": [
        "PATCH",
        "/v1/betaAppClipInvocationLocalizations",
        [],
        [
            "betaAppClipInvocationLocalizationId",
            "title"
        ]
    ],
    "update_beta_app_localization": [
        "PATCH",
        "/v1/betaAppLocalizations",
        [],
        [
            "betaAppLocalizationId",
            "description",
            "feedbackEmail",
            "marketingUrl",
            "privacyPolicyUrl",
            "tvOsPrivacyPolicy"
        ]
    ],
    "update_beta_app_review_detail": [
        "PATCH",
        "/v1/betaAppLocalizations",
        [],
        [
            "betaAppReviewDetailId",
            "contactFirstName",
            "contactLastName",
            "contactPhone",
            "contactEmail",
            "demoAccountName",
            "demoAccountPassword",
            "demoAccountRequired",
            "notes"
        ]
    ],
    "update_beta_build_localization": [
        "PATCH",
        "/v1/betaBuildLocalizations",
        [],
        [
            "betaBuildLocalizationId",
            "whatsNew"
        ]
    ],
    "update_beta_group": [
        "PATCH",
        "/v1/builds",
        [],
        [
            "betaGroupId",
            "name",
            "publicLinkEnabled",
            "publicLinkLimitEnabled",
            "publicLinkLimit",
            "feedbackEnabled",
            "iosBuildsAvailableForAppleSiliconMac",
            "iosBuildsAvailableForAppleVision"
        ]
    ],
    "update_beta_license_agreement": [
        "PATCH",
        "/v1/betaTesterInvitations",
        [],
        [
            "betaLicenseAgreementId",
            "agreementText"
        ]
    ],
    "update_beta_recruitment_criterion": [
        "PATCH",
        "/v1/betaRecruitmentCriterionOptions",
        [],
        [
            "betaRecruitmentCriterionId",
            "deviceFamilyOsVersionFilters"
        ]
    ],
    "update_build": [
        "POST",
        "/v1/builds",
        [],
        [
            "buildId",
            "expired",
            "usesNonExemptEncryption"
        ]
    ],
    "update_build_beta_detail": [
        "PATCH",
        "/v1/buildBetaNotifications",
        [],
        [
            "buildBetaDetailId",
            "autoNotifyEnabled"
        ]
    ],
    "update_build_test_notes": [
        "PATCH",
        "/v1/betaBuildLocalizations",
        [],
        [
            "buildId",
            "locale",
            "whatsNew"
        ]
    ],
    "update_bundle_id": [
        "PATCH",
        "/v1/bundleIds",
        [],
        [
            "bundleIdId",
            "name"
        ]
    ],
    "update_bundle_id_capability": [
        "PATCH",
        "/v1/bundleIdCapabilities",
        [],
        [
            "bundleIdCapabilityId",
            "capabilityType",
            "settings"
        ]
    ],
    "update_certificate": [
        "PATCH",
        "/v1/profiles",
        [],
        [
            "certificateId",
            "activated"
        ]
    ],
    "update_ci_workflow": [
        "PATCH",
        "/v1/ciWorkflows",
        [],
        [
            "ciWorkflowId",
            "name",
            "description",
            "branchStartCondition",
            "tagStartCondition",
            "pullRequestStartCondition",
            "scheduledStartCondition",
            "manualBranchStartCondition",
            "manualTagStartCondition",
            "manualPullRequestStartCondition",
            "actions",
            "isEnabled",
            "isLockedForEditing",
            "clean",
            "containerFilePath",
            "ciXcodeVersionId",
            "ciMacOsVersionId"
        ]
    ],
    "update_device": [
        "PATCH",
        "/v1/merchantIds",
        [],
        [
            "deviceId",
            "name",
            "status"
        ]
    ],
    "update_end_user_license_agreement": [
        "PATCH",
        "/v1/endUserLicenseAgreements",
        [],
        [
            "endUserLicenseAgreementId",
            "agreementText",
            "territoryIds"
        ]
    ],
    "update_game_center_achievement": [
        "PATCH",
        "/v2/gameCenterAchievements",
        [],
        [
            "gameCenterAchievementId",
            "referenceName",
            "points",
            "showBeforeEarned",
            "repeatable",
            "archived",
            "activityProperties"
        ]
    ],
    "update_game_center_achievement_localization": [
        "PATCH",
        "/v2/gameCenterAchievementLocalizations",
        [],
        [
            "gameCenterAchievementLocalizationId",
            "name",
            "beforeEarnedDescription",
            "afterEarnedDescription"
        ]
    ],
    "update_game_center_activity": [
        "PATCH",
        "/v1/gameCenterActivities",
        [],
        [
            "gameCenterActivityId",
            "referenceName",
            "playStyle",
            "minimumPlayersCount",
            "maximumPlayersCount",
            "supportsPartyCode",
            "archived",
            "properties"
        ]
    ],
    "update_game_center_activity_localization": [
        "PATCH",
        "/v1/gameCenterActivityLocalizations",
        [],
        [
            "gameCenterActivityLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_game_center_activity_version": [
        "PATCH",
        "/v1/gameCenterActivityVersions",
        [],
        [
            "gameCenterActivityVersionId",
            "fallbackUrl"
        ]
    ],
    "update_game_center_app_version": [
        "PATCH",
        "/v1/gameCenterAppVersions",
        [],
        [
            "gameCenterAppVersionId",
            "enabled"
        ]
    ],
    "update_game_center_challenge": [
        "PATCH",
        "/v1/gameCenterChallenges",
        [],
        [
            "gameCenterChallengeId",
            "referenceName",
            "archived",
            "repeatable",
            "gameCenterLeaderboardId"
        ]
    ],
    "update_game_center_challenge_localization": [
        "PATCH",
        "/v1/gameCenterChallengeLocalizations",
        [],
        [
            "gameCenterChallengeLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_game_center_detail": [
        "PATCH",
        "/v1/gameCenterDetails",
        [],
        [
            "gameCenterDetailId",
            "gameCenterGroupId",
            "defaultLeaderboardId",
            "defaultGroupLeaderboardId"
        ]
    ],
    "update_game_center_group": [
        "PATCH",
        "/v1/gameCenterGroups",
        [],
        [
            "gameCenterGroupId",
            "referenceName"
        ]
    ],
    "update_game_center_leaderboard": [
        "PATCH",
        "/v2/gameCenterLeaderboards",
        [],
        [
            "gameCenterLeaderboardId",
            "referenceName",
            "defaultFormatter",
            "submissionType",
            "scoreSortType",
            "scoreRangeStart",
            "scoreRangeEnd",
            "recurrenceStartDate",
            "recurrenceDuration",
            "recurrenceRule",
            "archived",
            "activityProperties",
            "visibility"
        ]
    ],
    "update_game_center_leaderboard_localization": [
        "PATCH",
        "/v2/gameCenterLeaderboardLocalizations",
        [],
        [
            "gameCenterLeaderboardLocalizationId",
            "name",
            "formatterOverride",
            "formatterSuffix",
            "formatterSuffixSingular",
            "description"
        ]
    ],
    "update_game_center_leaderboard_set": [
        "POST",
        "/v2/gameCenterLeaderboardSets",
        [],
        [
            "gameCenterLeaderboardSetId",
            "referenceName"
        ]
    ],
    "update_game_center_leaderboard_set_localization": [
        "POST",
        "/v2/gameCenterLeaderboardSetLocalizations",
        [],
        [
            "gameCenterLeaderboardSetLocalizationId",
            "name"
        ]
    ],
    "update_game_center_leaderboard_set_member_localization": [
        "POST",
        "/v1/gameCenterLeaderboardSetMemberLocalizations",
        [],
        [
            "gameCenterLeaderboardSetMemberLocalizationId",
            "name"
        ]
    ],
    "update_game_center_matchmaking_queue": [
        "PATCH",
        "/v1/gameCenterMatchmakingQueues",
        [],
        [
            "gameCenterMatchmakingQueueId",
            "classicMatchmakingBundleIds",
            "gameCenterMatchmakingRuleSetId",
            "experimentRuleSetId"
        ]
    ],
    "update_game_center_matchmaking_rule": [
        "PATCH",
        "/v1/gameCenterMatchmakingTeams",
        [],
        [
            "gameCenterMatchmakingRuleId",
            "description",
            "expression",
            "weight"
        ]
    ],
    "update_game_center_matchmaking_rule_set": [
        "POST",
        "/v1/gameCenterMatchmakingRuleSets",
        [],
        [
            "gameCenterMatchmakingRuleSetId",
            "minPlayers",
            "maxPlayers"
        ]
    ],
    "update_game_center_matchmaking_team": [
        "PATCH",
        "/v1/gameCenterMatchmakingTeams",
        [],
        [
            "gameCenterMatchmakingTeamId",
            "minPlayers",
            "maxPlayers"
        ]
    ],
    "update_in_app_purchase": [
        "PATCH",
        "/v2/inAppPurchases",
        [],
        [
            "inAppPurchaseId",
            "name",
            "reviewNote",
            "familySharable"
        ]
    ],
    "update_in_app_purchase_localization": [
        "PATCH",
        "/v1/inAppPurchaseLocalizations",
        [],
        [
            "inAppPurchaseLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_in_app_purchase_offer_code": [
        "PATCH",
        "/v1/inAppPurchaseOfferCodes",
        [],
        [
            "inAppPurchaseOfferCodeId",
            "active"
        ]
    ],
    "update_in_app_purchase_offer_code_custom_code": [
        "PATCH",
        "/v1/inAppPurchaseOfferCodeOneTimeUseCodes",
        [],
        [
            "inAppPurchaseOfferCodeCustomCodeId",
            "active"
        ]
    ],
    "update_in_app_purchase_offer_code_one_time_use_code": [
        "PATCH",
        "/v1/inAppPurchaseOfferCodeOneTimeUseCodes",
        [],
        [
            "inAppPurchaseOfferCodeOneTimeUseCodeId",
            "active"
        ]
    ],
    "update_in_app_purchase_version_localization": [
        "PATCH",
        "/v1/inAppPurchaseSubmissions",
        [],
        [
            "inAppPurchaseVersionLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_marketplace_search_detail": [
        "PATCH",
        "/v1/marketplaceSearchDetails",
        [],
        [
            "marketplaceSearchDetailId",
            "catalogUrl"
        ]
    ],
    "update_merchant_id": [
        "PATCH",
        "/v1/passTypeIds",
        [],
        [
            "merchantIdId",
            "name"
        ]
    ],
    "update_nomination": [
        "PATCH",
        "/v1/nominations",
        [],
        [
            "nominationId",
            "name",
            "type",
            "description",
            "submitted",
            "archived",
            "publishStartDate",
            "publishEndDate",
            "notes",
            "deviceFamilies",
            "locales",
            "supplementalMaterialsUris",
            "hasInAppEvents",
            "launchInSelectMarketsFirst",
            "preOrderEnabled",
            "relatedAppIds",
            "inAppEventIds",
            "supportedTerritoryIds"
        ]
    ],
    "update_pass_type_id": [
        "PATCH",
        "/v1/passTypeIds",
        [],
        [
            "passTypeIdId",
            "name"
        ]
    ],
    "update_promoted_purchase": [
        "PATCH",
        "/v1/promotedPurchases",
        [],
        [
            "promotedPurchaseId",
            "visibleForAllUsers",
            "enabled"
        ]
    ],
    "update_review_submission_item": [
        "PATCH",
        "/v1/reviewSubmissionItems",
        [],
        [
            "reviewSubmissionItemId",
            "resolved",
            "removed"
        ]
    ],
    "update_sandbox_tester": [
        "PATCH",
        "/v2/sandboxTestersClearPurchaseHistoryRequest",
        [],
        [
            "sandboxTesterId",
            "territory",
            "interruptPurchases",
            "subscriptionRenewalRate"
        ]
    ],
    "update_subscription": [
        "PATCH",
        "/v1/subscriptions",
        [],
        [
            "subscriptionId",
            "name",
            "subscriptionPeriod",
            "familySharable",
            "reviewNote",
            "groupLevel"
        ]
    ],
    "update_subscription_grace_period": [
        "PATCH",
        "/v1/subscriptionGracePeriods",
        [],
        [
            "subscriptionGracePeriodId",
            "optIn",
            "sandboxOptIn",
            "duration",
            "renewalType"
        ]
    ],
    "update_subscription_group": [
        "PATCH",
        "/v1/subscriptionGroups",
        [],
        [
            "subscriptionGroupId",
            "referenceName"
        ]
    ],
    "update_subscription_group_localization": [
        "PATCH",
        "/v1/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId",
            "name",
            "customAppName"
        ]
    ],
    "update_subscription_group_version_localization": [
        "PATCH",
        "/v2/subscriptionGroupLocalizations",
        [],
        [
            "subscriptionGroupLocalizationId",
            "name",
            "customAppName"
        ]
    ],
    "update_subscription_introductory_offer": [
        "PATCH",
        "/v1/subscriptionIntroductoryOffers",
        [],
        [
            "subscriptionIntroductoryOfferId",
            "endDate"
        ]
    ],
    "update_subscription_localization": [
        "PATCH",
        "/v1/subscriptionLocalizations",
        [],
        [
            "subscriptionLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_subscription_offer_code": [
        "PATCH",
        "/v1/subscriptionOfferCodes",
        [],
        [
            "subscriptionOfferCodeId",
            "active"
        ]
    ],
    "update_subscription_offer_code_custom_code": [
        "PATCH",
        "/v1/subscriptionOfferCodeCustomCodes",
        [],
        [
            "subscriptionOfferCodeCustomCodeId",
            "active"
        ]
    ],
    "update_subscription_offer_code_one_time_use_code": [
        "PATCH",
        "/v1/subscriptionOfferCodeOneTimeUseCodes",
        [],
        [
            "subscriptionOfferCodeOneTimeUseCodeId",
            "active"
        ]
    ],
    "update_subscription_plan_availability": [
        "PATCH",
        "/v1/subscriptionPlanAvailabilities",
        [],
        [
            "subscriptionPlanAvailabilityId",
            "availableTerritoryIds",
            "availableInNewTerritories"
        ]
    ],
    "update_subscription_promotional_offer": [
        "PATCH",
        "/v1/subscriptionPromotionalOffers",
        [],
        [
            "subscriptionPromotionalOfferId",
            "prices"
        ]
    ],
    "update_subscription_version_localization": [
        "PATCH",
        "/v2/subscriptionLocalizations",
        [],
        [
            "subscriptionLocalizationId",
            "name",
            "description"
        ]
    ],
    "update_territory_availability": [
        "PATCH",
        "/v1/endAppAvailabilityPreOrders",
        [],
        [
            "territoryAvailabilityId",
            "available",
            "releaseDate",
            "preOrderEnabled"
        ]
    ],
    "update_user": [
        "PATCH",
        "/v1/users",
        [],
        [
            "userId",
            "roles",
            "allAppsVisible",
            "provisioningAllowed",
            "visibleAppIds"
        ]
    ],
    "update_webhook": [
        "PATCH",
        "/v1/webhooks",
        [],
        [
            "webhookId",
            "name",
            "url",
            "secret",
            "eventTypes",
            "enabled"
        ]
    ],
    "update_win_back_offer": [
        "PATCH",
        "/v1/winBackOffers",
        [],
        [
            "winBackOfferId",
            "customerEligibilityPaidSubscriptionDurationInMonths",
            "customerEligibilityTimeSinceLastSubscribedInMonths",
            "customerEligibilityWaitBetweenOffersInMonths",
            "startDate",
            "endDate",
            "priority",
            "promotionIntent"
        ]
    ]
}

class AppStoreConnectDynamicAction(Action):
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
            raise ValueError(f"App Store Connect API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class AppStoreConnectProvider(Provider):
    def __init__(self):
        super().__init__(
            service="app_store_connect",
            display_name="App Store Connect",
            category="Developer Tools",
            auth_types=["custom_credential", "api_key"],
            description="Apple App Store Connect API for managing apps, TestFlight builds, user invitations, and reviews with 653 actions."
        )
        for act in get_provider_actions("app_store_connect"):
            self.register_action(AppStoreConnectDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.appstoreconnect.apple.com/v1/apps?limit=1"
        for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))
        if val_url.startswith("{instanceUrl}"):
            inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
            val_url = val_url.replace("{instanceUrl}", inst)

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
            raise ValueError(f"App Store Connect connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid App Store Connect credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"App Store Connect validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"App Store Connect Account"
        }

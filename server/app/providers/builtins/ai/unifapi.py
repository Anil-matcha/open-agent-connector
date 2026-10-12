"""
UnifAPI Provider for ConnectorHub.
Loads and registers 220 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.unifapi.com"

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
    "aggregate_geo_mentions": [
        "GET",
        "/aggregate_geo_mentions",
        [],
        [
            "target",
            "engine",
            "location",
            "language",
            "filters",
            "internal_list_limit"
        ]
    ],
    "batch_get_tiktok_videos": [
        "GET",
        "/batch_get_tiktok_videos",
        [],
        [
            "ids"
        ]
    ],
    "browse_instagram_explore": [
        "GET",
        "/browse_instagram_explore",
        [],
        [
            "cursor"
        ]
    ],
    "browse_instagram_recommended_reels": [
        "GET",
        "/browse_instagram_recommended_reels",
        [],
        [
            "cursor"
        ]
    ],
    "browse_reddit_feed_home": [
        "GET",
        "/browse_reddit_feed_home",
        [],
        [
            "cursor"
        ]
    ],
    "browse_reddit_feed_news": [
        "GET",
        "/browse_reddit_feed_news",
        [],
        [
            "cursor"
        ]
    ],
    "browse_reddit_feed_popular": [
        "GET",
        "/browse_reddit_feed_popular",
        [],
        [
            "cursor"
        ]
    ],
    "browse_youtube_trending": [
        "GET",
        "/browse_youtube_trending",
        [],
        [
            "country",
            "type",
            "language_code"
        ]
    ],
    "capture_screenshot": [
        "GET",
        "/capture_screenshot",
        [],
        [
            "url",
            "wait_until",
            "timeout_ms",
            "viewport",
            "full_page",
            "format",
            "quality",
            "selector",
            "omit_background"
        ]
    ],
    "check_x_friendship": [
        "GET",
        "/check_x_friendship",
        [],
        [
            "source_id",
            "target_id",
            "source_screen_name",
            "target_screen_name"
        ]
    ],
    "classify_seo_keyword_intent": [
        "GET",
        "/classify_seo_keyword_intent",
        [],
        [
            "keywords",
            "language"
        ]
    ],
    "collect_seo_keyword_autocomplete": [
        "GET",
        "/collect_seo_keyword_autocomplete",
        [],
        [
            "keyword",
            "location",
            "language",
            "cursor_pointer",
            "client"
        ]
    ],
    "collect_seo_serp": [
        "GET",
        "/collect_seo_serp",
        [],
        [
            "query",
            "target",
            "location",
            "language",
            "device",
            "os",
            "page",
            "depth",
            "limit",
            "view",
            "include_ai_overview",
            "people_also_ask_depth",
            "include_pixel_rankings",
            "viewport",
            "google_domain",
            "google_search_params",
            "include_omitted_results",
            "remove_url_params",
            "expand_related_results",
            "stop_at_target",
            "target_match",
            "target_search_mode",
            "target_element_types"
        ]
    ],
    "compare_geo_mention_groups": [
        "GET",
        "/compare_geo_mention_groups",
        [],
        [
            "groups",
            "engine",
            "location",
            "language",
            "filters",
            "internal_list_limit"
        ]
    ],
    "convert_instagram_media_id": [
        "GET",
        "/convert_instagram_media_id",
        [],
        [
            "shortcode"
        ]
    ],
    "convert_instagram_shortcode_from_media": [
        "GET",
        "/convert_instagram_shortcode_from_media",
        [],
        [
            "media_id"
        ]
    ],
    "convert_instagram_user_id": [
        "GET",
        "/convert_instagram_user_id",
        [],
        [
            "username"
        ]
    ],
    "count_seo_bulk_backlinks": [
        "GET",
        "/count_seo_bulk_backlinks",
        [],
        [
            "targets"
        ]
    ],
    "count_seo_bulk_new_lost_backlinks": [
        "GET",
        "/count_seo_bulk_new_lost_backlinks",
        [],
        [
            "targets",
            "date_from"
        ]
    ],
    "count_seo_bulk_new_lost_referring_domains": [
        "GET",
        "/count_seo_bulk_new_lost_referring_domains",
        [],
        [
            "targets",
            "date_from"
        ]
    ],
    "count_seo_bulk_referring_domains": [
        "GET",
        "/count_seo_bulk_referring_domains",
        [],
        [
            "targets"
        ]
    ],
    "discover_seo_keyword_ideas": [
        "GET",
        "/discover_seo_keyword_ideas",
        [],
        [
            "keywords",
            "location",
            "language",
            "limit",
            "offset",
            "offset_token",
            "closely_variants",
            "ignore_synonyms",
            "include_serp_info",
            "view"
        ]
    ],
    "estimate_seo_bulk_traffic": [
        "GET",
        "/estimate_seo_bulk_traffic",
        [],
        [
            "targets",
            "location",
            "language",
            "view"
        ]
    ],
    "estimate_seo_historical_bulk_traffic": [
        "GET",
        "/estimate_seo_historical_bulk_traffic",
        [],
        [
            "targets",
            "location",
            "language",
            "date_from",
            "date_to"
        ]
    ],
    "extract_instagram_shortcode": [
        "GET",
        "/extract_instagram_shortcode",
        [],
        [
            "url"
        ]
    ],
    "extract_links": [
        "GET",
        "/extract_links",
        [],
        [
            "url",
            "wait_until",
            "timeout_ms",
            "visible_links_only",
            "exclude_external_links"
        ]
    ],
    "find_seo_backlink_competitors": [
        "GET",
        "/find_seo_backlink_competitors",
        [],
        [
            "target",
            "main_domain",
            "exclude_large_domains",
            "exclude_internal_backlinks",
            "rank_scale",
            "filters",
            "order_by",
            "limit",
            "offset"
        ]
    ],
    "find_seo_backlink_domain_intersection": [
        "GET",
        "/find_seo_backlink_domain_intersection",
        [],
        [
            "targets",
            "exclude_targets",
            "intersection_mode",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "backlinks_filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "find_seo_backlink_page_intersection": [
        "GET",
        "/find_seo_backlink_page_intersection",
        [],
        [
            "targets",
            "exclude_targets",
            "intersection_mode",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "find_seo_domain_competitors": [
        "GET",
        "/find_seo_domain_competitors",
        [],
        [
            "target",
            "location",
            "language",
            "exclude_top_domains",
            "intersecting_domains",
            "limit",
            "offset",
            "view"
        ]
    ],
    "find_seo_domain_keyword_intersection": [
        "GET",
        "/find_seo_domain_keyword_intersection",
        [],
        [
            "target1",
            "target2",
            "location",
            "language",
            "intersections",
            "limit",
            "offset",
            "view"
        ]
    ],
    "find_seo_keyword_suggestions": [
        "GET",
        "/find_seo_keyword_suggestions",
        [],
        [
            "keyword",
            "location",
            "language",
            "limit",
            "offset",
            "offset_token",
            "exact_match",
            "ignore_synonyms",
            "include_serp_info",
            "include_seed_keyword",
            "view"
        ]
    ],
    "find_seo_page_keyword_intersection": [
        "GET",
        "/find_seo_page_keyword_intersection",
        [],
        [
            "pages",
            "exclude_pages",
            "location",
            "language",
            "intersection_mode",
            "limit",
            "offset",
            "view"
        ]
    ],
    "find_seo_ranked_keywords": [
        "GET",
        "/find_seo_ranked_keywords",
        [],
        [
            "target",
            "location",
            "language",
            "limit",
            "offset",
            "ignore_synonyms",
            "view"
        ]
    ],
    "find_seo_related_keywords": [
        "GET",
        "/find_seo_related_keywords",
        [],
        [
            "keyword",
            "location",
            "language",
            "depth",
            "limit",
            "offset",
            "ignore_synonyms",
            "include_serp_info",
            "include_seed_keyword",
            "view"
        ]
    ],
    "find_seo_serp_competitors": [
        "GET",
        "/find_seo_serp_competitors",
        [],
        [
            "keywords",
            "location",
            "language",
            "include_subdomains",
            "limit",
            "offset"
        ]
    ],
    "find_seo_site_keywords": [
        "GET",
        "/find_seo_site_keywords",
        [],
        [
            "target",
            "location",
            "language",
            "limit",
            "offset",
            "offset_token",
            "include_subdomains",
            "include_serp_info",
            "view"
        ]
    ],
    "get_geo_keyword_search_volume": [
        "GET",
        "/geo_keyword_search_volume",
        [],
        [
            "keywords",
            "location",
            "language"
        ]
    ],
    "get_hacker_news_item": [
        "GET",
        "/hacker_news_item",
        [],
        [
            "id"
        ]
    ],
    "get_hacker_news_max_item": [
        "GET",
        "/hacker_news_max_item",
        [],
        []
    ],
    "get_hacker_news_updates": [
        "PATCH",
        "/hacker_news_updates",
        [],
        []
    ],
    "get_hacker_news_user": [
        "GET",
        "/hacker_news_user",
        [],
        [
            "id"
        ]
    ],
    "get_hotel_info": [
        "GET",
        "/hotel_info",
        [],
        [
            "hotel_identifier",
            "location",
            "language",
            "check_in",
            "check_out",
            "currency",
            "adults",
            "children",
            "load_prices_by_dates",
            "prices_start_date",
            "prices_end_date",
            "prices_date_range"
        ]
    ],
    "get_instagram_location": [
        "GET",
        "/instagram_location",
        [],
        [
            "id"
        ]
    ],
    "get_instagram_post": [
        "POST",
        "/instagram_post",
        [],
        [
            "shortcode"
        ]
    ],
    "get_instagram_user": [
        "GET",
        "/instagram_user",
        [],
        [
            "username"
        ]
    ],
    "get_linkedin_ad": [
        "GET",
        "/linkedin_ad",
        [],
        [
            "id"
        ]
    ],
    "get_linkedin_company": [
        "GET",
        "/linkedin_company",
        [],
        [
            "slug"
        ]
    ],
    "get_linkedin_company_job_count": [
        "GET",
        "/linkedin_company_job_count",
        [],
        [
            "slug"
        ]
    ],
    "get_linkedin_company_member_insights": [
        "GET",
        "/linkedin_company_member_insights",
        [],
        [
            "slug"
        ]
    ],
    "get_linkedin_group": [
        "GET",
        "/linkedin_group",
        [],
        [
            "id"
        ]
    ],
    "get_linkedin_job": [
        "GET",
        "/linkedin_job",
        [],
        [
            "id",
            "include_skills"
        ]
    ],
    "get_linkedin_post": [
        "POST",
        "/linkedin_post",
        [],
        [
            "id"
        ]
    ],
    "get_linkedin_user": [
        "GET",
        "/linkedin_user",
        [],
        [
            "username"
        ]
    ],
    "get_linkedin_user_about": [
        "GET",
        "/linkedin_user_about",
        [],
        [
            "username"
        ]
    ],
    "get_linkedin_user_contact": [
        "GET",
        "/linkedin_user_contact",
        [],
        [
            "username"
        ]
    ],
    "get_linkedin_user_follower_count": [
        "GET",
        "/linkedin_user_follower_count",
        [],
        [
            "username"
        ]
    ],
    "get_reddit_post": [
        "POST",
        "/reddit_post",
        [],
        [
            "id"
        ]
    ],
    "get_reddit_subreddit": [
        "GET",
        "/reddit_subreddit",
        [],
        [
            "name"
        ]
    ],
    "get_reddit_user": [
        "GET",
        "/reddit_user",
        [],
        [
            "username"
        ]
    ],
    "get_seo_backlink_history": [
        "GET",
        "/seo_backlink_history",
        [],
        [
            "target",
            "date_from",
            "date_to",
            "rank_scale",
            "view"
        ]
    ],
    "get_seo_backlink_summary": [
        "GET",
        "/seo_backlink_summary",
        [],
        [
            "target",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "view"
        ]
    ],
    "get_seo_backlink_timeseries": [
        "GET",
        "/seo_backlink_timeseries",
        [],
        [
            "target",
            "date_from",
            "date_to",
            "group_range",
            "include_subdomains",
            "rank_scale"
        ]
    ],
    "get_seo_bulk_backlink_ranks": [
        "GET",
        "/seo_bulk_backlink_ranks",
        [],
        [
            "targets",
            "rank_scale"
        ]
    ],
    "get_seo_bulk_spam_scores": [
        "GET",
        "/seo_bulk_spam_scores",
        [],
        [
            "targets"
        ]
    ],
    "get_seo_domain_rank_overview": [
        "GET",
        "/seo_domain_rank_overview",
        [],
        [
            "target",
            "location",
            "language",
            "view"
        ]
    ],
    "get_seo_historical_rank_overview": [
        "GET",
        "/seo_historical_rank_overview",
        [],
        [
            "target",
            "location",
            "language",
            "date_from",
            "date_to",
            "view"
        ]
    ],
    "get_seo_historical_serps": [
        "GET",
        "/seo_historical_serps",
        [],
        [
            "keyword",
            "location",
            "language",
            "date_from",
            "date_to"
        ]
    ],
    "get_seo_keyword_history": [
        "GET",
        "/seo_keyword_history",
        [],
        [
            "keywords",
            "location",
            "language"
        ]
    ],
    "get_seo_keyword_overview": [
        "GET",
        "/seo_keyword_overview",
        [],
        [
            "keywords",
            "location",
            "language",
            "include_serp_info",
            "view"
        ]
    ],
    "get_seo_new_lost_backlinks_timeseries": [
        "GET",
        "/seo_new_lost_backlinks_timeseries",
        [],
        [
            "target",
            "date_from",
            "date_to",
            "group_range",
            "include_subdomains"
        ]
    ],
    "get_threads_user": [
        "GET",
        "/threads_user",
        [],
        [
            "username"
        ]
    ],
    "get_tiktok_hashtag": [
        "GET",
        "/tiktok_hashtag",
        [],
        [
            "id"
        ]
    ],
    "get_tiktok_music": [
        "GET",
        "/tiktok_music",
        [],
        [
            "id"
        ]
    ],
    "get_tiktok_recommended_feed": [
        "GET",
        "/tiktok_recommended_feed",
        [],
        [
            "cookie",
            "region",
            "limit"
        ]
    ],
    "get_tiktok_user": [
        "GET",
        "/tiktok_user",
        [],
        [
            "id"
        ]
    ],
    "get_tiktok_video": [
        "GET",
        "/tiktok_video",
        [],
        [
            "id"
        ]
    ],
    "get_x_autocomplete": [
        "GET",
        "/x_autocomplete",
        [],
        [
            "query"
        ]
    ],
    "get_x_community": [
        "GET",
        "/x_community",
        [],
        [
            "id",
            "community.fields"
        ]
    ],
    "get_x_community_about": [
        "GET",
        "/x_community_about",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "get_x_trends_by_woeid": [
        "GET",
        "/x_trends_by_woeid",
        [],
        [
            "woeid",
            "max_trends",
            "trend.fields"
        ]
    ],
    "get_x_tweet": [
        "GET",
        "/x_tweet",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields"
        ]
    ],
    "get_x_tweet_article": [
        "GET",
        "/x_tweet_article",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields"
        ]
    ],
    "get_x_tweets": [
        "GET",
        "/x_tweets",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "ids"
        ]
    ],
    "get_x_user": [
        "GET",
        "/x_user",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields"
        ]
    ],
    "get_x_user_by_username": [
        "GET",
        "/x_user_by_username",
        [],
        [
            "username",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields"
        ]
    ],
    "get_x_users": [
        "GET",
        "/x_users",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "ids"
        ]
    ],
    "get_x_users_by_usernames": [
        "GET",
        "/x_users_by_usernames",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "usernames"
        ]
    ],
    "get_youtube_channel": [
        "GET",
        "/youtube_channel",
        [],
        [
            "channel_id"
        ]
    ],
    "get_youtube_playlist": [
        "GET",
        "/youtube_playlist",
        [],
        [
            "playlist_id"
        ]
    ],
    "get_youtube_video": [
        "GET",
        "/youtube_video",
        [],
        [
            "video_id"
        ]
    ],
    "get_youtube_video_transcript": [
        "GET",
        "/youtube_video_transcript",
        [],
        [
            "video_id",
            "lang"
        ]
    ],
    "list_geo_top_mentioned_domains": [
        "GET",
        "/geo_top_mentioned_domains",
        [],
        [
            "target",
            "engine",
            "location",
            "language",
            "links_scope",
            "filters",
            "items_list_limit",
            "internal_list_limit"
        ]
    ],
    "list_geo_top_mentioned_pages": [
        "GET",
        "/geo_top_mentioned_pages",
        [],
        [
            "target",
            "engine",
            "location",
            "language",
            "links_scope",
            "filters",
            "items_list_limit",
            "internal_list_limit"
        ]
    ],
    "list_hacker_news_story_ids": [
        "GET",
        "/hacker_news_story_ids",
        [],
        [
            "feed",
            "cursor",
            "limit"
        ]
    ],
    "list_hacker_news_story_items": [
        "GET",
        "/hacker_news_story_items",
        [],
        [
            "feed",
            "cursor",
            "limit"
        ]
    ],
    "list_instagram_location_posts": [
        "POST",
        "/instagram_location_posts",
        [],
        [
            "id",
            "cursor",
            "tab"
        ]
    ],
    "list_instagram_nearby_locations": [
        "GET",
        "/instagram_nearby_locations",
        [],
        [
            "id"
        ]
    ],
    "list_instagram_post_comment_replies": [
        "POST",
        "/instagram_post_comment_replies",
        [],
        [
            "shortcode",
            "commentId",
            "cursor"
        ]
    ],
    "list_instagram_post_comments": [
        "POST",
        "/instagram_post_comments",
        [],
        [
            "shortcode",
            "cursor",
            "sort"
        ]
    ],
    "list_instagram_user_followers": [
        "GET",
        "/instagram_user_followers",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_instagram_user_following": [
        "GET",
        "/instagram_user_following",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_instagram_user_former_usernames": [
        "GET",
        "/instagram_user_former_usernames",
        [],
        [
            "username"
        ]
    ],
    "list_instagram_user_highlights": [
        "GET",
        "/instagram_user_highlights",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_instagram_user_posts": [
        "POST",
        "/instagram_user_posts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_instagram_user_reels": [
        "GET",
        "/instagram_user_reels",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_instagram_user_stories": [
        "GET",
        "/instagram_user_stories",
        [],
        [
            "username"
        ]
    ],
    "list_instagram_user_tagged_posts": [
        "POST",
        "/instagram_user_tagged_posts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_company_affiliated": [
        "GET",
        "/linkedin_company_affiliated",
        [],
        [
            "slug"
        ]
    ],
    "list_linkedin_company_jobs": [
        "GET",
        "/linkedin_company_jobs",
        [],
        [
            "slug",
            "cursor"
        ]
    ],
    "list_linkedin_company_people": [
        "GET",
        "/linkedin_company_people",
        [],
        [
            "slug",
            "cursor"
        ]
    ],
    "list_linkedin_company_posts": [
        "POST",
        "/linkedin_company_posts",
        [],
        [
            "slug",
            "cursor"
        ]
    ],
    "list_linkedin_group_posts": [
        "POST",
        "/linkedin_group_posts",
        [],
        [
            "id",
            "cursor"
        ]
    ],
    "list_linkedin_post_comment_replies": [
        "POST",
        "/linkedin_post_comment_replies",
        [],
        [
            "id",
            "comment_id",
            "cursor"
        ]
    ],
    "list_linkedin_post_comments": [
        "POST",
        "/linkedin_post_comments",
        [],
        [
            "id",
            "cursor"
        ]
    ],
    "list_linkedin_post_reactions": [
        "POST",
        "/linkedin_post_reactions",
        [],
        [
            "id",
            "cursor",
            "type"
        ]
    ],
    "list_linkedin_post_reposts": [
        "POST",
        "/linkedin_post_reposts",
        [],
        [
            "id",
            "cursor"
        ]
    ],
    "list_linkedin_user_certifications": [
        "GET",
        "/linkedin_user_certifications",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_comments": [
        "GET",
        "/linkedin_user_comments",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_educations": [
        "GET",
        "/linkedin_user_educations",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_experience": [
        "GET",
        "/linkedin_user_experience",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_honors": [
        "GET",
        "/linkedin_user_honors",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_images": [
        "GET",
        "/linkedin_user_images",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_interest_companies": [
        "GET",
        "/linkedin_user_interest_companies",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_interest_groups": [
        "GET",
        "/linkedin_user_interest_groups",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_posts": [
        "POST",
        "/linkedin_user_posts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_publications": [
        "GET",
        "/linkedin_user_publications",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_reactions": [
        "GET",
        "/linkedin_user_reactions",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_recommendations": [
        "GET",
        "/linkedin_user_recommendations",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_skills": [
        "GET",
        "/linkedin_user_skills",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_videos": [
        "GET",
        "/linkedin_user_videos",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_linkedin_user_volunteers": [
        "GET",
        "/linkedin_user_volunteers",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_reddit_post_comments": [
        "POST",
        "/reddit_post_comments",
        [],
        [
            "id",
            "cursor"
        ]
    ],
    "list_reddit_trending_searches": [
        "GET",
        "/reddit_trending_searches",
        [],
        []
    ],
    "list_reddit_user_comments": [
        "GET",
        "/reddit_user_comments",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_reddit_user_posts": [
        "POST",
        "/reddit_user_posts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_seo_backlink_anchors": [
        "GET",
        "/seo_backlink_anchors",
        [],
        [
            "target",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "backlinks_filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_seo_backlink_domain_pages": [
        "GET",
        "/seo_backlink_domain_pages",
        [],
        [
            "target",
            "backlinks_status_type",
            "include_subdomains",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "backlinks_filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_seo_backlinks": [
        "GET",
        "/seo_backlinks",
        [],
        [
            "target",
            "mode",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "rank_scale",
            "filters",
            "order_by",
            "limit",
            "offset",
            "search_after_token",
            "view"
        ]
    ],
    "list_seo_referring_domains": [
        "GET",
        "/seo_referring_domains",
        [],
        [
            "target",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_seo_referring_networks": [
        "GET",
        "/seo_referring_networks",
        [],
        [
            "target",
            "network_address_type",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "backlinks_filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_seo_relevant_pages": [
        "GET",
        "/seo_relevant_pages",
        [],
        [
            "target",
            "location",
            "language",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_seo_subdomains": [
        "GET",
        "/seo_subdomains",
        [],
        [
            "target",
            "location",
            "language",
            "limit",
            "offset",
            "view"
        ]
    ],
    "list_threads_user_posts": [
        "POST",
        "/threads_user_posts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_threads_user_replies": [
        "GET",
        "/threads_user_replies",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_threads_user_reposts": [
        "POST",
        "/threads_user_reposts",
        [],
        [
            "username",
            "cursor"
        ]
    ],
    "list_tiktok_hashtag_videos": [
        "GET",
        "/tiktok_hashtag_videos",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_music_videos": [
        "GET",
        "/tiktok_music_videos",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_user_followers": [
        "GET",
        "/tiktok_user_followers",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_user_following": [
        "GET",
        "/tiktok_user_following",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_user_likes": [
        "GET",
        "/tiktok_user_likes",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_user_videos": [
        "GET",
        "/tiktok_user_videos",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_video_comment_replies": [
        "GET",
        "/tiktok_video_comment_replies",
        [],
        [
            "id",
            "comment_id",
            "cursor",
            "limit"
        ]
    ],
    "list_tiktok_video_comments": [
        "GET",
        "/tiktok_video_comments",
        [],
        [
            "id",
            "cursor",
            "limit"
        ]
    ],
    "list_x_community_media": [
        "GET",
        "/x_community_media",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_community_members": [
        "GET",
        "/x_community_members",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_community_moderators": [
        "GET",
        "/x_community_moderators",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_community_tweets": [
        "GET",
        "/x_community_tweets",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_list_followers": [
        "GET",
        "/x_list_followers",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_list_members": [
        "GET",
        "/x_list_members",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_list_tweets": [
        "GET",
        "/x_list_tweets",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_tweet_liking_users": [
        "GET",
        "/x_tweet_liking_users",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_tweet_quotes": [
        "GET",
        "/x_tweet_quotes",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_tweet_repost_users": [
        "POST",
        "/x_tweet_repost_users",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_follower_ids": [
        "GET",
        "/x_user_follower_ids",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_followers": [
        "GET",
        "/x_user_followers",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_following": [
        "GET",
        "/x_user_following",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_following_ids": [
        "GET",
        "/x_user_following_ids",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_liked_tweets": [
        "GET",
        "/x_user_liked_tweets",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_x_user_tweets": [
        "GET",
        "/x_user_tweets",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results",
            "exclude"
        ]
    ],
    "list_x_user_verified_followers": [
        "GET",
        "/x_user_verified_followers",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results"
        ]
    ],
    "list_youtube_channel_community_posts": [
        "POST",
        "/youtube_channel_community_posts",
        [],
        [
            "channel_id",
            "cursor"
        ]
    ],
    "list_youtube_channel_playlists": [
        "GET",
        "/youtube_channel_playlists",
        [],
        [
            "channel_id",
            "cursor"
        ]
    ],
    "list_youtube_channel_shorts": [
        "GET",
        "/youtube_channel_shorts",
        [],
        [
            "channel_id",
            "cursor"
        ]
    ],
    "list_youtube_channel_videos": [
        "GET",
        "/youtube_channel_videos",
        [],
        [
            "channel_id",
            "cursor"
        ]
    ],
    "list_youtube_hashtag_videos": [
        "GET",
        "/youtube_hashtag_videos",
        [],
        [
            "tag",
            "cursor"
        ]
    ],
    "list_youtube_playlist_videos": [
        "GET",
        "/youtube_playlist_videos",
        [],
        [
            "playlist_id",
            "cursor"
        ]
    ],
    "list_youtube_related_videos": [
        "GET",
        "/youtube_related_videos",
        [],
        [
            "video_id",
            "cursor"
        ]
    ],
    "list_youtube_video_captions": [
        "GET",
        "/youtube_video_captions",
        [],
        [
            "video_id"
        ]
    ],
    "list_youtube_video_comments": [
        "GET",
        "/youtube_video_comments",
        [],
        [
            "video_id",
            "cursor",
            "sort_by"
        ]
    ],
    "render_html": [
        "GET",
        "/render_html",
        [],
        [
            "url",
            "wait_until",
            "timeout_ms"
        ]
    ],
    "render_markdown": [
        "GET",
        "/render_markdown",
        [],
        [
            "url",
            "wait_until",
            "timeout_ms"
        ]
    ],
    "resolve_linkedin_industries": [
        "GET",
        "/resolve_linkedin_industries",
        [],
        [
            "keyword"
        ]
    ],
    "resolve_linkedin_locations": [
        "GET",
        "/resolve_linkedin_locations",
        [],
        [
            "keyword"
        ]
    ],
    "resolve_tiktok_user": [
        "GET",
        "/resolve_tiktok_user",
        [],
        [
            "username"
        ]
    ],
    "resolve_tiktok_video": [
        "GET",
        "/resolve_tiktok_video",
        [],
        [
            "url"
        ]
    ],
    "resolve_youtube_channel_id": [
        "GET",
        "/resolve_youtube_channel_id",
        [],
        [
            "url"
        ]
    ],
    "score_seo_keyword_difficulty": [
        "GET",
        "/score_seo_keyword_difficulty",
        [],
        [
            "keywords",
            "location",
            "language"
        ]
    ],
    "search_events": [
        "GET",
        "/search_events",
        [],
        [
            "query",
            "location",
            "language",
            "limit",
            "view",
            "os",
            "date_range"
        ]
    ],
    "search_geo_ai_mode": [
        "GET",
        "/search_geo_ai_mode",
        [],
        [
            "query",
            "target",
            "location",
            "language",
            "device",
            "include_pixel_rankings",
            "view"
        ]
    ],
    "search_geo_mentions": [
        "GET",
        "/search_geo_mentions",
        [],
        [
            "target",
            "engine",
            "location",
            "language",
            "filters",
            "order_by",
            "limit",
            "offset",
            "cursor",
            "view"
        ]
    ],
    "search_hotels": [
        "GET",
        "/search_hotels",
        [],
        [
            "query",
            "location",
            "language",
            "limit",
            "check_in",
            "check_out",
            "currency",
            "adults",
            "children",
            "stars",
            "min_rating",
            "sort_by",
            "min_price",
            "max_price",
            "free_cancellation",
            "is_vacation_rentals",
            "amenities"
        ]
    ],
    "search_instagram": [
        "GET",
        "/search_instagram",
        [],
        [
            "cursor",
            "q"
        ]
    ],
    "search_linkedin_ads": [
        "GET",
        "/search_linkedin_ads",
        [],
        [
            "cursor",
            "keyword",
            "advertiser_name",
            "country",
            "date"
        ]
    ],
    "search_linkedin_jobs": [
        "GET",
        "/search_linkedin_jobs",
        [],
        [
            "cursor",
            "keyword",
            "sort_by",
            "date_posted",
            "geocode",
            "company",
            "experience_level",
            "remote",
            "job_type",
            "easy_apply",
            "has_verifications",
            "under_10_applicants",
            "fair_chance_employer"
        ]
    ],
    "search_linkedin_people": [
        "GET",
        "/search_linkedin_people",
        [],
        [
            "cursor",
            "name",
            "first_name",
            "last_name",
            "title",
            "company",
            "school",
            "geocode_location",
            "current_company",
            "profile_language",
            "industry",
            "service_category"
        ]
    ],
    "search_linkedin_posts": [
        "POST",
        "/search_linkedin_posts",
        [],
        [
            "cursor",
            "keyword",
            "date_posted",
            "sort_by",
            "from_member",
            "from_company",
            "content_type"
        ]
    ],
    "search_linkedin_schools": [
        "GET",
        "/search_linkedin_schools",
        [],
        [
            "cursor",
            "keyword"
        ]
    ],
    "search_local": [
        "GET",
        "/search_local",
        [],
        [
            "query",
            "location",
            "language",
            "limit",
            "view",
            "device",
            "os",
            "min_rating",
            "time_filter"
        ]
    ],
    "search_maps": [
        "GET",
        "/search_maps",
        [],
        [
            "query",
            "location",
            "language",
            "limit",
            "view",
            "device",
            "os",
            "search_this_area",
            "search_places"
        ]
    ],
    "search_news": [
        "GET",
        "/search_news",
        [],
        [
            "query",
            "location",
            "language",
            "limit",
            "view",
            "os"
        ]
    ],
    "search_threads_profiles": [
        "GET",
        "/search_threads_profiles",
        [],
        [
            "q"
        ]
    ],
    "search_threads_recent": [
        "GET",
        "/search_threads_recent",
        [],
        [
            "cursor",
            "q"
        ]
    ],
    "search_threads_top": [
        "GET",
        "/search_threads_top",
        [],
        [
            "cursor",
            "q"
        ]
    ],
    "search_tiktok": [
        "GET",
        "/search_tiktok",
        [],
        [
            "cursor",
            "limit",
            "q"
        ]
    ],
    "search_tiktok_hashtags": [
        "GET",
        "/search_tiktok_hashtags",
        [],
        [
            "cursor",
            "limit",
            "q"
        ]
    ],
    "search_tiktok_users": [
        "GET",
        "/search_tiktok_users",
        [],
        [
            "cursor",
            "limit",
            "q"
        ]
    ],
    "search_tiktok_videos": [
        "GET",
        "/search_tiktok_videos",
        [],
        [
            "cursor",
            "limit",
            "q"
        ]
    ],
    "search_x_communities": [
        "GET",
        "/search_x_communities",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results",
            "query",
            "community.fields"
        ]
    ],
    "search_x_community_member": [
        "GET",
        "/search_x_community_member",
        [],
        [
            "id",
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results",
            "query"
        ]
    ],
    "search_x_lists": [
        "GET",
        "/search_x_lists",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results",
            "query"
        ]
    ],
    "search_x_recent_tweets": [
        "GET",
        "/search_x_recent_tweets",
        [],
        [
            "expansions",
            "tweet.fields",
            "user.fields",
            "media.fields",
            "place.fields",
            "poll.fields",
            "pagination_token",
            "next_token",
            "max_results",
            "query"
        ]
    ],
    "search_youtube_channel": [
        "GET",
        "/search_youtube_channel",
        [],
        [
            "channel_id",
            "cursor",
            "q"
        ]
    ],
    "search_youtube_channels": [
        "GET",
        "/search_youtube_channels",
        [],
        [
            "cursor",
            "q"
        ]
    ],
    "search_youtube_playlists": [
        "GET",
        "/search_youtube_playlists",
        [],
        [
            "cursor",
            "q"
        ]
    ],
    "search_youtube_videos": [
        "GET",
        "/search_youtube_videos",
        [],
        [
            "cursor",
            "q",
            "sort_by",
            "upload_date",
            "duration",
            "region",
            "language"
        ]
    ],
    "summarize_seo_backlink_domain_pages": [
        "GET",
        "/summarize_seo_backlink_domain_pages",
        [],
        [
            "target",
            "backlinks_status_type",
            "include_subdomains",
            "include_indirect_links",
            "exclude_internal_backlinks",
            "internal_list_limit",
            "rank_scale",
            "filters",
            "backlinks_filters",
            "order_by",
            "limit",
            "offset",
            "view"
        ]
    ],
    "summarize_seo_bulk_pages": [
        "GET",
        "/summarize_seo_bulk_pages",
        [],
        [
            "targets",
            "include_subdomains",
            "rank_scale",
            "view"
        ]
    ],
    "translate_x_tweet": [
        "GET",
        "/translate_x_tweet",
        [],
        [
            "id",
            "language"
        ]
    ],
    "translate_x_user_profile": [
        "GET",
        "/translate_x_user_profile",
        [],
        [
            "id",
            "language"
        ]
    ]
}

class UnifapiDynamicAction(Action):
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
            raise ValueError(f"UnifAPI API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class UnifapiProvider(Provider):
    def __init__(self):
        super().__init__(
            service="unifapi",
            display_name="UnifAPI",
            category="AI & Machine Learning",
            auth_types=["api_key"],
            description="UnifAPI unified web intelligence, search, and social media data with 220 actions."
        )
        for act in get_provider_actions("unifapi"):
            self.register_action(UnifapiDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.unifapi.com/hacker-news/max-item"
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
            raise ValueError(f"UnifAPI connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid UnifAPI credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"UnifAPI validation failed: {resp.status_code} {resp.text}")

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
            "display_name": f"UnifAPI Account"
        }

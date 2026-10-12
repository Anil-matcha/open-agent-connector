"""
TwitterAPI.io Provider for ConnectorHub.
Loads and registers 39 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.twitterapi.io"

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

    auth_mode = "x_api_key"
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
    "add_monitored_tweet_user": [
        "POST",
        "/oapi/x_user_stream/add_user_to_monitor_tweet",
        [],
        [
            "xUserName"
        ]
    ],
    "add_tweet_filter_rule": [
        "POST",
        "/oapi/tweet_filter/add_rule",
        [],
        [
            "tag",
            "value",
            "intervalSeconds"
        ]
    ],
    "advanced_search_tweets": [
        "GET",
        "/twitter/tweet/advanced_search",
        [],
        [
            "query",
            "queryType",
            "cursor"
        ]
    ],
    "batch_get_users": [
        "GET",
        "/twitter/user/batch_info_by_ids",
        [],
        [
            "userIds"
        ]
    ],
    "check_follow_relationship": [
        "GET",
        "/twitter/user/check_follow_relationship",
        [],
        [
            "sourceUserName",
            "targetUserName"
        ]
    ],
    "delete_tweet_filter_rule": [
        "DELETE",
        "/oapi/tweet_filter/delete_rule",
        [],
        [
            "ruleId"
        ]
    ],
    "get_account_info": [
        "GET",
        "/oapi/my/info",
        [],
        []
    ],
    "get_article": [
        "GET",
        "/twitter/article",
        [],
        [
            "tweetId"
        ]
    ],
    "get_community_info": [
        "POST",
        "/twitter/community/info",
        [],
        [
            "communityId"
        ]
    ],
    "get_community_members": [
        "POST",
        "/twitter/community/members",
        [],
        [
            "communityId",
            "cursor"
        ]
    ],
    "get_community_moderators": [
        "POST",
        "/twitter/community/moderators",
        [],
        [
            "communityId",
            "cursor"
        ]
    ],
    "get_community_tweets": [
        "POST",
        "/twitter/community/tweets",
        [],
        [
            "communityId",
            "cursor"
        ]
    ],
    "get_list_followers": [
        "GET",
        "/twitter/list/followers",
        [],
        [
            "listId",
            "cursor"
        ]
    ],
    "get_list_members": [
        "GET",
        "/twitter/list/members",
        [],
        [
            "listId",
            "cursor"
        ]
    ],
    "get_list_timeline": [
        "GET",
        "/twitter/list/tweets_timeline",
        [],
        [
            "listId",
            "cursor"
        ]
    ],
    "get_list_tweets": [
        "GET",
        "/twitter/list/tweets",
        [],
        [
            "listId",
            "sinceTime",
            "untilTime",
            "includeReplies",
            "cursor"
        ]
    ],
    "get_space": [
        "POST",
        "/twitter/spaces/detail",
        [],
        [
            "spaceId"
        ]
    ],
    "get_trends": [
        "POST",
        "/twitter/trends",
        [],
        [
            "woeid",
            "count"
        ]
    ],
    "get_tweet_quotes": [
        "GET",
        "/twitter/tweet/quotes",
        [],
        [
            "tweetId",
            "sinceTime",
            "untilTime",
            "includeReplies",
            "cursor"
        ]
    ],
    "get_tweet_replies": [
        "GET",
        "/twitter/tweet/replies/v2",
        [],
        [
            "tweetId",
            "cursor",
            "queryType"
        ]
    ],
    "get_tweet_replies_legacy": [
        "GET",
        "/twitter/tweet/replies",
        [],
        [
            "tweetId",
            "sinceTime",
            "untilTime",
            "cursor"
        ]
    ],
    "get_tweet_retweeters": [
        "GET",
        "/twitter/tweet/retweeters",
        [],
        [
            "tweetId",
            "cursor"
        ]
    ],
    "get_tweet_thread_context": [
        "GET",
        "/twitter/tweet/thread_context",
        [],
        [
            "tweetId",
            "cursor"
        ]
    ],
    "get_tweets": [
        "GET",
        "/twitter/tweets",
        [],
        [
            "tweetIds"
        ]
    ],
    "get_user": [
        "GET",
        "/twitter/user/info",
        [],
        [
            "userName"
        ]
    ],
    "get_user_about": [
        "GET",
        "/twitter/user_about",
        [],
        [
            "userName"
        ]
    ],
    "get_user_follower_ids": [
        "GET",
        "/twitter/user/followers_ids",
        [],
        [
            "userName",
            "userId",
            "count",
            "cursor"
        ]
    ],
    "get_user_followers": [
        "GET",
        "/twitter/user/followers",
        [],
        [
            "userName",
            "cursor",
            "pageSize"
        ]
    ],
    "get_user_followings": [
        "GET",
        "/twitter/user/followings",
        [],
        [
            "userName",
            "cursor",
            "pageSize"
        ]
    ],
    "get_user_last_tweets": [
        "GET",
        "/twitter/user/last_tweets",
        [],
        [
            "userId",
            "userName",
            "cursor",
            "includeReplies"
        ]
    ],
    "get_user_mentions": [
        "GET",
        "/twitter/user/mentions",
        [],
        [
            "userName",
            "sinceTime",
            "untilTime",
            "cursor"
        ]
    ],
    "get_user_timeline": [
        "GET",
        "/twitter/user/tweet_timeline",
        [],
        [
            "userId",
            "cursor",
            "includeReplies",
            "includeParentTweet"
        ]
    ],
    "get_user_verified_followers": [
        "GET",
        "/twitter/user/verifiedFollowers",
        [],
        [
            "userId",
            "cursor"
        ]
    ],
    "list_monitored_tweet_users": [
        "POST",
        "/oapi/x_user_stream/get_user_to_monitor_tweet",
        [],
        []
    ],
    "list_tweet_filter_rules": [
        "POST",
        "/oapi/tweet_filter/get_rules",
        [],
        []
    ],
    "remove_monitored_tweet_user": [
        "POST",
        "/oapi/x_user_stream/remove_user_to_monitor_tweet",
        [],
        [
            "idForUser"
        ]
    ],
    "search_all_community_tweets": [
        "POST",
        "/twitter/community/get_tweets_from_all_community",
        [],
        [
            "query",
            "queryType",
            "cursor"
        ]
    ],
    "search_users": [
        "GET",
        "/twitter/user/search",
        [],
        [
            "query",
            "cursor"
        ]
    ],
    "update_tweet_filter_rule": [
        "POST",
        "/oapi/tweet_filter/update_rule",
        [],
        [
            "ruleId",
            "tag",
            "value",
            "intervalSeconds",
            "isEffect"
        ]
    ]
}

class TwitterapiIoDynamicAction(Action):
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
        if "x_api_key" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "x_api_key" == "pushover_token" and token:
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
            raise ValueError(f"TwitterAPI.io API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class TwitterapiIoProvider(Provider):
    def __init__(self):
        super().__init__(
            service="twitterapi_io",
            display_name="TwitterAPI.io",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="TwitterAPI.io real-time Twitter/X data API with 39 actions for tweets, user intelligence, and community monitoring."
        )
        for act in get_provider_actions("twitterapi_io"):
            self.register_action(TwitterapiIoDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.twitterapi.io/twitter/user/info"
        for key in ["site", "domain", "subdomain", "host", "tenant", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "invalid-target"))

        token = _extract_token(cred)
        if "{token}" in val_url:
            val_url = val_url.replace("{token}", token or "invalid-token")

        assert_public_url(val_url)
        headers = _build_headers(cred)

        req_params = {}
        if "x_api_key" == "bing_webmaster" and token:
            req_params["apikey"] = token
        elif "x_api_key" == "pushover_token" and token:
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
            raise ValueError(f"TwitterAPI.io connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid TwitterAPI.io credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"TwitterAPI.io validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "twitterapi_io" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid TwitterAPI.io credentials: {body.get('msg') or resp.text}")
                elif "twitterapi_io" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid TwitterAPI.io credentials: {body.get('errmsg') or resp.text}")
                elif "twitterapi_io" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid TwitterAPI.io credentials: {body.get('error_msg') or resp.text}")
                elif "twitterapi_io" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid TwitterAPI.io credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"TwitterAPI.io Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"TwitterAPI.io Account"
        }

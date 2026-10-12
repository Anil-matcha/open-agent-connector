"""
App Store Server API Provider for ConnectorHub.
Loads and registers 30 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.storekit.apple.com"

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
    "configure_default_retention_message": [
        "PUT",
        "/configure_default_retention_message",
        [],
        [
            "productId",
            "locale",
            "messageIdentifier"
        ]
    ],
    "configure_retention_realtime_url": [
        "PUT",
        "{messagingRoot}/realtime/url",
        [
            "messagingRoot"
        ],
        [
            "realtimeUrl"
        ]
    ],
    "delete_default_retention_message": [
        "DELETE",
        "{messagingRoot}/realtime/url",
        [
            "messagingRoot"
        ],
        [
            "productId",
            "locale"
        ]
    ],
    "delete_retention_image": [
        "DELETE",
        "/retention_image",
        [],
        [
            "imageIdentifier"
        ]
    ],
    "delete_retention_message": [
        "DELETE",
        "/retention_message",
        [],
        [
            "messageIdentifier"
        ]
    ],
    "delete_retention_realtime_url": [
        "DELETE",
        "{messagingRoot}/realtime/url",
        [
            "messagingRoot"
        ],
        []
    ],
    "extend_renewal_date_for_all_active_subscribers": [
        "POST",
        "/inApps/v1/subscriptions/extend/mass",
        [],
        [
            "productId",
            "extendByDays",
            "extendReasonCode",
            "requestIdentifier",
            "storefrontCountryCodes"
        ]
    ],
    "extend_subscription_renewal_date": [
        "PUT",
        "/inApps/v1/subscriptions/extend/mass",
        [],
        [
            "originalTransactionId",
            "extendByDays",
            "extendReasonCode",
            "requestIdentifier"
        ]
    ],
    "finish_transaction": [
        "POST",
        "/inApps/v1/transactions",
        [],
        [
            "transactionId"
        ]
    ],
    "get_all_subscription_statuses": [
        "PUT",
        "/inApps/v1/subscriptions",
        [],
        [
            "transactionId",
            "statuses"
        ]
    ],
    "get_app_transaction_info": [
        "PUT",
        "/inApps/v1/transactions/appTransactions",
        [],
        [
            "transactionId"
        ]
    ],
    "get_default_retention_message": [
        "DELETE",
        "{messagingRoot}/realtime/url",
        [
            "messagingRoot"
        ],
        [
            "productId",
            "locale"
        ]
    ],
    "get_notification_history": [
        "POST",
        "/inApps/v1/notifications/history",
        [],
        [
            "startDate",
            "endDate",
            "notificationType",
            "notificationSubtype",
            "transactionId",
            "onlyFailures",
            "paginationToken"
        ]
    ],
    "get_refund_history": [
        "PUT",
        "/inApps/v2/refund/lookup",
        [],
        [
            "transactionId",
            "revision"
        ]
    ],
    "get_retention_image_list": [
        "DELETE",
        "{messagingRoot}/image/list",
        [
            "messagingRoot"
        ],
        []
    ],
    "get_retention_message_list": [
        "DELETE",
        "{messagingRoot}/message/list",
        [
            "messagingRoot"
        ],
        []
    ],
    "get_retention_performance_test_results": [
        "GET",
        "/retention_performance_test_results",
        [],
        [
            "requestId"
        ]
    ],
    "get_retention_realtime_url": [
        "DELETE",
        "{messagingRoot}/realtime/url",
        [
            "messagingRoot"
        ],
        []
    ],
    "get_subscription_renewal_date_extension_status": [
        "GET",
        "/inApps/v1/subscriptions/extend/mass",
        [],
        [
            "productId",
            "requestIdentifier"
        ]
    ],
    "get_test_notification_status": [
        "POST",
        "/inApps/v1/notifications/history",
        [],
        [
            "testNotificationToken"
        ]
    ],
    "get_transaction_history": [
        "GET",
        "/inApps/v2/history",
        [],
        [
            "transactionId",
            "revision",
            "startDate",
            "endDate",
            "productIds",
            "productTypes",
            "subscriptionGroupIdentifiers",
            "inAppOwnershipType",
            "revoked",
            "sort"
        ]
    ],
    "get_transaction_info": [
        "GET",
        "/inApps/v1/transactions",
        [],
        [
            "transactionId"
        ]
    ],
    "initiate_retention_performance_test": [
        "POST",
        "{messagingRoot}/performanceTest",
        [
            "messagingRoot"
        ],
        [
            "originalTransactionId"
        ]
    ],
    "look_up_order_id": [
        "PUT",
        "/inApps/v1/lookup",
        [],
        [
            "orderId"
        ]
    ],
    "request_test_notification": [
        "POST",
        "/inApps/v1/notifications/test",
        [],
        []
    ],
    "send_consumption_information": [
        "PUT",
        "/inApps/v2/transactions/consumption",
        [],
        [
            "transactionId",
            "customerConsented",
            "deliveryStatus",
            "sampleContentProvided",
            "consumptionPercentage",
            "refundPreference"
        ]
    ],
    "send_consumption_information_v1": [
        "PUT",
        "/inApps/v1/transactions/consumption",
        [],
        [
            "transactionId",
            "customerConsented",
            "sampleContentProvided",
            "appAccountToken",
            "accountTenure",
            "consumptionStatus",
            "deliveryStatus",
            "lifetimeDollarsPurchased",
            "lifetimeDollarsRefunded",
            "platform",
            "playTime",
            "userStatus",
            "refundPreference"
        ]
    ],
    "set_app_account_token": [
        "PUT",
        "/inApps/v1/transactions",
        [],
        [
            "originalTransactionId",
            "appAccountToken"
        ]
    ],
    "upload_retention_image": [
        "PUT",
        "{messagingRoot}/image/list",
        [
            "messagingRoot"
        ],
        [
            "imageIdentifier",
            "imageSize",
            "file"
        ]
    ],
    "upload_retention_message": [
        "PUT",
        "/upload_retention_message",
        [],
        [
            "messageIdentifier",
            "header",
            "body",
            "image",
            "bulletPoints",
            "headerPosition"
        ]
    ]
}

class AppStoreServerDynamicAction(Action):
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
            raise ValueError(f"App Store Server API API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class AppStoreServerProvider(Provider):
    def __init__(self):
        super().__init__(
            service="app_store_server",
            display_name="App Store Server API",
            category="Developer Tools",
            auth_types=["custom_credential"],
            description="Apple App Store Server API for in-app purchases, transaction history, and subscription status with 30 actions."
        )
        for act in get_provider_actions("app_store_server"):
            self.register_action(AppStoreServerDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.storekit.apple.com/inApps/v1/transactions/0"
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
            raise ValueError(f"App Store Server API connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid App Store Server API credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"App Store Server API validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"App Store Server API Account"
        }

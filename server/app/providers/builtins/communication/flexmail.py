"""
Flexmail Provider for ConnectorHub.
Loads and registers 24 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.flexmail.eu"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serviceToken", "personalAccessToken", "tokenKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE

    if "flexmail" in ["shopify_admin", "shopify_storefront"]:
        shop = str(cred.get("shopDomain") or cred.get("shop") or "default.myshopify.com").strip()
        shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
        return base.replace("{shopDomain}", shop).rstrip("/")

    if "flexmail" == "shopify_partner":
        org_id = str(cred.get("organizationId") or cred.get("orgId") or "1").strip()
        return base.replace("{organizationId}", org_id).rstrip("/")

    if "flexmail" == "sendbird":
        app_id = str(cred.get("applicationId") or cred.get("appId") or "default").strip()
        return base.replace("{applicationId}", app_id).rstrip("/")

    if "flexmail" == "listmonk":
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

    auth_mode = "flexmail"
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
    "add_contact_interest_subscription": [
        "POST",
        "/contacts/{encodeURIComponent}/interest-subscriptions",
        [
            "encodeURIComponent"
        ],
        [
            "contactId",
            "interestId"
        ]
    ],
    "add_contact_preference_subscription": [
        "POST",
        "/contact-preference-subscriptions",
        [],
        [
            "contactId",
            "preferenceId"
        ]
    ],
    "create_contact": [
        "POST",
        "/contacts",
        [],
        [
            "email",
            "first_name",
            "name",
            "language",
            "custom_fields",
            "source"
        ]
    ],
    "create_interest": [
        "POST",
        "/interests",
        [],
        [
            "name",
            "visibility",
            "label",
            "description"
        ]
    ],
    "delete_interest": [
        "DELETE",
        "/interests/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "get_contact": [
        "GET",
        "/contacts/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "get_interest": [
        "GET",
        "/interests/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "get_source": [
        "GET",
        "/sources/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "list_account_contact_languages": [
        "GET",
        "/account-contact-languages",
        [],
        []
    ],
    "list_contact_interest_subscriptions": [
        "GET",
        "/contacts/{encodeURIComponent}/interest-subscriptions",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "list_contact_preferences": [
        "GET",
        "/contacts/{encodeURIComponent}/preferences",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "list_contact_sources": [
        "GET",
        "/contacts/{encodeURIComponent}/sources",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "list_contacts": [
        "GET",
        "/contacts",
        [],
        [
            "email",
            "limit",
            "offset"
        ]
    ],
    "list_custom_fields": [
        "GET",
        "/custom-fields",
        [],
        [
            "type",
            "language"
        ]
    ],
    "list_interest_labels": [
        "GET",
        "/interest-labels",
        [],
        []
    ],
    "list_interests": [
        "GET",
        "/interests",
        [],
        [
            "name",
            "visibility",
            "order_by",
            "order_direction",
            "limit",
            "offset"
        ]
    ],
    "list_preferences": [
        "GET",
        "/preferences",
        [],
        []
    ],
    "list_segments": [
        "GET",
        "/segments",
        [],
        []
    ],
    "list_sources": [
        "GET",
        "/sources",
        [],
        []
    ],
    "remove_contact_interest_subscription": [
        "DELETE",
        "/contacts/{encodeURIComponent}/interest-subscriptions/{encodeURIComponent}",
        [
            "encodeURIComponent",
            "encodeURIComponent"
        ],
        [
            "contactId",
            "interestId"
        ]
    ],
    "remove_contact_preference_subscription": [
        "DELETE",
        "/contact-preference-subscriptions/{id}",
        [
            "id"
        ],
        []
    ],
    "unsubscribe_contact": [
        "POST",
        "/contacts/{encodeURIComponent}/unsubscribe",
        [
            "encodeURIComponent"
        ],
        [
            "id"
        ]
    ],
    "update_contact": [
        "PATCH",
        "/contacts/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id",
            "first_name",
            "name",
            "language",
            "custom_fields"
        ]
    ],
    "update_interest": [
        "PATCH",
        "/interests/{encodeURIComponent}",
        [
            "encodeURIComponent"
        ],
        [
            "id",
            "name",
            "visibility",
            "label",
            "description"
        ]
    ]
}

class FlexmailDynamicAction(Action):
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
            raise ValueError(f"Flexmail API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class FlexmailProvider(Provider):
    def __init__(self):
        super().__init__(
            service="flexmail",
            display_name="Flexmail",
            category="Marketing & Sales",
            auth_types=['custom_credential'],
            description="Flexmail email marketing and contact management platform with 24 actions."
        )
        for act in get_provider_actions("flexmail"):
            self.register_action(FlexmailDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        token = _extract_token(cred)

        if "flexmail" in ["shopify_admin", "shopify_storefront"]:
            shop = str(cred.get("shopDomain") or cred.get("shop") or "").strip()
            if not shop:
                raise ValueError("Shopify shopDomain is required in credentials.")
            shop = shop.replace("https://", "").replace("http://", "").split("/")[0]
            val_url = "https://api.flexmail.eu/contacts?limit=1".replace("{shopDomain}", shop)
        elif "flexmail" == "shopify_partner":
            org_id = str(cred.get("organizationId") or cred.get("orgId") or "").strip()
            if not org_id:
                raise ValueError("Shopify Partner organizationId is required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1".replace("{organizationId}", org_id)
        elif "flexmail" == "sendbird":
            app_id = str(cred.get("applicationId") or cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("Sendbird applicationId is required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1".replace("{applicationId}", app_id)
        elif "flexmail" == "listmonk":
            base_url = str(cred.get("baseUrl") or "").strip()
            user = str(cred.get("apiUser") or cred.get("username") or "").strip()
            if not base_url:
                raise ValueError("Listmonk baseUrl is required in credentials.")
            if not user:
                raise ValueError("Listmonk apiUser is required in credentials.")
            if not base_url.startswith("http://") and not base_url.startswith("https://"):
                base_url = f"https://{base_url}"
            val_url = f"{base_url.rstrip('/')}/api/subscribers?per_page=1"
        elif "flexmail" == "flexmail":
            acc_id = str(cred.get("accountId") or "").strip()
            pat = token or str(cred.get("personalAccessToken") or "").strip()
            if not acc_id or not pat:
                raise ValueError("Flexmail accountId and personalAccessToken are required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1"
        elif "flexmail" == "crisp":
            token_id = str(cred.get("tokenIdentifier") or "").strip()
            token_key = token or str(cred.get("tokenKey") or "").strip()
            if not token_id or not token_key:
                raise ValueError("Crisp tokenIdentifier and tokenKey are required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1"
        elif "flexmail" == "vonage":
            api_key = str(cred.get("apiKey") or token or "").strip()
            api_secret = str(cred.get("apiSecret") or "").strip()
            if not api_key or not api_secret:
                raise ValueError("Vonage apiKey and apiSecret are required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1"
        elif "flexmail" == "onesignal_rest_api":
            app_id = str(cred.get("appId") or "").strip()
            if not app_id:
                raise ValueError("OneSignal appId is required in credentials.")
            val_url = "https://api.flexmail.eu/contacts?limit=1"
        else:
            if not token:
                raise ValueError("API token or key is required for Flexmail.")
            val_url = "https://api.flexmail.eu/contacts?limit=1"
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
            raise ValueError(f"Flexmail connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Flexmail credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Flexmail validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "flexmail" == "shopee" and body.get("error"):
                    raise ValueError(f"Invalid Flexmail credentials: {body.get('message') or resp.text}")
                elif "flexmail" == "coingecko" and body.get("error"):
                    raise ValueError(f"Invalid Flexmail credentials: {body.get('error')}")
                elif "flexmail" == "sendbird" and body.get("error") is True:
                    raise ValueError(f"Invalid Flexmail credentials: {body.get('message') or resp.text}")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Flexmail Account"
        }

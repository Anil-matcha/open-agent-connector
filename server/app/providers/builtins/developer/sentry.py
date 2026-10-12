"""
Sentry Provider for ConnectorHub.
Loads and registers 24 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://sentry.io"

def _headers(token: str, credential: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "userKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Sentry credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "sentry" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "list_organization_integrations": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/integrations/",
        [
            "organizationIdOrSlug"
        ],
        [
            "providerKey",
            "includeConfig"
        ]
    ],
    "get_organization_integration": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/integrations/{integrationId}/",
        [
            "organizationIdOrSlug",
            "integrationId"
        ],
        []
    ],
    "get_organization_integration_config": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/config/integrations/",
        [
            "organizationIdOrSlug"
        ],
        [
            "providerKey"
        ]
    ],
    "list_project_keys": [
        "GET",
        "/api/0/projects/{organizationIdOrSlug}/{projectIdOrSlug}/keys/",
        [
            "organizationIdOrSlug",
            "projectIdOrSlug"
        ],
        []
    ],
    "get_project_key": [
        "GET",
        "/api/0/projects/{organizationIdOrSlug}/{projectIdOrSlug}/keys/{keyId}/",
        [
            "organizationIdOrSlug",
            "projectIdOrSlug",
            "keyId"
        ],
        []
    ],
    "list_issues": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/issues/",
        [
            "organizationIdOrSlug"
        ],
        [
            "query",
            "statsPeriod",
            "cursor"
        ]
    ],
    "get_issue": [
        "GET",
        "/api/0/issues/{issueId}/",
        [
            "issueId"
        ],
        []
    ],
    "get_issue_event": [
        "GET",
        "/api/0/issues/{issueId}/events/{eventId}/",
        [
            "issueId",
            "eventId"
        ],
        []
    ],
    "list_issue_hashes": [
        "GET",
        "/api/0/issues/{issueId}/hashes/",
        [
            "issueId"
        ],
        []
    ],
    "list_issue_events": [
        "GET",
        "/api/0/issues/{issueId}/events/",
        [
            "issueId"
        ],
        []
    ],
    "get_latest_issue_event": [
        "GET",
        "/api/0/issues/{issueId}/events/latest/",
        [
            "issueId"
        ],
        []
    ],
    "update_issue": [
        "PUT",
        "/api/0/issues/{issueId}/",
        [
            "issueId"
        ],
        []
    ],
    "list_organization_releases": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/releases/",
        [
            "organizationIdOrSlug"
        ],
        []
    ],
    "get_organization_release": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/releases/{version}/",
        [
            "organizationIdOrSlug",
            "version"
        ],
        []
    ],
    "get_release_health_stats": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/releases/{version}/",
        [
            "organizationIdOrSlug",
            "version"
        ],
        []
    ],
    "list_organization_replays": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/replays/",
        [
            "organizationIdOrSlug"
        ],
        []
    ],
    "get_replay": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/replays/{replayId}/",
        [
            "organizationIdOrSlug",
            "replayId"
        ],
        []
    ],
    "list_alerts": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/combined-rules/",
        [
            "organizationIdOrSlug"
        ],
        []
    ],
    "get_alert": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/alert-rules/{ruleId}/",
        [
            "organizationIdOrSlug",
            "ruleId"
        ],
        []
    ],
    "get_project": [
        "GET",
        "/api/0/projects/{organizationIdOrSlug}/{projectIdOrSlug}/",
        [
            "organizationIdOrSlug",
            "projectIdOrSlug"
        ],
        []
    ],
    "list_organization_projects": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/projects/",
        [
            "organizationIdOrSlug"
        ],
        []
    ],
    "list_organization_issues": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/issues/",
        [
            "organizationIdOrSlug"
        ],
        [
            "query",
            "statsPeriod",
            "cursor"
        ]
    ],
    "get_sentry_app": [
        "GET",
        "/api/0/sentry-apps/{sentryAppSlug}/",
        [
            "sentryAppSlug"
        ],
        []
    ],
    "list_organization_sentry_apps": [
        "GET",
        "/api/0/organizations/{organizationIdOrSlug}/sentry-apps/",
        [
            "organizationIdOrSlug"
        ],
        []
    ]
}

class SentryDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Developer Tools"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        self.action_meta = action_meta
        act_name = action_meta["name"]
        route_info = ROUTES.get(act_name) or [
            action_meta.get("method", "GET"),
            action_meta.get("endpoint", ""),
            action_meta.get("pathParams", []),
            action_meta.get("queryParams", [])
        ]
        self.method = route_info[0]
        self.endpoint_template = route_info[1]
        self.path_params = route_info[2]
        self.query_params = set(route_info[3])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        inputs = dict(input_data or {})
        headers = _headers(token, credential)

        path = self.endpoint_template
        # Replace path variables (supporting camelCase, snake_case, and kebab-case)
        path_matches = re.findall(r"\{([^\}]+)\}", path)
        for var in path_matches:
            val = None
            candidates = [
                var,
                "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_"),
                var.replace("-", "_"),
                "id",
                "name"
            ]
            for cand in candidates:
                if cand in inputs:
                    val = inputs.pop(cand)
                    break
            if val is not None:
                path = path.replace(chr(123) + var + chr(125), urllib.parse.quote(str(val), safe=""))

        # Special endpoints overriding base URL
        if "sentry" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "sentry" == "new_relic" and path.startswith("/graphql"):
            base_url = "https://api.newrelic.com"

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        params = {}
        body = {}

        for k, v in inputs.items():
            if v is None or v == "":
                continue
            if req_method in ["GET", "DELETE"] or k in self.query_params or k in ["limit", "offset", "cursor", "page", "per_page"]:
                params[k] = v
            else:
                body[k] = v

        # Payload wraps / transforms if required
        if "sentry" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "sentry" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "sentry" == "pagerduty" and self.name == "resolve_incident":
            body = {"incident": {"type": "incident_reference", "status": "resolved"}}

        json_body = body if (req_method in ["POST", "PUT", "PATCH"] and body) else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=json_body
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("detail") or resp.text
            raise ValueError(f"Sentry API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class SentryProvider(Provider):
    def __init__(self):
        super().__init__(
            service="sentry",
            display_name="Sentry",
            category="Developer Tools",
            auth_types=["api_key"] if "sentry" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="Sentry integration suite for ConnectorHub."
        )
        for act in get_provider_actions("sentry"):
            self.register_action(SentryDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/api/0/users/me/"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Sentry credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Sentry validation failed: {resp.status_code} {resp.text}")

        try:
            res_data = resp.json()
        except Exception:
            res_data = {}

        acc_id = None
        disp_name = None
        for key in ["id", "user_id", "userId", "username", "login", "email", "name", "account_id"]:
            if isinstance(res_data, dict):
                if key in res_data:
                    acc_id = str(res_data[key])
                    break
                user_obj = res_data.get("user") or res_data.get("data")
                if isinstance(user_obj, dict) and key in user_obj:
                    acc_id = str(user_obj[key])
                    disp_name = str(user_obj.get("name") or user_obj.get("username") or acc_id)
                    break

        return {
            "account_id": acc_id or "connected_account",
            "display_name": disp_name or f"Sentry ({acc_id or 'verified'})"
        }

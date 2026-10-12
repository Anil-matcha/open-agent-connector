"""
PostHog Provider for ConnectorHub.
Loads and registers 57 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

API_BASE = "https://us.i.posthog.com"

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
    raise ValueError("PostHog credentials required. Please connect your account first.")

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["baseUrl", "clusterUrl", "host", "instanceUrl", "url"]:
        if cred.get(k):
            return str(cred[k]).strip().rstrip("/")
    if "posthog" == "datadog" and cred.get("site"):
        return f"https://api.{cred['site'].strip().lstrip('https://').rstrip('/')}"
    return API_BASE

# Exact Route Specifications: action_name -> (method, endpoint, path_params, query_params)
ROUTES: Dict[str, List[Any]] = {
    "get_current_user": [
        "GET",
        "/api/users/@me/",
        [],
        []
    ],
    "list_projects": [
        "GET",
        "/api/organizations/{organizationId}/projects/",
        [
            "organizationId"
        ],
        []
    ],
    "get_project": [
        "GET",
        "/api/organizations/{organizationId}/projects/{id}/",
        [
            "organizationId",
            "id"
        ],
        []
    ],
    "list_event_definitions": [
        "GET",
        "/api/projects/{projectId}/event_definitions/",
        [
            "projectId"
        ],
        []
    ],
    "get_event_definition": [
        "GET",
        "/api/projects/{projectId}/event_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_event_definition": [
        "POST",
        "/api/projects/{projectId}/event_definitions/",
        [
            "projectId"
        ],
        []
    ],
    "update_event_definition": [
        "PATCH",
        "/api/projects/{projectId}/event_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_event_definition": [
        "DELETE",
        "/api/projects/{projectId}/event_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_event_definition_by_name": [
        "GET",
        "/api/projects/{projectId}/event_definitions/by_name/",
        [
            "projectId"
        ],
        [
            "name"
        ]
    ],
    "get_event_definition_primary_properties": [
        "GET",
        "/api/projects/{projectId}/event_definitions/primary_properties/",
        [
            "projectId"
        ],
        []
    ],
    "bulk_update_event_definition_tags": [
        "POST",
        "/api/projects/{projectId}/event_definitions/bulk_update_tags/",
        [
            "projectId"
        ],
        []
    ],
    "list_property_definitions": [
        "GET",
        "/api/projects/{projectId}/property_definitions/",
        [
            "projectId"
        ],
        []
    ],
    "get_property_definition": [
        "GET",
        "/api/projects/{projectId}/property_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "update_property_definition": [
        "PATCH",
        "/api/projects/{projectId}/property_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_property_definition": [
        "DELETE",
        "/api/projects/{projectId}/property_definitions/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "bulk_update_property_definition_tags": [
        "POST",
        "/api/projects/{projectId}/property_definitions/bulk_update_tags/",
        [
            "projectId"
        ],
        []
    ],
    "list_annotations": [
        "GET",
        "/api/projects/{projectId}/annotations/",
        [
            "projectId"
        ],
        []
    ],
    "get_annotation": [
        "GET",
        "/api/projects/{projectId}/annotations/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_annotation": [
        "POST",
        "/api/projects/{projectId}/annotations/",
        [
            "projectId"
        ],
        []
    ],
    "update_annotation": [
        "PATCH",
        "/api/projects/{projectId}/annotations/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_annotation": [
        "DELETE",
        "/api/projects/{projectId}/annotations/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "list_cohorts": [
        "GET",
        "/api/projects/{projectId}/cohorts/",
        [
            "projectId"
        ],
        []
    ],
    "get_cohort": [
        "GET",
        "/api/projects/{projectId}/cohorts/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_cohort": [
        "POST",
        "/api/projects/{projectId}/cohorts/",
        [
            "projectId"
        ],
        []
    ],
    "update_cohort": [
        "PATCH",
        "/api/projects/{projectId}/cohorts/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_cohort": [
        "DELETE",
        "/api/projects/{projectId}/cohorts/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "add_persons_to_static_cohort": [
        "POST",
        "/api/projects/{projectId}/cohorts/{id}/add_persons_to_static_cohort/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_cohort_persons": [
        "GET",
        "/api/projects/{projectId}/cohorts/{id}/persons/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_cohort_calculation_history": [
        "GET",
        "/api/projects/{projectId}/cohorts/{id}/calculation_history/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "list_insights": [
        "GET",
        "/api/projects/{projectId}/insights/",
        [
            "projectId"
        ],
        []
    ],
    "get_insight": [
        "GET",
        "/api/projects/{projectId}/insights/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_insight": [
        "POST",
        "/api/projects/{projectId}/insights/",
        [
            "projectId"
        ],
        []
    ],
    "update_insight": [
        "PATCH",
        "/api/projects/{projectId}/insights/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_insight": [
        "DELETE",
        "/api/projects/{projectId}/insights/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "list_dashboards": [
        "GET",
        "/api/environments/{projectId}/dashboards/",
        [
            "projectId"
        ],
        []
    ],
    "get_dashboard": [
        "GET",
        "/api/environments/{projectId}/dashboards/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_dashboard": [
        "POST",
        "/api/environments/{projectId}/dashboards/",
        [
            "projectId"
        ],
        []
    ],
    "update_dashboard": [
        "PATCH",
        "/api/environments/{projectId}/dashboards/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_dashboard": [
        "DELETE",
        "/api/environments/{projectId}/dashboards/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "run_dashboard_insights": [
        "GET",
        "/api/environments/{projectId}/dashboards/{id}/run_insights/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "copy_dashboard_tile": [
        "POST",
        "/api/environments/{projectId}/dashboards/{id}/copy_tile/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "move_dashboard_tile": [
        "PATCH",
        "/api/environments/{projectId}/dashboards/{id}/move_tile/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "reorder_dashboard_tiles": [
        "POST",
        "/api/environments/{projectId}/dashboards/{id}/reorder_tiles/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "list_dashboard_collaborators": [
        "GET",
        "/api/environments/{projectId}/dashboards/{dashboardId}/collaborators/",
        [
            "projectId",
            "dashboardId"
        ],
        []
    ],
    "list_feature_flags": [
        "GET",
        "/api/projects/{projectId}/feature_flags/",
        [
            "projectId"
        ],
        []
    ],
    "get_feature_flag": [
        "GET",
        "/api/projects/{projectId}/feature_flags/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "create_feature_flag": [
        "POST",
        "/api/projects/{projectId}/feature_flags/",
        [
            "projectId"
        ],
        []
    ],
    "update_feature_flag": [
        "PATCH",
        "/api/projects/{projectId}/feature_flags/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "delete_feature_flag": [
        "DELETE",
        "/api/projects/{projectId}/feature_flags/{id}/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_feature_flag_status": [
        "GET",
        "/api/projects/{projectId}/feature_flags/{id}/status/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_feature_flag_dependent_flags": [
        "GET",
        "/api/projects/{projectId}/feature_flags/{id}/dependent_flags/",
        [
            "projectId",
            "id"
        ],
        []
    ],
    "get_feature_flags_local_evaluation": [
        "GET",
        "/api/projects/{projectId}/feature_flags/local_evaluation/",
        [
            "projectId"
        ],
        []
    ],
    "run_query": [
        "POST",
        "/api/projects/{projectId}/query/",
        [
            "projectId"
        ],
        []
    ],
    "get_async_query_status": [
        "GET",
        "/api/projects/{projectId}/query/{queryId}/",
        [
            "projectId",
            "queryId"
        ],
        []
    ],
    "cancel_query": [
        "DELETE",
        "/api/projects/{projectId}/query/{queryId}/",
        [
            "projectId",
            "queryId"
        ],
        []
    ],
    "add_dashboard_collaborator": [
        "POST",
        "/api/environments/{projectId}/dashboards/{dashboardId}/collaborators/",
        [
            "projectId",
            "dashboardId"
        ],
        []
    ],
    "remove_dashboard_collaborator": [
        "DELETE",
        "/api/environments/{projectId}/dashboards/{dashboardId}/collaborators/{userId}/",
        [
            "projectId",
            "dashboardId",
            "userId"
        ],
        []
    ]
}

class PostHogDynamicAction(Action):
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
        if "posthog" == "deepseek" and self.name == "create_anthropic_message":
            base_url = "https://api.deepseek.com/anthropic"
        elif "posthog" == "new_relic" and path.startswith("/graphql"):
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
        if "posthog" == "postman" and self.name == "create_a_collection":
            if "collection" not in body and body:
                body = {"collection": {"info": {"name": body.get("name", "New Collection"), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}
            elif isinstance(body.get("collection"), dict):
                coll_info = body["collection"].setdefault("info", {})
                if "schema" not in coll_info:
                    coll_info["schema"] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        elif "posthog" == "pagerduty" and self.name == "acknowledge_incident":
            body = {"incident": {"type": "incident_reference", "status": "acknowledged"}}
        elif "posthog" == "pagerduty" and self.name == "resolve_incident":
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
            raise ValueError(f"PostHog API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class PostHogProvider(Provider):
    def __init__(self):
        super().__init__(
            service="posthog",
            display_name="PostHog",
            category="Developer Tools",
            auth_types=["api_key"] if "posthog" not in ["datadog", "sentry"] else ["api_key", "oauth2"],
            description="PostHog integration suite for ConnectorHub."
        )
        for act in get_provider_actions("posthog"):
            self.register_action(PostHogDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _headers(token, credential)

        val_url = f"{base_url}/api/users/@me/"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid PostHog credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"PostHog validation failed: {resp.status_code} {resp.text}")

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
            "display_name": disp_name or f"PostHog ({acc_id or 'verified'})"
        }

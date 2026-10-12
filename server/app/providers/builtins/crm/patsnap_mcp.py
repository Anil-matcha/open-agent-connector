"""
Patsnap MCP Provider for ConnectorHub.
Loads and registers 49 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://connect.patsnap.com"

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
    "abstract_image": [
        "GET",
        "/abstract_image",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "abstract_translated": [
        "GET",
        "/abstract_translated",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number",
            "lang"
        ]
    ],
    "award_data": [
        "GET",
        "/award_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "bibliography": [
        "GET",
        "/bibliography",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "claim_translated": [
        "GET",
        "/claim_translated",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number",
            "lang"
        ]
    ],
    "claims": [
        "GET",
        "/claims",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number"
        ]
    ],
    "customs_data": [
        "GET",
        "/customs_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "description": [
        "GET",
        "/description",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number"
        ]
    ],
    "description_translated": [
        "GET",
        "/description_translated",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number",
            "lang"
        ]
    ],
    "design_create_image_upload_url": [
        "POST",
        "/design_create_image_upload_url",
        [],
        [
            "content_type",
            "file_extension",
            "expire_seconds"
        ]
    ],
    "design_get_stage_result": [
        "GET",
        "/design_get_stage_result",
        [],
        [
            "stage",
            "task_id"
        ]
    ],
    "design_get_task_status": [
        "GET",
        "/design_get_task_status",
        [],
        [
            "task_id"
        ]
    ],
    "design_submit_workflow": [
        "POST",
        "/design_submit_workflow",
        [],
        [
            "country",
            "main_field",
            "loc_items",
            "apply_end_time",
            "apply_start_time",
            "title",
            "simple_legal_status",
            "url"
        ]
    ],
    "family": [
        "GET",
        "/family",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "forward_citation": [
        "GET",
        "/forward_citation",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "fulltext_image": [
        "GET",
        "/fulltext_image",
        [],
        [
            "patent_id",
            "offset",
            "patent_number",
            "limit"
        ]
    ],
    "get_patent_legal_status": [
        "GET",
        "/patent_legal_status",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "landscape_applicant_rank": [
        "GET",
        "/landscape_applicant_rank",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_applicant_technology_analysis": [
        "GET",
        "/landscape_applicant_technology_analysis",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_applicant_trend": [
        "GET",
        "/landscape_applicant_trend",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_cooperation_applicant_analysis": [
        "GET",
        "/landscape_cooperation_applicant_analysis",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_detail": [
        "GET",
        "/landscape_detail",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number",
            "lang"
        ]
    ],
    "landscape_detail_aggregation": [
        "GET",
        "/landscape_detail_aggregation",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "landscape_detail_text": [
        "GET",
        "/landscape_detail_text",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "landscape_domain_map": [
        "GET",
        "/landscape_domain_map",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_famn_rank": [
        "GET",
        "/landscape_famn_rank",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_get_patent_pdf": [
        "GET",
        "/landscape_get_patent_pdf",
        [],
        [
            "patent_id",
            "replace_by_related",
            "patent_number"
        ]
    ],
    "landscape_get_rec_office_year": [
        "GET",
        "/landscape_get_rec_office_year",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_info": [
        "GET",
        "/landscape_info",
        [],
        [
            "patent_number"
        ]
    ],
    "landscape_list": [
        "GET",
        "/landscape_list",
        [],
        [
            "collapse_order_authority",
            "offset",
            "limit",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_map_3d": [
        "GET",
        "/landscape_map_3d",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_rec_office": [
        "GET",
        "/landscape_rec_office",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_refered_rank": [
        "GET",
        "/landscape_refered_rank",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_search_patents_facet": [
        "GET",
        "/landscape_search_patents_facet",
        [],
        [
            "field",
            "offset",
            "limit",
            "stemming",
            "sort",
            "lang",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_search_patents_statistics": [
        "GET",
        "/landscape_search_patents_statistics",
        [],
        [
            "field",
            "limit",
            "stemming",
            "lang",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_search_patents_v3": [
        "GET",
        "/landscape_search_patents_v3",
        [],
        [
            "offset",
            "stemming",
            "sort",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_search_patents_with_detail": [
        "GET",
        "/landscape_search_patents_with_detail",
        [],
        [
            "patent_id",
            "offset",
            "replace_by_related",
            "stemming",
            "sort",
            "lang",
            "query_text",
            "pn",
            "collapse_type",
            "collapse_by",
            "posiofpat"
        ]
    ],
    "landscape_tech_applicant_dist": [
        "GET",
        "/landscape_tech_applicant_dist",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_technology_constitute": [
        "GET",
        "/landscape_technology_constitute",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_technology_life_cycle": [
        "GET",
        "/landscape_technology_life_cycle",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "landscape_trend": [
        "GET",
        "/landscape_trend",
        [],
        [
            "collapse_order_authority",
            "sort",
            "collapse_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "legal_data": [
        "GET",
        "/legal_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "license_data": [
        "GET",
        "/license_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "list_tools": [
        "GET",
        "/tools",
        [],
        [
            "server"
        ]
    ],
    "pdf": [
        "GET",
        "/pdf",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "pledge_data": [
        "GET",
        "/pledge_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "reexamination_invalidation": [
        "GET",
        "/reexamination_invalidation",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ],
    "search_patents": [
        "GET",
        "/search_patents",
        [],
        [
            "collapse_order_authority",
            "offset",
            "sort_field",
            "limit",
            "stemming",
            "collapse_order",
            "sort_order",
            "query_text",
            "collapse_type",
            "collapse_by"
        ]
    ],
    "transfer_data": [
        "GET",
        "/transfer_data",
        [],
        [
            "patent_id",
            "patent_number"
        ]
    ]
}

class PatsnapMcpDynamicAction(Action):
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
            raise ValueError(f"Patsnap MCP API error: {resp.status_code} {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}

class PatsnapMcpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="patsnap_mcp",
            display_name="Patsnap MCP",
            category="Marketing & Sales",
            auth_types=["api_key"],
            description="Patsnap global patent search, landscape analytics, and design infringement MCP API with 49 actions."
        )
        for act in get_provider_actions("patsnap_mcp"):
            self.register_action(PatsnapMcpDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://connect.patsnap.com/api/v1/user"
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
            raise ValueError(f"Patsnap MCP connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Patsnap MCP credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Patsnap MCP validation failed: {resp.status_code} {resp.text}")

        try:
            body = resp.json()
            if isinstance(body, dict):
                if "patsnap_mcp" in ["feishu", "feishu_app_bot"] and body.get("code", 0) != 0:
                    raise ValueError(f"Invalid Patsnap MCP credentials: {body.get('msg') or resp.text}")
                elif "patsnap_mcp" in ["wecom_bot", "weixin_official_account"] and body.get("errcode", 0) != 0:
                    raise ValueError(f"Invalid Patsnap MCP credentials: {body.get('errmsg') or resp.text}")
                elif "patsnap_mcp" == "patsnap_mcp" and (body.get("status") is False or body.get("error_code", 0) != 0):
                    raise ValueError(f"Invalid Patsnap MCP credentials: {body.get('error_msg') or resp.text}")
                elif "patsnap_mcp" == "apollo" and body.get("is_logged_in") is False:
                    raise ValueError(f"Invalid Patsnap MCP credentials: not logged in or invalid api key")
        except ValueError:
            raise
        except Exception:
            pass

        return {
            "account_id": "verified",
            "display_name": f"Patsnap MCP Account"
        }

        return {
            "account_id": "verified",
            "display_name": f"Patsnap MCP Account"
        }

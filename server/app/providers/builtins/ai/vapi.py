"""
Vapi Provider for ConnectorHub.
Loads and registers 38 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.vapi.ai"

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
    "create_analytics_query": [
        "POST",
        "/analytics_query",
        [],
        [
            "queries"
        ]
    ],
    "create_assistant": [
        "POST",
        "/assistant",
        [],
        [
            "name",
            "model",
            "voice",
            "transcriber",
            "firstMessage",
            "systemPrompt",
            "clientMessages",
            "serverMessages",
            "maxDurationSeconds",
            "voicemailDetection"
        ]
    ],
    "create_eval": [
        "POST",
        "/eval",
        [],
        [
            "name",
            "type",
            "messages",
            "description"
        ]
    ],
    "create_openai_chat": [
        "POST",
        "/openai_chat",
        [],
        [
            "name",
            "input",
            "squad",
            "stream",
            "squadId",
            "assistant",
            "sessionId",
            "transport",
            "assistantId",
            "previousChatId",
            "assistantOverrides"
        ]
    ],
    "create_phone_number": [
        "POST",
        "/phone_number",
        [],
        [
            "name",
            "number",
            "sipUri",
            "provider",
            "squadId",
            "smsEnabled",
            "workflowId",
            "assistantId",
            "credentialId",
            "twilioApiKey",
            "twilioApiSecret",
            "twilioAuthToken",
            "twilioAccountSid",
            "numberDesiredAreaCode",
            "numberE164CheckEnabled"
        ]
    ],
    "create_policy": [
        "POST",
        "/policy",
        [],
        [
            "name",
            "interval",
            "schedule",
            "severity",
            "threshold",
            "monitorIds",
            "lookbackWindowMinutes"
        ]
    ],
    "create_provider_resource": [
        "POST",
        "/provider_resource",
        [],
        [
            "provider",
            "resourceName",
            "name",
            "rules"
        ]
    ],
    "create_scorecard": [
        "POST",
        "/scorecard",
        [],
        [
            "name",
            "metrics",
            "description",
            "assistantIds"
        ]
    ],
    "create_session": [
        "POST",
        "/session",
        [],
        [
            "name",
            "assistant",
            "assistantId"
        ]
    ],
    "delete_call": [
        "DELETE",
        "/call",
        [],
        [
            "id"
        ]
    ],
    "delete_chat": [
        "DELETE",
        "/chat",
        [],
        [
            "id"
        ]
    ],
    "delete_eval": [
        "DELETE",
        "/eval",
        [],
        [
            "id"
        ]
    ],
    "delete_eval_run": [
        "POST",
        "/eval_run",
        [],
        [
            "id"
        ]
    ],
    "delete_phone_number": [
        "DELETE",
        "/phone_number",
        [],
        [
            "id"
        ]
    ],
    "get_assistant": [
        "GET",
        "/assistant",
        [],
        [
            "id"
        ]
    ],
    "get_call": [
        "GET",
        "/call",
        [],
        [
            "id"
        ]
    ],
    "get_chat": [
        "GET",
        "/chat",
        [],
        [
            "id"
        ]
    ],
    "get_eval": [
        "GET",
        "/eval",
        [],
        [
            "id"
        ]
    ],
    "get_file": [
        "GET",
        "/file",
        [],
        [
            "id"
        ]
    ],
    "get_tool": [
        "GET",
        "/tool",
        [],
        [
            "id"
        ]
    ],
    "list_assistants": [
        "GET",
        "/assistants",
        [],
        [
            "limit",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_calls": [
        "GET",
        "/calls",
        [],
        [
            "id",
            "limit",
            "assistantId",
            "phoneNumberId",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_chats": [
        "GET",
        "/chats",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt",
            "squadId",
            "sessionId",
            "assistantId",
            "assistantIdAny",
            "previousChatId"
        ]
    ],
    "list_evals": [
        "DELETE",
        "/evals",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_insights": [
        "GET",
        "/insights",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_monitoring_policies": [
        "GET",
        "/monitoring_policies",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt",
            "severity",
            "monitorId"
        ]
    ],
    "list_phone_numbers": [
        "GET",
        "/phone_numbers",
        [],
        [
            "limit",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_provider_resources": [
        "GET",
        "/provider_resources",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt",
            "provider",
            "resourceName",
            "resourceId"
        ]
    ],
    "list_scorecards": [
        "GET",
        "/scorecards",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt"
        ]
    ],
    "list_sessions": [
        "GET",
        "/sessions",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt",
            "name",
            "squadId",
            "workflowId",
            "assistantId",
            "assistantIdAny"
        ]
    ],
    "list_structured_outputs": [
        "GET",
        "/structured_outputs",
        [],
        [
            "id",
            "page",
            "limit",
            "sortOrder",
            "createdAtGe",
            "createdAtGt",
            "createdAtLe",
            "createdAtLt",
            "updatedAtGe",
            "updatedAtGt",
            "updatedAtLe",
            "updatedAtLt",
            "name"
        ]
    ],
    "test_code_tool_execution": [
        "GET",
        "/test_code_tool_execution",
        [],
        [
            "code"
        ]
    ],
    "update_assistant": [
        "PATCH",
        "/assistant",
        [],
        [
            "id",
            "name",
            "model",
            "voice",
            "metadata",
            "serverUrl",
            "messagePlan",
            "monitorPlan",
            "transcriber",
            "analysisPlan",
            "artifactPlan",
            "firstMessage",
            "hipaaEnabled",
            "credentialIds",
            "clientMessages",
            "maxDurationPlan",
            "serverMessages",
            "backgroundSound",
            "endCallMessage",
            "endCallPhrases",
            "stopSpeakingPlan",
            "serverUrlSecret",
            "startSpeakingPlan",
            "voicemailMessage",
            "firstMessageMode",
            "backchannelEnabled",
            "maxDurationSeconds",
            "responseDelaySeconds",
            "silenceTimeoutSeconds",
            "transportConfigurations",
            "llmRequestDelaySeconds",
            "backgroundDenoisingEnabled",
            "modelOutputInMessagesEnabled",
            "numWordsToInterruptAssistant"
        ]
    ],
    "update_eval": [
        "PATCH",
        "/eval",
        [],
        [
            "id",
            "name",
            "type",
            "messages",
            "description"
        ]
    ],
    "update_insight": [
        "PATCH",
        "/insight",
        [],
        [
            "id",
            "name",
            "type",
            "formula",
            "groupBy",
            "queries",
            "formulas",
            "metadata",
            "timeRange"
        ]
    ],
    "update_phone_number": [
        "PATCH",
        "/phone_number",
        [],
        [
            "id",
            "name",
            "hooks",
            "number",
            "server",
            "sipUri",
            "squadId",
            "smsEnabled",
            "workflowId",
            "assistantId",
            "credentialId",
            "authentication",
            "twilioApiKey",
            "twilioApiSecret",
            "twilioAuthToken",
            "twilioAccountSid",
            "fallbackDestination",
            "numberE164CheckEnabled"
        ]
    ],
    "update_tool": [
        "PATCH",
        "/tool",
        [],
        [
            "id",
            "url",
            "type",
            "async",
            "method",
            "server",
            "function",
            "messages",
            "backoffPlan",
            "destinations",
            "rejectionPlan",
            "variableExtractionPlan"
        ]
    ],
    "upload_file": [
        "POST",
        "/upload_file",
        [],
        [
            "file"
        ]
    ]
}

class VapiDynamicAction(Action):
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
            raise ValueError(f"Vapi API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class VapiProvider(Provider):
    def __init__(self):
        super().__init__(
            service="vapi",
            display_name="Vapi",
            category="AI & Machine Learning",
            auth_types=["api_key"],
            description="Vapi voice AI platform for building, testing, and deploying conversational voice agents with 38 actions."
        )
        for act in get_provider_actions("vapi"):
            self.register_action(VapiDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.vapi.ai/assistant?limit=1"
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
            raise ValueError(f"Vapi connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Vapi credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Vapi validation failed: {resp.status_code} {resp.text}")

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
            "display_name": f"Vapi Account"
        }

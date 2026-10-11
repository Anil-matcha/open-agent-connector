"""
Firecrawl Provider for ConnectorHub.
Loads and registers 30 actions from 'actions_catalog.json'.
Web scraping, crawling, structured data extraction, search, LLM-ready markdown, and deep web research via the Firecrawl API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_FIRECRAWL_API_BASE = "https://api.firecrawl.dev"

FIRECRAWL_ENDPOINT_MAP = {
    "firecrawl.scrape": ("POST", "/v2/scrape"),
    "firecrawl.batch_scrape": ("POST", "/v2/batch/scrape"),
    "firecrawl.batch_scrape_get": ("GET", "/v2/batch/scrape/{id}"),
    "firecrawl.batch_scrape_get_errors": ("GET", "/v2/batch/scrape/{id}/errors"),
    "firecrawl.batch_scrape_cancel": ("DELETE", "/v2/batch/scrape/{id}"),
    "firecrawl.crawl": ("POST", "/v2/crawl"),
    "firecrawl.crawl_v2": ("POST", "/v2/crawl"),
    "firecrawl.crawl_get": ("GET", "/v2/crawl/{id}"),
    "firecrawl.get_the_status_of_a_crawl_job": ("GET", "/v2/crawl/{id}"),
    "firecrawl.crawl_get_errors": ("GET", "/v2/crawl/{id}/errors"),
    "firecrawl.crawl_cancel": ("DELETE", "/v2/crawl/{id}"),
    "firecrawl.crawl_delete": ("DELETE", "/v2/crawl/{id}"),
    "firecrawl.crawl_list_active": ("GET", "/v2/crawl/active"),
    "firecrawl.crawl_params_preview": ("POST", "/v2/crawl/params-preview"),
    "firecrawl.extract": ("POST", "/v2/extract"),
    "firecrawl.extract_get": ("GET", "/v2/extract/{id}"),
    "firecrawl.search": ("POST", "/v2/search"),
    "firecrawl.map_multiple_urls_based_on_options": ("POST", "/v2/map"),
    "firecrawl.start_agent": ("POST", "/v2/agent"),
    "firecrawl.get_agent_status": ("GET", "/v2/agent/{id}"),
    "firecrawl.agent_cancel": ("DELETE", "/v2/agent/{id}"),
    "firecrawl.deep_research": ("POST", "/v1/deep-research"),
    "firecrawl.get_deep_research_status": ("GET", "/v1/deep-research/{id}"),
    "firecrawl.llms_txt_generate": ("POST", "/v1/llmstxt"),
    "firecrawl.llms_txt_get": ("GET", "/v1/llmstxt/{id}"),
    "firecrawl.queue_get": ("GET", "/v2/team/queue-status"),
    "firecrawl.credit_usage_get": ("GET", "/v2/team/credit-usage"),
    "firecrawl.credit_usage_get_historical": ("GET", "/v2/team/credit-usage/historical"),
    "firecrawl.token_usage_get": ("GET", "/v2/team/token-usage"),
    "firecrawl.token_usage_get_historical": ("GET", "/v2/team/token-usage/historical"),
}

def _firecrawl_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken") or (credential or {}).get("token")
    if not token or not str(token).strip():
        raise ValueError("Firecrawl API Key required. Please connect your Firecrawl account first.")
    return str(token).strip()

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    base = (credential or {}).get("baseUrl")
    if base and str(base).strip():
        return str(base).strip().rstrip("/")
    return DEFAULT_FIRECRAWL_API_BASE

class FirecrawlDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Data"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        mapped_method, mapped_endpoint = FIRECRAWL_ENDPOINT_MAP.get(
            action_meta["id"],
            ("POST" if "create" in action_meta["name"] or "start" in action_meta["name"] else "GET", "/v2/scrape")
        )
        self.method = mapped_method
        self.endpoint_template = mapped_endpoint

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        inputs = dict(input_data or {})
        headers = _firecrawl_headers(api_key)

        path = self.endpoint_template
        for var in ["id", "job_id"]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{base_url}{path}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method == "GET" else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            err_msg = str(data)
            if isinstance(data, dict):
                err_msg = data.get("error") or data.get("message") or str(data)
            raise ValueError(f"Firecrawl API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}

class FirecrawlProvider(Provider):
    def __init__(self):
        super().__init__(
            service="firecrawl",
            display_name="Firecrawl",
            category="Data",
            auth_types=["api_key"],
            description="Turn entire websites into LLM-ready markdown or clean structured data with intelligent web scraping and crawling.",
            homepage_url="https://firecrawl.dev",
            base_url=DEFAULT_FIRECRAWL_API_BASE,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Firecrawl API Key",
                    "placeholder": "fc-...",
                    "description": "Firecrawl API key used with the Authorization Bearer header.",
                    "docs_url": "https://firecrawl.dev/app/api-keys",
                    "docs_label": "Firecrawl API Keys Dashboard",
                    "setup_guide": {
                        "title": "Firecrawl API Key Guide",
                        "docs_url": "https://firecrawl.dev/app/api-keys",
                        "docs_label": "Firecrawl App Dashboard",
                        "instructions": [
                            "1. Sign in to Firecrawl at firecrawl.dev/app.",
                            "2. Navigate to API Keys.",
                            "3. Click 'Create API Key' (starts with 'fc-').",
                            "4. Copy your key and paste it below."
                        ],
                        "scopes": ["scrape:write", "crawl:write", "extract:write"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "fc-...",
                            "description": "Firecrawl API Key."
                        },
                        {
                            "key": "baseUrl",
                            "label": "Base URL (Optional)",
                            "type": "text",
                            "required": False,
                            "placeholder": "https://api.firecrawl.dev",
                            "description": "Optional base URL of a self-hosted Firecrawl instance."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("firecrawl"):
            self.register_action(FirecrawlDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Firecrawl API Key by querying GET /v2/team/credit-usage."""
        api_key = _extract_token(credential)
        base_url = _resolve_base_url(credential)
        headers = _firecrawl_headers(api_key)
        url = f"{base_url}/v2/team/credit-usage"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Firecrawl API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Firecrawl API Key. Firecrawl returned Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Firecrawl credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        usage = body.get("data", {})
        return {
            "valid": True,
            "accountId": "firecrawl_api_key",
            "displayName": "Firecrawl API Key",
            "metadata": {
                "validationEndpoint": "/v2/team/credit-usage",
                "remainingCredits": usage.get("remaining_credits"),
                "plan": usage.get("plan")
            }
        }

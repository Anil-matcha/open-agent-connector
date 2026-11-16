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
    # Firecrawl shuts down /v1/deep-research on 2026-12-10, so deep research runs on the agent endpoint.
    # https://docs.firecrawl.dev/migrating-from-deep-research
    "firecrawl.deep_research": ("POST", "/v2/agent"),
    "firecrawl.get_deep_research_status": ("GET", "/v2/agent/{id}"),
    # Firecrawl shuts down /v1/llmstxt on 2026-12-10, so llms.txt is built from map and batch scrape results.
    # https://docs.firecrawl.dev/migrating-from-llmstxt
    "firecrawl.llms_txt_generate": ("POST", "/v2/map"),
    "firecrawl.llms_txt_get": ("GET", "/v2/batch/scrape/{id}"),
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

def _deep_research_agent_body(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Map a deep research request onto an agent run: one merged prompt, and a schema for the report and sources."""
    json_options = inputs.get("jsonOptions") if isinstance(inputs.get("jsonOptions"), dict) else {}
    json_schema = json_options.get("schema") if isinstance(json_options.get("schema"), dict) else None
    parts = [inputs.get("query"), inputs.get("systemPrompt"), inputs.get("analysisPrompt"), json_options.get("prompt")]
    prompt = "\n\n".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    properties: Dict[str, Any] = {
        "report": {"type": "string", "description": "A markdown report that answers the question."},
        "sources": {
            "type": "array",
            "description": "The sources the report is based on.",
            "items": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "title": {"type": "string"}},
                "required": ["url", "title"],
            },
        },
    }
    required = ["report", "sources"]
    if json_schema:
        properties["json"] = json_schema
        required.append("json")
    body: Dict[str, Any] = {"prompt": prompt, "schema": {"type": "object", "properties": properties, "required": required}}
    if inputs.get("maxCredits") is not None:
        body["maxCredits"] = inputs["maxCredits"]
    return body

def _deep_research_status(payload: Any) -> Any:
    """Return a finished agent run in the deep research shape: data.finalAnalysis, data.sources and sources."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return payload
    run = payload["data"]
    data = {"finalAnalysis": run.get("report"), "sources": run.get("sources")}
    if "json" in run:
        data["json"] = run["json"]
    return {**payload, "data": data, "sources": run.get("sources")}

LLMS_TXT_SUMMARY_FORMAT = {
    "type": "json",
    "prompt": "Write a 3-4 word title and a 9-10 word description of this page.",
    "schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
        "required": ["title", "description"],
    },
}

async def _firecrawl_request(client: httpx.AsyncClient, method: str, url: str, headers: Dict[str, str], json_body: Any = None):
    """Send one guarded Firecrawl request; returns (status code, payload) and raises like the other actions do."""
    assert_public_url(url)
    resp = await execute_guarded_request(client=client, method=method, url=url, headers=headers, json_body=json_body)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    if resp.status_code >= 400:
        err_msg = str(data)
        if isinstance(data, dict):
            err_msg = data.get("error") or data.get("message") or str(data)
        raise ValueError(f"Firecrawl API error ({resp.status_code}): {err_msg}")
    return resp.status_code, data

async def _start_llms_txt(inputs: Dict[str, Any], base_url: str, headers: Dict[str, str], client: httpx.AsyncClient) -> Dict[str, Any]:
    """Map the site, then batch scrape its pages with a JSON format for each page's title and description, plus
    markdown for llms-full.txt. A batch scrape keeps neither the root url nor the map order, so both are returned
    with the job id for llms_txt_get."""
    url = inputs.get("url")
    limit = inputs.get("maxUrls")
    _, mapped = await _firecrawl_request(client, "POST", f"{base_url}/v2/map", headers, {
        "url": url,
        "limit": 10 if limit is None else limit,
        "includeSubdomains": False,
    })
    links = mapped.get("links") if isinstance(mapped, dict) else None
    urls = [link.get("url") if isinstance(link, dict) else link for link in links or []]
    urls = [link for link in urls if isinstance(link, str) and link.strip()]
    if not urls:
        raise ValueError(f"Firecrawl map found no pages to scrape for {url}")

    formats = ["markdown", LLMS_TXT_SUMMARY_FORMAT] if inputs.get("showFullText") is True else [LLMS_TXT_SUMMARY_FORMAT]
    body: Dict[str, Any] = {"urls": urls, "formats": formats}
    if inputs.get("cache") is False:
        body["maxAge"] = 0
    status_code, batch = await _firecrawl_request(client, "POST", f"{base_url}/v2/batch/scrape", headers, body)
    batch = batch if isinstance(batch, dict) else {}
    return {"status": status_code, "data": {"success": batch.get("success") is True, "id": batch.get("id"), "url": url, "urls": urls}}

async def _get_llms_txt(inputs: Dict[str, Any], base_url: str, headers: Dict[str, str], client: httpx.AsyncClient) -> Dict[str, Any]:
    """Read an LLMs.txt job's batch scrape and, once it has completed, return every page of results written into the
    /v1/llmstxt status shape. Running batches report processing, failed and cancelled ones failed."""
    job_id = urllib.parse.quote(str(inputs.get("id")), safe="")
    status_code, job = await _firecrawl_request(client, "GET", f"{base_url}/v2/batch/scrape/{job_id}", headers)
    job = job if isinstance(job, dict) else {}
    state = job.get("status")
    if state == "scraping":
        return {"status": status_code, "data": _compact({"success": True, "status": "processing", "expiresAt": job.get("expiresAt")})}
    if state != "completed":
        error = job.get("error") or f"Firecrawl batch scrape {state or 'failed'}"
        return {"status": status_code, "data": _compact({"success": False, "status": "failed", "error": error, "expiresAt": job.get("expiresAt")})}

    # A completed batch pages its results through next, which ends after the last page.
    results = list(job.get("data") or [])
    next_url = job.get("next")
    while next_url:
        parts = urllib.parse.urlsplit(next_url)
        page_url = f"{base_url}{parts.path}" + (f"?{parts.query}" if parts.query else "")
        _, page = await _firecrawl_request(client, "GET", page_url, headers)
        page = page if isinstance(page, dict) else {}
        results.extend(page.get("data") or [])
        following = page.get("next")
        next_url = None if following == next_url else following

    data = _build_llms_txt(results, inputs.get("url"), inputs.get("urls"))
    return {"status": status_code, "data": _compact({"success": True, "status": "completed", "data": data, "expiresAt": job.get("expiresAt")})}

def _build_llms_txt(results: list, root_url: Optional[str] = None, urls: Optional[list] = None) -> Dict[str, str]:
    """Write llms.txt and llms-full.txt in the format /v1/llmstxt returned, leaving out pages that came back with a
    status of 400 or more. Given the root url and map order from llms_txt_generate, the header names the root url and
    the pages follow map order (batch results come back in the order they finish). Without them, the header names
    the site's origin and the pages keep the order Firecrawl returned them in."""
    pages = [page if isinstance(page, dict) else {} for page in results]

    def metadata(page: Dict[str, Any]) -> Dict[str, Any]:
        return page["metadata"] if isinstance(page.get("metadata"), dict) else {}

    def page_url(page: Dict[str, Any]) -> str:
        return _first_text(metadata(page).get("url"), metadata(page).get("sourceURL")) or ""

    def kept_page(page: Dict[str, Any]) -> bool:
        status_code = metadata(page).get("statusCode")
        return not (isinstance(status_code, (int, float)) and status_code >= 400)

    kept = [page for page in pages if kept_page(page)]
    if isinstance(urls, list):
        map_order: Dict[str, int] = {}
        for index, mapped_url in enumerate(urls):
            map_order.setdefault(mapped_url, index)
        kept.sort(key=lambda page: map_order.get(_first_text(metadata(page).get("sourceURL")) or "", len(urls)))

    if isinstance(root_url, str) and root_url.strip():
        root = root_url
    else:
        root = _site_origin(page_url(kept[0])) if kept else ""
    llmstxt = f"# {root} llms.txt\n\n"
    llmsfulltxt = f"# {root} llms-full.txt\n\n"
    for page in kept:
        summary = page["json"] if isinstance(page.get("json"), dict) else {}
        url = page_url(page)
        title = _first_text(summary.get("title"), metadata(page).get("title")) or url
        description = _first_text(summary.get("description"), metadata(page).get("description")) or ""
        markdown = page["markdown"] if isinstance(page.get("markdown"), str) else ""
        llmstxt += f"- [{title}]({url}): {description}\n"
        llmsfulltxt += f"## {title}\n{markdown}\n\n"

    # The pages carry markdown only when llms_txt_generate was asked for llms-full.txt.
    if any(isinstance(page.get("markdown"), str) for page in pages):
        return {"llmstxt": llmstxt, "llmsfulltxt": llmsfulltxt}
    return {"llmstxt": llmstxt}

def _first_text(*values: Any) -> Optional[str]:
    """Return the first non-empty string; page metadata can hold a string or a list of strings."""
    for value in values:
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def _site_origin(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""

def _compact(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}

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

        if self.id == "firecrawl.llms_txt_generate":
            return await _start_llms_txt(inputs, base_url, headers, client)
        if self.id == "firecrawl.llms_txt_get":
            return await _get_llms_txt(inputs, base_url, headers, client)

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
        if self.id == "firecrawl.deep_research":
            json_body = _deep_research_agent_body(inputs)
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

        if self.id == "firecrawl.get_deep_research_status":
            data = _deep_research_status(data)

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

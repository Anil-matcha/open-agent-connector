from typing import Dict, Any, Optional
from urllib.parse import urldefrag, urljoin
import httpx
from app.providers.base import Provider, Action
from app.core.ssrf import assert_public_url, execute_guarded_request

MAX_PAGINATION_PAGES = 10
MAX_PAGINATION_BYTES = 10 * 1024 * 1024


def _origin(url: httpx.URL):
    return url.scheme, url.host, url.port or (443 if url.scheme == "https" else 80)


def _next_page(response: httpx.Response, origin) -> Optional[str]:
    for link in response.links.values():
        if "next" not in link.get("rel", "").split():
            continue
        url = httpx.URL(urldefrag(urljoin(str(response.url), link["url"]))[0])
        if url.username or url.password or _origin(url) != origin:
            raise ValueError("Pagination next link must stay on the original origin without URL credentials.")
        return str(url)
    return None


def _response_data(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


class HttpRequestAction(Action):
    def __init__(self):
        super().__init__(
            id="custom.http_request",
            name="Custom HTTP Request",
            description="Send a custom SSRF-safe HTTP request to any external API with headers and payload.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full destination HTTP/HTTPS URL"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
                    "headers": {"type": "object", "description": "Optional HTTP headers dictionary"},
                    "body": {"type": "object", "description": "Optional JSON body object"},
                    "max_pages": {
                        "type": "integer", "minimum": 1, "maximum": MAX_PAGINATION_PAGES,
                        "default": 1,
                        "description": "For GET without a body, follow same-origin Link rel=next. Values above 1 return pages and a next_url continuation."
                    }
                },
                "required": ["url"]
            }
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        url = input_data["url"]
        method = input_data.get("method", "GET").upper()
        headers = dict(input_data.get("headers") or {})
        body = input_data.get("body")
        max_pages = input_data.get("max_pages", 1)
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_PAGINATION_PAGES:
            raise ValueError(f"max_pages must be an integer between 1 and {MAX_PAGINATION_PAGES}.")
        if max_pages > 1 and (method != "GET" or body is not None):
            raise ValueError("Pagination requires GET without a body.")

        # Inject custom credential apiKey if present
        if credential and credential.get("apiKey"):
            headers.setdefault("Authorization", f"Bearer {credential['apiKey']}")

        if max_pages > 1:
            return await self._request_pages(url, headers, client, max_pages)

        assert_public_url(url)
        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=url,
            json_body=body if body else None,
            headers=headers
        )
        
        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": _response_data(resp)
        }

    async def _request_pages(self, url, headers, client, max_pages):
        current_url = str(httpx.URL(urldefrag(url)[0]))
        origin = _origin(httpx.URL(current_url))
        seen = set()
        pages = []
        remaining_bytes = MAX_PAGINATION_BYTES
        next_url = None
        for _ in range(max_pages):
            seen.add(current_url)
            response = await execute_guarded_request(
                client=client, method="GET", url=current_url, headers=headers,
                max_response_bytes=remaining_bytes, stream_response=True,
            )
            response.raise_for_status()
            final_url = str(httpx.URL(urldefrag(str(response.url))[0]))
            if final_url != current_url and final_url in seen:
                raise ValueError("Pagination cycle detected after redirect.")
            seen.add(final_url)
            remaining_bytes -= len(response.content)
            if remaining_bytes < 0:
                raise ValueError("Paginated response exceeded the total size limit.")
            pages.append({
                "url": final_url,
                "status": response.status_code,
                "headers": dict(response.headers),
                "data": _response_data(response),
            })
            next_url = _next_page(response, origin)
            if next_url is None:
                break
            if next_url in seen:
                raise ValueError("Pagination cycle detected.")
            current_url = next_url
        return {"pages": pages, "page_count": len(pages), "next_url": next_url}

class CustomHttpProvider(Provider):
    def __init__(self):
        super().__init__(
            service="custom",
            display_name="Custom Webhook / HTTP",
            category="Utilities",
            auth_types=["no_auth", "api_key"],
            description="Execute arbitrary SSRF-guarded HTTP requests and webhooks to any external API.",
            homepage_url="",
            auth_configs=[
                {
                    "type": "no_auth",
                    "label": "Anonymous / Public HTTP Request",
                    "description": "Send unauthenticated HTTP calls or webhooks to public APIs.",
                    "setup_guide": {
                        "title": "Public HTTP / Webhook Guide",
                        "instructions": [
                            "Send unauthenticated HTTP calls or webhooks to public APIs.",
                            "All outbound traffic is protected by strict SSRF guardrails blocking private IPs and loopbacks."
                        ]
                    }
                },
                {
                    "type": "api_key",
                    "label": "Custom Bearer Token / API Key",
                    "placeholder": "Bearer secret_token_xyz or api_key_...",
                    "description": "Optionally attach an Authorization Bearer header to all requests.",
                    "setup_guide": {
                        "title": "Custom HTTP / Bearer Auth Guide",
                        "instructions": [
                            "Enter an optional API key or Bearer token to be sent with outbound requests.",
                            "If specified, the token will be attached as 'Authorization: Bearer <token>'."
                        ]
                    }
                }
            ]
        )
        self.register_action(HttpRequestAction())

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        api_key = credential.get("apiKey") or credential.get("accessToken")
        return {
            "account_id": "api_key" if api_key else "anonymous",
            "display_name": "Custom HTTP Client",
            "granted_scopes": []
        }

import json
import socket

import httpx
import jsonschema
import pytest

from app.core import ssrf
from app.providers.builtins.ai.firecrawl import FirecrawlProvider

CREDENTIAL = {"apiKey": "fc-test"}
SUMMARY_FORMAT = {
    "type": "json",
    "prompt": "Write a 3-4 word title and a 9-10 word description of this page.",
    "schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
        "required": ["title", "description"],
    },
}
MAPPED = [
    "https://example.com",
    "https://example.com/docs",
    "https://example.com/blog",
    "https://example.com/pricing",
]
HOME = {
    "markdown": "# Example\nWelcome.",
    "json": {"title": "Example Home", "description": "The landing page that introduces Example and its main features."},
    "metadata": {"sourceURL": "https://example.com", "url": "https://example.com/", "statusCode": 200, "title": "Example"},
}
DOCS = {
    "markdown": "# Getting started\nInstall it.",
    "json": {"title": "Docs Getting Started", "description": "How to install Example and make your first API request."},
    "metadata": {"sourceURL": "https://example.com/docs", "url": "https://example.com/docs", "statusCode": 200},
}
BLOG = {
    "markdown": "Not found",
    "json": {"title": "Missing Page", "description": "Nothing here."},
    "metadata": {"sourceURL": "https://example.com/blog", "url": "https://example.com/blog", "statusCode": 404},
}
# JSON extraction came back empty, so the title and description come from the page metadata.
PRICING = {
    "markdown": "# Pricing\nFree and paid plans.",
    "metadata": {
        "sourceURL": "https://example.com/pricing",
        "url": "https://example.com/pricing",
        "statusCode": 200,
        "title": ["Pricing", "Pricing | Example"],
        "description": "Plans and prices for Example.",
    },
}
HOME_LINE = "- [Example Home](https://example.com/): The landing page that introduces Example and its main features."
DOCS_LINE = "- [Docs Getting Started](https://example.com/docs): How to install Example and make your first API request."
PRICING_LINE = "- [Pricing](https://example.com/pricing): Plans and prices for Example."


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    # Keep the SSRF guard in the loop without resolving api.firecrawl.dev for real.
    def getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    monkeypatch.setattr(ssrf.socket, "getaddrinfo", getaddrinfo)


def mock_client(routes, seen):
    """Answer each "METHOD /path?query" with its payload and anything else with a 404."""

    async def handler(request: httpx.Request):
        seen.append(request)
        query = f"?{request.url.query.decode()}" if request.url.query else ""
        payload = routes.get(f"{request.method} {request.url.path}{query}")
        if payload is None:
            return httpx.Response(404, json={"success": False, "error": "Not found"})
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def action(action_id):
    return FirecrawlProvider().actions[action_id]


@pytest.mark.asyncio
async def test_llms_txt_generate_maps_the_site_and_batch_scrapes_the_pages():
    seen = []
    routes = {
        "POST /v2/map": {"success": True, "links": [{"url": url, "title": "Mapped title"} for url in MAPPED]},
        "POST /v2/batch/scrape": {"success": True, "id": "batch-1", "url": "https://api.firecrawl.dev/v2/batch/scrape/batch-1"},
    }

    async with mock_client(routes, seen) as client:
        result = await action("firecrawl.llms_txt_generate").execute(
            {"url": "https://example.com", "maxUrls": 5, "showFullText": True, "cache": False}, CREDENTIAL, client
        )

    assert result == {
        "status": 200,
        "data": {"success": True, "id": "batch-1", "url": "https://example.com", "urls": MAPPED},
    }
    assert [(request.method, str(request.url)) for request in seen] == [
        ("POST", "https://api.firecrawl.dev/v2/map"),
        ("POST", "https://api.firecrawl.dev/v2/batch/scrape"),
    ]
    assert json.loads(seen[0].content) == {"url": "https://example.com", "limit": 5, "includeSubdomains": False}
    assert json.loads(seen[1].content) == {"urls": MAPPED, "formats": ["markdown", SUMMARY_FORMAT], "maxAge": 0}


@pytest.mark.asyncio
async def test_llms_txt_generate_maps_ten_urls_by_default_and_scrapes_no_markdown():
    seen = []
    routes = {
        "POST /v2/map": {"success": True, "links": [{"url": "https://example.com/docs"}]},
        "POST /v2/batch/scrape": {"success": True, "id": "batch-2"},
    }

    async with mock_client(routes, seen) as client:
        result = await action("firecrawl.llms_txt_generate").execute({"url": "https://example.com"}, CREDENTIAL, client)

    assert result["data"] == {
        "success": True,
        "id": "batch-2",
        "url": "https://example.com",
        "urls": ["https://example.com/docs"],
    }
    assert json.loads(seen[0].content) == {"url": "https://example.com", "limit": 10, "includeSubdomains": False}
    assert json.loads(seen[1].content) == {"urls": ["https://example.com/docs"], "formats": [SUMMARY_FORMAT]}


@pytest.mark.asyncio
async def test_llms_txt_generate_fails_without_a_batch_scrape_when_map_finds_no_pages():
    seen = []

    async with mock_client({"POST /v2/map": {"success": True, "links": []}}, seen) as client:
        with pytest.raises(ValueError, match="^Firecrawl map found no pages to scrape for https://example.com$"):
            await action("firecrawl.llms_txt_generate").execute({"url": "https://example.com"}, CREDENTIAL, client)

    assert [str(request.url) for request in seen] == ["https://api.firecrawl.dev/v2/map"]


@pytest.mark.asyncio
async def test_llms_txt_get_writes_both_files_from_every_page_in_map_order():
    seen = []
    routes = {
        "GET /v2/batch/scrape/batch-1": {
            "success": True,
            "status": "completed",
            "completed": 4,
            "total": 4,
            "expiresAt": "2026-12-01T00:00:00.000Z",
            "data": [PRICING, DOCS],
            "next": "https://api.firecrawl.dev/v2/batch/scrape/batch-1?skip=2",
        },
        "GET /v2/batch/scrape/batch-1?skip=2": {
            "success": True,
            "status": "completed",
            "completed": 4,
            "total": 4,
            "data": [BLOG, HOME],
            "next": None,
        },
    }

    async with mock_client(routes, seen) as client:
        result = await action("firecrawl.llms_txt_get").execute(
            {"id": "batch-1", "url": "https://example.com", "urls": MAPPED}, CREDENTIAL, client
        )

    assert result == {
        "status": 200,
        "data": {
            "success": True,
            "status": "completed",
            "data": {
                "llmstxt": "\n".join(["# https://example.com llms.txt", "", HOME_LINE, DOCS_LINE, PRICING_LINE, ""]),
                "llmsfulltxt": "\n".join(
                    [
                        "# https://example.com llms-full.txt",
                        "",
                        "## Example Home",
                        "# Example",
                        "Welcome.",
                        "",
                        "## Docs Getting Started",
                        "# Getting started",
                        "Install it.",
                        "",
                        "## Pricing",
                        "# Pricing",
                        "Free and paid plans.",
                        "",
                        "",
                    ]
                ),
            },
            "expiresAt": "2026-12-01T00:00:00.000Z",
        },
    }
    assert [str(request.url) for request in seen] == [
        "https://api.firecrawl.dev/v2/batch/scrape/batch-1",
        "https://api.firecrawl.dev/v2/batch/scrape/batch-1?skip=2",
    ]


@pytest.mark.asyncio
async def test_llms_txt_get_falls_back_to_the_site_origin_and_firecrawls_order():
    seen = []
    without_markdown = [{key: value for key, value in page.items() if key != "markdown"} for page in (PRICING, DOCS)]
    routes = {"GET /v2/batch/scrape/batch-2": {"success": True, "status": "completed", "data": without_markdown}}

    async with mock_client(routes, seen) as client:
        result = await action("firecrawl.llms_txt_get").execute({"id": "batch-2"}, CREDENTIAL, client)

    assert result == {
        "status": 200,
        "data": {
            "success": True,
            "status": "completed",
            "data": {"llmstxt": "\n".join(["# https://example.com llms.txt", "", PRICING_LINE, DOCS_LINE, ""])},
        },
    }


@pytest.mark.asyncio
async def test_llms_txt_get_reports_running_failed_and_cancelled_batches():
    expires_at = "2026-12-01T00:00:00.000Z"
    cases = [
        (
            {"success": True, "status": "scraping", "completed": 1, "total": 4, "data": [DOCS], "next": "https://x/y?skip=1", "expiresAt": expires_at},
            {"success": True, "status": "processing", "expiresAt": expires_at},
        ),
        (
            {"success": False, "status": "failed", "error": "Insufficient credits", "data": []},
            {"success": False, "status": "failed", "error": "Insufficient credits"},
        ),
        (
            {"success": True, "status": "cancelled", "data": []},
            {"success": False, "status": "failed", "error": "Firecrawl batch scrape cancelled"},
        ),
    ]

    for payload, output in cases:
        seen = []
        async with mock_client({"GET /v2/batch/scrape/batch-1": payload}, seen) as client:
            result = await action("firecrawl.llms_txt_get").execute({"id": "batch-1"}, CREDENTIAL, client)

        assert result == {"status": 200, "data": output}
        assert [str(request.url) for request in seen] == ["https://api.firecrawl.dev/v2/batch/scrape/batch-1"]


def test_llms_txt_get_accepts_the_url_and_urls_from_llms_txt_generate():
    # Same check the action runner applies before an action executes.
    validator = jsonschema.Draft7Validator(action("firecrawl.llms_txt_get").input_schema)

    assert validator.is_valid({"id": "batch-1"})
    assert validator.is_valid({"id": "batch-1", "url": "https://example.com", "urls": MAPPED})
    assert not validator.is_valid({"id": "batch-1", "urls": "https://example.com"})

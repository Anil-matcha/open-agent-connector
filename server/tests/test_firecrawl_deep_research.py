import json
import socket

import httpx
import pytest

from app.core import ssrf
from app.providers.builtins.ai.firecrawl import FirecrawlProvider

CREDENTIAL = {"apiKey": "fc-test"}
REPORT_PROPERTIES = {
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


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    # Keep the SSRF guard in the loop without resolving api.firecrawl.dev for real.
    def getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    monkeypatch.setattr(ssrf.socket, "getaddrinfo", getaddrinfo)


def mock_client(responses, seen):
    async def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(200, json=responses.pop(0))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_deep_research_starts_an_agent_run():
    action = FirecrawlProvider().actions["firecrawl.deep_research"]
    studies_schema = {"type": "object", "properties": {"studies": {"type": "array"}}}
    seen = []

    async with mock_client([{"success": True, "id": "job-1"}], seen) as client:
        result = await action.execute(
            {
                "query": "How do EVs and gas cars compare on lifetime emissions?",
                "systemPrompt": "Prefer peer-reviewed sources.",
                "analysisPrompt": "Answer in three sections.",
                "jsonOptions": {"prompt": "List the studies you used.", "schema": studies_schema},
                "maxCredits": 500,
                "maxUrls": 20,
                "maxDepth": 3,
                "timeLimit": 120,
                "formats": ["markdown", "json"],
            },
            CREDENTIAL,
            client,
        )

    assert result == {"status": 200, "data": {"success": True, "id": "job-1"}}
    assert seen[0].method == "POST"
    assert str(seen[0].url) == "https://api.firecrawl.dev/v2/agent"
    assert json.loads(seen[0].content) == {
        "prompt": "How do EVs and gas cars compare on lifetime emissions?\n\nPrefer peer-reviewed sources."
        "\n\nAnswer in three sections.\n\nList the studies you used.",
        "schema": {
            "type": "object",
            "properties": {**REPORT_PROPERTIES, "json": studies_schema},
            "required": ["report", "sources", "json"],
        },
        "maxCredits": 500,
    }


@pytest.mark.asyncio
async def test_deep_research_without_json_options_asks_for_report_and_sources():
    action = FirecrawlProvider().actions["firecrawl.deep_research"]
    seen = []

    async with mock_client([{"success": True, "id": "job-2"}], seen) as client:
        await action.execute({"query": "What is Firecrawl?"}, CREDENTIAL, client)

    assert json.loads(seen[0].content) == {
        "prompt": "What is Firecrawl?",
        "schema": {"type": "object", "properties": REPORT_PROPERTIES, "required": ["report", "sources"]},
    }


@pytest.mark.asyncio
async def test_deep_research_status_maps_a_completed_agent_run():
    action = FirecrawlProvider().actions["firecrawl.get_deep_research_status"]
    sources = [{"url": "https://example.com/study", "title": "Lifetime emissions study"}]
    seen = []

    async with mock_client(
        [
            {
                "success": True,
                "status": "completed",
                "data": {"report": "# Findings", "sources": sources},
                "expiresAt": "2026-12-01T00:00:00.000Z",
                "creditsUsed": 42,
            }
        ],
        seen,
    ) as client:
        result = await action.execute({"id": "job-1"}, CREDENTIAL, client)

    assert seen[0].method == "GET"
    assert str(seen[0].url) == "https://api.firecrawl.dev/v2/agent/job-1"
    assert result == {
        "status": 200,
        "data": {
            "success": True,
            "status": "completed",
            "data": {"finalAnalysis": "# Findings", "sources": sources},
            "sources": sources,
            "expiresAt": "2026-12-01T00:00:00.000Z",
            "creditsUsed": 42,
        },
    }


@pytest.mark.asyncio
async def test_deep_research_status_passes_processing_and_failed_runs_through():
    action = FirecrawlProvider().actions["firecrawl.get_deep_research_status"]
    processing = {"success": True, "status": "processing", "expiresAt": "2026-12-01T00:00:00.000Z"}
    failed = {"success": True, "status": "failed", "error": "Agent reached max credits", "stopReason": "credit_limit_reached"}
    seen = []

    async with mock_client([dict(processing), dict(failed)], seen) as client:
        assert await action.execute({"id": "job-1"}, CREDENTIAL, client) == {"status": 200, "data": processing}
        assert await action.execute({"id": "job-1"}, CREDENTIAL, client) == {"status": 200, "data": failed}

    assert [str(request.url) for request in seen] == ["https://api.firecrawl.dev/v2/agent/job-1"] * 2

import gzip
import socket

import httpx
import jsonschema
import pytest

from app.core import ssrf
from app.providers.builtins.utility.custom_http import HttpRequestAction
from app.providers.catalog import get_provider_actions


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", lambda host, port, *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
    ])


def client_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_follows_relative_next_links_and_preserves_each_page():
    seen = []

    def handler(request):
        seen.append(request)
        page = int(request.url.params.get("page", "1"))
        headers = {"Link": f'<?page={page+1}>; rel="next"'} if page < 3 else {}
        return httpx.Response(200, json={"items": [{"id": page}]}, headers=headers)

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute(
            {"url": "https://example.com/items", "max_pages": 5}, {"apiKey": "test-key"}, client
        )
    assert result["page_count"] == 3
    assert result["next_url"] is None
    assert [page["data"]["items"][0]["id"] for page in result["pages"]] == [1, 2, 3]
    assert all(request.headers["Authorization"] == "Bearer test-key" for request in seen)


@pytest.mark.asyncio
async def test_default_request_keeps_the_existing_response_shape():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[1], headers={"Link": '<?page=2>; rel="next"'})

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute({"url": "https://example.com/items"}, None, client)
    assert set(result) == {"status", "headers", "data"}
    assert result["data"] == [1]
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_page_cap_returns_explicit_continuation():
    seen = []

    def handler(request):
        seen.append(request)
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json=[page], headers={"Link": f'<?page={page+1}>; rel="next"'})

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute(
            {"url": "https://example.com/items", "max_pages": 2}, None, client
        )
    assert len(seen) == result["page_count"] == 2
    assert result["next_url"] == "https://example.com/items?page=3"


@pytest.mark.asyncio
@pytest.mark.parametrize("link", [
    "https://other.example/items", "http://example.com/items", "https://127.0.0.1/items",
    "https://user:password@example.com/items", "https://example.com:8443/items",
])
async def test_unsafe_continuations_are_rejected_before_another_request(link):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[1], headers={"Link": f'<{link}>; rel="next"'})

    async with client_for(handler) as client:
        with pytest.raises(ValueError):
            await HttpRequestAction().execute(
                {"url": "https://example.com/items", "max_pages": 3}, {"apiKey": "secret"}, client
            )
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_cycle_is_rejected_instead_of_returning_repeated_data():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=[1], headers={"Link": '</items#ignored>; rel="next"'})

    async with client_for(handler) as client:
        with pytest.raises(ValueError, match="cycle"):
            await HttpRequestAction().execute(
                {"url": "https://example.com/items", "max_pages": 3}, None, client
            )
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_error_on_a_later_page_does_not_claim_completion():
    def handler(request):
        if "page=2" in str(request.url):
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json=[1], headers={"Link": '<?page=2>; rel="next"'})

    async with client_for(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await HttpRequestAction().execute(
                {"url": "https://example.com/items", "max_pages": 3}, None, client
            )


@pytest.mark.asyncio
async def test_total_response_limit_covers_all_pages_without_content_length():
    def handler(request):
        response = httpx.Response(200, content=b"x" * (6 * 1024 * 1024),
                                  headers={"Link": '<?page=2>; rel="next"'})
        del response.headers["content-length"]
        return response

    async with client_for(handler) as client:
        with pytest.raises(ValueError, match="size"):
            await HttpRequestAction().execute(
                {"url": "https://example.com/items", "max_pages": 3}, None, client
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [{"max_pages": 0}, {"max_pages": 11}, {"max_pages": True},
                                    {"max_pages": 2, "method": "POST"},
                                    {"max_pages": 2, "body": {"query": "anything"}}])
async def test_invalid_pagination_makes_no_network_request(extra):
    def handler(request):
        pytest.fail("invalid pagination must be rejected before making a request")

    async with client_for(handler) as client:
        with pytest.raises(ValueError):
            await HttpRequestAction().execute({"url": "https://example.com/items", **extra}, None, client)


def test_catalog_and_runtime_expose_the_same_pagination_schema():
    runtime = HttpRequestAction().input_schema
    catalog = get_provider_actions("custom")[0]["input_schema"]
    assert catalog["properties"]["max_pages"] == runtime["properties"]["max_pages"]
    jsonschema.validate({"url": "https://example.com/items", "max_pages": 3}, runtime)
    for invalid in [0, 11, True, "3"]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({"url": "https://example.com/items", "max_pages": invalid}, runtime)


@pytest.mark.asyncio
async def test_next_link_resolves_against_the_redirected_page():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/pages/first"})
        if request.url.path == "/pages/first":
            return httpx.Response(200, json=[1], headers={"Link": '<second>; rel="next"'})
        return httpx.Response(200, json=[2])

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute(
            {"url": "https://example.com/start", "max_pages": 3}, None, client
        )
    assert seen == ["https://example.com/start", "https://example.com/pages/first",
                    "https://example.com/pages/second"]
    assert result["page_count"] == 2
    assert result["next_url"] is None


@pytest.mark.asyncio
async def test_redirect_to_an_already_returned_page_is_a_cycle():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/second":
            return httpx.Response(302, headers={"Location": "/first"})
        return httpx.Response(200, json=[1], headers={"Link": '</second>; rel="next"'})

    async with client_for(handler) as client:
        with pytest.raises(ValueError, match="cycle"):
            await HttpRequestAction().execute(
                {"url": "https://example.com/first", "max_pages": 3}, None, client
            )
    assert len(seen) == 3


@pytest.mark.asyncio
async def test_streaming_stops_at_the_remaining_aggregate_budget():
    streams = []

    class Chunks(httpx.AsyncByteStream):
        def __init__(self):
            self.consumed = 0
            self.closed = False

        async def __aiter__(self):
            for _ in range(3):
                self.consumed += 1
                yield b"x" * (6 * 1024 * 1024)

        async def aclose(self):
            self.closed = True

    def handler(request):
        stream = Chunks()
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    async with client_for(handler) as client:
        with pytest.raises(ValueError, match="size"):
            await HttpRequestAction().execute(
                {"url": "https://example.com/items", "max_pages": 3}, None, client
            )
    assert streams[0].consumed == 2
    assert streams[0].closed


@pytest.mark.asyncio
async def test_streamed_compressed_page_is_decoded_once():
    class Compressed(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield gzip.compress(b'{"items": [1, 2]}')

    def handler(request):
        return httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=Compressed())

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute(
            {"url": "https://example.com/items", "max_pages": 3}, None, client
        )
    assert result["pages"][0]["data"] == {"items": [1, 2]}


@pytest.mark.asyncio
async def test_streamed_redirect_keeps_existing_cross_origin_secret_stripping():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"Location": "https://other.example/items"})
        return httpx.Response(200, json=[1])

    async with client_for(handler) as client:
        result = await HttpRequestAction().execute(
            {"url": "https://example.com/items", "max_pages": 3,
             "headers": {"Cookie": "session=test"}}, {"apiKey": "test-key"}, client
        )
    assert result["page_count"] == 1
    assert "Authorization" in seen[0].headers and "Cookie" in seen[0].headers
    assert "Authorization" not in seen[1].headers and "Cookie" not in seen[1].headers

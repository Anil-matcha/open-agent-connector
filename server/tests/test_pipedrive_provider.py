import pytest
import httpx
from app.providers.builtins.crm.pipedrive import PipedriveProvider, _pipedrive_headers

@pytest.mark.asyncio
async def test_pipedrive_headers_format():
    # API key (40 chars)
    api_headers = _pipedrive_headers({"apiKey": "285031ce0b081f2b56794cfe33b29a7c1a4aa798"})
    assert "x-api-token" in api_headers
    assert "Authorization" not in api_headers

    # OAuth access token
    oauth_headers = _pipedrive_headers({"accessToken": "oauth_token_1234567890_abcdefghijklmnopqrstuvwxyz", "authType": "oauth2"})
    assert "Authorization" in oauth_headers
    assert oauth_headers["Authorization"] == "Bearer oauth_token_1234567890_abcdefghijklmnopqrstuvwxyz"
    assert "x-api-token" not in oauth_headers

@pytest.mark.asyncio
async def test_pipedrive_validate_oauth_credentials():
    provider = PipedriveProvider()
    
    async def handler(request: httpx.Request):
        assert request.headers.get("Authorization") == "Bearer oauth_token_test_1234567890_abcdefghijklmnopqrstuvwxyz"
        assert "x-api-token" not in request.headers
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "id": 12345,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "company_id": 999,
                    "company_name": "Acme Corp",
                    "company_domain": "acme"
                }
            }
        )
    
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        res = await provider.validate_credentials({
            "accessToken": "oauth_token_test_1234567890_abcdefghijklmnopqrstuvwxyz",
            "authType": "oauth2"
        }, client)
        
        assert res["valid"] is True
        assert res["displayName"] == "Jane Doe"
        assert res["metadata"]["apiDomain"] == "https://acme.pipedrive.com"
        assert res["metadata"]["companyDomain"] == "acme"

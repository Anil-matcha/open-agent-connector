"""
Acceptance & Contract Tests for 15 E-Commerce, Payments & Communication Providers:
1. Shopify Admin (shopify_admin, 26 actions)
2. Shopify Storefront (shopify_storefront, 8 actions)
3. Shopify Partner (shopify_partner, 5 actions)
4. Shopee (shopee, 24 actions)
5. Paddle (paddle, 12 actions)
6. Gumroad (gumroad, 9 actions)
7. CoinGecko (coingecko, 25 actions)
8. Sendbird (sendbird, 28 actions)
9. Listmonk (listmonk, 28 actions)
10. Mailgun (mailgun, 17 actions)
11. Flexmail (flexmail, 24 actions)
12. Crisp (crisp, 5 actions)
13. Telnyx (telnyx, 4 actions)
14. Vonage (vonage, 4 actions)
15. OneSignal REST API (onesignal_rest_api, 4 actions)

Total: 15 Providers, 223 Actions.
Registry Combined Total: 217 Providers, 7,740 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_15_PROVIDERS = [
    ("shopify_admin", 26, ["api_key"], "E-Commerce & Retail"),
    ("shopify_storefront", 8, ["api_key"], "E-Commerce & Retail"),
    ("shopify_partner", 5, ["api_key"], "E-Commerce & Retail"),
    ("shopee", 24, ["oauth2"], "E-Commerce & Retail"),
    ("paddle", 12, ["api_key"], "E-Commerce & Retail"),
    ("gumroad", 9, ["api_key"], "E-Commerce & Retail"),
    ("coingecko", 25, ["api_key"], "Finance & Accounting"),
    ("sendbird", 28, ["api_key"], "Customer Support & Communication"),
    ("listmonk", 28, ["api_key"], "Marketing & Sales"),
    ("mailgun", 17, ["api_key"], "Customer Support & Communication"),
    ("flexmail", 24, ["custom_credential"], "Marketing & Sales"),
    ("crisp", 5, ["api_key"], "Customer Support & Communication"),
    ("telnyx", 4, ["api_key"], "Customer Support & Communication"),
    ("vonage", 4, ["custom_credential"], "Customer Support & Communication"),
    ("onesignal_rest_api", 4, ["api_key"], "Customer Support & Communication"),
]

def test_registry_has_all_217_providers():
    assert len(registry.list_providers()) >= 217
    assert len(registry.list_actions()) >= 7740

    for service, expected_count, expected_auth, expected_cat in NEXT_15_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_next_15():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEXT_15_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_next_15():
    client = TestClient(app)
    for service, expected_count, _, _ in NEXT_15_PROVIDERS:
        resp = client.get(f"/v1/actions?service={service}")
        assert resp.status_code == 200
        actions = resp.json().get("data", [])
        assert len(actions) == expected_count, f"{service} returned {len(actions)} actions, expected {expected_count}"
        sample = actions[0]
        assert "id" in sample
        assert "name" in sample
        assert "inputSchema" in sample
        assert "outputSchema" in sample

@pytest.mark.asyncio
async def test_live_credential_validation_rejection_for_next_15():
    dummy_creds = {
        "shopify_admin": {"apiKey": "fake_token", "shopDomain": "test-shop.myshopify.com"},
        "shopify_storefront": {"apiKey": "fake_token", "shopDomain": "test-shop.myshopify.com"},
        "shopify_partner": {"apiKey": "fake_token", "organizationId": "123456"},
        "shopee": {"accessToken": "fake_token"},
        "paddle": {"apiKey": "fake_token"},
        "gumroad": {"apiKey": "fake_token"},
        "coingecko": {"apiKey": "fake_token"},
        "sendbird": {"apiKey": "fake_token", "applicationId": "test-app-id"},
        "listmonk": {"apiKey": "fake_token", "baseUrl": "https://listmonk.example.com", "apiUser": "testuser"},
        "mailgun": {"apiKey": "fake_token"},
        "flexmail": {"accountId": "testacc", "personalAccessToken": "fake_token"},
        "crisp": {"tokenIdentifier": "test_id", "tokenKey": "fake_token"},
        "telnyx": {"apiKey": "fake_token"},
        "vonage": {"apiKey": "fake_key", "apiSecret": "fake_secret"},
        "onesignal_rest_api": {"apiKey": "fake_token", "appId": "fake_app_id"},
    }

    async with httpx.AsyncClient() as client:
        for service, cred in dummy_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None, f"Provider {service} missing"
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

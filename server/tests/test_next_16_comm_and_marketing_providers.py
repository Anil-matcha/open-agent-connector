"""
Acceptance & Contract Tests for 16 Communication, Support, Marketing & Intelligence Providers:
1. Feishu (feishu, 403 actions)
2. Feishu App Bot (feishu_app_bot, 332 actions)
3. AgentMail (agent_mail, 102 actions)
4. Discord Bot (discordbot, 55 actions)
5. WeCom Bot (wecom_bot, 54 actions)
6. WeChat Official Account (weixin_official_account, 42 actions)
7. Pushover (pushover, 29 actions)
8. Front (front, 5 actions)
9. Freshdesk (freshdesk, 4 actions)
10. Apple Ads (apple_ads, 98 actions)
11. FastMoss MCP (fastmoss_mcp, 57 actions)
12. Bing Webmaster Tools (bing_webmaster, 54 actions)
13. Patsnap MCP (patsnap_mcp, 49 actions)
14. SellerSprite MCP (sellersprite_mcp, 47 actions)
15. TwitterAPI.io (twitterapi_io, 39 actions)
16. Apollo (apollo, 5 actions)

Total: 16 Providers, 1,375 Actions.
Registry Combined Total: 170 Providers, 6,795 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_16_PROVIDERS = [
    ("feishu", 403, ["oauth2"], "Communication & Messaging"),
    ("feishu_app_bot", 332, ["api_key"], "Communication & Messaging"),
    ("agent_mail", 102, ["api_key"], "Communication & Messaging"),
    ("discordbot", 55, ["api_key"], "Communication & Messaging"),
    ("wecom_bot", 54, ["api_key"], "Communication & Messaging"),
    ("weixin_official_account", 42, ["api_key"], "Communication & Messaging"),
    ("pushover", 29, ["api_key"], "Communication & Messaging"),
    ("front", 5, ["api_key"], "Communication & Messaging"),
    ("freshdesk", 4, ["api_key"], "Communication & Messaging"),
    ("apple_ads", 98, ["api_key"], "Marketing & Sales"),
    ("fastmoss_mcp", 57, ["api_key"], "Marketing & Sales"),
    ("bing_webmaster", 54, ["api_key"], "Marketing & Sales"),
    ("patsnap_mcp", 49, ["api_key"], "Marketing & Sales"),
    ("sellersprite_mcp", 47, ["api_key"], "Marketing & Sales"),
    ("twitterapi_io", 39, ["api_key"], "Marketing & Sales"),
    ("apollo", 5, ["api_key"], "Marketing & Sales"),
]

def test_registry_has_all_170_providers():
    assert len(registry.list_providers()) >= 170
    assert len(registry.list_actions()) >= 6795

    for service, expected_count, expected_auth, expected_cat in NEXT_16_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_next_16():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEXT_16_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_next_16():
    client = TestClient(app)
    for service, expected_count, _, _ in NEXT_16_PROVIDERS:
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
async def test_live_credential_validation_rejection_for_next_16():
    dummy_creds = {
        "feishu": {"accessToken": "fake_token"},
        "feishu_app_bot": {"accessToken": "fake_token"},
        "agent_mail": {"apiKey": "fake_token"},
        "discordbot": {"apiKey": "fake_token"},
        "wecom_bot": {"apiKey": "fake_token"},
        "weixin_official_account": {"apiKey": "fake_token"},
        "pushover": {"apiKey": "fake_token"},
        "front": {"apiKey": "fake_token"},
        "freshdesk": {"apiKey": "fake_token", "domain": "dummytestdomain123"},
        "apple_ads": {"apiKey": "fake_token"},
        "fastmoss_mcp": {"apiKey": "fake_token"},
        "bing_webmaster": {"apiKey": "fake_token"},
        "patsnap_mcp": {"apiKey": "fake_token"},
        "sellersprite_mcp": {"apiKey": "fake_token"},
        "twitterapi_io": {"apiKey": "fake_token"},
        "apollo": {"apiKey": "fake_token"},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service, cred in dummy_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

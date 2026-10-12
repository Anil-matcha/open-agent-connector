"""
Acceptance & Contract Tests for 14 Database, Backend & AI Providers:
1. Elasticsearch (elasticsearch, 21 actions)
2. NocoDB (nocodb, 24 actions)
3. Convex (convex, 23 actions)
4. PlanetScale (planetscale, 10 actions)
5. Render (render, 10 actions)
6. Vultr (vultr, 14 actions)
7. Algolia (algolia, 9 actions)
8. Hugging Face (huggingface, 14 actions)
9. ChatBotKit (chatbotkit, 27 actions)
10. Anthropic Admin (anthropic_admin, 6 actions)
11. JigsawStack (jigsawstack, 6 actions)
12. Jimeng AI (jimeng_ai, 28 actions)
13. SunoAPI (sunoapi, 26 actions)
14. Baidu Qianfan (qianfan, 25 actions)

Total: 14 Providers, 243 Actions.
Registry Combined Total: 202 Providers, 7,517 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_14_PROVIDERS = [
    ("elasticsearch", 21, ["api_key", "custom_credential"], "Developer & Cloud Infrastructure"),
    ("nocodb", 24, ["api_key"], "Developer & Cloud Infrastructure"),
    ("convex", 23, ["api_key", "oauth2"], "Developer & Cloud Infrastructure"),
    ("planetscale", 10, ["api_key"], "Developer & Cloud Infrastructure"),
    ("render", 10, ["api_key"], "Developer & Cloud Infrastructure"),
    ("vultr", 14, ["api_key"], "Developer & Cloud Infrastructure"),
    ("algolia", 9, ["api_key"], "Developer & Cloud Infrastructure"),
    ("huggingface", 14, ["api_key", "oauth2"], "AI & Machine Learning"),
    ("chatbotkit", 27, ["api_key"], "AI & Machine Learning"),
    ("anthropic_admin", 6, ["api_key"], "AI & Machine Learning"),
    ("jigsawstack", 6, ["api_key"], "AI & Machine Learning"),
    ("jimeng_ai", 28, ["custom_credential"], "AI & Machine Learning"),
    ("sunoapi", 26, ["api_key"], "AI & Machine Learning"),
    ("qianfan", 25, ["api_key"], "AI & Machine Learning"),
]

def test_registry_has_all_202_providers():
    assert len(registry.list_providers()) >= 202
    assert len(registry.list_actions()) >= 7517

    for service, expected_count, expected_auth, expected_cat in NEXT_14_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_next_14():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEXT_14_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_next_14():
    client = TestClient(app)
    for service, expected_count, _, _ in NEXT_14_PROVIDERS:
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
async def test_live_credential_validation_rejection_for_next_14():
    dummy_creds = {
        "elasticsearch": {"apiKey": "fake_token", "baseUrl": "https://es.example.com:9200"},
        "nocodb": {"apiKey": "fake_token", "baseUrl": "https://nocodb.example.com"},
        "convex": {"apiKey": "fake_token"},
        "planetscale": {"apiKey": "fake_token", "serviceTokenId": "fake_id"},
        "render": {"apiKey": "fake_token"},
        "vultr": {"apiKey": "fake_token"},
        "algolia": {"apiKey": "fake_token", "applicationId": "testapp"},
        "huggingface": {"apiKey": "fake_token"},
        "chatbotkit": {"apiKey": "fake_token"},
        "anthropic_admin": {"apiKey": "fake_token"},
        "jigsawstack": {"apiKey": "fake_token"},
        "jimeng_ai": {"accessKeyId": "fake_ak", "secretAccessKey": "fake_sk"},
        "sunoapi": {"apiKey": "fake_token"},
        "qianfan": {"apiKey": "fake_token"},
    }

    async with httpx.AsyncClient() as client:
        for service, cred in dummy_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None, f"Provider {service} missing"
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

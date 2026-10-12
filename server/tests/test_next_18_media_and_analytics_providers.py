"""
Acceptance & Contract Tests for 18 Media, Content, Commerce & Analytics Providers:
1. Paperless-ngx (paperless_ngx, 139 actions)
2. Xiaohongshu Store (xiaohongshu_store, 36 actions)
3. Oura (oura, 35 actions)
4. Strava (strava, 34 actions)
5. Amara (amara, 33 actions)
6. WeChat Store (weixin_store, 32 actions)
7. Vimeo (vimeo, 25 actions)
8. Unsplash (unsplash, 6 actions)
9. Databricks (databricks, 36 actions)
10. Google Analytics (google_analytics, 28 actions)
11. Metabase (metabase, 28 actions)
12. Fathom Analytics (fathom, 15 actions)
13. Umami Analytics (umami, 8 actions)
14. Databox (databox, 7 actions)
15. Axiom (axiom, 5 actions)
16. Amplitude (amplitude, 4 actions)
17. Plausible Analytics (plausible_analytics, 4 actions)
18. Grafana Cloud (grafana_cloud, 4 actions)

Total: 18 Providers, 479 Actions.
Registry Combined Total: 188 Providers, 7,274 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_18_PROVIDERS = [
    ("paperless_ngx", 139, ["api_key"], "Media & Content"),
    ("xiaohongshu_store", 36, ["api_key"], "E-Commerce & Retail"),
    ("oura", 35, ["oauth2"], "Health & Fitness"),
    ("strava", 34, ["oauth2"], "Health & Fitness"),
    ("amara", 33, ["api_key"], "Media & Content"),
    ("weixin_store", 32, ["api_key"], "E-Commerce & Retail"),
    ("vimeo", 25, ["oauth2"], "Media & Content"),
    ("unsplash", 6, ["api_key"], "Media & Content"),
    ("databricks", 36, ["api_key"], "Developer & Cloud Infrastructure"),
    ("google_analytics", 28, ["oauth2"], "Google Workspace & Cloud"),
    ("metabase", 28, ["api_key"], "Developer & Cloud Infrastructure"),
    ("fathom", 15, ["api_key"], "Marketing & Sales"),
    ("umami", 8, ["api_key"], "Marketing & Sales"),
    ("databox", 7, ["api_key"], "Marketing & Sales"),
    ("axiom", 5, ["api_key"], "Developer & Cloud Infrastructure"),
    ("amplitude", 4, ["api_key"], "Marketing & Sales"),
    ("plausible_analytics", 4, ["api_key"], "Marketing & Sales"),
    ("grafana_cloud", 4, ["api_key"], "Developer & Cloud Infrastructure"),
]

def test_registry_has_all_188_providers():
    assert len(registry.list_providers()) >= 188
    assert len(registry.list_actions()) >= 7274

    for service, expected_count, expected_auth, expected_cat in NEXT_18_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_next_18():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEXT_18_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_next_18():
    client = TestClient(app)
    for service, expected_count, _, _ in NEXT_18_PROVIDERS:
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
async def test_live_credential_validation_rejection_for_next_18():
    dummy_creds = {
        "paperless_ngx": {"apiKey": "fake_token", "host": "paperless.testsite.local"},
        "xiaohongshu_store": {"apiKey": "fake_token"},
        "oura": {"accessToken": "fake_token"},
        "strava": {"accessToken": "fake_token"},
        "amara": {"apiKey": "fake_token"},
        "weixin_store": {"apiKey": "fake_token"},
        "vimeo": {"accessToken": "fake_token"},
        "unsplash": {"apiKey": "fake_token"},
        "databricks": {"apiKey": "fake_token", "host": "dbc-test.cloud.databricks.com"},
        "google_analytics": {"accessToken": "fake_token"},
        "metabase": {"apiKey": "fake_token", "host": "metabase.testsite.local"},
        "fathom": {"apiKey": "fake_token"},
        "umami": {"apiKey": "fake_token"},
        "databox": {"apiKey": "apiKey", "apiKey": "fake_token"},
        "axiom": {"apiKey": "fake_token"},
        "amplitude": {"apiKey": "fake_token", "secretKey": "fake_secret"},
        "plausible_analytics": {"apiKey": "fake_token"},
        "grafana_cloud": {"apiKey": "fake_token"},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        for service, cred in dummy_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

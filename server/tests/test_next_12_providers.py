"""
Acceptance & Contract Tests for 12 Finance, Billing & AI Providers:
1. Longbridge (longbridge, 80 actions)
2. Alpha Vantage (alpha_vantage, 44 actions)
3. Polygon.io (polygon_io, 40 actions)
4. Financial Modeling Prep (financial_modeling_prep, 37 actions)
5. Recurly (recurly, 10 actions)
6. Chargebee (chargebee, 9 actions)
7. Wise (wise, 3 actions)
8. UnifAPI (unifapi, 220 actions)
9. OOMOL Fusion API (fusion-api, 82 actions)
10. PixelLab (pixellab, 56 actions)
11. Vapi (vapi, 38 actions)
12. Voiceflow (voiceflow, 4 actions)

Total: 12 Providers, 623 Actions.
Registry Combined Total: 154 Providers, 5,420 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_12_PROVIDERS = [
    ("longbridge", 80, ["oauth2"], "Finance & Accounting"),
    ("alpha_vantage", 44, ["api_key"], "Finance & Accounting"),
    ("polygon_io", 40, ["api_key"], "Finance & Accounting"),
    ("financial_modeling_prep", 37, ["api_key"], "Finance & Accounting"),
    ("recurly", 10, ["api_key"], "Finance & Accounting"),
    ("chargebee", 9, ["api_key"], "Finance & Accounting"),
    ("wise", 3, ["api_key"], "Finance & Accounting"),
    ("unifapi", 220, ["api_key"], "AI & Machine Learning"),
    ("fusion-api", 82, ["api_key"], "AI & Machine Learning"),
    ("pixellab", 56, ["api_key"], "AI & Machine Learning"),
    ("vapi", 38, ["api_key"], "AI & Machine Learning"),
    ("voiceflow", 4, ["api_key"], "AI & Machine Learning"),
]

def test_registry_has_all_154_providers():
    assert len(registry.list_providers()) == 154
    assert len(registry.list_actions()) == 5420

    for service, expected_count, expected_auth, expected_cat in NEXT_12_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_next_12():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEXT_12_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_next_12():
    client = TestClient(app)
    for service, expected_count, _, _ in NEXT_12_PROVIDERS:
        resp = client.get(f"/v1/actions?service={service}")
        assert resp.status_code == 200
        actions = resp.json().get("data", [])
        assert len(actions) == expected_count, f"Actions for {service} mismatch"
        for a in actions:
            assert "inputSchema" in a
            assert "outputSchema" in a
            assert "id" in a and a["id"].startswith(f"{service}.")

@pytest.mark.anyio
async def test_credential_validation_error_handling_next_12():
    async with httpx.AsyncClient() as client:
        test_creds = {
            "longbridge": {"accessToken": "fake_token"},
            "alpha_vantage": {"apiKey": "fake_token"},
            "polygon_io": {"apiKey": "fake_token"},
            "financial_modeling_prep": {"apiKey": "fake_token"},
            "recurly": {"apiKey": "fake_token"},
            "chargebee": {"apiKey": "fake_token", "site": "testsite"},
            "wise": {"apiKey": "fake_token"},
            "unifapi": {"apiKey": "fake_token"},
            "fusion-api": {"apiKey": "fake_token"},
            "pixellab": {"apiKey": "fake_token"},
            "vapi": {"apiKey": "fake_token"},
            "voiceflow": {"apiKey": "fake_token"},
        }
        for service, cred in test_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

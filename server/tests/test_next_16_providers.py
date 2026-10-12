"""
Verification and Acceptance Test for Next 16 SaaS Providers:
1. LaunchDarkly (launch_darkly, 40 actions)
2. Calendly (calendly, 37 actions)
3. Figma (figma, 26 actions)
4. Help Scout (helpscout, 24 actions)
5. Neon (neon, 18 actions)
6. WordPress (wordpress, 18 actions)
7. WorkOS (workos, 14 actions)
8. Mixpanel (mixpanel, 13 actions)
9. Clerk (clerk, 11 actions)
10. Webflow (webflow, 11 actions)
11. Turso (turso, 10 actions)
12. Ghost (ghost, 9 actions)
13. Upstash Redis (upstash_redis, 7 actions)
14. Klaviyo (klaviyo, 7 actions)
15. Segment (segment, 7 actions)
16. ActiveCampaign (activecampaign, 6 actions)

Total: 16 Providers, 258 Actions.
Hub Combined Total: 127 Providers, 2,973 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_16_PROVIDERS = [
    ("launch_darkly", 40, ["api_key"], "Developer Tools"),
    ("neon", 18, ["api_key"], "Developer Tools"),
    ("workos", 14, ["api_key"], "Identity & Security"),
    ("clerk", 11, ["api_key"], "Identity & Security"),
    ("turso", 10, ["api_key"], "Developer Tools"),
    ("upstash_redis", 7, ["custom_credential"], "Developer Tools"),
    ("calendly", 37, ["oauth2", "api_key"], "Project Management"),
    ("figma", 26, ["oauth2", "api_key"], "Project Management"),
    ("wordpress", 18, ["oauth2", "api_key"], "Content & Media"),
    ("webflow", 11, ["oauth2", "api_key"], "Content & Media"),
    ("ghost", 9, ["api_key"], "Content & Media"),
    ("helpscout", 24, ["oauth2"], "CRM & Sales"),
    ("mixpanel", 13, ["api_key"], "Analytics & Marketing"),
    ("klaviyo", 7, ["api_key"], "CRM & Sales"),
    ("segment", 7, ["api_key"], "Analytics & Marketing"),
    ("activecampaign", 6, ["api_key"], "CRM & Sales"),
]

def test_registry_has_all_127_providers():
    assert len(registry.list_providers()) >= 127
    assert len(registry.list_actions()) >= 2973

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
        assert len(actions) == expected_count, f"Actions for {service} mismatch"
        for a in actions:
            assert "inputSchema" in a
            assert "outputSchema" in a
            assert "id" in a and a["id"].startswith(f"{service}.")

@pytest.mark.anyio
async def test_credential_validation_error_handling_next_16():
    async with httpx.AsyncClient() as client:
        test_creds = {
            "launch_darkly": {"apiKey": "fake_token"},
            "neon": {"apiKey": "fake_token"},
            "workos": {"apiKey": "fake_token"},
            "clerk": {"apiKey": "fake_token"},
            "turso": {"apiKey": "fake_token"},
            "upstash_redis": {"restUrl": "https://test.upstash.io", "restToken": "fake_token"},
            "calendly": {"apiKey": "fake_token"},
            "figma": {"apiKey": "fake_token"},
            "wordpress": {"siteUrl": "https://example.com", "apiKey": "fake_token"},
            "webflow": {"apiKey": "fake_token"},
            "ghost": {"siteUrl": "https://demo.ghost.io", "apiKey": "fake_token"},
            "helpscout": {"accessToken": "fake_token"},
            "mixpanel": {"serviceAccountUsername": "svc_test", "apiKey": "fake_secret"},
            "klaviyo": {"apiKey": "fake_key"},
            "segment": {"apiKey": "fake_key"},
            "activecampaign": {"apiUrl": "https://account.api-us1.com", "apiKey": "fake_token"},
        }
        for service, cred in test_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None, f"Provider {service} missing"
            with pytest.raises(ValueError):
                await prov.validate_credentials(cred, client)

if __name__ == "__main__":
    test_registry_has_all_127_providers()
    test_api_providers_listing_next_16()
    test_api_actions_listing_next_16()
    print("All assertions for next 16 providers passed successfully!")

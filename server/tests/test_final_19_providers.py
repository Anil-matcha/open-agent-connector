"""
Acceptance & Contract Tests for the Final 19 Providers:
Productivity, Collaboration & Work Management (8):
1. Toggl Track (toggl, 24 actions)
2. Capsule CRM (capsule_crm, 25 actions)
3. ClickMeeting (clickmeeting, 19 actions)
4. Nozbe Teams (nozbe_teams, 16 actions)
5. Quipteams (quipteams, 11 actions)
6. KoboToolbox (kobotoolbox, 11 actions)
7. Dropbox Sign (dropbox_sign, 5 actions)
8. Systeme.io (systeme_io, 24 actions)

Headless CMS & Content Infrastructure (3):
9. Contentful (contentful, 8 actions)
10. Storyblok (storyblok, 7 actions)
11. Sanity (sanity, 3 actions)

Smart Home, Geospatial, Networking & Workflow (8):
12. Home Assistant (home_assistant, 28 actions)
13. HomeBox (homebox, 18 actions)
14. ipdata.co (ipdata_co, 30 actions)
15. IPinfo (ipinfo_io, 27 actions)
16. Mapbox (mapbox, 5 actions)
17. Cloudflare DNS (cloudflare_dns, 8 actions)
18. Make (make, 9 actions)
19. Pipedream (pipedream, 6 actions)

Total: 19 Providers, 284 Actions.
Registry Combined Total: 236 Providers, 8,024 Actions.
100% of open-connector catalog is now implemented in ConnectorHub!
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

FINAL_19_PROVIDERS = [
    # PM & Productivity
    ("toggl", 24, ["api_key"], "Project Management"),
    ("capsule_crm", 25, ["api_key"], "Project Management"),
    ("clickmeeting", 19, ["api_key"], "Project Management"),
    ("nozbe_teams", 16, ["api_key"], "Project Management"),
    ("quipteams", 11, ["api_key"], "Project Management"),
    ("kobotoolbox", 11, ["api_key"], "Project Management"),
    ("dropbox_sign", 5, ["api_key", "oauth2"], "Project Management"),
    ("systeme_io", 24, ["api_key"], "Project Management"),

    # Media & CMS
    ("contentful", 8, ["api_key"], "Media & Content"),
    ("storyblok", 7, ["api_key"], "Media & Content"),
    ("sanity", 3, ["api_key"], "Media & Content"),

    # Utility & Geospatial
    ("home_assistant", 28, ["api_key"], "Utilities & Tools"),
    ("homebox", 18, ["api_key"], "Utilities & Tools"),
    ("ipdata_co", 30, ["api_key"], "Utilities & Tools"),
    ("ipinfo_io", 27, ["api_key"], "Utilities & Tools"),
    ("mapbox", 5, ["api_key"], "Utilities & Tools"),

    # Developer & Workflow
    ("cloudflare_dns", 8, ["api_key", "oauth2"], "Developer Tools"),
    ("make", 9, ["api_key"], "Developer Tools"),
    ("pipedream", 6, ["api_key"], "Developer Tools"),
]

def test_registry_has_all_236_providers():
    assert len(registry.list_providers()) >= 236
    assert len(registry.list_actions()) >= 8024

    for service, expected_count, expected_auth, expected_cat in FINAL_19_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_final_19():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in FINAL_19_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_final_19():
    client = TestClient(app)
    for service, expected_count, _, _ in FINAL_19_PROVIDERS:
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
async def test_live_credential_validation_rejection_for_final_19():
    dummy_creds = {
        "toggl": {"apiKey": "fake_token"},
        "capsule_crm": {"apiKey": "fake_token"},
        "clickmeeting": {"apiKey": "fake_token"},
        "nozbe_teams": {"apiKey": "fake_token"},
        "quipteams": {"apiKey": "fake_token"},
        "kobotoolbox": {"apiKey": "fake_token", "baseUrl": "https://kf.kobotoolbox.org"},
        "dropbox_sign": {"apiKey": "fake_token"},
        "systeme_io": {"apiKey": "fake_token"},
        "contentful": {"apiKey": "fake_token"},
        "storyblok": {"apiKey": "fake_token"},
        "sanity": {"apiKey": "fake_token", "projectId": "fake-project"},
        "home_assistant": {"apiKey": "fake_token", "baseUrl": "https://ha.example.com"},
        "homebox": {"apiKey": "fake_token", "baseUrl": "https://homebox.example.com"},
        "ipdata_co": {"apiKey": "fake_token"},
        "ipinfo_io": {"apiKey": "fake_token"},
        "mapbox": {"apiKey": "fake_token"},
        "cloudflare_dns": {"apiKey": "fake_token"},
        "make": {"apiKey": "fake_token", "zoneUrl": "https://eu1.make.com"},
        "pipedream": {"apiKey": "fake_token"},
    }

    async with httpx.AsyncClient() as client:
        for service, cred in dummy_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None, f"Provider {service} missing"
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

"""
Acceptance & Contract Tests for 15 Developer Infrastructure & Workflow Providers:
1. App Store Connect (app_store_connect, 653 actions)
2. Dokploy (dokploy, 524 actions)
3. Gitea (gitea, 93 actions)
4. Keygen (keygen, 76 actions)
5. ZeroTier (zerotier, 68 actions)
6. Doppler (doppler, 44 actions)
7. Pi-hole (pi_hole, 40 actions)
8. Oracle Cloud Infrastructure (oracle_cloud, 34 actions)
9. ReadMe (readme, 33 actions)
10. Google BigQuery (google_bigquery, 32 actions)
11. App Store Server API (app_store_server, 30 actions)
12. n8n (n8n, 36 actions)
13. Sunsama MCP (sunsama_mcp, 59 actions)
14. Karakeep (karakeep, 55 actions)
15. Mingdao (mingdao, 47 actions)

Total: 15 Providers, 1,792 Actions.
Registry Combined Total: 142 Providers, 4,797 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEXT_15_PROVIDERS = [
    ("app_store_connect", 653, ["custom_credential", "api_key"], "Developer Tools"),
    ("dokploy", 524, ["api_key"], "Developer Tools"),
    ("gitea", 93, ["api_key"], "Developer Tools"),
    ("keygen", 76, ["api_key"], "Developer Tools"),
    ("zerotier", 68, ["api_key", "custom_credential"], "Developer Tools"),
    ("doppler", 44, ["api_key"], "Developer Tools"),
    ("pi_hole", 40, ["api_key"], "Developer Tools"),
    ("oracle_cloud", 34, ["custom_credential", "api_key"], "Developer Tools"),
    ("readme", 33, ["api_key"], "Developer Tools"),
    ("google_bigquery", 32, ["oauth2", "custom_credential"], "Developer Tools"),
    ("app_store_server", 30, ["custom_credential"], "Developer Tools"),
    ("n8n", 36, ["api_key"], "Project Management"),
    ("sunsama_mcp", 59, ["oauth2", "api_key"], "Project Management"),
    ("karakeep", 55, ["api_key"], "Project Management"),
    ("mingdao", 47, ["api_key", "custom_credential"], "Project Management"),
]

def test_registry_has_all_142_providers():
    assert len(registry.list_providers()) == 142
    assert len(registry.list_actions()) == 4797

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
        assert len(actions) == expected_count, f"Actions for {service} mismatch"
        for a in actions:
            assert "inputSchema" in a
            assert "outputSchema" in a
            assert "id" in a and a["id"].startswith(f"{service}.")

@pytest.mark.anyio
async def test_credential_validation_error_handling_next_15():
    async with httpx.AsyncClient() as client:
        test_creds = {
            "app_store_connect": {"apiKey": "fake_token"},
            "dokploy": {"apiKey": "fake_token", "instanceUrl": "https://example.com"},
            "gitea": {"apiKey": "fake_token", "instanceUrl": "https://example.com"},
            "keygen": {"apiKey": "fake_token"},
            "zerotier": {"token": "fake_token"},
            "doppler": {"apiKey": "fake_token"},
            "pi_hole": {"apiKey": "fake_token", "instanceUrl": "https://example.com"},
            "oracle_cloud": {"apiKey": "fake_token", "region": "us-ashburn-1"},
            "readme": {"apiKey": "fake_token"},
            "google_bigquery": {"accessToken": "fake_token"},
            "app_store_server": {"apiKey": "fake_token"},
            "n8n": {"apiKey": "fake_token", "instanceUrl": "https://example.com"},
            "sunsama_mcp": {"accessToken": "fake_token"},
            "karakeep": {"apiKey": "fake_token"},
            "mingdao": {"apiKey": "fake_token"},
        }
        for service, cred in test_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None
            with pytest.raises(Exception):
                await prov.validate_credentials(cred, client)

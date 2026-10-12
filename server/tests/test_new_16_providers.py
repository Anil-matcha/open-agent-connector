"""
Verification and Acceptance Test for the 16 New Providers:
Productivity, Scheduling & Collaboration:
1. Cal.com (cal, 47 actions)
2. Trello (trello, 28 actions)
3. Todoist (todoist, 19 actions)
4. Close (close, 16 actions)
5. PandaDoc (pandadoc, 13 actions)
6. Wrike (wrike, 7 actions)
7. Salesloft (salesloft, 7 actions)
8. Gong (gong, 6 actions)
9. Smartsheet (smartsheet, 5 actions)

Identity, HR & Forms:
10. Okta (okta, 14 actions)
11. SurveyMonkey (survey_monkey, 14 actions)
12. Workday (workday, 7 actions)
13. Typeform (typeform, 6 actions)
14. Rippling (rippling, 4 actions)
15. BambooHR (bamboohr, 4 actions)
16. Tally (tally, 4 actions)

Total: 16 Providers, 201 Actions.
Combined Hub Total: 111 Providers, 2,715 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEW_16_PROVIDERS = [
    ("cal", 47, ["oauth2", "api_key"], "Project Management"),
    ("trello", 28, ["custom_credential"], "Project Management"),
    ("todoist", 19, ["oauth2", "api_key"], "Project Management"),
    ("close", 16, ["api_key"], "CRM & Sales"),
    ("pandadoc", 13, ["api_key"], "Project Management"),
    ("wrike", 7, ["api_key"], "Project Management"),
    ("salesloft", 7, ["api_key"], "CRM & Sales"),
    ("gong", 6, ["custom_credential"], "CRM & Sales"),
    ("smartsheet", 5, ["api_key"], "Project Management"),
    ("okta", 14, ["custom_credential"], "Identity & Security"),
    ("survey_monkey", 14, ["oauth2", "api_key"], "Forms & Surveys"),
    ("workday", 7, ["oauth2"], "HR & Enterprise"),
    ("typeform", 6, ["oauth2", "api_key"], "Forms & Surveys"),
    ("rippling", 4, ["api_key"], "HR & Workforce"),
    ("bamboohr", 4, ["custom_credential"], "HR & People"),
    ("tally", 4, ["api_key"], "Forms & Surveys"),
]

def test_registry_has_all_111_providers_and_16_new():
    assert len(registry.list_providers()) == 111
    assert len(registry.list_actions()) == 2715

    for service, expected_count, expected_auth, expected_cat in NEW_16_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_count, f"Provider {service} action count mismatch: {len(prov.actions)} vs {expected_count}"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing_16():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEW_16_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing_16():
    client = TestClient(app)
    for service, expected_count, _, _ in NEW_16_PROVIDERS:
        resp = client.get(f"/v1/actions?service={service}")
        assert resp.status_code == 200
        actions = resp.json().get("data", [])
        assert len(actions) == expected_count, f"Actions for {service} mismatch"
        for a in actions:
            assert "inputSchema" in a
            assert "outputSchema" in a
            assert "id" in a and a["id"].startswith(f"{service}.")

@pytest.mark.anyio
async def test_credential_validation_error_handling_16():
    async with httpx.AsyncClient() as client:
        test_creds = {
            "cal": {"apiKey": "cal_live_fake"},
            "trello": {"apiKey": "fake_key", "token": "fake_token"},
            "todoist": {"accessToken": "fake_token"},
            "close": {"apiKey": "api_fake"},
            "pandadoc": {"apiKey": "fake_token"},
            "wrike": {"apiKey": "fake_token"},
            "salesloft": {"apiKey": "fake_token"},
            "gong": {"accessKey": "fake_key", "accessKeySecret": "fake_secret"},
            "smartsheet": {"apiKey": "fake_token"},
            "okta": {"domain": "trial.okta.com", "apiToken": "fake_token"},
            "survey_monkey": {"accessToken": "fake_token"},
            "workday": {"host": "wd2-impl.workday.com", "tenant": "mytenant", "accessToken": "fake_token"},
            "typeform": {"accessToken": "fake_token"},
            "rippling": {"apiKey": "fake_token"},
            "bamboohr": {"subdomain": "mycompany", "apiKey": "fake_key"},
            "tally": {"apiKey": "fake_token"},
        }
        for service, cred in test_creds.items():
            prov = registry.get_provider(service)
            assert prov is not None
            with pytest.raises(ValueError):
                await prov.validate_credentials(cred, client)

if __name__ == "__main__":
    test_registry_has_all_111_providers_and_16_new()
    test_api_providers_listing_16()
    test_api_actions_listing_16()
    print("All 16 providers verification tests passed successfully!")

"""
Verification and Acceptance Test for:
1. QuickBooks Online (147 actions)
2. WooCommerce (26 actions)
3. Xero (15 actions)
4. Mailtrap (50 actions)
5. Webex (40 actions)
6. Resend (12 actions)
7. Postmark (12 actions)
8. Twilio (8 actions)
9. Zoom (4 actions)
10. SendGrid (4 actions)
Total: 10 Providers, 318 Actions.
"""
import pytest
import httpx
from fastapi.testclient import TestClient

from app.providers.registry import registry
from main import app

NEW_PROVIDERS = [
    ("quickbooks", 147, ["oauth2"], "Accounting & Finance"),
    ("woocommerce", 26, ["custom_credential"], "Ecommerce"),
    ("xero", 15, ["oauth2"], "Accounting & Finance"),
    ("mailtrap", 50, ["api_key"], "Communication"),
    ("webex", 40, ["oauth2"], "Communication"),
    ("resend", 12, ["api_key"], "Communication"),
    ("postmark", 12, ["api_key"], "Communication"),
    ("twilio", 8, ["custom_credential"], "Communication"),
    ("zoom", 4, ["oauth2"], "Communication"),
    ("sendgrid", 4, ["api_key"], "Communication")
]

def test_registry_has_all_10_providers():
    assert len(registry.list_providers()) == 95
    assert len(registry.list_actions()) == 2514

    for service, expected_action_count, expected_auth, expected_cat in NEW_PROVIDERS:
        prov = registry.get_provider(service)
        assert prov is not None, f"Provider {service} not found in registry"
        assert len(prov.actions) == expected_action_count, f"Provider {service} action count mismatch"
        assert prov.auth_types == expected_auth, f"Provider {service} auth mismatch"
        assert prov.category == expected_cat, f"Provider {service} category mismatch"

def test_api_providers_listing():
    client = TestClient(app)
    resp = client.get("/v1/providers")
    assert resp.status_code == 200
    providers = resp.json().get("data", [])
    service_map = {p["service"]: p for p in providers}

    for service, expected_count, _, _ in NEW_PROVIDERS:
        assert service in service_map, f"Provider {service} missing from /v1/providers"
        assert service_map[service]["actionCount"] == expected_count

def test_api_actions_listing():
    client = TestClient(app)
    for service, expected_count, _, _ in NEW_PROVIDERS:
        resp = client.get(f"/v1/actions?service={service}")
        assert resp.status_code == 200
        actions = resp.json().get("data", [])
        assert len(actions) == expected_count, f"Actions for {service} mismatch"
        for a in actions:
            assert "inputSchema" in a
            assert "outputSchema" in a
            assert "id" in a and a["id"].startswith(f"{service}.")

@pytest.mark.anyio
async def test_credential_validation_error_handling():
    async with httpx.AsyncClient() as client:
        test_creds = {
            "quickbooks": {"accessToken": "fake_token", "realmId": "123456789"},
            "xero": {"accessToken": "fake_token"},
            "mailtrap": {"apiKey": "fake_key"},
            "webex": {"accessToken": "fake_token"},
            "resend": {"apiKey": "re_fake_key"},
            "postmark": {"apiKey": "fake_token"},
            "twilio": {"accountSid": "AC_TEST_MOCK_ACCOUNT_SID", "authToken": "fake_token"},
            "zoom": {"accessToken": "fake_token"},
            "sendgrid": {"apiKey": "SG.fake_key"}
        }
        for service, cred in test_creds.items():
            prov = registry.get_provider(service)
            with pytest.raises(ValueError):
                await prov.validate_credentials(cred, client)

if __name__ == "__main__":
    test_registry_has_all_10_providers()
    test_api_providers_listing()
    test_api_actions_listing()
    print("All assertions passed!")

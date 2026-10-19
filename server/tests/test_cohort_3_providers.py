import pytest
import httpx
from app.providers.registry import registry
from app.services.oauth_service import OAUTH_PROVIDERS

EXPECTED_COHORT_3 = [
    ("instagram", 9, ["oauth2"], "Marketing"),
    ("netlify", 20, ["oauth2", "api_key"], "Developer Tools"),
    ("ticktick", 21, ["oauth2", "api_key"], "Productivity"),
    ("googleslides", 7, ["oauth2", "api_key"], "Productivity"),
    ("google_search_console", 10, ["oauth2", "api_key"], "Marketing"),
    ("harvest", 15, ["oauth2", "api_key"], "Productivity"),
    ("confluence", 5, ["oauth2", "api_key"], "Productivity"),
]

@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_COHORT_3)
def test_cohort_3_provider_registration(service, action_count, auth_types, category):
    provider = registry.get_provider(service)
    assert provider is not None, f"Provider '{service}' is not registered in registry"
    assert provider.service == service
    assert len(provider.actions) == action_count, f"{service} expected {action_count} actions, got {len(provider.actions)}"
    assert provider.category == category
    assert provider.auth_types == auth_types

    # Validate action attributes
    for action_id, action in provider.actions.items():
        assert action.id.startswith(f"{service}."), f"Action ID '{action.id}' does not start with prefix '{service}.'"
        assert action.name, f"Action '{action_id}' missing name"
        assert action.description, f"Action '{action_id}' missing description"
        assert isinstance(action.input_schema, dict), f"Action '{action_id}' input_schema not dict"
        assert isinstance(action.output_schema, dict), f"Action '{action_id}' output_schema not dict"
        d = action.to_dict()
        assert d["id"] == action.id
        assert d["name"] == action.name

@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_COHORT_3)
def test_cohort_3_oauth_registration(service, action_count, auth_types, category):
    if "oauth2" in auth_types:
        assert service in OAUTH_PROVIDERS, f"{service} missing from OAUTH_PROVIDERS"
        cfg = OAUTH_PROVIDERS[service]
        assert "authorize_url" in cfg and cfg["authorize_url"].startswith("https://")
        assert "token_url" in cfg and cfg["token_url"].startswith("https://")
        assert "default_scopes" in cfg and isinstance(cfg["default_scopes"], list)

@pytest.mark.asyncio
@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_COHORT_3)
async def test_cohort_3_provider_live_validation_rejects_bad_token(service, action_count, auth_types, category):
    provider = registry.get_provider(service)
    assert provider is not None

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Should raise ValueError when validating with bad credentials
        with pytest.raises(ValueError) as excinfo:
            await provider.validate_credentials({"apiKey": "invalid_bogus_token_12345", "accessToken": "invalid_bogus_token_12345"}, client)
        assert len(str(excinfo.value)) > 0

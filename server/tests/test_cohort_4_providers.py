import pytest
import httpx
from app.providers.registry import registry

EXPECTED_COHORT_4 = [
    ("clockify", 12, ["api_key"], "Productivity"),
    ("shortcut", 15, ["api_key"], "Productivity"),
    ("hunter", 18, ["api_key"], "Marketing"),
    ("google_maps", 8, ["api_key"], "Developer Tools"),
    ("openweather_api", 21, ["api_key"], "Data & Analytics"),
]

@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_COHORT_4)
def test_cohort_4_provider_registration(service, action_count, auth_types, category):
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

@pytest.mark.asyncio
@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_COHORT_4)
async def test_cohort_4_provider_live_validation_rejects_bad_token(service, action_count, auth_types, category):
    provider = registry.get_provider(service)
    assert provider is not None

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Should raise ValueError when validating with bad credentials
        with pytest.raises(ValueError) as excinfo:
            await provider.validate_credentials({"apiKey": "invalid_bogus_token_12345", "accessToken": "invalid_bogus_token_12345"}, client)
        assert len(str(excinfo.value)) > 0

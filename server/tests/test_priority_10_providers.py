import pytest
import httpx
from app.providers.registry import registry

EXPECTED_APPS = [
    ("canva", 13, ["oauth2"], "Design & Media"),
    ("miro", 12, ["oauth2"], "Productivity"),
    ("mailerlite", 13, ["api_key"], "Marketing"),
    ("getresponse", 14, ["api_key"], "Marketing"),
    ("jotform", 7, ["api_key"], "Productivity"),
    ("bitly", 6, ["api_key"], "Utilities & Tools"),
    ("braze", 4, ["api_key"], "Marketing"),
    ("hotjar", 4, ["api_key"], "Analytics"),
    ("nasa", 27, ["api_key"], "Utilities & Tools"),
    ("tiktok_business", 15, ["oauth2", "api_key"], "Marketing"),
]

@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_APPS)
def test_provider_registration(service, action_count, auth_types, category):
    provider = registry.get_provider(service)
    assert provider is not None, f"Provider '{service}' is not registered in registry"
    assert provider.service == service
    assert len(provider.actions) == action_count, f"{service} expected {action_count} actions, got {len(provider.actions)}"
    assert provider.category == category

@pytest.mark.asyncio
@pytest.mark.parametrize("service,action_count,auth_types,category", EXPECTED_APPS)
async def test_provider_live_validation_rejects_bad_token(service, action_count, auth_types, category):
    provider = registry.get_provider(service)
    assert provider is not None

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Should raise ValueError when validating with bad credentials
        with pytest.raises(ValueError) as excinfo:
            await provider.validate_credentials({"apiKey": "invalid_bogus_token_12345"}, client)
        assert len(str(excinfo.value)) > 0

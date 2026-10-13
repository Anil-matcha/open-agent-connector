"""The OAuth redirect URI must follow CONNECTOR_PUBLIC_ORIGIN, not a hardcoded localhost."""
from urllib.parse import urlparse, parse_qs

import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.services.oauth_service import OAuthService

ADMIN = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_callback_url_uses_public_origin(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", "https://connector.example.com/")
    assert OAuthService.callback_url("gmail") == \
        "https://connector.example.com/api/oauth/gmail/callback"


def test_authorize_url_redirect_uri_follows_origin(client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", "https://connector.example.com")
    saved = client.post("/api/oauth/github/config", headers=ADMIN,
                        json={"clientId": "test-id", "clientSecret": "test-secret"})
    assert saved.status_code == 200
    res = client.get("/api/oauth/github/authorize", headers=ADMIN)
    assert res.status_code == 200, res.text
    url = res.json()["data"]["authorization_url"]
    assert url, res.json()
    redirect = parse_qs(urlparse(url).query)["redirect_uri"][0]
    assert redirect == "https://connector.example.com/api/oauth/github/callback"


def test_no_hardcoded_localhost_in_oauth_service():
    import inspect
    import app.services.oauth_service as mod
    assert "localhost" not in inspect.getsource(mod)

"""Comprehensive tests for Hosted OAuth Support on connector.suparagent.ai."""
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


def test_hosted_domain_defaults():
    assert "connector.suparagent.ai" in settings.PUBLIC_ORIGIN or "connector.suparagent.ai" in settings.HOSTED_DOMAIN


def test_hosted_vs_custom_oauth_configuration(client):
    # 1. Save hosted credentials for github
    res_hosted = client.post(
        "/api/oauth/github/config?mode=hosted",
        headers=ADMIN,
        json={"clientId": "hosted-gh-client-id", "clientSecret": "hosted-gh-client-secret"}
    )
    assert res_hosted.status_code == 200
    assert res_hosted.json()["mode"] == "hosted"

    # 2. Check config status
    status = client.get("/api/oauth/github/config", headers=ADMIN).json()
    assert status["success"] is True
    assert status["hostedAvailable"] is True
    assert status["configured"] is True
    assert status["hostedDomain"] == "connector.suparagent.ai"

    # 3. Authorize with mode=hosted
    auth_hosted = client.get("/api/oauth/github/authorize?mode=hosted", headers=ADMIN).json()
    assert auth_hosted["success"] is True
    url_hosted = auth_hosted["data"]["authorization_url"]
    parsed_hosted = parse_qs(urlparse(url_hosted).query)
    assert parsed_hosted["client_id"][0] == "hosted-gh-client-id"

    # 4. Save custom credentials for github
    res_custom = client.post(
        "/api/oauth/github/config?mode=custom",
        headers=ADMIN,
        json={"clientId": "custom-gh-client-id", "clientSecret": "custom-gh-client-secret"}
    )
    assert res_custom.status_code == 200
    assert res_custom.json()["mode"] == "custom"

    # 5. Check config status again - both should be available
    status2 = client.get("/api/oauth/github/config", headers=ADMIN).json()
    assert status2["hostedAvailable"] is True
    assert status2["customConfigured"] is True

    # 6. Authorize with mode=custom explicitly
    auth_custom = client.get("/api/oauth/github/authorize?mode=custom", headers=ADMIN).json()
    assert auth_custom["success"] is True
    url_custom = auth_custom["data"]["authorization_url"]
    parsed_custom = parse_qs(urlparse(url_custom).query)
    assert parsed_custom["client_id"][0] == "custom-gh-client-id"


def test_hosted_redirect_uri_matches_public_origin(client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", "https://connector.suparagent.ai")
    assert OAuthService.callback_url("slack") == "https://connector.suparagent.ai/api/oauth/slack/callback"
    assert OAuthService.callback_url("github") == "https://connector.suparagent.ai/api/oauth/github/callback"
    assert OAuthService.callback_url("gmail") == "https://connector.suparagent.ai/api/oauth/gmail/callback"

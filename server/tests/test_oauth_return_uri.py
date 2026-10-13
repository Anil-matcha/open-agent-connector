"""The OAuth callback must never redirect anywhere the flow's starter did not (validly) choose."""
import pytest
from urllib.parse import parse_qs, urlparse
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.core.redirects import validate_return_uri

ORIGIN = "https://connector.example.com"
ADMIN = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}


@pytest.fixture(autouse=True)
def fixed_origin(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setattr(settings, "ALLOWED_RETURN_ORIGINS", "http://localhost:3000, https://app.partner.example:8443")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/oauth/github/config", headers=ADMIN, json={"clientId": "id", "clientSecret": "secret"})
        yield c


# --- validator --------------------------------------------------------------

@pytest.mark.parametrize("uri", [
    f"{ORIGIN}/connections",
    f"{ORIGIN}/connections?tab=oauth#x",
    "http://localhost:3000/connections",
    "https://app.partner.example:8443/done",
    f"{ORIGIN.upper().replace('HTTPS', 'https')}/x",
])
def test_allowed_return_urls(uri):
    assert validate_return_uri(uri) == uri.strip()


@pytest.mark.parametrize("uri", [
    "https://evil.example/",
    f"{ORIGIN}.evil.example/",
    f"https://evil.example/{ORIGIN}",
    "https://evil.example@connector.example.com/",
    "https://connector.example.com@evil.example/",
    f"{ORIGIN}:8443/",
    "http://connector.example.com/",
    "https://app.partner.example/",
    "//evil.example/path",
    "/connections",
    "javascript:alert(1)",
    "data:text/html,hi",
    f"{ORIGIN}\\@evil.example/",
    f"{ORIGIN}/a b",
    f"{ORIGIN}/\r\nLocation: https://evil.example",
    "not a url",
])
def test_rejected_return_urls(uri):
    with pytest.raises(ValueError):
        validate_return_uri(uri)


def test_empty_return_url_is_none():
    assert validate_return_uri(None) is None and validate_return_uri("  ") is None


# --- authorize --------------------------------------------------------------

def test_authorize_rejects_foreign_return_url(client):
    res = client.get("/api/oauth/github/authorize", headers=ADMIN,
                     params={"redirectUri": "https://evil.example/steal", "mode": "custom"})
    assert res.status_code == 400


def test_authorize_accepts_own_origin(client):
    res = client.get("/api/oauth/github/authorize", headers=ADMIN,
                     params={"redirectUri": f"{ORIGIN}/connections", "mode": "custom"})
    assert res.status_code == 200, res.text


# --- callback ---------------------------------------------------------------

def test_callback_ignores_return_uri_query_parameter(client):
    """The original open redirect: a crafted link with an attacker-controlled returnUri."""
    res = client.get(
        "/api/oauth/github/callback",
        params={"code": "x", "state": "does-not-exist", "returnUri": "https://evil.example/phish"},
        follow_redirects=False,
    )
    assert res.status_code == 400
    assert "location" not in {k.lower() for k in res.headers}


def test_callback_redirects_only_to_stored_return_url(client, monkeypatch):
    from app.providers.registry import registry
    import app.services.oauth_service as oauth_module

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"access_token": "tok", "token_type": "bearer"}

    async def fake_request(*a, **k):
        return FakeResponse()

    async def fake_validate(credential, http_client):
        return {"account_id": "acct", "display_name": "Fake", "granted_scopes": []}

    monkeypatch.setattr(oauth_module, "execute_guarded_request", fake_request)
    monkeypatch.setattr(registry.get_provider("github"), "validate_credentials", fake_validate)

    auth = client.get("/api/oauth/github/authorize", headers=ADMIN, params={
        "redirectUri": f"{ORIGIN}/connections", "connectionName": "ret&evil=1", "mode": "custom"})
    state = auth.json()["data"]["state"]

    res = client.get("/api/oauth/github/callback",
                     params={"code": "c", "state": state, "returnUri": "https://evil.example/x"},
                     follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert location.startswith(f"{ORIGIN}/connections?")
    query = parse_qs(urlparse(location).query)
    assert query["status"] == ["connected"] and query["service"] == ["github"]
    assert query["connectionName"] == ["ret&evil=1"]  # encoded, so it cannot inject parameters
    assert "evil.example" not in location


def test_callback_error_redirects_to_stored_return_url(client, monkeypatch):
    import app.services.oauth_service as oauth_module

    class Rejected:
        status_code = 400
        text = "bad_verification_code"

        def json(self):
            return {}

    async def fake_request(*a, **k):
        return Rejected()

    monkeypatch.setattr(oauth_module, "execute_guarded_request", fake_request)
    auth = client.get("/api/oauth/github/authorize", headers=ADMIN,
                      params={"redirectUri": f"{ORIGIN}/connections", "mode": "custom"})
    state = auth.json()["data"]["state"]
    res = client.get("/api/oauth/github/callback", params={"code": "c", "state": state},
                     follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"].startswith(f"{ORIGIN}/connections?status=error")


def test_flow_without_return_url_returns_json(client, monkeypatch):
    import app.services.oauth_service as oauth_module

    class Rejected:
        status_code = 400
        text = "bad_verification_code"

        def json(self):
            return {}

    async def fake_request(*a, **k):
        return Rejected()

    monkeypatch.setattr(oauth_module, "execute_guarded_request", fake_request)
    auth = client.get("/api/oauth/github/authorize", headers=ADMIN, params={"mode": "custom"})
    state = auth.json()["data"]["state"]
    res = client.get("/api/oauth/github/callback", params={"code": "c", "state": state},
                     follow_redirects=False)
    assert res.status_code in (400, 500) and "location" not in {k.lower() for k in res.headers}


def test_callback_rechecks_stored_return_url(client, monkeypatch):
    """A stored URL that is no longer allowed (allowlist tightened, row tampered) is never followed."""
    import sqlite3
    import uuid
    import app.services.oauth_service as oauth_module

    class Rejected:
        status_code = 400
        text = "bad_verification_code"

        def json(self):
            return {}

    async def fake_request(*a, **k):
        return Rejected()

    monkeypatch.setattr(oauth_module, "execute_guarded_request", fake_request)
    state = f"planted-{uuid.uuid4().hex}"
    path = settings.DATABASE_URL.split("///", 1)[1]
    db = sqlite3.connect(path)
    db.execute(
        "INSERT INTO oauth_states (state, tenant_id, service, connection_name, auth_mode, return_uri, created_at, expires_at) "
        "VALUES (?, 'default', 'github', 'default', 'custom', 'https://evil.example/x', '2026-01-01T00:00:00Z', '2999-01-01T00:00:00Z')",
        (state,),
    )
    db.commit()
    db.close()
    res = client.get("/api/oauth/github/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert res.status_code in (400, 500)
    assert "location" not in {k.lower() for k in res.headers}

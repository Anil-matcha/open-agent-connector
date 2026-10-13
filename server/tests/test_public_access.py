import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs startup so the schema exists and is migrated
        yield c


admin_headers = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}


@pytest.fixture(autouse=True)
def sandbox_enabled(monkeypatch):
    """These tests exercise the public sandbox, which is off by default."""
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ACCESS", True)


def test_public_access_to_connections_and_providers(client):
    """Verify unauthenticated public visitors can list connections and oauth configs."""
    # 1. GET /api/connections without any token
    res = client.get("/api/connections")
    assert res.status_code == 200
    assert "data" in res.json()

    # 2. GET /api/oauth/providers without token
    res_oauth = client.get("/api/oauth/providers")
    assert res_oauth.status_code == 200
    assert "data" in res_oauth.json()

    # 3. GET /api/oauth/github/config without token
    res_gh = client.get("/api/oauth/github/config")
    assert res_gh.status_code == 200
    assert res_gh.json()["service"] == "github"


def test_public_access_to_tokens(client):
    """Verify unauthenticated public visitors can list and create runtime tokens."""
    # List tokens
    res = client.get("/api/runtime-tokens")
    assert res.status_code == 200

    # Create token
    create_payload = {
        "name": "Public Agent Token",
        "allowedActions": ["*"],
        "allowedConnections": ["default"],
        "allowedProxies": []
    }
    res_create = client.post("/api/runtime-tokens", json=create_payload)
    assert res_create.status_code == 200
    token_id = res_create.json()["data"]["id"]

    # Delete token
    res_del = client.delete(f"/api/runtime-tokens/{token_id}")
    assert res_del.status_code == 200


def test_hosted_oauth_config_requires_master_admin(client):
    """Verify public users cannot overwrite server-wide hosted oauth credentials, but admin can."""
    # 1. Unauthenticated / public attempt to set hosted OAuth config -> 403 Forbidden
    payload = {
        "clientId": "test_public_client_id",
        "clientSecret": "test_public_secret",
        "mode": "hosted"
    }
    res_unauth = client.post("/api/oauth/github/config?mode=hosted", json=payload)
    assert res_unauth.status_code == 403
    assert "master admin" in res_unauth.json()["detail"].lower()

    # 2. Authenticated admin can configure hosted OAuth
    res_admin = client.post("/api/oauth/github/config?mode=hosted", json=payload, headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["mode"] == "hosted"


def test_mcp_still_requires_authentication(client):
    """Ensure MCP protocol fails closed for unauthenticated requests even with public web access."""
    res = client.get("/mcp/tools")
    assert res.status_code == 401


def test_public_access_is_off_by_default():
    """A fresh install with no configuration must not hand out a working anonymous sandbox."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {k: v for k, v in os.environ.items() if "ALLOW_PUBLIC_ACCESS" not in k}
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
    out = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; print(settings.ALLOW_PUBLIC_ACCESS)"],
        env=env, cwd=env["PYTHONPATH"], capture_output=True, text=True, timeout=60,
    )
    assert out.stdout.strip().splitlines()[-1] == "False", out.stdout + out.stderr


def test_anonymous_requests_are_rejected_when_the_sandbox_is_off(client, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ACCESS", False)
    assert client.get("/api/connections").status_code == 401
    assert client.get("/api/runs").status_code == 401
    assert client.get("/api/oauth/providers").status_code == 401
    assert client.post("/api/runtime-tokens", json={"name": "x"}).status_code == 401
    assert client.post("/v1/actions/github.get_current_user", json={"input": {}}).status_code == 401
    assert client.get("/api/connections", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    # the operator token still works, and the status route tells the console what is on offer
    assert client.get("/api/connections", headers=admin_headers).status_code == 200
    assert client.get("/api/auth/status").json()["allowPublicAccess"] is False

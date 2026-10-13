"""
Tenant isolation contract.

Two hosted tenants (A, B), the self-hosted operator ("default") and anonymous
public visitors each try to reach the others' data through every route family.
Principals for tenants A and B come from a registered resolver, exactly how a
hosted layer plugs in. Rows are seeded straight into SQLite so no provider or
network is needed.
"""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.auth import Principal
from app.core.config import settings
from app.core.idempotency import compute_idempotency_scope_key
from app.core.security import encrypt_secret
from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    PUBLIC_TENANT_ID,
    register_principal_resolver,
    unregister_principal_resolver,
)

RUN = uuid.uuid4().hex[:8]
TENANT_A = f"tenant-a-{RUN}"
TENANT_B = f"tenant-b-{RUN}"
TOKENS = {
    f"admin-a-{RUN}": ("tenant_admin", TENANT_A),
    f"admin-b-{RUN}": ("tenant_admin", TENANT_B),
    f"agent-a-{RUN}": ("runtime", TENANT_A),
    f"agent-b-{RUN}": ("runtime", TENANT_B),
}
A_ADMIN = {"Authorization": f"Bearer admin-a-{RUN}"}
B_ADMIN = {"Authorization": f"Bearer admin-b-{RUN}"}
A_AGENT = {"Authorization": f"Bearer agent-a-{RUN}"}
OPERATOR = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}
ANON = {}

CONN_A = f"conn-a-{RUN}"
CONN_B = None  # set after seeding (UUID shaped ids are required for id lookups)


def _db():
    path = settings.DATABASE_URL.split("///", 1)[1]
    return sqlite3.connect(path)


async def _test_resolver(raw_token, db):
    entry = TOKENS.get(raw_token)
    if not entry:
        return None
    kind, tenant = entry
    return Principal(
        kind=kind,
        id=f"{kind}-{tenant}",
        name=f"test {kind} {tenant}",
        allowed_actions=["*"] if kind == "runtime" else None,
        tenant_id=tenant,
    )


def _seed_connection(tenant, secret, service="github", name="default"):
    conn_id = str(uuid.uuid4())
    c = _db()
    c.execute(
        "INSERT INTO connections (id, tenant_id, service, connection_name, auth_type, encrypted_value, status) "
        "VALUES (?, ?, ?, ?, 'api_key', ?, 'active')",
        (conn_id, tenant, service, name, encrypt_secret(json.dumps({"apiKey": secret}))),
    )
    c.commit()
    c.close()
    return conn_id


def _seed_run(tenant):
    run_id = str(uuid.uuid4())
    c = _db()
    c.execute(
        "INSERT INTO runs (id, tenant_id, action_id, service, caller, ok, status_code, duration_ms) "
        "VALUES (?, ?, 'github.get_current_user', 'github', 'http', 1, 200, 1.0)",
        (run_id, tenant),
    )
    c.commit()
    c.close()
    return run_id


def _row(table, row_id):
    c = _db()
    row = c.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    c.close()
    return row


@pytest.fixture(scope="module")
def client():
    register_principal_resolver(_test_resolver)
    with TestClient(app) as c:
        yield c
    unregister_principal_resolver(_test_resolver)


@pytest.fixture(scope="module")
def seeded(client):
    return {
        "conn_a": _seed_connection(TENANT_A, "A-secret"),
        "conn_b": _seed_connection(TENANT_B, "B-secret"),  # same service + name as A: must coexist
        "conn_op": _seed_connection(DEFAULT_TENANT_ID, "OPERATOR-secret", name=f"op-{RUN}"),
        "conn_pub": _seed_connection(PUBLIC_TENANT_ID, "PUBLIC-secret", name=f"pub-{RUN}"),
        "run_a": _seed_run(TENANT_A),
        "run_b": _seed_run(TENANT_B),
    }


def _ids(response):
    return {c["id"] for c in response.json()["data"]}


# --- principals -----------------------------------------------------------

def test_principal_tenants(client):
    assert client.get("/api/auth/status").status_code == 200
    # Operator token is the default tenant, never a tenant admin.
    assert Principal(kind="admin", id="x", name="x").tenant_id == DEFAULT_TENANT_ID
    assert not Principal(kind="tenant_admin", id="x", name="x", tenant_id="t").is_admin
    assert Principal(kind="tenant_admin", id="x", name="x", tenant_id="t").is_tenant_owner


# --- connections ----------------------------------------------------------

def test_each_tenant_lists_only_its_own_connections(client, seeded):
    a = _ids(client.get("/api/connections", headers=A_ADMIN))
    b = _ids(client.get("/api/connections", headers=B_ADMIN))
    assert a == {seeded["conn_a"]}
    assert b == {seeded["conn_b"]}


def test_operator_and_public_do_not_see_tenant_data(client, seeded, monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_ACCESS", True)
    operator = _ids(client.get("/api/connections", headers=OPERATOR))
    public = _ids(client.get("/api/connections", headers=ANON))
    assert seeded["conn_a"] not in operator | public
    assert seeded["conn_b"] not in operator | public
    assert seeded["conn_op"] in operator and seeded["conn_op"] not in public
    assert seeded["conn_pub"] in public and seeded["conn_pub"] not in operator


def test_cannot_read_other_tenants_connection_by_id(client, seeded):
    assert client.get(f"/api/connections/{seeded['conn_b']}", headers=A_ADMIN).status_code == 404
    assert client.get(f"/api/connections/{seeded['conn_a']}", headers=B_ADMIN).status_code == 404
    assert client.get(f"/api/connections/{seeded['conn_a']}", headers=A_ADMIN).status_code == 200


def test_service_name_lookup_stays_inside_tenant(client, seeded):
    # Both tenants own github/default; each resolves to its own row.
    a = client.get("/api/connections/github", headers=A_ADMIN).json()["data"]
    b = client.get("/api/connections/github", headers=B_ADMIN).json()["data"]
    assert a["id"] == seeded["conn_a"] and b["id"] == seeded["conn_b"]


def test_cannot_modify_or_delete_other_tenants_connection(client, seeded):
    cid = seeded["conn_b"]
    before = _row("connections", cid)
    attempts = [
        client.post(f"/api/connections/{cid}/test", headers=A_ADMIN),
        client.post(f"/api/connections/{cid}/disconnect", headers=A_ADMIN),
        client.post(f"/api/connections/{cid}/reconnect", headers=A_ADMIN, json={"values": {"apiKey": "stolen"}}),
        client.delete(f"/api/connections/{cid}", headers=A_ADMIN),
    ]
    assert all(r.status_code in (400, 404) for r in attempts), [r.status_code for r in attempts]
    assert _row("connections", cid) == before  # untouched


def test_credentials_resolve_per_tenant(client, seeded):
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.connection_service import ConnectionService

    async def creds(tenant):
        async with AsyncSessionLocal() as s:
            return await ConnectionService.resolve_credentials(s, tenant, "github", "default")

    assert asyncio.run(creds(TENANT_A))["apiKey"] == "A-secret"
    assert asyncio.run(creds(TENANT_B))["apiKey"] == "B-secret"
    assert asyncio.run(creds(f"tenant-c-{RUN}")) is None


def test_connection_unique_per_tenant_only(client, seeded):
    c = _db()
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(
            "INSERT INTO connections (id, tenant_id, service, connection_name, auth_type, encrypted_value, status) "
            "VALUES (?, ?, 'github', 'default', 'api_key', 'x', 'active')",
            (str(uuid.uuid4()), TENANT_A),
        )
    c.close()


# --- runtime tokens -------------------------------------------------------

def test_runtime_tokens_are_tenant_scoped(client, seeded):
    created = client.post("/api/runtime-tokens", headers=A_ADMIN, json={"name": "a-key", "allowedActions": ["*"]})
    assert created.status_code == 200
    token_id = created.json()["data"]["id"]
    raw = created.json()["data"]["rawToken"]

    assert token_id in {t["id"] for t in client.get("/api/runtime-tokens", headers=A_ADMIN).json()["data"]}
    assert token_id not in {t["id"] for t in client.get("/api/runtime-tokens", headers=B_ADMIN).json()["data"]}
    assert client.delete(f"/api/runtime-tokens/{token_id}", headers=B_ADMIN).status_code == 404

    # The minted token authenticates as tenant A and sees only A's connections via MCP.
    mcp = client.post(
        "/mcp",
        headers={"Authorization": f"Bearer {raw}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_connections", "arguments": {}}},
    )
    assert mcp.status_code == 200
    ids = {c["id"] for c in mcp.json()["result"]["data"]["connections"]}
    assert ids == {seeded["conn_a"]}  # a database-stored token resolves to the tenant that minted it
    assert client.delete(f"/api/runtime-tokens/{token_id}", headers=A_ADMIN).status_code == 200


def test_mcp_list_connections_is_tenant_scoped(client, seeded):
    res = client.post(
        "/mcp",
        headers=A_AGENT,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_connections", "arguments": {}}},
    )
    ids = {c["id"] for c in res.json()["result"]["data"]["connections"]}
    assert ids == {seeded["conn_a"]}


# --- runs and stats -------------------------------------------------------

def test_runs_and_stats_are_tenant_scoped(client, seeded):
    runs_a = {r["id"] for r in client.get("/api/runs?limit=200", headers=A_ADMIN).json()["data"]}
    runs_b = {r["id"] for r in client.get("/api/runs?limit=200", headers=B_ADMIN).json()["data"]}
    assert runs_a == {seeded["run_a"]} and runs_b == {seeded["run_b"]}
    assert client.get(f"/api/runs/{seeded['run_b']}", headers=A_ADMIN).status_code == 404
    assert client.get(f"/api/runs/{seeded['run_a']}", headers=A_ADMIN).status_code == 200
    stats = client.get("/api/stats", headers=A_ADMIN).json()["data"]
    assert stats["totalRuns"] == 1 and stats["totalConnections"] == 1


# --- OAuth ----------------------------------------------------------------

def test_oauth_client_config_is_per_tenant(client):
    saved = client.post(
        "/api/oauth/github/config", headers=A_ADMIN,
        json={"clientId": "a-client", "clientSecret": "a-secret"},
    )
    assert saved.status_code == 200
    a = client.get("/api/oauth/github/config", headers=A_ADMIN).json()
    b = client.get("/api/oauth/github/config", headers=B_ADMIN).json()
    assert a["customConfigured"] is True and a["clientId"] == "a-client"
    assert b["customConfigured"] is False and b["clientId"] != "a-client"


def test_tenant_admin_cannot_set_platform_hosted_credentials(client):
    res = client.post(
        "/api/oauth/github/config?mode=hosted", headers=A_ADMIN,
        json={"clientId": "x", "clientSecret": "y"},
    )
    assert res.status_code == 403


def test_operator_environment_oauth_credentials_are_not_shared(client, monkeypatch):
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.oauth_service import OAuthService

    # "linear" is not configured by any other test, so no stored row can mask the environment.
    monkeypatch.setenv("CONNECTOR_LINEAR_CLIENT_ID", "operator-env-id")
    monkeypatch.setenv("CONNECTOR_LINEAR_CLIENT_SECRET", "operator-env-secret")

    async def lookup(tenant):
        async with AsyncSessionLocal() as s:
            return await OAuthService.get_custom_client_config(s, tenant, "linear")

    default_cfg = asyncio.run(lookup(DEFAULT_TENANT_ID))
    other_cfg = asyncio.run(lookup(f"tenant-c-{RUN}"))
    assert default_cfg and default_cfg["client_id"] == "operator-env-id"
    assert other_cfg is None


def test_oauth_callback_connects_into_the_tenant_that_started_the_flow(client, monkeypatch):
    """The callback is unauthenticated; the tenant must come from the stored state."""
    from app.providers.registry import registry
    import app.services.oauth_service as oauth_module

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"access_token": "tok-from-provider", "token_type": "bearer"}

    async def fake_request(*args, **kwargs):
        return FakeResponse()

    provider = registry.get_provider("github")

    async def fake_validate(credential, http_client):
        return {"account_id": f"acct-{RUN}", "display_name": "Fake GitHub", "granted_scopes": []}

    monkeypatch.setattr(oauth_module, "execute_guarded_request", fake_request)
    monkeypatch.setattr(provider, "validate_credentials", fake_validate)

    client.post("/api/oauth/github/config", headers=A_ADMIN, json={"clientId": "a-client", "clientSecret": "a-secret"})
    auth = client.get("/api/oauth/github/authorize?connectionName=oauth-flow", headers=A_ADMIN)
    assert auth.status_code == 200, auth.text
    state = auth.json()["data"]["state"]

    # An unauthenticated caller (or tenant B) completes the callback with A's state.
    cb = client.get(f"/api/oauth/github/callback?code=abc&state={state}")
    assert cb.status_code == 200, cb.text
    new_id = cb.json()["data"]["id"]

    assert new_id in _ids(client.get("/api/connections", headers=A_ADMIN))
    assert new_id not in _ids(client.get("/api/connections", headers=B_ADMIN))
    # State is single use.
    assert client.get(f"/api/oauth/github/callback?code=abc&state={state}").status_code == 400


def test_tenant_never_uses_another_tenants_oauth_app(client):
    # Tenant A registered its own GitHub app; tenant B must never be handed it.
    # B either has no usable app (400) or falls back to the shared hosted app.
    from urllib.parse import parse_qs, urlparse

    client.post("/api/oauth/github/config", headers=A_ADMIN, json={"clientId": "a-client", "clientSecret": "a-secret"})
    res = client.get("/api/oauth/github/authorize", headers=B_ADMIN)
    assert res.status_code in (200, 400)
    if res.status_code == 200:
        url = res.json()["data"]["authorization_url"]
        assert parse_qs(urlparse(url).query)["client_id"][0] != "a-client"
    a = client.get("/api/oauth/github/authorize?mode=custom", headers=A_ADMIN)
    assert parse_qs(urlparse(a.json()["data"]["authorization_url"]).query)["client_id"][0] == "a-client"


# --- idempotency ----------------------------------------------------------

def test_idempotency_keys_do_not_collide_across_tenants():
    args = dict(idempotency_key="same-key", principal_id="p", action_id="github.x", connection_name="default")
    assert compute_idempotency_scope_key(tenant_id=TENANT_A, **args) != compute_idempotency_scope_key(tenant_id=TENANT_B, **args)

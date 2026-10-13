"""Accounts: signup policy, emailed codes, cookie sessions, CSRF, lockout, isolation, reset and deletion."""
import re
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app.accounts import mailer
from app.accounts.ratelimit import limiter
from app.accounts.security import code_matches, hash_code, hash_password, needs_rehash, verify_password
from app.accounts.service import AccountError, effective_signup_mode, normalize_email, validate_password
from app.core.config import settings

H = {"X-Connector-CSRF": "1"}
PASSWORD = "correct horse battery"
OPERATOR = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}


def _db():
    return sqlite3.connect(settings.DATABASE_URL.split("///", 1)[1])


def _q(sql, *args):
    c = _db()
    rows = c.execute(sql, args).fetchall()
    c.commit()
    c.close()
    return rows


def new_email():
    return f"user-{uuid.uuid4().hex[:10]}@acme-corp.dev"


def last_code(email):
    for to, _subject, body in reversed(mailer.OUTBOX):
        if to == email:
            return re.search(r"\b(\d{6})\b", body).group(1)
    raise AssertionError(f"no email sent to {email}")


@pytest.fixture(autouse=True)
def accounts_env(monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "open")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "console")
    monkeypatch.setattr(settings, "ACCOUNTS_COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "ACCOUNTS_INVITE_CODES", "")
    monkeypatch.setattr(settings, "ACCOUNTS_BLOCKED_EMAIL_DOMAINS", "")
    limiter.clear()
    mailer.OUTBOX.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client, email=None, password=PASSWORD, **extra):
    email = email or new_email()
    r = client.post("/api/accounts/signup", headers=H, json={"email": email, "password": password, **extra})
    return email, r


def make_user(client, email=None, password=PASSWORD):
    """Sign up, verify the emailed code, and leave `client` signed in."""
    email, r = register(client, email, password)
    assert r.status_code == 202, r.text
    v = client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": last_code(email)})
    assert v.status_code == 200, v.text
    return email


def tenant_of(client):
    return client.get("/api/accounts/me").json()["user"]["tenantId"]


def seed_connection(tenant, name="default"):
    cid = str(uuid.uuid4())
    _q("INSERT INTO connections (id, tenant_id, service, connection_name, auth_type, encrypted_value, status) "
       "VALUES (?, ?, 'github', ?, 'api_key', 'x', 'active')", cid, tenant, name)
    return cid


# --- signup policy ---------------------------------------------------------

def test_signup_disabled_by_default_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "disabled")
    assert register(client)[1].status_code == 403
    assert client.get("/api/accounts/config").json()["signupMode"] == "disabled"


def test_invite_mode_requires_a_valid_code(client, monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "invite")
    monkeypatch.setattr(settings, "ACCOUNTS_INVITE_CODES", "beta-one, beta-two")
    assert register(client)[1].status_code == 403
    assert register(client, inviteCode="wrong")[1].status_code == 403
    assert register(client, inviteCode="beta-two")[1].status_code == 202


def test_unsafe_modes_fall_back_to_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "open")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "none")  # open signup without email is unsafe
    assert effective_signup_mode() == "disabled"
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "invite")
    monkeypatch.setattr(settings, "ACCOUNTS_INVITE_CODES", "")  # invite mode without codes is unsafe
    assert effective_signup_mode() == "disabled"


def test_invite_only_without_email_creates_a_verified_account(client, monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_SIGNUP_MODE", "invite")
    monkeypatch.setattr(settings, "ACCOUNTS_INVITE_CODES", "beta")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "none")
    email, r = register(client, inviteCode="beta")
    assert r.status_code == 201
    assert client.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 200
    assert register(client, email, inviteCode="beta")[1].status_code == 409  # no mail to hide behind
    assert client.post("/api/accounts/forgot-password", headers=H, json={"email": email}).status_code == 503


def test_duplicate_signup_looks_the_same_when_email_is_enabled(client):
    email = make_user(client)
    mailer.OUTBOX.clear()
    other = TestClient(app)
    again = other.post("/api/accounts/signup", headers=H, json={"email": email, "password": PASSWORD})
    fresh = other.post("/api/accounts/signup", headers=H, json={"email": new_email(), "password": PASSWORD})
    assert again.status_code == fresh.status_code == 202
    assert again.json() == fresh.json()
    assert [m for m in mailer.OUTBOX if m[0] == email] == []  # nothing sent to the existing account


@pytest.mark.parametrize("email", [
    "", "plain", "a@b", "a b@acme-corp.dev", "a@acme-corp", "@acme-corp.dev", "a@@acme-corp.dev",
    "x@example.com", "x@example.org", "x@thing.test", "x@thing.invalid", "x@host.local", "x" * 250 + "@acme-corp.dev",
])
def test_rejects_bad_or_reserved_emails(email):
    with pytest.raises(AccountError):
        normalize_email(email)


def test_email_is_normalised_and_blockable(client, monkeypatch):
    assert normalize_email("  Mixed.Case@Acme-Corp.DEV ") == "mixed.case@acme-corp.dev"
    monkeypatch.setattr(settings, "ACCOUNTS_BLOCKED_EMAIL_DOMAINS", "throwaway.io, spam.dev")
    with pytest.raises(AccountError):
        normalize_email("a@spam.dev")
    email = new_email()
    assert register(client, email.upper())[1].status_code == 202
    assert register(client, email)[1].status_code == 202  # same account, no second user
    assert _q("select count(*) from users where email = ?", email)[0][0] == 1


@pytest.mark.parametrize("password", ["short", "x" * 129, "password123", "1234567890", "", None])
def test_rejects_weak_passwords(password):
    with pytest.raises(AccountError):
        validate_password(password, "someone@acme-corp.dev")


def test_password_may_not_be_the_email_name():
    with pytest.raises(AccountError):
        validate_password("someone-else", "someone-else@acme-corp.dev")


def test_signup_is_rate_limited_per_ip(client):
    codes = [client.post("/api/accounts/signup", headers=H, json={"email": "bad", "password": PASSWORD}).status_code
             for _ in range(11)]
    assert codes[:10] == [400] * 10 and codes[10] == 429


# --- verification codes ----------------------------------------------------

def test_verification_logs_in_and_sets_a_hardened_cookie(client):
    email, r = register(client)
    assert r.status_code == 202
    v = client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": last_code(email)})
    assert v.status_code == 200 and v.json()["user"]["email"] == email
    cookie = v.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert client.get("/api/accounts/me").json()["user"]["email"] == email


def test_cookie_is_secure_and_host_prefixed_on_https(client, monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_COOKIE_SECURE", None)
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", "https://connector.example.com")
    email, _ = register(client)
    v = client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": last_code(email)})
    cookie = v.headers["set-cookie"]
    assert cookie.startswith("__Host-connector_session=") and "Secure" in cookie and "Domain" not in cookie


def test_code_is_six_digits_and_stored_only_as_a_keyed_hash(client):
    email, _ = register(client)
    code = last_code(email)
    assert re.fullmatch(r"\d{6}", code)
    stored = _q("select code_hash from email_challenges where user_id = (select id from users where email = ?)", email)[0][0]
    assert stored != code and re.fullmatch(r"[0-9a-f]{64}", stored)
    assert code not in str(_q("select * from email_challenges"))


def test_wrong_codes_burn_the_challenge_after_five_tries(client):
    email, _ = register(client)
    good = last_code(email)
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": bad}).status_code == 401
    # Even the right code no longer works: the guesses used the attempts up.
    assert client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": good}).status_code == 401


def test_expired_code_is_rejected(client):
    email, _ = register(client)
    _q("update email_challenges set expires_at = '2000-01-01T00:00:00.000000Z' "
       "where user_id = (select id from users where email = ?)", email)
    assert client.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": last_code(email)}).status_code == 401


def test_code_cannot_be_reused(client):
    email = make_user(client)
    other = TestClient(app)
    assert other.post("/api/accounts/verify-email", headers=H, json={"email": email, "code": last_code(email)}).status_code == 401


def test_resend_cooldown_limits_email_volume(client):
    email, _ = register(client)
    register(client, email)
    register(client, email)
    assert len([m for m in mailer.OUTBOX if m[0] == email]) == 1


def test_cannot_log_in_before_verifying(client):
    email, _ = register(client)
    r = client.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD})
    assert r.status_code == 403 and r.json()["detail"]["error"]["code"] == "EMAIL_NOT_VERIFIED"


# --- login, sessions, CSRF -------------------------------------------------

def test_login_failures_do_not_reveal_which_part_was_wrong(client):
    email = make_user(client)
    anon = TestClient(app)
    wrong = anon.post("/api/accounts/login", headers=H, json={"email": email, "password": "not the password"})
    ghost = anon.post("/api/accounts/login", headers=H, json={"email": new_email(), "password": "not the password"})
    assert wrong.status_code == ghost.status_code == 401 and wrong.json() == ghost.json()


def test_account_locks_after_repeated_failures(client):
    email = make_user(client)
    anon = TestClient(app)
    for _ in range(5):
        assert anon.post("/api/accounts/login", headers=H, json={"email": email, "password": "nope-nope-nope"}).status_code == 401
    # Locked out, even for the right password.
    assert anon.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 429


def test_login_needs_the_csrf_header(client):
    email = make_user(client)
    anon = TestClient(app)
    assert anon.post("/api/accounts/login", json={"email": email, "password": PASSWORD}).status_code == 403
    assert anon.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 200


def test_cookie_requests_without_the_csrf_header_are_not_acted_on_as_the_user(client):
    make_user(client)
    mine = client.post("/api/runtime-tokens", headers=H, json={"name": "with-header"}).json()["data"]["id"]
    forged = client.post("/api/runtime-tokens", json={"name": "forged"})  # cookie sent, header missing
    mine_ids = {t["id"] for t in client.get("/api/runtime-tokens").json()["data"]}
    assert mine in mine_ids
    if forged.status_code == 200:  # treated as an anonymous visitor, never as this user
        assert forged.json()["data"]["id"] not in mine_ids


def test_session_token_is_stored_only_as_a_hash(client):
    make_user(client)
    raw = client.cookies.get("connector_session")
    assert raw and raw.startswith("cs_")
    rows = _q("select token_hash from account_sessions")
    assert raw not in str(rows) and all(re.fullmatch(r"[0-9a-f]{64}", r[0]) for r in rows)


def test_logout_revokes_the_session_and_stale_cookies_never_fall_back_to_public(client):
    make_user(client)
    raw = client.cookies.get("connector_session")
    assert client.post("/api/accounts/logout", headers=H).status_code == 200
    stale = TestClient(app, cookies={"connector_session": raw})
    assert stale.get("/api/accounts/me").status_code == 401
    assert stale.get("/api/connections").status_code == 401  # not silently served from the public sandbox


def test_expired_session_is_rejected(client):
    make_user(client)
    _q("update account_sessions set expires_at = '2000-01-01T00:00:00.000000Z'")
    assert client.get("/api/accounts/me").status_code == 401


def test_disabled_accounts_lose_access(client):
    email = make_user(client)
    _q("update users set is_active = 0 where email = ?", email)
    assert client.get("/api/accounts/me").status_code == 401
    assert TestClient(app).post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 403


def test_password_hashing_is_argon2id_and_verifies():
    h = hash_password("a long enough secret")
    assert h.startswith("$argon2id$") and verify_password(h, "a long enough secret")
    assert not verify_password(h, "wrong") and not verify_password("garbage", "x") and not needs_rehash(h)


def test_code_helpers_are_keyed_and_constant_time_safe():
    h = hash_code("challenge-1", "123456")
    assert code_matches("challenge-1", " 123456 ", h) and not code_matches("challenge-2", "123456", h)


# --- tenant isolation between real users -------------------------------------

def test_each_user_only_sees_their_own_tenant(client):
    a, b = client, TestClient(app)
    make_user(a)
    make_user(b)
    ta, tb = tenant_of(a), tenant_of(b)
    assert ta != tb
    conn_a = seed_connection(ta)
    conn_b = seed_connection(tb)
    ids = lambda c: {x["id"] for x in c.get("/api/connections").json()["data"]}
    assert conn_a in ids(a) and conn_b not in ids(a)
    assert conn_b in ids(b) and conn_a not in ids(b)
    assert b.get(f"/api/connections/{conn_a}").status_code == 404
    anon_ids = {x["id"] for x in TestClient(app).get("/api/connections").json()["data"]}
    operator_ids = {x["id"] for x in TestClient(app).get("/api/connections", headers=OPERATOR).json()["data"]}
    assert not ({conn_a, conn_b} & (anon_ids | operator_ids))


def test_user_minted_runtime_tokens_stay_inside_the_users_tenant(client):
    make_user(client)
    other = TestClient(app)
    make_user(other)
    mine, theirs = seed_connection(tenant_of(client)), seed_connection(tenant_of(other))
    raw = client.post("/api/runtime-tokens", headers=H, json={"name": "agent", "allowedActions": ["*"]}).json()["data"]["rawToken"]
    res = TestClient(app).post("/mcp", headers={"Authorization": f"Bearer {raw}"}, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_connections", "arguments": {}}})
    ids = {c["id"] for c in res.json()["result"]["data"]["connections"]}
    assert ids == {mine} and theirs not in ids


def test_users_cannot_set_platform_hosted_oauth_credentials(client):
    make_user(client)
    hosted = client.post("/api/oauth/github/config?mode=hosted", headers=H, json={"clientId": "x", "clientSecret": "y"})
    custom = client.post("/api/oauth/github/config?mode=custom", headers=H, json={"clientId": "x", "clientSecret": "y"})
    assert hosted.status_code == 403 and custom.status_code == 200


# --- password reset, change, deletion -------------------------------------------

def test_forgot_password_answers_the_same_for_known_and_unknown_emails(client):
    email = make_user(client)
    mailer.OUTBOX.clear()
    anon = TestClient(app)
    known = anon.post("/api/accounts/forgot-password", headers=H, json={"email": email})
    unknown = anon.post("/api/accounts/forgot-password", headers=H, json={"email": new_email()})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert [m[0] for m in mailer.OUTBOX] == [email]


def test_reset_password_sets_a_new_password_and_signs_out_every_device(client):
    email = make_user(client)
    second = TestClient(app)
    assert second.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 200
    anon = TestClient(app)
    anon.post("/api/accounts/forgot-password", headers=H, json={"email": email})
    code = last_code(email)
    res = anon.post("/api/accounts/reset-password", headers=H, json={"email": email, "code": code, "password": "a brand new passphrase"})
    assert res.status_code == 200
    assert client.get("/api/accounts/me").status_code == 401 and second.get("/api/accounts/me").status_code == 401
    assert anon.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 401
    assert anon.post("/api/accounts/login", headers=H, json={"email": email, "password": "a brand new passphrase"}).status_code == 200
    # one-time: the same code cannot reset again
    assert anon.post("/api/accounts/reset-password", headers=H, json={"email": email, "code": code, "password": "yet another passphrase"}).status_code == 401


def test_reset_with_wrong_code_changes_nothing_and_guessing_is_capped(client):
    email = make_user(client)
    anon = TestClient(app)
    anon.post("/api/accounts/forgot-password", headers=H, json={"email": email})
    good = last_code(email)
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert anon.post("/api/accounts/reset-password", headers=H, json={"email": email, "code": bad, "password": "attacker chosen pass"}).status_code == 401
    assert anon.post("/api/accounts/reset-password", headers=H, json={"email": email, "code": good, "password": "attacker chosen pass"}).status_code == 401
    assert TestClient(app).post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 200


def test_change_password_keeps_this_device_and_signs_out_the_others(client):
    email = make_user(client)
    other_device = TestClient(app)
    other_device.post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD})
    wrong = client.post("/api/accounts/change-password", headers=H, json={"currentPassword": "nope", "newPassword": "another long passphrase"})
    assert wrong.status_code == 401
    ok = client.post("/api/accounts/change-password", headers=H, json={"currentPassword": PASSWORD, "newPassword": "another long passphrase"})
    assert ok.status_code == 200
    assert client.get("/api/accounts/me").status_code == 200
    assert other_device.get("/api/accounts/me").status_code == 401


def test_deleting_an_account_removes_its_data_and_nothing_else(client):
    email = make_user(client)
    bystander = TestClient(app)
    make_user(bystander)
    mine, theirs = tenant_of(client), tenant_of(bystander)
    seed_connection(mine)
    keep = seed_connection(theirs)
    client.post("/api/runtime-tokens", headers=H, json={"name": "agent"})
    client.post("/api/oauth/github/config", headers=H, json={"clientId": "x", "clientSecret": "y"})
    _q("INSERT INTO runs (id, tenant_id, action_id, service, caller, ok, status_code, duration_ms) "
       "VALUES (?, ?, 'a.b', 'github', 'http', 1, 200, 1.0)", str(uuid.uuid4()), mine)

    assert client.post("/api/accounts/delete", headers=H, json={"password": "wrong password"}).status_code == 401
    gone = client.post("/api/accounts/delete", headers=H, json={"password": PASSWORD})
    assert gone.status_code == 200

    for table in ("connections", "runtime_tokens", "runs", "oauth_states", "action_idempotency"):
        assert _q(f"select count(*) from {table} where tenant_id = ?", mine)[0][0] == 0, table
    assert _q("select count(*) from oauth_client_configs where service like ?", f"tenant:{mine}:%")[0][0] == 0
    assert _q("select count(*) from users where email = ?", email)[0][0] == 0
    assert _q("select count(*) from account_sessions where user_id not in (select id from users)")[0][0] == 0
    assert client.get("/api/accounts/me").status_code == 401
    assert TestClient(app).post("/api/accounts/login", headers=H, json={"email": email, "password": PASSWORD}).status_code == 401
    assert _q("select count(*) from connections where id = ?", keep)[0][0] == 1  # bystander untouched


# --- CORS and client address ------------------------------------------------------

def test_only_this_services_own_origin_may_send_credentialed_requests(client, monkeypatch):
    ask = lambda origin: client.options("/api/accounts/me", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET"})
    assert ask("https://connector.suparagent.ai").headers.get("access-control-allow-origin") == "https://connector.suparagent.ai"
    # A sibling site on the same registrable domain, or any other site, gets no CORS grant.
    assert "access-control-allow-origin" not in ask("https://suparagent.ai").headers
    assert "access-control-allow-origin" not in ask("https://evil.example").headers


def test_client_ip_only_trusts_forwarded_header_from_the_local_proxy():
    from app.accounts.service import client_ip

    class Req:
        def __init__(self, peer, real_ip=None):
            self.client = type("C", (), {"host": peer})()
            self.headers = {"x-real-ip": real_ip} if real_ip else {}

    assert client_ip(Req("203.0.113.9", "1.2.3.4")) == "203.0.113.9"   # direct caller cannot spoof
    assert client_ip(Req("127.0.0.1", "198.51.100.7")) == "198.51.100.7"  # nginx on the same host
    assert client_ip(Req("172.18.0.1", "198.51.100.8")) == "198.51.100.8"  # docker bridge to nginx
    assert client_ip(Req("127.0.0.1")) == "127.0.0.1"


# --- resend verification --------------------------------------------------------

def test_resend_verification_only_mails_unverified_accounts_and_never_says_which(client):
    pending, _ = register(client)             # unverified
    done = make_user(TestClient(app))          # verified
    anon = TestClient(app)
    _q("update email_challenges set created_at = '2000-01-01T00:00:00.000000Z'")  # clear the cooldown
    mailer.OUTBOX.clear()
    answers = [anon.post("/api/accounts/resend-verification", headers=H, json={"email": e})
               for e in (pending, done, new_email(), "not-an-email")]
    assert {a.status_code for a in answers} == {202} and len({str(a.json()) for a in answers}) == 1
    assert [m[0] for m in mailer.OUTBOX] == [pending]
    # the fresh code works and the cooldown stops a second email straight away
    anon.post("/api/accounts/resend-verification", headers=H, json={"email": pending})
    assert [m[0] for m in mailer.OUTBOX] == [pending]
    assert anon.post("/api/accounts/verify-email", headers=H, json={"email": pending, "code": last_code(pending)}).status_code == 200


def test_resend_verification_is_unavailable_without_email(client, monkeypatch):
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "none")
    assert client.post("/api/accounts/resend-verification", headers=H, json={"email": new_email()}).status_code == 503


# --- Amazon SES backend -----------------------------------------------------------

class _FakeSES:
    def __init__(self, sink):
        self.sink = sink

    def send_email(self, **kwargs):
        self.sink["sent"].append(kwargs)


def _fake_boto3(monkeypatch, sink):
    import sys
    import types

    def client(service, **kwargs):
        sink["service"], sink["client_kwargs"] = service, kwargs
        return _FakeSES(sink)

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=client))


def test_ses_backend_sends_through_the_ses_api_with_the_configured_sender(client, monkeypatch):
    sink = {"sent": []}
    _fake_boto3(monkeypatch, sink)
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "ses")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_FROM", "ConnectorHub <support@acme-corp.dev>")
    monkeypatch.setattr(settings, "ACCOUNTS_SES_REGION", "ap-south-1")
    monkeypatch.setattr(settings, "ACCOUNTS_SES_ACCESS_KEY", "AKIAEXAMPLE")
    monkeypatch.setattr(settings, "ACCOUNTS_SES_SECRET_KEY", "example-secret")
    email, r = register(client)
    assert r.status_code == 202
    assert sink["service"] == "ses"
    assert sink["client_kwargs"] == {"region_name": "ap-south-1", "aws_access_key_id": "AKIAEXAMPLE",
                                     "aws_secret_access_key": "example-secret"}
    [msg] = sink["sent"]
    assert msg["Source"] == "ConnectorHub <support@acme-corp.dev>"
    assert msg["Destination"] == {"ToAddresses": [email]}
    assert re.search(r"\b\d{6}\b", msg["Message"]["Body"]["Text"]["Data"])
    assert "verification code" in msg["Message"]["Subject"]["Data"]


def test_ses_backend_falls_back_to_the_machines_aws_credentials(client, monkeypatch):
    sink = {"sent": []}
    _fake_boto3(monkeypatch, sink)
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "ses")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_FROM", "support@acme-corp.dev")
    monkeypatch.setattr(settings, "ACCOUNTS_SES_ACCESS_KEY", "")
    monkeypatch.setattr(settings, "ACCOUNTS_SES_SECRET_KEY", "")
    register(client)
    assert "aws_access_key_id" not in sink["client_kwargs"]  # default credential chain (e.g. an IAM role)


def test_ses_outage_never_breaks_signup_or_leaks_into_the_response(client, monkeypatch):
    import sys
    import types

    def boom(service, **kwargs):
        raise RuntimeError("SES is down: secret-detail")

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=boom))
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "ses")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_FROM", "support@acme-corp.dev")
    email, r = register(client)
    assert r.status_code == 202 and "secret-detail" not in r.text


def test_ses_without_a_sender_sends_nothing(client, monkeypatch):
    sink = {"sent": []}
    _fake_boto3(monkeypatch, sink)
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_BACKEND", "ses")
    monkeypatch.setattr(settings, "ACCOUNTS_EMAIL_FROM", "")
    monkeypatch.setattr(settings, "ACCOUNTS_SMTP_FROM", "")
    monkeypatch.setattr(settings, "ACCOUNTS_SMTP_USER", "")
    assert register(client)[1].status_code == 202
    assert sink["sent"] == []

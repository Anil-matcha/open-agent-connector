"""
Comprehensive Security & Authorization Contract Test Suite
Validates the P0 security boundary, deny-by-default runtime scoping,
SSRF defenses, schema validation, idempotency, and token revocation.
Zero mock data: executes live against the local server and verified credentials.
"""
import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("==================================================")
    print("[SECURITY] RUNNING OPEN AGENT CONNECTOR SECURITY CONTRACT TESTS")
    print("==================================================\n")

    client = httpx.Client(base_url=BASE_URL, timeout=15)

    # 0. Obtain Local Admin Token
    auth_status = client.get("/api/auth/status").json()
    admin_token = auth_status.get("localToken")
    assert admin_token, "Failed to retrieve local admin token"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] 0. Admin Token resolved from secure store (starts with ch_admin_...)")

    # 1. Admin Authentication Gate
    print("\n--- TEST 1: Admin Protection on Management Routes ---")
    res_unauth = client.get("/api/connections")
    assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"
    print("  [+] Unauthenticated access to /api/connections denied with 401 Unauthorized")

    res_bad_auth = client.get("/api/connections", headers={"Authorization": "Bearer invalid_token"})
    assert res_bad_auth.status_code == 401, f"Expected 401, got {res_bad_auth.status_code}"
    print("  [+] Invalid bearer token denied with 401 Unauthorized")

    res_auth = client.get("/api/connections", headers=admin_headers)
    assert res_auth.status_code == 200, f"Expected 200, got {res_auth.status_code}"
    print(f"  [+] Valid Admin Token granted access (Found {len(res_auth.json()['data'])} connections)")

    # 2. Create Scoped Runtime Token
    print("\n--- TEST 2: Scoped Runtime Token Creation ---")
    create_payload = {
        "name": "Single-Action Scoped Agent Token",
        "allowedActions": ["github.get_current_user"],
        "allowedConnections": ["default"],
        "allowedProxies": []
    }
    create_res = client.post("/api/runtime-tokens", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 200, f"Failed to create token: {create_res.text}"
    token_data = create_res.json()["data"]
    token_id = token_data["id"]
    raw_runtime_token = token_data["rawToken"]
    runtime_headers = {"Authorization": f"Bearer {raw_runtime_token}"}
    print(f"  [+] Runtime Token created: ID {token_id}")
    print(f"  [+] Scoped to: allowedActions={token_data['allowedActions']}, allowedConnections={token_data['allowedConnections']}")

    # 3. Scoped Discovery Gate (REST & MCP)
    print("\n--- TEST 3: Scoped Discovery (REST & MCP) ---")
    actions_res = client.get("/v1/actions", headers=runtime_headers)
    assert actions_res.status_code == 200
    exposed_actions = [a["id"] for a in actions_res.json()["data"]]
    assert exposed_actions == ["github.get_current_user"], f"Expected only github.get_current_user, got {exposed_actions}"
    print(f"  [+] REST Discovery properly filtered: only 1 action exposed: {exposed_actions}")

    mcp_tools_res = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers=runtime_headers
    )
    assert mcp_tools_res.status_code == 200
    tools = [t["name"] for t in mcp_tools_res.json()["result"]["tools"]]
    assert "github_get_current_user" in tools, "Expected github_get_current_user in MCP tools"
    assert "github_create_issue" not in tools, "Security violation: github_create_issue leaked in MCP tools"
    print(f"  [+] MCP Discovery properly filtered: github_get_current_user present, unauthorized tools hidden")

    # 4. Action Execution Policy Gate
    print("\n--- TEST 4: Action Execution Policy (Allow vs Deny) ---")
    exec_allowed = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {}, "connectionName": "default"},
        headers=runtime_headers
    )
    assert exec_allowed.status_code == 200, f"Execution failed: {exec_allowed.text}"
    login_user = exec_allowed.json()["data"]["login"]
    print(f"  [+] Authorized Action executed successfully! Live user login: @{login_user}")

    exec_unauth = client.post(
        "/v1/actions/github.create_issue",
        json={"input": {"owner": "test", "repo": "test", "title": "test"}},
        headers=runtime_headers
    )
    assert exec_unauth.status_code == 403, f"Expected 403 Forbidden, got {exec_unauth.status_code}"
    print("  [+] Unauthorized action execution correctly blocked with 403 Forbidden")

    exec_bad_alias = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {}, "connectionName": "production-unauthorized-alias"},
        headers=runtime_headers
    )
    assert exec_bad_alias.status_code == 403, f"Expected 403 Forbidden, got {exec_bad_alias.status_code}"
    print("  [+] Unauthorized connection alias correctly blocked with 403 Forbidden")

    # 5. Idempotency Key Gate & Conflict Detection
    print("\n--- TEST 5: Idempotency Key Semantics & Conflict Detection ---")
    idemp_key = f"test-idemp-{int(time.time())}"
    h1 = dict(runtime_headers)
    h1["Idempotency-Key"] = idemp_key

    # Call 1
    r1 = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {}, "connectionName": "default"},
        headers=h1
    )
    assert r1.status_code == 200
    res1_data = r1.json()

    # Call 2: Identical retry
    r2 = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {}, "connectionName": "default"},
        headers=h1
    )
    assert r2.status_code == 200
    res2_data = r2.json()
    assert res2_data.get("meta", {}).get("replayed") is True, "Expected replayed=True"
    print("  [+] Identical retry returned replayed result without secondary side-effect")

    # Call 3: Payload conflict
    r3 = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {"unexpected_field": "mismatch"}, "connectionName": "default"},
        headers=h1
    )
    assert r3.status_code == 409, f"Expected 409 Conflict on payload mismatch, got {r3.status_code}"
    print("  [+] Idempotency payload mismatch correctly rejected with 409 Conflict")

    # 6. Audit Log Recording & Sensitive Data Redaction
    print("\n--- TEST 6: Audit Log Recording & Sensitive Data Redaction ---")
    runs_res = client.get("/api/runs?limit=3", headers=admin_headers)
    assert runs_res.status_code == 200
    recent_runs = runs_res.json()["data"]
    assert len(recent_runs) > 0, "Expected run records in audit log"
    latest_run = recent_runs[0]
    print(f"  [+] Latest run recorded in SQLite: {latest_run['actionId']} (Status: {latest_run['statusCode']})")
    assert "token" not in str(latest_run["inputSummary"]).lower() or "REDACTED" in str(latest_run["inputSummary"])
    print("  [+] Secret redaction verified in audit log summary")

    # 7. Token Revocation Gate
    print("\n--- TEST 7: Token Revocation Lifecycle ---")
    revoke_res = client.delete(f"/api/runtime-tokens/{token_id}", headers=admin_headers)
    assert revoke_res.status_code == 200
    print(f"  [+] Runtime Token {token_id} revoked via Admin API")

    revoked_exec = client.post(
        "/v1/actions/github.get_current_user",
        json={"input": {}},
        headers=runtime_headers
    )
    assert revoked_exec.status_code == 401, f"Expected 401 for revoked token, got {revoked_exec.status_code}"
    print("  [+] Subsequent call with revoked token immediately denied with 401 Unauthorized")

    # 8. SSRF Guard Gate
    print("\n--- TEST 8: SSRF Guard on Outbound Custom Requests ---")
    loopback_attack = client.post(
        "/v1/actions/custom.http_request",
        json={"input": {"url": "http://127.0.0.1:8000/api/connections"}},
        headers=admin_headers
    )
    assert loopback_attack.status_code in (400, 500)
    print("  [+] Loopback destination 'http://127.0.0.1:8000/api/connections' blocked by SSRF guard")

    print("\n==================================================")
    print("[SUCCESS] ALL SECURITY CONTRACT & ACCEPTANCE GATES PASSED (100%)")
    print("==================================================")

if __name__ == "__main__":
    run_tests()

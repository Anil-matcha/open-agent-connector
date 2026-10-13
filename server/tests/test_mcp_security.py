"""
Security Regression Tests for MCP Authentication & SSRF Guard Hardening
Validates P0 MCP authentication closure, permission enforcement, connection filtering,
revocation lifecycle, and SSRF transport-level address verification.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.core.ssrf import assert_public_url, SSRFViolationError, GuardedTransport
import httpx

client = TestClient(app)
admin_headers = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}

def test_mcp_discovery_requires_authentication():
    """P0 Security: GET /mcp/tools must reject unauthenticated callers with HTTP 401."""
    # 1. Absent token
    res_no_token = client.get("/mcp/tools")
    assert res_no_token.status_code == 401, f"Expected 401, got {res_no_token.status_code}"
    assert "Bearer" in res_no_token.headers.get("www-authenticate", "")

    # 2. Invalid token
    res_bad_token = client.get("/mcp/tools", headers={"Authorization": "Bearer invalid_mcp_token_xyz"})
    assert res_bad_token.status_code == 401

    # 3. Valid Admin Token
    res_admin = client.get("/mcp/tools", headers=admin_headers)
    assert res_admin.status_code == 200
    tools = res_admin.json().get("tools", [])
    assert len(tools) > 5, "Admin should see discovery tools and action tools"

def test_mcp_protocol_handshake_and_unauthenticated_gating():
    """POST /mcp requires authentication on every RPC method, failing closed on unauthenticated calls."""
    # 1. Unauthenticated initialize and ping must be rejected with 401
    assert client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).status_code == 401
    assert client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "ping"}).status_code == 401

    # 2. Authenticated initialize returns negotiated capabilities
    res_init = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"}
    }, headers=admin_headers)
    assert res_init.status_code == 200
    assert res_init.json()["result"]["serverInfo"]["name"] == "connector-hub"

    # 3. Authenticated ping returns empty result
    res_ping = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "ping"
    }, headers=admin_headers)
    assert res_ping.status_code == 200
    assert res_ping.json()["result"] == {}

    # 4. Unauthenticated tools/list must be rejected with 401
    res_unauth_list = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    })
    assert res_unauth_list.status_code == 401, f"Expected 401, got {res_unauth_list.status_code}"

    # 4. Unauthenticated tools/call must be rejected with 401
    res_unauth_call = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "execute_action", "arguments": {"actionId": "github.get_current_user"}}
    })
    assert res_unauth_call.status_code == 401, f"Expected 401, got {res_unauth_call.status_code}"

    # 5. Invalid token on tools/list must be rejected with 401
    res_bad_list = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
        headers={"Authorization": "Bearer bad_secret_token"}
    )
    assert res_bad_list.status_code == 401

def test_scoped_runtime_token_mcp_discovery_and_policy_enforcement():
    """Verify that scoped runtime tokens only see authorized actions and cannot call blocked actions/connections."""
    # 1. Create a scoped runtime token via Admin API
    create_payload = {
        "name": "MCP-Scoped-Agent-Token",
        "allowedActions": ["github.get_current_user"],
        "allowedConnections": ["default"],
        "allowedProxies": []
    }
    create_res = client.post("/api/runtime-tokens", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 200
    token_info = create_res.json()["data"]
    token_id = token_info["id"]
    raw_token = token_info["rawToken"]
    runtime_headers = {"Authorization": f"Bearer {raw_token}"}

    try:
        # 2. tools/list via MCP exposes only github_get_current_user and core discovery tools
        list_res = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
            headers=runtime_headers
        )
        assert list_res.status_code == 200
        exposed_tool_names = [t["name"] for t in list_res.json()["result"]["tools"]]
        assert "github_get_current_user" in exposed_tool_names
        assert "github_create_issue" not in exposed_tool_names, "Unauthorized action leaked in MCP tools/list"
        assert "slack_send_message" not in exposed_tool_names, "Unauthorized action leaked in MCP tools/list"

        # 3. GET /mcp/tools with runtime token is also properly scoped
        tools_get_res = client.get("/mcp/tools", headers=runtime_headers)
        assert tools_get_res.status_code == 200
        get_tool_names = [t["name"] for t in tools_get_res.json()["tools"]]
        assert "github_get_current_user" in get_tool_names
        assert "github_create_issue" not in get_tool_names

        # 4. MCP search_actions tool only returns authorized actions
        search_res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {"name": "search_actions", "arguments": {"query": "user", "service": "github"}}
            },
            headers=runtime_headers
        )
        assert search_res.status_code == 200
        action_results = search_res.json()["result"]["data"]["actions"]
        action_ids = [a["id"] for a in action_results]
        assert "github.get_current_user" in action_ids
        for aid in action_ids:
            assert aid == "github.get_current_user", f"Unauthorized action {aid} returned by search_actions"

        # 5. MCP get_action_guide enforces authorization
        guide_unauth = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {"name": "get_action_guide", "arguments": {"actionId": "github.create_issue"}}
            },
            headers=runtime_headers
        )
        assert guide_unauth.status_code == 200
        assert guide_unauth.json()["result"]["isError"] is True
        assert "Permission denied" in guide_unauth.json()["result"]["content"][0]["text"]

        # 6. MCP execute_action blocks unauthorized action
        call_unauth_action = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "execute_action",
                    "arguments": {
                        "actionId": "github.create_issue",
                        "input": {"owner": "test", "repo": "test", "title": "test"},
                        "connectionName": "default"
                    }
                }
            },
            headers=runtime_headers
        )
        assert call_unauth_action.status_code == 200
        assert call_unauth_action.json()["result"]["isError"] is True
        assert "Permission denied" in call_unauth_action.json()["result"]["content"][0]["text"]

        # 7. MCP execute_action blocks unauthorized connection
        call_unauth_conn = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 14,
                "method": "tools/call",
                "params": {
                    "name": "execute_action",
                    "arguments": {
                        "actionId": "github.get_current_user",
                        "input": {},
                        "connectionName": "unauthorized-prod-alias"
                    }
                }
            },
            headers=runtime_headers
        )
        assert call_unauth_conn.status_code == 200
        assert call_unauth_conn.json()["result"]["isError"] is True
        assert "connection 'unauthorized-prod-alias' is not authorized" in call_unauth_conn.json()["result"]["content"][0]["text"]

        # 8. MCP direct tool call blocks unauthorized action
        call_direct_unauth = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 15,
                "method": "tools/call",
                "params": {
                    "name": "github_create_issue",
                    "arguments": {"owner": "test", "repo": "test", "title": "test"}
                }
            },
            headers=runtime_headers
        )
        assert call_direct_unauth.status_code == 200
        assert call_direct_unauth.json()["result"]["isError"] is True
        assert "Permission denied" in call_direct_unauth.json()["result"]["content"][0]["text"]

    finally:
        # 9. Revocation Gate: Delete runtime token
        del_res = client.delete(f"/api/runtime-tokens/{token_id}", headers=admin_headers)
        assert del_res.status_code == 200

    # 10. Subsequent MCP requests with revoked token must be rejected with 401
    revoked_list = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 16, "method": "tools/list", "params": {}},
        headers=runtime_headers
    )
    assert revoked_list.status_code == 401, f"Revoked token expected 401, got {revoked_list.status_code}"

    revoked_get = client.get("/mcp/tools", headers=runtime_headers)
    assert revoked_get.status_code == 401

def test_ssrf_validation_and_transport_pinning():
    """Validates SSRF prevention rules and transport-level network blocking."""
    # 1. Loopback addresses
    for blocked_url in ["http://127.0.0.1:8000", "http://localhost:8000", "http://[::1]:8000"]:
        with pytest.raises(SSRFViolationError):
            assert_public_url(blocked_url)

    # 2. Private networks
    for private_url in ["http://10.0.0.1", "http://192.168.1.1", "http://172.16.0.1"]:
        with pytest.raises(SSRFViolationError):
            assert_public_url(private_url)

    # 3. Cloud metadata endpoint
    with pytest.raises(SSRFViolationError):
        assert_public_url("http://169.254.169.254/latest/meta-data/")

    # 4. Non-standard ports
    with pytest.raises(SSRFViolationError):
        assert_public_url("http://example.com:2222")

    # 5. Unsupported schemes
    with pytest.raises(SSRFViolationError):
        assert_public_url("ftp://example.com/file")
    with pytest.raises(SSRFViolationError):
        assert_public_url("file:///etc/passwd")


@pytest.mark.asyncio
async def test_guarded_transport_loopback_connection_blocked():
    """Verify that GuardedTransport strictly blocks TCP connections to loopback targets."""
    transport = GuardedTransport(allow_private=False)
    async_client = httpx.AsyncClient(transport=transport)
    try:
        with pytest.raises((SSRFViolationError, httpx.ConnectError)):
            await async_client.get("http://127.0.0.1:8000")
    finally:
        await async_client.aclose()


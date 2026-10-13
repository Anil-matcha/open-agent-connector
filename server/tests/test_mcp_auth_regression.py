"""
Regression tests for the P0 MCP authentication boundary.
Runs in-process (no live server): every remote MCP call must fail closed.
"""
import json

import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.services.mcp_service import McpService



@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs startup so tables exist
        yield c

ADMIN = {"Authorization": f"Bearer {settings.ADMIN_TOKEN}"}
BAD = {"Authorization": "Bearer not-a-real-token"}

RPC_CALLS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
     "params": {"name": "list_connections", "arguments": {}}},
    {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
     "params": {"name": "execute_action",
                "arguments": {"actionId": "github.get_current_user"}}},
]


@pytest.mark.parametrize("rpc", RPC_CALLS)
def test_mcp_rejects_anonymous(client, rpc):
    assert client.post("/mcp", json=rpc).status_code == 401


@pytest.mark.parametrize("rpc", RPC_CALLS)
def test_mcp_rejects_invalid_token(client, rpc):
    assert client.post("/mcp", json=rpc, headers=BAD).status_code == 401


def test_mcp_tools_endpoint_requires_auth(client):
    assert client.get("/mcp/tools").status_code == 401
    assert client.get("/mcp/tools", headers=BAD).status_code == 401
    assert client.get("/mcp/tools", headers=ADMIN).status_code == 200


def test_mcp_admin_can_list_tools(client):
    res = client.post("/mcp", json=RPC_CALLS[2], headers=ADMIN)
    assert res.status_code == 200
    assert len(res.json()["result"]["tools"]) > 5


@pytest.mark.asyncio
async def test_service_refuses_missing_principal():
    result = await McpService.handle_call_tool(
        session=None, name="execute_action",
        arguments={"actionId": "github.get_current_user"}, principal=None)
    assert "error" in result


def test_service_hides_actions_without_principal():
    tools = McpService.get_tool_definitions(include_actions=True, principal=None)
    assert {t["name"] for t in tools} == {
        "list_apps", "list_connections", "search_actions",
        "get_action_guide", "execute_action"}


def test_local_token_not_leaked_through_proxy_headers(client):
    assert client.get("/api/auth/status", headers={"X-Forwarded-For": "1.2.3.4"}
                      ).json()["localToken"] is None

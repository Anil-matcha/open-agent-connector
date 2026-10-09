"""
Model Context Protocol (MCP) STDIO transport server for ConnectorHub.
Allows Claude Desktop, Cursor, and any MCP client to communicate via stdin/stdout.
"""
import sys
import os
import json
import asyncio
from typing import Optional
from pathlib import Path

# Ensure 'server' directory is on sys.path regardless of how this script is invoked
server_dir = Path(__file__).resolve().parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from app.db.session import AsyncSessionLocal
from app.services.mcp_service import McpService
from app.core.auth import resolve_principal, Principal
from app.core.config import settings

# In local stdio mode, check if a specific runtime token is passed via environment
stdio_token = os.environ.get("CONNECTOR_RUNTIME_TOKEN") or os.environ.get("CONNECTOR_ADMIN_TOKEN")

async def get_active_principal(session) -> Optional[Principal]:
    if stdio_token:
        p = await resolve_principal(stdio_token, session)
        if p:
            return p
    # By default, local terminal stdio runs with Operator Admin principal
    return Principal(
        kind="admin",
        id="stdio-operator",
        name="Local Desktop Operator",
        allowed_actions=["*"],
        allowed_connections=["*"],
        allowed_proxies=["*"]
    )

async def process_message(line: str):
    if not line.strip():
        return
    try:
        rpc = json.loads(line)
    except Exception:
        response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: Invalid JSON"}
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
        return

    rpc_id = rpc.get("id")
    method = rpc.get("method")
    params = rpc.get("params") or {}

    # Handle notifications (requests without 'id')
    if rpc_id is None and method in ["notifications/initialized", "initialized"]:
        return

    # 1. MCP Handshake: initialize
    if method == "initialize":
        res = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "connector-hub",
                    "version": "1.0.0"
                }
            }
        }
    # 2. Ping
    elif method == "ping":
        res = {"jsonrpc": "2.0", "id": rpc_id, "result": {}}

    # 3. List tools
    elif method == "tools/list":
        async with AsyncSessionLocal() as session:
            principal = await get_active_principal(session)
            tools = McpService.get_tool_definitions(include_actions=True, principal=principal)
            res = {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": tools}}

    # 4. Call tool
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        async with AsyncSessionLocal() as session:
            principal = await get_active_principal(session)
            try:
                tool_res = await McpService.handle_call_tool(
                    session=session,
                    name=tool_name,
                    arguments=args,
                    principal=principal
                )
                is_err = isinstance(tool_res, dict) and "error" in tool_res
                res = {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "isError": is_err,
                        "content": [
                            {"type": "text", "text": tool_res.get("error") if is_err else str(tool_res)}
                        ],
                        "data": tool_res
                    }
                }
            except Exception as e:
                res = {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                    }
                }
    else:
        res = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32601, "message": f"Method not found: '{method}'"}
        }

    sys.stdout.write(json.dumps(res) + "\n")
    sys.stdout.flush()

async def main():
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            break
        await process_message(line)

if __name__ == "__main__":
    asyncio.run(main())

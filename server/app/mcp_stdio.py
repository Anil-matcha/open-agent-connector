"""
Model Context Protocol (MCP) STDIO transport server for ConnectorHub.
Allows Claude Desktop, Cursor, and any MCP client to communicate via stdin/stdout.
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# Ensure 'server' directory is on sys.path regardless of how this script is invoked
server_dir = Path(__file__).resolve().parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from app.db.session import AsyncSessionLocal
from app.services.mcp_service import McpService


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
        tools = McpService.get_tool_definitions(include_actions=True)
        res = {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": tools}}

    # 4. Call tool
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        async with AsyncSessionLocal() as session:
            try:
                tool_res = await McpService.handle_call_tool(session, tool_name, args)
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

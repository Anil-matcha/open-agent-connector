from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.session import get_db
from app.services.mcp_service import McpService

router = APIRouter(tags=["MCP"])

@router.get("/mcp/tools")
async def list_mcp_tools():
    """List tool definitions for MCP clients and preview inspectors."""
    return {"tools": McpService.get_tool_definitions()}

@router.post("/mcp")
async def handle_mcp_jsonrpc(request: Request, db: AsyncSession = Depends(get_db)):
    """Full Model Context Protocol (MCP) JSON-RPC 2.0 endpoint for Claude Desktop, Cursor, Antigravity, and all MCP agents."""
    try:
        rpc = await request.json()
    except Exception:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: Invalid JSON"}
        }

    rpc_id = rpc.get("id")
    method = rpc.get("method")
    params = rpc.get("params") or {}

    # Handle notifications (requests without 'id')
    if rpc_id is None and method in ["notifications/initialized", "initialized"]:
        return {"status": "ok"}

    # 1. MCP Protocol Handshake: 'initialize'
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "connector-hub",
                    "version": "1.0.0"
                }
            }
        }

    # 2. Heartbeat: 'ping'
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {}
        }

    # 3. Discovery: 'tools/list'
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "tools": McpService.get_tool_definitions(include_actions=True)
            }
        }

    # 4. Tool Execution: 'tools/call'
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            tool_result = await McpService.handle_call_tool(db, tool_name, arguments)
            is_err = isinstance(tool_result, dict) and "error" in tool_result
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "isError": is_err,
                    "content": [
                        {
                            "type": "text",
                            "text": tool_result.get("error") if is_err else str(tool_result)
                        }
                    ],
                    "data": tool_result
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                    "error": str(e)
                }
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32601, "message": f"Method not found: '{method}'"}
        }

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.services.mcp_service import McpService
from app.core.auth import resolve_principal, _extract_token, Principal

router = APIRouter(tags=["MCP"])


async def _require_mcp_principal(request: Request, db: AsyncSession) -> Principal:
    """Fail closed: every remote MCP call needs a valid admin or runtime token."""
    token = _extract_token(request)
    principal = await resolve_principal(token, db) if token else None
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: missing, invalid, or revoked token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


@router.get("/mcp/tools")
async def list_mcp_tools(request: Request, db: AsyncSession = Depends(get_db)):
    """List tool definitions for MCP clients, scoped to caller credentials."""
    principal = await _require_mcp_principal(request, db)
    return {"tools": McpService.get_tool_definitions(include_actions=True, principal=principal)}


@router.post("/mcp")
async def handle_mcp_jsonrpc(request: Request, db: AsyncSession = Depends(get_db)):
    """Full Model Context Protocol (MCP) JSON-RPC 2.0 endpoint for Claude Desktop, Cursor, Antigravity, and all MCP agents."""
    principal = await _require_mcp_principal(request, db)

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
        client_version = params.get("protocolVersion")
        supported_versions = ["2025-11-25", "2024-11-05"]
        negotiated_version = client_version if client_version in supported_versions else "2025-11-25"

        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": negotiated_version,
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
        tools = McpService.get_tool_definitions(include_actions=True, principal=principal)
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "tools": tools
            }
        }

    # 4. Tool Execution: 'tools/call'
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            tool_result = await McpService.handle_call_tool(
                session=db,
                name=tool_name,
                arguments=arguments,
                principal=principal
            )
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

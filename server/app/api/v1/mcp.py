from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.services.mcp_service import McpService
from app.core.auth import resolve_principal, _extract_token, Principal
from app.core.config import settings

router = APIRouter(tags=["MCP"])

def _is_loopback_request(request: Request) -> bool:
    """Checks if incoming HTTP request originates from a local loopback client."""
    client_host = request.client.host if request.client else ""
    return client_host in ("127.0.0.1", "::1", "localhost", "testclient")

async def _authenticate_mcp_request(request: Request, db: AsyncSession) -> Optional[Principal]:
    """
    Resolves principal from Authorization or dedicated token headers.
    Enforces fail-closed authentication unless ALLOW_ANONYMOUS_MCP is explicitly enabled on loopback.
    Raises HTTP 401 Unauthorized for missing, invalid, or revoked tokens.
    """
    token = _extract_token(request)
    if not token:
        if settings.ALLOW_ANONYMOUS_MCP and _is_loopback_request(request):
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP authentication required: missing bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    principal = await resolve_principal(token, db)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP authentication failed: invalid or revoked bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return principal

@router.get("/mcp/tools")
async def list_mcp_tools(request: Request, db: AsyncSession = Depends(get_db)):
    """List tool definitions for MCP clients, scoped to caller credentials."""
    principal = await _authenticate_mcp_request(request, db)
    return {"tools": McpService.get_tool_definitions(include_actions=True, principal=principal)}

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

    # All operational methods (tools/list, tools/call, etc.) require an authenticated principal
    principal = await _authenticate_mcp_request(request, db)

    # 3. Discovery: 'tools/list'
    if method == "tools/list":
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

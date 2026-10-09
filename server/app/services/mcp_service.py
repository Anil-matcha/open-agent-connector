from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.providers.registry import registry
from app.services.connection_service import ConnectionService
from app.services.action_runner import ActionRunner

class McpService:
    @staticmethod
    def get_tool_definitions(include_actions: bool = True, principal: Optional[Any] = None) -> List[Dict[str, Any]]:
        # 1. Core discovery and metadata tools
        tools = [
            {
                "name": "list_apps",
                "description": "List every provider app in the catalog. Returns service IDs, display names, categories, and auth requirements.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Optional category filter"}
                    }
                }
            },
            {
                "name": "list_connections",
                "description": "List configured provider accounts with safe identities and display names (no secrets returned).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Optional service ID filter"}
                    }
                }
            },
            {
                "name": "search_actions",
                "description": "Search catalog actions by free-text keywords or provider service ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keywords to match against action names or descriptions"},
                        "service": {"type": "string", "description": "Optional service ID to filter (e.g. github, hackernews)"}
                    }
                }
            },
            {
                "name": "get_action_guide",
                "description": "Get detailed Markdown parameter documentation and usage schema for a specific action ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actionId": {"type": "string", "description": "Full action ID (e.g. github.get_current_user or github.create_issue)"}
                    },
                    "required": ["actionId"]
                }
            },
            {
                "name": "execute_action",
                "description": "Execute any provider action with input arguments. Returns live upstream results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "actionId": {"type": "string", "description": "Action ID (e.g. github.create_issue or github.get_current_user)"},
                        "input": {"type": "object", "description": "JSON arguments matching the action's schema"},
                        "connectionName": {"type": "string", "description": "Optional connection alias (defaults to 'default')"}
                    },
                    "required": ["actionId"]
                }
            }
        ]

        # 2. Expose individual actions directly, filtered by caller's permissions
        if include_actions:
            for action in registry.list_actions():
                # If caller principal has scoped permissions, filter actions
                if principal and not principal.can_access_action(action.id):
                    continue

                provider = registry.get_action_provider(action.id)
                tool_name = action.id.replace(".", "_")
                
                clean_schema = dict(action.input_schema or {"type": "object", "properties": {}})
                clean_schema.setdefault("type", "object")
                clean_schema.setdefault("properties", {})
                
                if "connectionName" not in clean_schema["properties"]:
                    clean_schema["properties"]["connectionName"] = {
                        "type": "string",
                        "description": "Optional connection alias (defaults to 'default')"
                    }

                tools.append({
                    "name": tool_name,
                    "description": f"[{provider.display_name if provider else 'Provider'}] {action.description}",
                    "inputSchema": clean_schema
                })

        return tools

    @staticmethod
    async def handle_call_tool(
        session: AsyncSession,
        name: str,
        arguments: Dict[str, Any],
        principal: Optional[Any] = None
    ) -> Dict[str, Any]:
        args = dict(arguments or {})

        # 1. Meta Tools
        if name == "list_apps":
            providers = registry.list_providers()
            category = args.get("category")
            if category:
                providers = [p for p in providers if p.category.lower() == category.lower()]
            return {
                "apps": [
                    {
                        "service": p.service,
                        "displayName": p.display_name,
                        "category": p.category,
                        "authTypes": p.auth_types,
                        "actionCount": len(p.actions),
                        "description": p.description
                    }
                    for p in providers
                ]
            }

        elif name == "list_connections":
            conns = await ConnectionService.list_connections(session, args.get("service"))
            # If principal is restricted by connection, filter results
            if principal and not principal.is_admin and principal.allowed_connections:
                conns = [c for c in conns if c["connectionName"] in principal.allowed_connections]
            return {"connections": conns}

        elif name == "search_actions":
            matched = registry.search_actions(args.get("query", ""), args.get("service"))
            if principal and not principal.is_admin:
                matched = [a for a in matched if principal.can_access_action(a.id)]
            return {
                "actions": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "category": getattr(a, "category", "General"),
                        "requiredScopes": a.required_scopes
                    }
                    for a in matched
                ]
            }

        elif name == "get_action_guide":
            action_id = args.get("actionId", "")
            action = registry.get_action(action_id)
            if not action and "_" in action_id:
                action = registry.get_action(action_id.replace("_", ".", 1))
            if not action:
                return {"error": f"Unknown action: '{action_id}'"}

            if principal and not principal.can_access_action(action.id):
                return {"error": f"Permission denied: action '{action.id}' is not authorized for this token"}
            
            provider = registry.get_action_provider(action.id)
            props = action.input_schema.get("properties", {})
            required = action.input_schema.get("required", [])
            
            guide = [
                f"# Action: {action.name} (`{action.id}`)",
                f"**Provider**: {provider.display_name if provider else 'Unknown'}",
                f"**Description**: {action.description}",
                "",
                "### Required Scopes",
                ", ".join(action.required_scopes) if action.required_scopes else "None",
                "",
                "### Input Parameters",
            ]
            if not props:
                guide.append("This action requires no input parameters (`input: {}`).")
            else:
                guide.append("| Parameter | Type | Required | Description |")
                guide.append("| :--- | :--- | :--- | :--- |")
                for k, v in props.items():
                    req_badge = "**Yes**" if k in required else "No"
                    guide.append(f"| `{k}` | `{v.get('type', 'any')}` | {req_badge} | {v.get('description', '')} |")

            return {
                "actionId": action.id,
                "markdown": "\n".join(guide),
                "schema": action.input_schema
            }

        elif name == "execute_action":
            action_id = args.get("actionId", "")
            input_data = args.get("input", {})
            conn_name = args.get("connectionName", "default")

            if principal:
                if not principal.can_access_action(action_id):
                    return {"error": f"Permission denied: action '{action_id}' is not authorized for this token"}
                if not principal.can_access_connection(conn_name):
                    return {"error": f"Permission denied: connection '{conn_name}' is not authorized for this token"}

            return await ActionRunner.run(
                session=session,
                action_id=action_id,
                input_data=input_data,
                connection_name=conn_name,
                caller="mcp",
                principal_id=principal.id if principal else None
            )

        # 2. Direct Action Execution (e.g. github_create_issue, github_get_current_user)
        target_action = registry.get_action(name)
        if not target_action and "_" in name:
            candidate = name.replace("_", ".", 1)
            target_action = registry.get_action(candidate)

        if target_action:
            conn_name = args.pop("connectionName", "default")
            if principal:
                if not principal.can_access_action(target_action.id):
                    return {"error": f"Permission denied: action '{target_action.id}' is not authorized for this token"}
                if not principal.can_access_connection(conn_name):
                    return {"error": f"Permission denied: connection '{conn_name}' is not authorized for this token"}

            return await ActionRunner.run(
                session=session,
                action_id=target_action.id,
                input_data=args,
                connection_name=conn_name,
                caller="mcp",
                principal_id=principal.id if principal else None
            )

        return {"error": f"Unknown MCP tool: '{name}'"}

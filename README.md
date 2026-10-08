# Open Agent Connector

**An open-source, self-hosted integration gateway for AI agents.** Connect accounts to app APIs, keep credentials in your own runtime, and let agents discover and run actions through the Model Context Protocol (MCP) or a REST API.

This project is for developers who want to inspect, run, and extend their own agent integration layer. It is an early-stage open-source option to evaluate alongside [Composio](https://composio.dev/), [Nango](https://nango.dev/), [Merge.dev](https://www.merge.dev/), and [Arcade.dev](https://www.arcade.dev/). Those platforms offer broader catalogs and managed capabilities; Open Agent Connector currently prioritizes a compact self-hosted implementation that you can modify.

## Project description

Open Agent Connector gives an agent a consistent way to discover connected services, find an action, read its input schema, and execute it. A FastAPI backend manages provider definitions, connections, outbound requests, and run records. A Next.js console provides screens for browsing providers and actions, managing connections and runtime tokens, and reviewing activity. SQLite stores application data locally by default.

The current built-in providers are **GitHub**, **Slack**, **Hacker News**, and **Custom HTTP**. The GitHub catalog contains 147 action definitions. The other providers have a smaller set of focused actions. The catalog is code-defined and intentionally extensible; it is not a claim of broad coverage across third-party apps.

## Features

- **MCP gateway:** supports JSON-RPC methods for initialization, ping, tool discovery, and tool execution over `POST /mcp`.
- **Action discovery:** agents can list providers, search actions, inspect action guides and schemas, and execute actions.
- **Direct MCP actions:** provider actions are also exposed as individual MCP tools, alongside five discovery and execution tools.
- **REST API:** list providers and actions, execute an action, or use a provider proxy where supported.
- **Connections:** save named provider connections; credential values are encrypted before they are stored.
- **Local web console:** browse the catalog, configure connections, and view token and run-log screens.
- **Request safeguards:** outbound HTTP requests check destination addresses to block private and internal targets by default. Cloud metadata and loopback targets remain blocked.
- **Idempotent execution:** action requests can use an `Idempotency-Key`; matching completed requests can return a saved response instead of repeating the upstream call.
- **Run records:** action executions record status, timing, and bounded input/output summaries for inspection.
- **Extensible providers:** provider and action definitions live in Python, with the GitHub action catalog in JSON.

## How it compares

These products overlap in connecting apps to software and AI agents, but they have different scopes. Composio centers on a large app toolkit and agent execution platform. Nango focuses on building and operating product integrations, including auth and sync. Merge.dev provides unified APIs and common models across product integration categories. Arcade.dev focuses on agent-ready tools, authentication, and runtime controls. Open Agent Connector is a smaller self-hosted project for teams who want to own and extend the integration service.

Choose based on the catalog breadth, managed operations, authentication, security controls, and support your application needs. Open Agent Connector is still early-stage and should not be treated as feature-equivalent to those established services.

## Architecture

```text
Agent or application
        │
        ├── MCP JSON-RPC: POST /mcp
        └── REST: /v1/*
                │
        FastAPI action runtime
        ├── provider and action registry
        ├── connection and credential handling
        ├── guarded outbound HTTP client
        └── run logs and idempotency records
                │
        SQLite database + external provider APIs

Next.js web console ───────────────┘
```

### Stack

| Area | Technology |
| --- | --- |
| Web console | Next.js App Router, React, TypeScript, Tailwind CSS |
| API and runtime | FastAPI, Python, Pydantic |
| Persistence | SQLite, SQLAlchemy async, aiosqlite |
| Credential encryption | AES-256-GCM via `cryptography` |
| Agent interface | MCP JSON-RPC over HTTP |

## Built-in providers

| Provider | Authentication | Examples |
| --- | --- | --- |
| GitHub | Personal access token or OAuth access token | Repository, issue, pull request, workflow, and user actions from the JSON catalog |
| Slack | Bot or OAuth access token | Post a message and list channels |
| Hacker News | None | Get top stories, retrieve an item, and search stories |
| Custom HTTP | None or API key | Send an SSRF-guarded HTTP request to an external HTTP or HTTPS endpoint |

Provider availability and action inputs are defined by the running catalog. Query `GET /v1/providers` and `GET /v1/actions` for the current schemas.

## Quick start

### Requirements

- Python 3.11 or newer
- Node.js and npm

### 1. Run the API

```bash
cd server
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

On Windows PowerShell, activate the environment with:

```powershell
venv\Scripts\Activate.ps1
```

The API creates its SQLite database and a local encryption key on first startup if they do not exist. For a durable deployment, configure and back up a stable key before saving credentials; losing the key makes previously encrypted credentials unreadable.

### 2. Run the web console

Open another terminal from the repository root:

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The console uses `http://localhost:8000` for the API by default. Set `NEXT_PUBLIC_API_URL` before starting or building the frontend to use a different API URL.

### Local service URLs

- Web console: `http://localhost:3000`
- Health check: `http://localhost:8000/health`
- Interactive API docs: `http://localhost:8000/docs`
- MCP endpoint: `http://localhost:8000/mcp`
- MCP tool preview: `http://localhost:8000/mcp/tools`

## Configuration

Backend settings use the `CONNECTOR_` environment prefix. A `.env` file in the `server/` directory is loaded when you launch Uvicorn from that directory.

| Variable | Purpose | Default |
| --- | --- | --- |
| `CONNECTOR_HOST` | API bind address | `127.0.0.1` |
| `CONNECTOR_PORT` | API port | `8000` |
| `CONNECTOR_PUBLIC_ORIGIN` | Public origin used by the service | `http://localhost:8000` |
| `CONNECTOR_DATABASE_URL` | SQLAlchemy async database URL | SQLite file under `server/data/` |
| `CONNECTOR_DATA_DIR` | Application data directory | `server/data/` |
| `CONNECTOR_ENCRYPTION_KEY` | Stable key used to encrypt stored secrets | Generated local key file if unset |
| `CONNECTOR_ALLOW_PRIVATE_NETWORK` | Allow private network destinations for outbound requests | `false` |
| `NEXT_PUBLIC_API_URL` | API base URL used by the browser frontend | `http://localhost:8000` |

Set `CONNECTOR_ENCRYPTION_KEY` to a strong, stable secret before creating connections in an environment you need to preserve. Back up the key separately from the database and restrict access to both. Do not commit `.env` files or secret values.

## Connect an account

1. Start both the API and web console.
2. Open the **Connections** screen and select a provider.
3. Add the required token or credential fields and choose a connection name, such as `default`.
4. Browse the **Actions** screen to inspect available operations and their inputs.
5. Use MCP or the REST API to call an action with that connection name.

GitHub and Slack credentials are validated against their provider APIs when saved. Hacker News does not require credentials. Custom HTTP can use no auth or a saved API key.

## MCP usage

Configure an MCP client that supports remote HTTP MCP with the local endpoint:

```json
{
  "mcpServers": {
    "open-agent-connector": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

The MCP endpoint provides discovery tools for listing apps and connections, searching actions, retrieving an action guide, and executing an action. It also exposes individual provider actions. An action call may include a `connectionName` argument; it defaults to `default`.

## REST API examples

List providers:

```bash
curl http://localhost:8000/v1/providers
```

Search GitHub actions:

```bash
curl 'http://localhost:8000/v1/actions?service=github&query=issue'
```

Execute an action after configuring a GitHub connection:

```bash
curl -X POST http://localhost:8000/v1/actions/github.get_current_user \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-request-001' \
  -d '{"input": {}, "connectionName": "default"}'
```

### Main routes

| Route | Purpose |
| --- | --- |
| `GET /v1/providers` | List providers; accepts an optional `category` filter |
| `GET /v1/providers/{service}` | Get a provider and its actions |
| `GET /v1/actions` | Search actions; accepts `query` and `service` filters |
| `GET /v1/actions/{action_id}` | Get an action schema and provider details |
| `POST /v1/actions/{action_id}` | Execute an action |
| `POST /v1/proxy/{service}` | Use a provider's proxy implementation where available |
| `POST /mcp` | MCP JSON-RPC endpoint |
| `GET /mcp/tools` | List MCP tool definitions |
| `/api/connections` | Create, list, and delete saved connections |
| `/api/runtime-tokens` | Create, list, and revoke runtime token records |
| `/api/runs` and `/api/stats` | Inspect run records and summary statistics |

Action execution accepts an `input` object and optional `connectionName`. You can also select a connection with the `x-connector-alias` header. The `Idempotency-Key` header is supported on action execution.

## Extending the catalog

Providers are registered in `server/app/providers/registry.py`. Built-in implementations live in `server/app/providers/builtins/` and share the base classes in `server/app/providers/base.py`.

To add an action:

1. Define its stable action ID, display name, description, input JSON schema, and required scopes.
2. Implement its asynchronous `execute` method using the shared HTTP client and the provider credential passed to it.
3. Register it from the provider implementation and register the provider in the registry.
4. Add or update credential validation if the provider requires authentication.
5. Confirm the action schema works through both the REST API and MCP clients.

GitHub actions are data-driven from `server/app/providers/builtins/github_actions.json`; the other providers define actions in Python.

## Data and security notes

- The default database and generated local key are stored under `server/data/`; keep this directory out of source control and protect it in backups.
- Connection credentials are encrypted at rest with AES-256-GCM. The database alone is not sufficient to recover them; the encryption key must also be preserved securely.
- Outbound requests check resolved IP addresses and block private or internal destinations by default. The `CONNECTOR_ALLOW_PRIVATE_NETWORK` option relaxes some private-address blocking and should be used only in a controlled environment. Loopback, link-local, and metadata addresses remain blocked.
- Run logs keep bounded summaries of action inputs and outputs. Avoid sending sensitive values in action inputs unless you have reviewed how the logs are stored and protected.
- **Authentication is not yet enforced by middleware on the HTTP API, admin routes, or MCP endpoint.** Runtime token records and configuration fields are present, but they do not currently form an access-control boundary. Keep the service bound to localhost for development. Before exposing it to a network or using production credentials, add and verify authentication, authorization, and deployment controls.

## Development

Backend dependencies are listed in `server/requirements.txt`. Frontend scripts are defined in `client/package.json`:

```bash
cd client
npm run lint
npm run build
```

For API changes, run the backend locally with Uvicorn's reload option and use `/docs` to inspect the generated OpenAPI schema.

## Project status

Open Agent Connector is an early-stage project. Expect a smaller integration catalog and fewer production operations features than mature integration platforms. Contributions that improve provider coverage, authentication, authorization, deployment guidance, and observability are welcome.

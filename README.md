# Open Agent Connector

**An open-source, self-hosted integration gateway for AI agents.** Connect accounts to app APIs, keep credentials in your own runtime, and let agents discover and run actions through the Model Context Protocol (MCP) or a REST API.

This project is for developers who want to inspect, run, and extend their own agent integration layer. It is an open-source option to evaluate alongside [Composio](https://composio.dev/), [Nango](https://nango.dev/), [Merge.dev](https://www.merge.dev/), and [Arcade.dev](https://www.arcade.dev/). Those platforms offer broader catalogs and managed capabilities; Open Agent Connector currently prioritizes a compact self-hosted implementation that you can modify.

## Project description

Open Agent Connector gives an agent a consistent way to discover connected services, find an action, read its input schema, and execute it. A FastAPI backend manages provider definitions, connections, outbound requests, and run records. A Next.js console provides screens for browsing providers and actions, managing connections and runtime tokens, and reviewing activity. SQLite stores application data locally by default.

The catalog currently registers **236 providers** with **8,024 actions** (counted from `server/app/providers/registry.py` and `actions_catalog.json`). The catalog is code-defined and extensible. Registered does not mean battle-tested: not every provider action or OAuth flow has been verified against a live account, so confirm the ones you depend on.

## Features

- **MCP gateway:** supports JSON-RPC methods for initialization, ping, tool discovery, and tool execution over `POST /mcp`. Every MCP call requires an admin or runtime token.
- **Scoped runtime tokens:** hashed, revocable tokens with deny-by-default action grants plus optional connection and proxy restrictions.
- **OAuth:** authorization URL, state and code exchange, encrypted token storage, and refresh for providers that support OAuth.
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

Choose based on the catalog breadth, managed operations, authentication, security controls, and support your application needs. Open Agent Connector has a smaller catalog and fewer production operations features than those established services.

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

## Providers

The registry holds 236 providers (GitHub, Slack, Notion, Linear, Gmail and many more) and 8,024 actions. Authentication types differ per provider (API key, personal access token, OAuth). Provider availability and action inputs are defined by the running catalog, so query `GET /v1/providers` and `GET /v1/actions` for the current list and schemas.

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
| `CONNECTOR_ADMIN_TOKEN` | Bearer token for the admin API and console | Generated into `server/data/.admin_token` if unset |
| `CONNECTOR_RUNTIME_TOKEN` | Optional static runtime token for `/v1` and `/mcp` | Unset |
| `CONNECTOR_EXPOSE_LOCAL_TOKEN` | Let `/api/auth/status` return the admin token to genuine loopback callers (never when proxy headers are present). Set `false` on any network-facing deployment. | `true` |
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
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer <runtime-or-admin-token>" }
    }
  }
}
```

A token is required. Unauthenticated, invalid, or revoked tokens receive `401`. Tool discovery and execution are filtered by the token's action and connection grants.

The MCP endpoint provides discovery tools for listing apps and connections, searching actions, retrieving an action guide, and executing an action. It also exposes individual provider actions. An action call may include a `connectionName` argument; it defaults to `default`.

## REST API examples

List providers:

```bash
curl http://localhost:8000/v1/providers
```

(Catalog browsing is public; execution below needs a token.)

Search GitHub actions:

```bash
curl 'http://localhost:8000/v1/actions?service=github&query=issue'
```

Execute an action after configuring a GitHub connection:

```bash
curl -X POST http://localhost:8000/v1/actions/github.get_current_user \
  -H 'Authorization: Bearer <runtime-or-admin-token>' \
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
| `POST /mcp` | MCP JSON-RPC endpoint (runtime or admin token) |
| `GET /mcp/tools` | List MCP tool definitions (runtime or admin token) |
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

Provider actions are maintained in a single unified catalog at `server/app/providers/actions_catalog.json`, partitioned by provider service ID for simple, scalable expansion.

## Data and security notes

- The default database and generated local key are stored under `server/data/`; keep this directory out of source control and protect it in backups.
- Connection credentials are encrypted at rest with AES-256-GCM. The database alone is not sufficient to recover them; the encryption key must also be preserved securely.
- Outbound requests check resolved IP addresses and block private or internal destinations by default. The `CONNECTOR_ALLOW_PRIVATE_NETWORK` option relaxes some private-address blocking and should be used only in a controlled environment. Loopback, link-local, and metadata addresses remain blocked.
- Run logs keep bounded summaries of action inputs and outputs. Avoid sending sensitive values in action inputs unless you have reviewed how the logs are stored and protected.
- **Authentication is enforced per route:**

  | Routes | Credential |
  | --- | --- |
  | `/api/*` (connections, runtime tokens, runs, stats, OAuth config and authorize) | Admin token |
  | `POST /v1/actions/{id}`, `POST /v1/proxy/{service}` | Runtime or admin token, plus action, connection, and proxy grants |
  | `POST /mcp`, `GET /mcp/tools` | Runtime or admin token (fail closed) |
  | `GET /v1/providers`, `GET /v1/actions`, `/health`, `/docs`, OAuth callback, `/api/auth/status` and `/api/auth/verify` | Public. These expose catalog metadata or the OAuth redirect, not credentials. |

- **Behind a reverse proxy**, set `CONNECTOR_EXPOSE_LOCAL_TOKEN=false`, bind the API to loopback or a private network, terminate TLS at the proxy, and rate-limit `/api/auth/verify`. See `docker-compose.prod.yml` for a loopback-only overlay.
- **Known limitations:** outbound DNS is validated separately from the HTTP client's own resolution, so DNS rebinding is not fully closed; schema migrations are SQLite-oriented, so run a single instance; the MCP endpoint is a custom JSON-RPC implementation (protocol versions `2025-11-25` and `2024-11-05`) rather than the official SDK.

## Production deployment

```bash
# .env.prod: PUBLIC_ORIGIN=https://connector.example.com
#            ADMIN_TOKEN=<long random value>  ENCRYPTION_KEY=<long random value>
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

This publishes the API on `127.0.0.1:8100` and the console on `127.0.0.1:3100`. Put nginx or another TLS-terminating proxy in front: route `/api`, `/v1`, `/mcp`, `/health`, and `/docs` to the API and everything else to the console. Back up `.env.prod` and the `connector_data` volume together; without the encryption key, saved credentials cannot be decrypted. Run one instance only.

## Development

Backend dependencies are listed in `server/requirements.txt`. Frontend scripts are defined in `client/package.json`:

```bash
cd client
npm run lint
npm run build
```

For API changes, run the backend locally with Uvicorn's reload option and use `/docs` to inspect the generated OpenAPI schema.

Run the in-process MCP authentication regression tests from `server/`:

```bash
pip install pytest pytest-asyncio
CONNECTOR_ADMIN_TOKEN=test-admin python -m pytest tests/test_mcp_auth_regression.py
```

## Project status

Open Agent Connector offers a focused integration catalog and is continuing to expand its production operations features. Contributions that improve provider coverage, authentication, authorization, deployment guidance, and observability are welcome.

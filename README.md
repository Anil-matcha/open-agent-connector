# Open Agent Connector

**An open-source, self-hosted integration gateway for AI agents.** Connect accounts to app APIs, keep credentials in your own runtime, and let agents discover and run actions through the Model Context Protocol (MCP) or a REST API.

This project is for developers who want to inspect, run, and extend their own agent integration layer. It is an open-source option to evaluate alongside [Composio](https://composio.dev/), [Nango](https://nango.dev/), [Merge.dev](https://www.merge.dev/), and [Arcade.dev](https://www.arcade.dev/). Those platforms offer broader catalogs and managed capabilities; Open Agent Connector currently prioritizes a compact self-hosted implementation that you can modify.

## Project description

Open Agent Connector gives an agent a consistent way to discover connected services, find an action, read its input schema, and execute it. A FastAPI backend manages provider definitions, connections, outbound requests, and run records. A Next.js console provides screens for browsing providers and actions, managing connections and runtime tokens, and reviewing activity. SQLite stores application data locally by default.

## Project description

Open Agent Connector gives an agent a consistent way to discover connected services, find an action, read its input schema, and execute it. A FastAPI backend manages provider definitions, connections, outbound requests, and run records. A Next.js console provides screens for browsing providers and actions, managing connections and runtime tokens, and reviewing activity. SQLite stores application data locally by default, with PostgreSQL supported via SQLAlchemy async and Alembic migrations.

The registry currently integrates **236 providers** with a catalog of **8,024 actions** spanning Developer tools, Project Management & CRM, Communication, Storage, AI/ML, E-Commerce, Social Media, Financial, and Utilities. For a complete list of all 236 providers, auth types, action counts, and category classifications, see [PROVIDER_GUIDE.md](PROVIDER_GUIDE.md).

## Features

- **MCP gateway:** Model Context Protocol (MCP) JSON-RPC 2.0 endpoint over `POST /mcp` and tool discovery over `GET /mcp/tools`. Fails closed by default; requires runtime or admin authentication with granular scope enforcement.
- **Action discovery:** agents can list providers, search actions, inspect action guides and schemas, and execute actions.
- **Direct MCP actions:** provider actions are exposed as individual MCP tools (scoped to caller token grants), alongside discovery and execution meta-tools.
- **REST API:** list providers and actions, execute an action, or use a provider proxy where supported.
- **Connections & credentials:** save named provider connections; credential values are encrypted at rest with AES-256-GCM.
- **Local web console:** browse the 236-provider catalog, configure connections, execute test runs, and manage runtime tokens and audit logs.
- **Outbound HTTP safeguards:** SSRF protection with hop-by-hop redirect verification, cross-origin secret stripping, response size caps, and socket-level IP address pinning to eliminate DNS-rebinding attacks.
- **Idempotent execution:** action requests can use an `Idempotency-Key`; matching completed requests return saved responses and detect payload conflicts.
- **Run records:** action executions record duration, HTTP status, and bounded, secret-redacted input/output summaries.
- **Unified catalog:** 8,024 action schemas maintained in `server/app/providers/actions_catalog.json` and registered through extensible Python providers.

## How it compares

These products overlap in connecting apps to software and AI agents, but they have different scopes. Composio centers on a large app toolkit and agent execution platform. Nango focuses on building and operating product integrations, including auth and sync. Merge.dev provides unified APIs and common models across product integration categories. Arcade.dev focuses on agent-ready tools, authentication, and runtime controls. Open Agent Connector is a self-hosted integration gateway for teams who want to inspect, own, and customize their agent runtime.

## Architecture

```text
Agent or application
        │
        ├── MCP JSON-RPC: POST /mcp (authenticated)
        └── REST: /v1/* (authenticated execution)
                │
        FastAPI action runtime
        ├── provider and action registry (236 providers / 8,024 actions)
        ├── principal resolution & deny-by-default policy enforcement
        ├── connection & AES-256-GCM credential encryption
        ├── DNS-pinned guarded outbound HTTP client (SSRF & rebinding guard)
        └── audit run logs and idempotency records
                │
        SQLite / PostgreSQL database + external provider APIs
                │
Next.js web console ────────┘
```

### Stack

| Area | Technology |
| --- | --- |
| Web console | Next.js App Router, React, TypeScript, Tailwind CSS |
| API and runtime | FastAPI, Python 3.11+, Pydantic v2 |
| Persistence | SQLite / PostgreSQL, SQLAlchemy async, aiosqlite / asyncpg, Alembic |
| Credential encryption | AES-256-GCM via `cryptography` |
| Agent interface | MCP JSON-RPC 2.0 (HTTP & STDIO transports) |

## Provider catalog overview

The registry includes 236 providers across 10 functional domains. Below is a representative cross-section:

| Category | Provider count | Representative providers | Auth types |
| --- | --- | --- | --- |
| **Developer & DevOps** | 35+ | GitHub, GitLab, Docker, Kubernetes, AWS, Cloudflare, Sentry, Jira | API Key, OAuth2, Bearer Token |
| **Communication & Marketing** | 40+ | Slack, Discord, Twilio, SendGrid, Mailchimp, WhatsApp, Telegram, ClickSend | OAuth2, Bot Token, API Key |
| **CRM & Sales** | 25+ | HubSpot, Salesforce, Pipedrive, Zoho CRM, Capsule CRM, Close | OAuth2, API Key |
| **Project Management** | 30+ | Notion, Linear, Asana, Trello, ClickUp, Monday, Basecamp, Toggl | OAuth2, API Key, Token |
| **AI & Machine Learning** | 15+ | OpenAI, Anthropic, ElevenLabs, Perplexity, Replicate, Mistral, Groq | API Key |
| **Storage & Cloud** | 20+ | Google Drive, Dropbox, Box, OneDrive, AWS S3, Cloudinary | OAuth2, API Key |
| **E-Commerce & Billing** | 18+ | Shopify, Stripe, PayPal, Square, WooCommerce, Chargebee | OAuth2, API Key |
| **Social Media & Content** | 18+ | Twitter/X, LinkedIn, Reddit, YouTube, Medium, WordPress | OAuth2, API Key |
| **Financial & Accounting** | 12+ | QuickBooks, Xero, FreshBooks, Wave, Plaid | OAuth2, API Key |
| **Utilities & Data** | 20+ | Hacker News, OpenWeatherMap, Mapbox, IPinfo, Custom HTTP | None, API Key |

For the complete 236-provider matrix and action schemas, consult [PROVIDER_GUIDE.md](PROVIDER_GUIDE.md). Provider definitions and action schemas can also be queried programmatically via `GET /v1/providers` and `GET /v1/actions`.

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
| `CONNECTOR_DATABASE_URL` | SQLAlchemy async database URL (SQLite or PostgreSQL) | SQLite file under `server/data/connector.db` |
| `CONNECTOR_DATA_DIR` | Application data directory | `server/data/` |
| `CONNECTOR_ENCRYPTION_KEY` | Stable AES-256 key used to encrypt stored credentials | Generated local key file if unset |
| `CONNECTOR_ADMIN_TOKEN` | Bearer token required for `/api/*` management routes | Auto-generated in `server/data/.admin_token` |
| `CONNECTOR_RUNTIME_TOKEN` | Optional static Bearer token for runtime action execution | `""` (persistent DB tokens preferred) |
| `CONNECTOR_ALLOW_ANONYMOUS_MCP` | Explicit opt-in for unauthenticated MCP access (restricted to loopback) | `false` (fail-closed) |
| `CONNECTOR_ALLOW_PRIVATE_NETWORK` | Allow private network destinations for outbound requests | `false` |
| `NEXT_PUBLIC_API_URL` | API base URL used by the browser frontend | `http://localhost:8000` |

Set `CONNECTOR_ENCRYPTION_KEY` to a strong, stable secret before creating connections in an environment you need to preserve. Back up the key separately from the database and restrict access to both. Do not commit `.env` files or secret values.

## Connect an account

1. Start both the API and web console.
2. Open the **Connections** screen and select any of the 236 providers.
3. Add the required token, API key, or OAuth credentials and choose a connection alias, such as `default`.
4. Browse the **Actions** screen to inspect available operations, required scopes, and JSON input schemas.
5. Generate a scoped runtime token on the **Tokens** screen granting access to selected actions and connection aliases.
6. Use MCP or the REST API to execute actions securely under that token.

GitHub and Slack credentials are validated against their provider APIs when saved. Hacker News does not require credentials. Custom HTTP can use no auth or a saved API key.

## MCP usage

Configure an MCP client (such as Claude Desktop, Cursor, or Antigravity) that supports remote HTTP MCP with the local endpoint:

```json
{
  "mcpServers": {
    "open-agent-connector": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_RUNTIME_TOKEN_OR_ADMIN_TOKEN>"
      }
    }
  }
}
```

The MCP gateway provides five discovery and execution meta-tools:
- `list_apps`: list providers with display names, categories, and authentication requirements.
- `list_connections`: list configured accounts with safe identities (filtered by token grants).
- `search_actions`: search 8,024 catalog actions by keywords or provider service ID (scoped to token grants).
- `get_action_guide`: retrieve full Markdown parameter documentation and JSON Schema for an action.
- `execute_action`: execute an authorized action with input arguments and target connection alias.

Individual provider actions are also exposed as direct MCP tools (e.g. `github_get_current_user`), dynamically filtered by the caller's authorized action permissions.

## REST API examples

List providers:

```bash
curl http://localhost:8000/v1/providers
```

Search actions across catalog:

```bash
curl 'http://localhost:8000/v1/actions?service=github&query=issue'
```

Execute an action with a runtime token:

```bash
curl -X POST http://localhost:8000/v1/actions/github.get_current_user \
  -H 'Authorization: Bearer ch_live_your_runtime_token_here' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-request-001' \
  -d '{"input": {}, "connectionName": "default"}'
```

### Main routes

| Route | Purpose | Authentication |
| --- | --- | --- |
| `GET /v1/providers` | List providers; accepts an optional `category` filter | Public |
| `GET /v1/providers/{service}` | Get a provider and its actions | Public |
| `GET /v1/actions` | Search actions; accepts `query` and `service` filters | Scoped by Bearer token |
| `GET /v1/actions/{action_id}` | Get an action schema and provider details | Scoped by Bearer token |
| `POST /v1/actions/{action_id}` | Execute an action with scoped permissions | Runtime or Admin Bearer token |
| `POST /v1/proxy/{service}` | Use a provider's raw proxy implementation | Runtime or Admin Bearer token |
| `POST /mcp` | MCP JSON-RPC 2.0 endpoint (tools/list & tools/call) | Runtime or Admin Bearer token |
| `GET /mcp/tools` | List MCP tool definitions scoped to caller | Runtime or Admin Bearer token |
| `/api/connections` | Create, list, and delete saved provider connections | Admin Bearer token |
| `/api/runtime-tokens` | Create, list, and revoke runtime token records | Admin Bearer token |
| `/api/runs` and `/api/stats` | Inspect audit run records and execution statistics | Admin Bearer token |

Action execution accepts an `input` object and optional `connectionName`. You can also select a connection with the `x-connector-alias` header. The `Idempotency-Key` header is supported on action execution.

## Extending the catalog

Providers are registered in `server/app/providers/registry.py`. Built-in implementations live in `server/app/providers/builtins/` and share the base classes in `server/app/providers/base.py`.

To add a new provider action:

1. Define its stable action ID, display name, description, input JSON schema, and required scopes.
2. Implement its asynchronous `execute` method using the shared HTTP client and the provider credential passed to it.
3. Register it from the provider implementation and register the provider in the registry.
4. Add or update credential validation if the provider requires authentication.
5. Confirm the action schema works through both the REST API and MCP clients.

Provider actions are maintained in a unified catalog at `server/app/providers/actions_catalog.json`, partitioned by provider service ID for scalable expansion.

## Data and security notes

- **Route Authentication & Authorization**:
  - Management endpoints under `/api/*` require an Administrator Bearer token (`ADMIN_TOKEN`).
  - Action execution routes (`POST /v1/actions/*`) and proxy routes (`POST /v1/proxy/*`) enforce granular runtime authentication with deny-by-default wildcard action matching (`allowedActions`, `blockedActions`) and connection restrictions (`allowedConnections`).
  - Remote MCP HTTP endpoints (`POST /mcp` and `GET /mcp/tools`) fail closed by default, requiring a valid runtime or admin token for tool discovery and execution. Protocol handshakes (`initialize`, `ping`) are public for client negotiation. Local single-user desktop development can explicitly opt into loopback anonymous access via `CONNECTOR_ALLOW_ANONYMOUS_MCP=true`.
- **Encrypted Credential Storage**: Connection credentials and OAuth access/refresh tokens are encrypted at rest with AES-256-GCM using `cryptography`. Secrets are never logged or returned unredacted in API responses.
- **Outbound HTTP / SSRF Defense**: All outbound provider calls execute through `GuardedTransport`, which validates target IP addresses and pins TCP connections directly to the vetted IP, preventing DNS rebinding (TOCTOU) attacks while preserving TLS SNI and certificate validation. Private subnets, loopback, link-local, and cloud metadata (e.g. AWS/GCP `169.254.169.254`) are strictly blocked.
- **Audit Logs & Redaction**: Action executions record execution duration, HTTP status, and bounded summaries with secret tokens automatically redacted.
- **Database Portability & Deployment**: Backed by SQLite async by default with auto-migration, with PostgreSQL supported via SQLAlchemy async and versioned Alembic migrations (`alembic upgrade head`). A single-instance deployment is recommended until distributed locking and replication coordination are configured across multiple instances.

## Development

Backend dependencies are listed in `server/requirements.txt`. Frontend scripts are defined in `client/package.json`:

```bash
cd client
npm run lint
npm run build
```

For API changes, run the backend locally with Uvicorn's reload option and use `/docs` to inspect the generated OpenAPI schema.

## Project status

Open Agent Connector provides 236 registered providers and 8,024 catalog actions with fail-closed MCP authentication, runtime token authorization, AES-256-GCM encryption, SSRF protection with DNS rebinding defenses, and versioned Alembic database migrations. Contributions that improve provider coverage, documentation, and agent workflows are welcome.

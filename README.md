# Open Agent Connector

**An open-source, self-hosted integration gateway for AI agents.** Connect accounts to app APIs, keep credentials in your own runtime, and let agents discover and run actions through the Model Context Protocol (MCP) or a REST API.

This project is for developers who want to inspect, run, and extend their own agent integration layer. It is an open-source option to evaluate alongside [Composio](https://composio.dev/), [Nango](https://nango.dev/), [Merge.dev](https://www.merge.dev/), and [Arcade.dev](https://www.arcade.dev/). Those platforms offer broader catalogs and managed capabilities; Open Agent Connector currently prioritizes a compact self-hosted implementation that you can modify.

## Project description

Open Agent Connector gives an agent a consistent way to discover connected services, find an action, read its input schema, and execute it. A FastAPI backend manages provider definitions, connections, outbound requests, and run records. A Next.js console provides screens for browsing providers and actions, managing connections and runtime tokens, and reviewing activity. SQLite stores application data locally by default, with PostgreSQL supported via SQLAlchemy async and Alembic migrations.

The catalog currently registers **236 providers** with **8,024 actions** (counted from `server/app/providers/registry.py` and `actions_catalog.json`) spanning Developer tools, Project Management & CRM, Communication, Storage, AI/ML, E-Commerce, Social Media, Financial, and Utilities. For a complete list of all 236 providers, auth types, action counts, and category classifications, see [PROVIDER_GUIDE.md](PROVIDER_GUIDE.md). Registered does not mean battle-tested: not every provider action or OAuth flow has been verified against a live account, so confirm the ones you depend on.

## Features

- **MCP gateway:** Model Context Protocol (MCP) JSON-RPC 2.0 endpoint over `POST /mcp` and tool discovery over `GET /mcp/tools`. Every remote MCP call fails closed and requires an admin or runtime token with granular scope enforcement.
- **Scoped runtime tokens:** hashed, revocable tokens with deny-by-default action grants plus optional connection and proxy restrictions.
- **OAuth:** authorization URL, state and code exchange, encrypted token storage, and refresh for providers that support OAuth.
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
| `CONNECTOR_ADMIN_TOKEN` | Bearer token for the admin API and management routes | Generated into `server/data/.admin_token` if unset |
| `CONNECTOR_RUNTIME_TOKEN` | Optional static runtime token for `/v1` and `/mcp` | Unset (persistent DB tokens preferred) |
| `CONNECTOR_EXPOSE_LOCAL_TOKEN` | Let `/api/auth/status` return the admin token to genuine loopback callers (never when proxy headers are present). Set `false` on any network-facing deployment. | `true` |
| `CONNECTOR_ALLOWED_RETURN_ORIGINS` | Comma-separated origins, besides `CONNECTOR_PUBLIC_ORIGIN`, that a `redirectUri` may point to after OAuth. Anything else is rejected, and the callback only ever redirects to the URL stored when the flow started. | `http://localhost:3000,http://127.0.0.1:3000` |
| `CONNECTOR_ACCOUNTS_SIGNUP_MODE` | `disabled`, `invite` (needs `..._INVITE_CODES`) or `open` (needs an email backend). Unsafe combinations fall back to `disabled`. | `disabled` |
| `CONNECTOR_ACCOUNTS_INVITE_CODES` | Comma-separated invite codes for `invite` mode | unset |
| `CONNECTOR_ACCOUNTS_EMAIL_BACKEND` | `none`, `ses` (Amazon SES API), `smtp`, or `console` (logs codes, development only) | `none` |
| `CONNECTOR_ACCOUNTS_EMAIL_FROM` | Sender, e.g. `ConnectorHub <support@example.com>`. Must be a verified SES identity or an address your SMTP server accepts. | unset |
| `CONNECTOR_ACCOUNTS_SES_REGION` / `_ACCESS_KEY` / `_SECRET_KEY` | SES settings. Leave the keys empty to use the machine's IAM role or default AWS credentials. The key only needs `ses:SendEmail`. | `us-east-1` |
| `CONNECTOR_ACCOUNTS_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` | SMTP settings for the `smtp` backend (STARTTLS on port 587) | unset |
| `CONNECTOR_ACCOUNTS_BLOCKED_EMAIL_DOMAINS` | Comma-separated domains refused at signup, on top of reserved test domains | unset |
| `CONNECTOR_ACCOUNTS_SESSION_DAYS` | Lifetime of a "remember me" session | `30` |
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
        "Authorization": "Bearer <runtime-or-admin-token>"
      }
    }
  }
}
```

A token is required. Unauthenticated, invalid, or revoked tokens receive `401`. Tool discovery and execution are filtered by the token's action and connection grants.

The MCP gateway provides five discovery and execution meta-tools:
- `list_apps`: list providers with display names, categories, and authentication requirements.
- `list_connections`: list configured accounts with safe identities (filtered by token grants).
- `search_actions`: search 8,024 catalog actions by keywords or provider service ID (scoped to token grants).
- `get_action_guide`: retrieve full Markdown parameter documentation and JSON Schema for an action.
- `execute_action`: execute an authorized action with input arguments and target connection alias.

Individual provider actions are also exposed as direct MCP tools (e.g. `github_get_current_user`), dynamically filtered by the caller's authorized action permissions. An action call may include a `connectionName` argument; it defaults to `default`.

## REST API examples

List providers (catalog browsing is public):

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
  -H 'Authorization: Bearer <runtime-or-admin-token>' \
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

- The default database and generated local key are stored under `server/data/`; keep this directory out of source control and protect it in backups.
- Connection credentials and OAuth tokens are encrypted at rest with AES-256-GCM. The database alone is not sufficient to recover them; the encryption key must also be preserved securely.
- Outbound requests check resolved IP addresses and block private or internal destinations by default. The `CONNECTOR_ALLOW_PRIVATE_NETWORK` option relaxes some private-address blocking and should be used only in a controlled environment. Loopback, link-local, and metadata addresses remain blocked.
- Run logs keep bounded summaries of action inputs and outputs with sensitive credentials automatically redacted.
- **Authentication is enforced per route:**

  | Routes | Credential |
  | --- | --- |
  | `/api/*` (connections, runtime tokens, runs, stats, OAuth config and authorize) | Admin token |
  | `POST /v1/actions/{id}`, `POST /v1/proxy/{service}` | Runtime or admin token, plus action, connection, and proxy grants |
  | `POST /mcp`, `GET /mcp/tools` | Runtime or admin token (fail closed) |
  | `GET /v1/providers`, `GET /v1/actions`, `/health`, `/docs`, OAuth callback, `/api/auth/status` and `/api/auth/verify` | Public. These expose catalog metadata or the OAuth redirect, not credentials. |

- **Outbound HTTP / SSRF Defense**: All outbound provider calls execute through `GuardedTransport`, which validates target IP addresses and pins TCP connections directly to the vetted IP, preventing DNS rebinding (TOCTOU) attacks while preserving TLS SNI and certificate validation. Private subnets, loopback, link-local, and cloud metadata (e.g. AWS/GCP `169.254.169.254`) are strictly blocked.
- **Behind a reverse proxy**, set `CONNECTOR_EXPOSE_LOCAL_TOKEN=false`, bind the API to loopback or a private network, terminate TLS at the proxy, and rate-limit `/api/auth/verify`. See `docker-compose.prod.yml` for a loopback-only overlay.
- **Database Portability & Deployment**: Backed by SQLite async by default with auto-migration, with PostgreSQL supported via SQLAlchemy async and versioned Alembic migrations (`alembic upgrade head`). A single-instance deployment is recommended until distributed locking and replication coordination are configured across multiple instances.

## Accounts

Optional email + password accounts, off by default. Each account owns one private tenant, so everything it
connects, mints or runs is invisible to everyone else (see Tenancy below). Without an account the console works
in a shared **public sandbox**; the operator admin token sees the `default` tenant.

- **Sign-up modes:** `invite` (a code you hand out) or `open` (anyone, with emailed verification). With an email
  backend configured, new accounts must verify a 6-digit code (valid 10 minutes, five guesses) before signing in.
  Without one, only `invite` mode works and accounts are active immediately; password reset by email is then
  unavailable.
- **Sessions:** opaque tokens, stored only as a SHA-256 hash, in an `HttpOnly`, `SameSite=Lax` cookie
  (`__Host-` prefixed and `Secure` over HTTPS). Logging out, resetting the password, or deleting the account
  revokes sessions; changing the password signs out every other device. Requests authenticated by the cookie must
  carry an `X-Connector-CSRF` header (the console sends it).
- **Passwords:** argon2id, 10+ characters. Login and code endpoints are rate limited, accounts lock for 15 minutes
  after five failed sign-ins, and the responses never reveal whether an email is registered. Rate limits are
  in-process, so run a single instance and also limit `/api/accounts/*` at your proxy.
- **Data rights:** the Account page deletes the account and all of its data.
- **Production:** set the variables above in `.env.prod`. CORS only allows this service's own origin, so a sibling
  site on the same domain cannot use a signed-in user's cookie.

## Tenancy

Every tenant-owned row (connections, OAuth state, runtime tokens, run logs, idempotency records) carries a
`tenant_id`. A self-hosted install uses a single `default` tenant, so nothing changes for you. The core
enforces the boundary on every query: services take `tenant_id` as a required argument, and a tenant id
only ever comes from the authenticated principal or from server-side state created for it (for example the
OAuth state record), never from request input.

- Connection names are unique per tenant, so two tenants can each have a `github` / `default` connection.
- OAuth client credentials a tenant supplies are stored per tenant. Credentials from the server
  environment belong to the operator and are used only by the `default` tenant.
- Unauthenticated visitors (when `CONNECTOR_ALLOW_PUBLIC_ACCESS` is on) live in a separate `public` tenant
  and never see the operator's data.
- A hosted layer plugs in with `app.core.tenancy.register_principal_resolver(...)`, mapping its own API keys
  or sessions to a `Principal` with a `tenant_id` (kind `tenant_admin` for the management API,
  `runtime` for agents). Platform-wide hosted OAuth credentials remain operator-only.

`server/tests/test_tenant_isolation.py` is the contract: two tenants, the operator, and anonymous visitors
try to reach each other's data through every route.

## Production deployment

```bash
# .env.prod: PUBLIC_ORIGIN=https://connector.example.com
#            ADMIN_TOKEN=<long random value>  ENCRYPTION_KEY=<long random value>
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

This publishes the API on `127.0.0.1:8100` and the console on `127.0.0.1:3100`. Put nginx or another TLS-terminating proxy in front: route `/api`, `/v1`, `/mcp`, `/health`, and `/docs` to the API and everything else to the console. Back up `.env.prod` and the `connector_data` volume together; without the encryption key, saved credentials cannot be decrypted. Run one instance only.

## Backups

`deploy/backup/connector-backup.sh` takes a consistent snapshot of the SQLite database while the service is
running (SQLite's online backup API), verifies it, keeps 14 days of history, and saves the env file (which holds
`ENCRYPTION_KEY`) whenever it changes. Run it daily from root's cron:

```bash
15 3 * * * COMPOSE_DIR=/home/ubuntu/open-agent-connector /home/ubuntu/open-agent-connector/deploy/backup/connector-backup.sh >> /var/log/connector-backup.log 2>&1
```

Snapshots land in `/var/backups/connector` (override with `BACKUP_DIR`). They protect against corruption and bad
migrations but not against losing the machine, so copy that directory off the host as well. The database holds
credentials encrypted with the key, so **store the key backup separately from the database backup** when you copy
them off the host.

To restore: stop the server, replace the database file in the data volume with a snapshot
(`gunzip -k connector-<time>.db.gz`), and start the server again. Check with `PRAGMA integrity_check` first.

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
CONNECTOR_ADMIN_TOKEN=test-admin python -m pytest tests/test_mcp_auth_regression.py tests/test_mcp_security.py
```

## Project status

Open Agent Connector provides 236 registered providers and 8,024 catalog actions with fail-closed MCP authentication, runtime token authorization, AES-256-GCM encryption, SSRF protection with DNS rebinding defenses, and versioned Alembic database migrations. Contributions that improve provider coverage, documentation, and agent workflows are welcome.

## License

Open Agent Connector is licensed under the [Apache License 2.0](LICENSE). Unless you state otherwise, any
contribution you submit for inclusion is licensed under the same terms (section 5 of the license).

# Open Agent Connector: Code Comparison and Gap Report

**Review date:** 13 October 2026  
**Repositories reviewed:** `Anil-matcha/open-agent-connector` and `oomol-lab/open-connector`  
**Review type:** static source and documentation review; tests were not run

## Executive summary

The current Anil-matcha repository is substantially more advanced than its README and the previous research memo describe. At reviewed commit `036e09e`, it registers **236 providers** and its action catalog contains **8,024 actions**. It already implements admin/runtime tokens, action and proxy policy data, OAuth authorization and refresh, input schema validation, scoped idempotency, redacted run summaries, and outbound HTTP protections.

The most important confirmed security gap is that the MCP HTTP endpoints do not require authentication. They resolve a token only when one is supplied, and `McpService` executes actions without a principal. Therefore an unauthenticated caller reaching `/mcp` can discover and execute actions using saved connections. This contradicts both the existing memo and README in different ways: the memo says route auth is generally absent, while the code protects several admin, REST execution, and proxy routes; the README says auth is missing everywhere, while its most serious omission is the unprotected MCP route.

Compared with OOMOL OpenConnector, the remaining broad gaps are: smaller catalog, no first-party SDK or CLI, less mature deployment/storage options, and a hand-maintained MCP implementation. OOMOL documents 1,000+ providers and 10,000+ Actions, SDK/CLI/MCP/HTTP/OpenAPI clients, PostgreSQL, Helm and multiple deployment targets. Those catalog figures are vendor-published and do not have identical counting rules to the Anil-matcha registry.

## Repository snapshot and verified inventory

| Project | Reviewed commit | Provider/action evidence |
|---|---|---|
| Anil-matcha Open Agent Connector | `036e09e7f19854a33e89292622757376f66753e5` (12 Oct 2026) | `ProviderRegistry` has 236 registrations; `actions_catalog.json` has 236 service keys and 8,024 actions. |
| OOMOL OpenConnector | `231b9ea77ca381971711e879e077d4b8d1c1fcc2` (12 Oct 2026) | README claims 1,000+ providers and 10,000+ Actions. The repository has extensive per-provider source and runtime code; its published counts are not directly comparable to Anil-matcha's direct registry/catalog count. |

The Anil-matcha README still says four built-in providers and 147 GitHub actions. That description is materially stale and should be corrected. The README also says authentication is not enforced on any API, admin, or MCP route; source shows enforcement on admin routes, action execution over REST, and proxy execution, but not on MCP execution. These statements should be reconciled with the implementation.

## Capability comparison

| Capability | Anil-matcha Open Agent Connector | OOMOL OpenConnector | Gap / implication |
|---|---|---|---|
| Catalog | 236 registered providers; 8,024 catalog actions | README claims 1,000+ providers and 10,000+ Actions | Anil-matcha is much smaller by published inventory. Prioritize useful, reliable vertical integrations over raw count. |
| Gateway authentication | Admin and runtime principals, hashed persistent runtime tokens, static runtime token option | Runtime tokens and local auth are documented | Anil-matcha has the core primitives, but MCP bypasses mandatory authentication. |
| Authorization | Action allow/block patterns, connection restrictions, proxy allowlists | Runtime scopes and action allow/block policy | Similar policy building blocks; Anil-matcha must apply them consistently to MCP discovery and execution. |
| OAuth | Authorization URL, state/code exchange, encrypted credentials, refresh logic exist in `oauth_service.py` | OAuth2 flows, token refresh, hosted OAuth documented | Core self-hosted OAuth exists in Anil-matcha. OOMOL has more complete product paths, including hosted authorization; verify provider-specific lifecycle coverage before claiming parity. |
| Agent interfaces | REST, HTTP MCP, plus an STDIO MCP entry point; FastAPI exposes OpenAPI | TypeScript SDK, `oo` CLI, MCP, HTTP/OpenAPI | No first-party SDK or CLI in Anil-matcha; its MCP server is custom protocol code rather than an adopted SDK implementation. |
| Execution safety | JSON Schema validation, scoped idempotency, safe error handling, bounded/redacted run summaries | Stable action contracts, runtime policy, redacted logs, file transit | Anil-matcha already has useful execution safeguards. OOMOL has broader runtime and file-transit capabilities; verify detailed behavior per release. |
| Outbound HTTP | DNS/address checks, standard-port policy, manual redirect handling, cross-origin credential stripping, response size cap | Provider-specific executor/runtime model and additional controls documented | Anil-matcha's protections are substantially beyond the old memo's description. A remaining concern is that DNS is checked separately from the HTTP client's resolution, leaving a possible DNS-rebinding gap unless the network layer pins the checked address. |
| Persistence and deployment | SQLite-oriented schema initialization and Docker Compose; default local DB | SQLite/PostgreSQL, Docker/Node, Helm/Kubernetes, Cloudflare and other deployment guides | Anil-matcha lacks a robust cross-database migration path and documented multi-instance production baseline. `init_db()` uses SQLite `PRAGMA` statements. |
| Product operations | Local Next.js console, token management, connections, run history | Console, generated API docs, hosted service, deployment/usage options | OOMOL offers more turnkey deployment and operator workflows. Hosted OOMOL runtime is outside a self-host-only comparison but is a user-facing option. |
| Event triggers | No equivalent trigger/subscription subsystem found in reviewed Anil-matcha tree | OOMOL includes provider-trigger and subscription code/docs | Gap if the target use case includes event-driven agents rather than request/response actions. |

## Highest-priority findings

### P0 — Protect MCP execution and connection discovery

`server/app/api/v1/mcp.py` resolves a principal only if a caller provides a token. `tools/list` also returns action tools for an absent/invalid principal. In `server/app/services/mcp_service.py`, permission checks are conditional on `if principal`; the `execute_action` and direct-action paths call `ActionRunner.run()` when no principal is present. This creates an anonymous route to all actions and saved provider credentials for any caller who can reach the service.

**Recommendation:** fail closed on all remote MCP calls: require a valid runtime or admin principal, filter tools by grants, and enforce action, connection, and proxy grants at execution. If anonymous MCP is desired for local use, make it an explicit opt-in bound to loopback and ensure container/proxy deployments cannot accidentally expose that mode. Add regression tests for absent, invalid, under-scoped, and revoked tokens on both MCP discovery and execution.

### P1 — Correct stale project documentation

The current README's four-provider/147-action description does not match the checked source (236 registrations/8,024 actions). Its security section incorrectly says no authentication is enforced anywhere. Update the inventory and explain the actual route-level behavior, including the MCP exception, before presenting the service as network-ready.

### P1 — Close the outbound DNS resolution gap

`core/ssrf.py` resolves and checks the hostname with `socket.getaddrinfo`, then passes the hostname to HTTPX, which performs its own connection resolution. Redirect destinations are rechecked and credentials are stripped cross-origin, which is good; however, the separate DNS lookups can allow an attacker-controlled hostname to change its answer between validation and connect. Consider pinning the vetted address while preserving TLS host/SNI, or using a trusted egress proxy that enforces destination policy.

### P1 — Replace SQLite-only schema evolution before scaling

The database initializer uses `create_all()` plus SQLite `PRAGMA table_info` and SQLite `ALTER TABLE`. The runtime configuration exposes a database URL, but this initialization path does not provide a portable PostgreSQL migration story. Add versioned migrations and test fresh install/upgrade. Document a single-instance deployment constraint until concurrent execution, idempotency claims, and storage behavior are verified across replicas.

### P2 — Reduce MCP protocol maintenance risk

The MCP endpoint is implemented directly as JSON-RPC handling in `api/v1/mcp.py`; it advertises protocol versions `2025-11-25` and `2024-11-05`. OOMOL provides the same MCP surface but also ships SDK, CLI, and OpenAPI entry points. Adopt and pin the official Python MCP SDK for supported transport behavior, or clearly scope and test the custom implementation against the protocol versions and target clients the project intends to support.

### P2 — Add SDK/CLI and event-driven options where users need them

OOMOL packages a TypeScript connector SDK and `oo` CLI relay. Anil-matcha currently exposes REST/MCP/OpenAPI but no equivalent first-party SDK or CLI. OOMOL also has trigger/subscription infrastructure; no comparable subsystem appeared in the reviewed Anil-matcha source tree. These are meaningful workflow gaps, but should follow the MCP security fix and deployment baseline.

## Strengths already present in Anil-matcha

- Separate admin and runtime principals; persistent runtime token hashes; revocation and last-used tracking.
- Deny-by-default action grants for runtime principals and independent connection/proxy policy fields.
- Admin dependencies on management APIs and required runtime/admin auth for REST action execution and proxy calls.
- OAuth state/code exchange and token-refresh service, plus encrypted provider credentials.
- JSON Schema validation before provider execution.
- Idempotency keyed by caller, action, connection, and request payload; payload mismatch and in-progress states are handled.
- Run summaries are bounded and redacted; errors pass through a safe-message helper.
- Outbound URL validation, redirect-by-redirect checks, cross-origin secret-header stripping, timeouts, and response-size limits.
- Docker Compose and a local web console are already present.

These findings are from static code inspection; they do not establish that every provider action, OAuth provider, or security edge case works correctly in deployment.

## Recommended sequence

1. **Close the MCP auth bypass.** Require and authorize principals in MCP discovery and every execution path; prevent connection listing and metadata access from leaking beyond intended scope.
2. **Add focused security regression coverage.** Test every transport for anonymous access, invalid tokens, scoped grants, connection restrictions, revocation, and direct MCP action invocation. Test SSRF rebinding and redirects at the network boundary.
3. **Fix the README and this plan's linked inventory.** Publish verified counts from code and explain which endpoints require what credentials. Avoid the stale four-provider claim.
4. **Add portable database migrations and deployment guidance.** Define SQLite limits, backup/restore and key rotation, readiness, reverse-proxy/TLS assumptions, and safe network exposure.
5. **Adopt the official MCP SDK or publish a tested compatibility contract.** Keep version negotiation, error semantics, transport behavior, and auth explicit.
6. **Then build ecosystem features.** Consider a typed SDK/CLI, event triggers, file transit, and selected provider expansion based on user demand.

## Backlog: hosted OAuth apps and SaaS user connections

**Objective:** let users connect supported third-party accounts through Open Agent Connector’s hosted service without creating or configuring their own provider OAuth apps. Keep the self-hosted runtime available for operators who supply their own provider app credentials.

This is a separate product capability from adding provider actions. Each provider requires an OAuth app registered and operated by us, and providers may require verification, review, approved scopes, or other distribution requirements. OOMOL documents both a hosted personal/team Connector and a SaaS project model in which a customer backend starts authorization and executes actions for that customer’s end users. Use that separation as a product reference, not as an assumption that the provider approval work is automatic.

### Backlog milestones

1. **Provider and product feasibility (discovery).** Select an initial set of providers based on demand and OAuth readiness. For each, record app registration requirements, production verification/review steps, scope policy, token-refresh behavior, rate limits, data-use terms, branding requirements, and support escalation path. Decide whether the first launch is personal/team hosted connections, SaaS customer projects, or both.
2. **Hosted identity and tenancy (design/build).** Define customer projects, project API keys, end users, connected-account IDs/aliases, and ownership rules. Ensure every authorization request, connection lookup, action execution, and run record is scoped to the owning project/user. Keep personal/team accounts separate from SaaS end-user accounts.
3. **Managed OAuth lifecycle (build).** Operate provider OAuth client IDs/secrets centrally; implement authorization start, callback validation, state/PKCE where supported, least-privilege scopes, encrypted token storage, refresh and refresh locking, reconnect, revocation, deletion, and provider-specific consent/error handling. Do not expose provider tokens to the customer backend or agent.
4. **Customer API and SDK (build).** Provide server-side APIs and a typed SDK for creating authorization URLs, receiving or polling connection status, listing a user’s connected accounts, selecting an account, and executing actions. Keep project keys server-side and make account selection explicit to avoid running against the wrong user’s connection.
5. **Hosted operations and controls (launch gate).** Add tenant-aware audit logs, quotas/rate limits, abuse detection, encryption-key and secret rotation, backups/restore, monitoring, incident response, privacy/data-retention controls, customer support tooling, and provider outage handling. Document how customer and provider data is stored and deleted.
6. **Private beta and provider expansion.** Launch with a small provider set, validate authorization and refresh against real accounts, test cross-tenant isolation and revocation, then add providers only as their app approvals and operational support are ready.

### Suggested provider onboarding order

Treat these as hosted OAuth rollouts for integrations already present in the Anil-matcha catalog where OAuth is supported—not as a commitment to add all provider code from scratch. OOMOL highlights Gmail, GitHub, Notion, and Slack as representative hosted Connector apps. The order below balances early usefulness with the fact that provider app reviews and scope approvals can take time; start review-heavy applications in parallel with the first launch.

| Order | Provider group | Why this order | Rollout notes |
|---|---|---|---|
| 0 — start approval work immediately | Google Workspace: Gmail, Calendar, Drive | High user value and several related integrations can share a Google OAuth app/project, but sensitive scopes can make verification a long pole. | Begin verification and scope review early. Launch with the narrowest useful scopes; add Gmail send/write later than read/search if the product supports staged grants. |
| 0 — start approval work immediately | Microsoft 365: Outlook, Calendar, OneDrive, Teams | High-value work suite with a related set of connectors; tenant/admin consent can affect onboarding. | Register the app and validate personal and organization account flows early. Request only the Graph permissions needed for the initial actions. |
| 1 — first hosted beta | GitHub | Clear agent use cases, already has OAuth and PAT paths in the repo, and works well for developer-focused early adopters. | Start with read-only repository/issue discovery; gate write actions through explicit action grants and scopes. |
| 1 — first hosted beta | Slack | Common team workflow and already implemented OAuth support. | Validate workspace installation, bot/user token semantics, scope upgrades, and workspace removal. Start with a narrow set such as channel/message workflows. |
| 1 — first hosted beta | Notion | Common knowledge/workspace integration, already in the catalog with OAuth support, and a focused first consent flow. | Ensure users understand workspace/page access and how to reconnect after access changes. |
| 1 — first hosted beta | Linear | Focused product/developer workflow, already has OAuth support, and pairs well with GitHub. | Start with issues/projects read and create/update only if users request write access. |
| 2 — next customer cohort | Atlassian Jira, HubSpot, Airtable | Strong demand for project tracking, CRM, and lightweight databases; expands beyond developer tools. | Verify account/tenant selection, per-tenant access and provider rate limits. Prioritize one based on beta customer demand rather than launching all together. |
| 3 — demand-led expansion | Shopify, Zoom, Asana, Monday, Trello, Dropbox and other catalog providers | Broad long-tail coverage is useful after hosted onboarding, support, and revocation are proven. Some providers have more complex review, admin consent, or data-handling expectations. | Select from customer requests and support capacity. Confirm each provider's current OAuth support before promising a managed connection. |
| Future connector addition | Salesforce | Salesforce was not present in the reviewed Anil-matcha action catalog, so it requires provider implementation as well as hosted OAuth onboarding. | Add only if customer demand justifies the connector work, provider review, and ongoing support. |

**Suggested execution order:** create Google and Microsoft OAuth apps and begin any verification first; launch GitHub, Slack, Notion, and Linear as the first hosted beta if their app approvals and testing are ready; then add Jira/Atlassian, HubSpot, and Airtable based on beta demand. Provider approval readiness can change this order. Do not treat listed app names as shipped hosted integrations until app registration, production approval, and end-to-end tests are complete.

**Prioritization rule:** score each candidate on user demand, reuse across the existing action catalog, OAuth approval/verification effort, scope sensitivity, token-refresh reliability, provider API limits, and support burden. A provider with many actions but difficult onboarding may follow a narrower integration users can successfully connect.

### Exit criteria

- A user can authorize a supported account without creating a provider OAuth app.
- A customer project can connect multiple end users and multiple accounts per user without cross-user access.
- Actions run only under the explicitly selected connected account and granted scopes.
- Provider access/refresh tokens and provider app secrets never appear in agent context, customer API responses, or ordinary logs.
- Disconnect, provider-side revocation, token expiry, refresh failure, customer deletion, and project-key rotation have defined and tested outcomes.
- Provider review/verification and ongoing terms are tracked per provider; the service has an operational owner and incident path.

**Scope note:** this backlog is intentionally later than the MCP authorization and single-tenant deployment gates. A hosted multi-tenant service should not be built on top of the current optional-auth MCP route or without a tenant-aware connection and run-log model.

## Source references

### Anil-matcha Open Agent Connector

- [Reviewed commit `036e09e`](https://github.com/Anil-matcha/open-agent-connector/tree/036e09e7f19854a33e89292622757376f66753e5)
- `server/app/providers/registry.py` — 236 provider registrations.
- `server/app/providers/actions_catalog.json` — 236 service keys / 8,024 action definitions.
- `server/app/core/auth.py` — principal resolution and policy helpers.
- `server/app/api/v1/mcp.py` and `server/app/services/mcp_service.py` — optional principal resolution and conditional MCP permission checks.
- `server/app/api/v1/actions.py`, `server/app/api/v1/proxy.py`, and `server/app/api/admin/` — REST execution and admin route dependencies.
- `server/app/services/oauth_service.py` — OAuth state, code exchange, and refresh lifecycle.
- `server/app/services/action_runner.py` — input validation, idempotency, error handling, and run logs.
- `server/app/core/ssrf.py` — destination checks, redirects, credential stripping, timeout and response-size controls.
- `server/app/db/session.py` — SQLite-specific startup schema checks.
- `README.md` — currently stale inventory and auth summary.

### OOMOL OpenConnector

- [Reviewed commit `231b9ea`](https://github.com/oomol-lab/open-connector/tree/231b9ea77ca381971711e879e077d4b8d1c1fcc2)
- [README](https://github.com/oomol-lab/open-connector/blob/231b9ea77ca381971711e879e077d4b8d1c1fcc2/README.md) — catalog claims, SDK/CLI/MCP/HTTP/OpenAPI, deployment options.
- [OOMOL Connector overview](https://oomol.com/docs/connector/) and [Connector for SaaS guide](https://oomol.com/docs/connector-saas/) — hosted personal/team and per-end-user SaaS connection models.
- [OOMOL SDK reference](https://oomol.com/docs/connector-sdk) — `Connector`, `ProjectConnector`, and `OpenConnector` client split.
- `src/server/api/auth.ts` — local auth middleware and route scoping.
- `src/oauth/`, `src/connection-service.ts` — OAuth and connection lifecycle.
- `src/triggers/` — provider trigger/subscription runtime.
- `docs/configuration.md` and `deploy/helm/open-connector/` — database/deployment options.

**Caveat:** the OOMOL catalog count is taken from its project README, whereas Anil-matcha's count was computed directly from its checked-in registry and JSON catalog. Provider/action counting conventions may differ. No tests or live service calls were run as part of this report.

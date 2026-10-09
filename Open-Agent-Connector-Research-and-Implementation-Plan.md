# Open Agent Connector

## Research and implementation plan

**Engineering memo · 9 October 2026**  
**Review basis:** current source and public primary sources

## Recommendation

Finish the secure **connect → authorize → discover → execute → audit → revoke** flow before expanding the provider catalog. The current code has useful building blocks and a working local happy path, but identity, policy enforcement, credential lifecycle, and execution guarantees do not yet form a dependable product boundary.

Recommended first release: a **single-operator, self-hosted connector runtime**. Treat admin access and agent/runtime access as distinct principals; enforce narrow grants on every REST, proxy, and MCP execution path. Keep multi-user hosting and broad provider coverage out of the first core milestone.

This review is based on the current SamurAIGPT/open-agent-connector source at commit `4accb3ae871ac529ae03308dadbe1cbb7555499f` and the public reference implementation at commit `7da88e987e33089b298c224d745799f7d715fd7c`. Findings below are direct code observations unless marked as a product recommendation or inference. Connector inventory was not used as a success measure.

## Executive findings

| Priority | Gap | Why it blocks a reliable flow |
|---|---|---|
| **P0** | Authentication and policy are declared but not enforced | Routes can be called without validating `ADMIN_TOKEN` or `RUNTIME_TOKEN`; scope records and policy helpers do not protect execution. |
| **P0** | Custom HTTP can send credentials to user-selected destinations | URL/header control plus redirect and DNS re-resolution behavior creates an SSRF and credential exposure path. |
| **P1** | Connections lack identity and lifecycle | Global service/name uniqueness has no owner/workspace boundary; OAuth refresh, expiry, and revoke lifecycle are not wired. |
| **P1** | Execution and audit semantics are weak | Input schema is not enforced; the idempotency key is ignored in the hash; errors/logs can expose raw values. |
| **P1** | MCP server is hand-built against an older contract | Current advertised version is `2024-11-05`; protocol and auth changed materially in the July 2026 final revision. |
| **P2** | Release and persistence baseline is incomplete | SQLite `create_all`, no migration path, CI/test packaging, deployment baseline, or operational readiness checks. |

## 1. Current flow and where it stops

The existing product path is recognizable: launch the FastAPI service and web UI, add a connection by entering credentials, browse actions, execute a REST or MCP call, then inspect a run log. The API/provider registry and UI already provide a base for a vertical slice. The missing behavior appears when the caller is untrusted, a credential expires, a request is retried, or an operation fails.

| Flow step | Current implementation evidence | Missing product contract |
|---|---|---|
| Boot and configure | `server/main.py` mounts `/api`, `/v1`, and `/mcp`; config defines `ADMIN_TOKEN` and `RUNTIME_TOKEN`. | No middleware consumes those token settings. Health is basic liveness; deployment defaults and key handling need definition. |
| Connect account | Connection service encrypts credential data; modal supports manual token entry. | No complete OAuth authorization/callback/refresh path. Connection is globally keyed by service and name. |
| Discover and authorize | Action registry and MCP `tools/list` expose actions. Policy helpers exist. | No caller grant check on discovery or execution; runtime token allow/deny scopes are stored but unused. |
| Execute and retry | `ActionRunner` calls provider action; idempotency table is present. | No schema validation; idempotency hash omits the supplied key; stale in-progress claims can remain. |
| Audit and recover | `RunLog` records input, output, and exception text. | No systematic redaction, bounded summaries, retention, safe public error envelope, or lifecycle recovery. |

**Security interpretation:** this is acceptable only as an isolated local prototype. A loopback default reduces network exposure but does not substitute for route authorization once a user deploys it on a host or container network. Do not expose it externally until the P0 gates are complete.

## 2. Research and design implications

### Authentication is two separate trust relationships

Provider credentials authorize the connector to act against a third-party service. Gateway credentials authorize an agent or operator to call this connector. The code must never confuse these. An admin principal manages connections and policy; a runtime principal receives explicitly scoped, revocable grants. Every request must resolve a principal and enforce a decision at the point of use.

The reference implementation is useful as a design benchmark for admin/runtime middleware, token hashing and usage tracking, policy gates, typed execution errors, OAuth transaction state, migrations, and tests. These are patterns to adapt to this project’s shape, not a mandate to copy unrelated platform features.

### MCP changed enough to avoid hand-maintaining the wire contract

The official MCP project’s 28 July 2026 revision is marked final in the protocol tracking matrix. It retires the initialize/initialized handshake and session ID model and changes request metadata and authorization expectations. The current server advertises `2024-11-05` and manually implements JSON-RPC methods. Adopt the official SDK, pin and test supported versions, and provide compatibility only where real client requirements justify it.

### OAuth must follow the correct flow for the principal

Provider-account OAuth and remote MCP server authorization solve different problems. For provider connections, implement Authorization Code with PKCE, transaction-bound state, exact callback matching, expiry and refresh handling, and clear reconnect/revoke states. For a remotely served MCP endpoint, implement the MCP OAuth resource-server behavior appropriate to the supported SDK and clients. A runtime token is not a substitute for provider authorization.

### Outbound HTTP needs destination controls at the network boundary

The custom HTTP provider accepts a connection URL and headers and may inject a stored API key as Bearer authorization. Its SSRF helper resolves a hostname before the HTTP client independently resolves it, while redirects are followed. Enforce safe schemes/ports and address policy at connection time and every hop; prevent DNS rebinding through connection pinning or a trusted egress component. Never forward stored credentials to a redirect destination.

## 3. Product decisions for the first release

| Decision | Recommendation | Reason |
|---|---|---|
| Deployment audience | Single-operator self-hosted runtime | Fits current UI and local SQLite assumptions; avoids pretending workspace isolation exists. |
| Identity model | Separate admin principal from runtime principal | Gives a clean boundary for connection management vs agent execution. |
| Runtime grants | Allowlist actions and named connections; deny by default | Least privilege that can be enforced identically through REST and MCP. |
| Connection ownership | Stable connection ID and operator scope in v1 | Prevents accidental global-name ambiguity; retains a path to workspace ownership later. |
| Credential UX | Make API-key/manual token reliable first; add reusable OAuth lifecycle next | Keeps the initial slice testable while designing OAuth state and refresh correctly. |
| MCP support | Current SDK protocol plus only validated compatibility versions | Avoids a local protocol fork and narrows client support commitments. |
| Storage | SQLite for single instance with versioned migrations | Supports local setup while keeping schema evolution and backup explicit. |
| Provider breadth | Pause catalog expansion through the core milestone | A small catalog can validate platform contracts; connector quantity cannot compensate for missing authorization. |

## 4. Sequenced implementation plan

### Phase 0 — Lock the contracts

- Write a one-page v1 boundary: one operator, one instance, local or private network deployment; explicitly defer shared-hosted multi-tenancy.
- Define principals, named connections, token grants, run-log fields, connection states, public error envelope, and supported MCP versions.
- Define one canonical action identity and one authorization function used by REST, proxy, MCP discovery, and MCP execution.

**Exit criteria:** reviewed API/data contract and a threat model naming credential stores, inbound callers, outbound destinations, and admin actions.

### Phase 1 — Close the security boundary (P0)

- Implement authentication middleware/dependencies for admin and runtime APIs. Hash stored runtime token secrets; compare safely; track last use; support revocation and rotation.
- Enforce scopes at every action, connection, proxy, and MCP tool path. Filter discovery to authorized actions; recheck at execution. Admin-only endpoints must fail closed.
- Apply deny-by-default policy and remove misleading token settings until enforcement is live. Return consistent `401` vs `403` responses without leaking secrets.
- Harden custom HTTP: block unsafe schemes, loopback/private/link-local/metadata destinations by default; handle DNS rebinding; disable redirects or validate each hop; set timeouts and response-size limits; never replay credentials cross-origin.

**Exit criteria:** unauthenticated and under-scoped requests fail through every transport; security tests cover revoked tokens, hidden tools, redirects, DNS changes, and private addresses.

### Phase 2 — Make connection lifecycle dependable

- Give each connection a stable ID, status, timestamps, and explicit create/test/reconnect/rotate/disconnect/delete operations. Keep secrets encrypted and never return them in API responses.
- Build a reliable API-key connection path first, including provider test, credential update, and clear failure states.
- Add OAuth Authorization Code + PKCE as a reusable service: expiring one-time state, exact redirect URI, provider/issuer binding where applicable, encrypted access and refresh tokens, expiry tracking, refresh locking, revocation, and reauthorization UX.

**Exit criteria:** a user can connect, validate, recover from expiry, rotate, and revoke credentials without manual database edits; concurrent refresh cannot corrupt a connection.

### Phase 3 — Specify and harden action execution

- Validate input against the action’s published JSON Schema before calling a provider; use the same schema for UI forms and MCP `inputSchema`.
- Define stable public error codes and safe retry hints. Keep upstream diagnostics internal and redact credentials, headers, URLs with secrets, and sensitive payload fields.
- Correct idempotency semantics: scope by actual key + principal + action + connection; bind it to canonical request hash; same key with a different payload returns conflict; atomically claim, store terminal result, expire and clean up records, and recover abandoned claims.
- Carry request/correlation IDs across API, provider calls, and log rows. Add bounded upstream timeouts and explicit retry policy only for safe/repeatable operations.

**Exit criteria:** contract tests prove schema rejection before side effects, duplicate retries return the same result, key misuse conflicts, and user-visible errors contain no secrets.

### Phase 4 — Move MCP onto the supported SDK

- Use the official Python SDK; pin a supported release and implement the current 2026-07-28 protocol. Verify transport and authorization behavior against actual target clients.
- If clients require an older revision, isolate it in a compatibility adapter with explicit tests and a removal/support policy. Do not advertise versions the server cannot honor.
- Keep tool discovery useful at scale: expose only grants available to the caller and consider a small search/list/call surface if publishing every action overwhelms agent context.
- Cover local STDIO and remote HTTP separately. Protect the remote endpoint with the appropriate bearer-token/resource metadata model; do not assume local transport is a security boundary.

**Exit criteria:** official SDK client tests pass for the supported version behavior, listing, calls, errors, authorization denial, cancellation, and notifications.

### Phase 5 — Make logs and operations safe to run

- Store bounded summaries, redact known secret fields and sensitive headers, paginate logs, define retention, and keep raw provider responses opt-in only where justified.
- Introduce versioned SQLite migrations; test fresh install and upgrade from the current schema. Document data directory and encryption-key backup/restore expectations.
- Add deployment packaging for a single instance, configurable CORS/origins, database readiness checks, structured logs, graceful shutdown, and a security-focused CI pipeline.
- Create deterministic tests for auth, policy, OAuth state, action contracts, idempotency, SSRF, and log redaction. Add lint/type checks and dependency scanning in CI.

**Exit criteria:** documented fresh install/upgrade/backup procedure, reliable readiness, and CI enforcing core security and behavior tests.

### Phase 6 — Expand carefully

Once the same contract is exercised end to end, add connectors as vertical slices: auth setup, connection lifecycle, typed actions, schemas, policy scopes, safe errors, and tests. Consider multiple operators or hosted deployment only after introducing and testing workspace ownership for connections, grants, and logs, plus tenant-aware encryption and isolation.

## 5. End-to-end acceptance scenario

Use this scenario as the release gate. It tests the complete product loop rather than counting providers.

1. Boot a clean install with generated encryption material and create an admin identity/token. Verify no management route is anonymously accessible.
2. Connect one provider account, validate it, and confirm secrets never appear in API responses or logs.
3. Create a runtime token scoped to one named connection and one action. Discover actions over REST and MCP; only the allowed action appears.
4. Call the allowed action with valid input through REST and MCP and verify identical authorization, validation, correlation ID, and result semantics.
5. Retry with the same idempotency key and payload; receive the stored result without a second side effect. Reuse the key with different input; receive conflict.
6. Inspect the run log and verify bounded/redacted input, output, and error summaries.
7. Revoke the runtime token and disconnect the connection. Verify subsequent calls are denied and the credential is removed or made unusable.

## 6. Risks, dependencies, and release gates

| Risk / dependency | Mitigation or gate |
|---|---|
| Open unauthenticated routes if bound beyond loopback | P0: auth and scope tests must pass before any external or private-network exposure. |
| Custom URL feature exfiltrates credentials or reaches internal services | P0: strict egress policy, redirect controls, DNS rebinding defenses, and secret-forwarding tests. |
| Global connection identity becomes a multi-user data leak | V1: explicitly single operator; before shared use, add owner/workspace foreign keys and isolation tests. |
| New MCP revision changes client behavior | Pin SDK, test target clients, support only explicit protocol versions, monitor official migration guidance. |
| SQLite used with multiple server replicas | Document single-instance constraint; do not run replicated deployment until storage and locking support are designed. |
| OAuth provider differences increase implementation complexity | Model provider-specific scopes/callback behavior behind a shared flow service; test one representative OAuth provider before broad rollout. |
| Sensitive execution logs persist longer than intended | Redact by default, bound payloads, define retention and deletion, and document encryption and backup guidance. |

## First milestone

Deliver the Phase 0 contract and Phase 1 security gate, plus a working API-key connection through the execution path. Do not call the system ready for network deployment until authorization and custom HTTP egress checks pass. Then complete the **connect, discover, execute, audit, revoke** acceptance scenario across REST and MCP.

## Sources and review basis

Repository observations were checked against these revisions on 9 October 2026. The source comparison is implementation research, not a claim of feature parity or a recommendation to copy another product’s full scope.

- [Current project repository, reviewed commit `4accb3a`](https://github.com/SamurAIGPT/open-agent-connector/tree/4accb3ae871ac529ae03308dadbe1cbb7555499f)
- [Reference implementation README and source, reviewed commit `7da88e9`](https://github.com/oomol-lab/open-connector/tree/7da88e987e33089b298c224d745799f7d715fd7c)
- [MCP: 28 July 2026 protocol revision announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [MCP protocol support matrix](https://plan.modelcontextprotocol.io/matrix)
- [MCP SDK migration guide for 2026-07-28](https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28)
- [MCP SDK authorization guide](https://ts.sdk.modelcontextprotocol.io/v2/serving/authorization)
- [RFC 9700: OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/rfc/rfc9700.html)
- [OWASP Server Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

Implementation evidence is drawn from `server/main.py`; `server/app/core/config.py`, `policy.py`, `ssrf.py`, and `idempotency.py`; `server/app/api/admin` and `server/app/api/v1`; `server/app/db/models.py`; `server/app/services/action_runner.py`, `connection_service.py`, and `mcp_service.py`; `server/app/providers/builtins/custom_http.py`; and the client connection/action/log/token views. Recommendations about release scope and sequencing are product judgments based on those findings and the cited primary sources.

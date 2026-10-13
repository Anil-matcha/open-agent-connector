"""
Tenant model for the open core.

Every tenant-owned row (connections, OAuth state, runtime tokens, run logs,
idempotency records) carries a ``tenant_id``. A self-hosted install uses the
single ``DEFAULT_TENANT_ID`` everywhere, so behaviour is unchanged. A hosted
deployment registers a principal resolver (see ``register_principal_resolver``)
that maps its own credentials (API keys, sessions) to a ``Principal`` bound to a
tenant; the core then enforces the boundary on every query.

Rules:
- Services take ``tenant_id`` as a required argument. Never default it.
- A tenant id always comes from the authenticated principal or from a
  server-side record created for that principal (e.g. OAuth state), never from
  request input.
"""
from typing import Awaitable, Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.auth import Principal

# Tenant used by single-tenant self-hosted installs and the static operator token.
DEFAULT_TENANT_ID = "default"
# Tenant used for unauthenticated visitors while ALLOW_PUBLIC_ACCESS is enabled.
# Kept separate from DEFAULT_TENANT_ID so visitors never see the operator's data.
PUBLIC_TENANT_ID = "public"

# resolver(raw_token, db) -> Principal | None
PrincipalResolver = Callable[[str, "AsyncSession"], Awaitable[Optional["Principal"]]]

_principal_resolvers: List[PrincipalResolver] = []


def register_principal_resolver(resolver: PrincipalResolver) -> None:
    """Register an extra credential resolver (used by hosted/multi-tenant layers)."""
    if resolver not in _principal_resolvers:
        _principal_resolvers.append(resolver)


def unregister_principal_resolver(resolver: PrincipalResolver) -> None:
    if resolver in _principal_resolvers:
        _principal_resolvers.remove(resolver)


def clear_principal_resolvers() -> None:
    """Remove all registered resolvers (test helper)."""
    _principal_resolvers.clear()


def get_principal_resolvers() -> List[PrincipalResolver]:
    return list(_principal_resolvers)


def custom_oauth_config_key(tenant_id: str, service: str) -> str:
    """Storage key for a tenant's own OAuth client credentials.

    The default tenant keeps the legacy plain ``service`` key, so existing rows
    keep working. Platform-managed ("hosted") credentials use ``hosted:<service>``
    and are shared by all tenants by design.
    """
    if tenant_id == DEFAULT_TENANT_ID:
        return service
    return f"tenant:{tenant_id}:{service}"

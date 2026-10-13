from typing import Optional

from fastapi import Request

from app.core.config import settings

CSRF_HEADER = "x-connector-csrf"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_PLAIN = "connector_session"
_HOST = "__Host-connector_session"


def cookie_secure() -> bool:
    if settings.ACCOUNTS_COOKIE_SECURE is not None:
        return settings.ACCOUNTS_COOKIE_SECURE
    return settings.PUBLIC_ORIGIN.lower().startswith("https://")


def cookie_name() -> str:
    # The __Host- prefix makes browsers reject cookies set by sibling subdomains.
    return _HOST if cookie_secure() else _PLAIN


def read_session_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(_HOST) or request.cookies.get(_PLAIN)


def csrf_ok(request: Request) -> bool:
    """Cookie-authenticated state changes must carry a custom header.

    Browsers only attach custom headers to cross-origin requests after a CORS preflight,
    and our CORS policy does not allow foreign origins.
    """
    return request.method not in UNSAFE_METHODS or bool(request.headers.get(CSRF_HEADER))

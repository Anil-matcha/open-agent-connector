"""Validation for post-OAuth return URLs, so the callback can never be turned into an open redirect."""
from typing import List, Optional
from urllib.parse import urlsplit

from app.core.config import settings


def _origin(scheme: str, host: str, port: Optional[int]) -> str:
    default_port = 443 if scheme == "https" else 80
    if port and port != default_port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _origin_of_url(url: str) -> Optional[str]:
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        return _origin(parts.scheme, parts.hostname.lower(), parts.port)
    except ValueError:
        return None


def allowed_return_origins() -> List[str]:
    origins = []
    for candidate in [settings.PUBLIC_ORIGIN, *settings.ALLOWED_RETURN_ORIGINS.split(",")]:
        origin = _origin_of_url(candidate) if candidate.strip() else None
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def validate_return_uri(uri: Optional[str]) -> Optional[str]:
    """Return the URL unchanged if its origin is allowed, None if no URL was given.

    Raises ValueError for anything else: other origins, userinfo, non-http(s)
    schemes, protocol-relative or backslash tricks, and control characters.
    """
    if uri is None or not uri.strip():
        return None
    uri = uri.strip()
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F or ch in "\\" for ch in uri) or " " in uri:
        raise ValueError("Return URL contains invalid characters.")
    try:
        parts = urlsplit(uri)
    except ValueError:
        raise ValueError("Return URL is not a valid URL.")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Return URL must not contain credentials.")
    origin = _origin_of_url(uri)
    if origin is None or origin not in allowed_return_origins():
        raise ValueError("Return URL origin is not allowed.")
    return uri

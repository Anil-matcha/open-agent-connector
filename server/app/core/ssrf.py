import socket
import ipaddress
from urllib.parse import urlparse
from typing import Optional, Set
import httpx
from app.core.config import settings

# Explicit safe headers that can survive a cross-origin redirect
SAFE_CROSS_ORIGIN_HEADERS: Set[str] = {
    "accept",
    "accept-charset",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "content-disposition",
    "content-encoding",
    "content-language",
    "content-length",
    "content-range",
    "content-type",
    "user-agent",
    "idempotency-key",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback IPv4
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),        # This host on this network
    ipaddress.ip_network("::1/128"),          # Loopback IPv6
    ipaddress.ip_network("fc00::/7"),         # Unique local address IPv6
    ipaddress.ip_network("fe80::/10"),        # Link-local IPv6
]

class SSRFViolationError(Exception):
    """Raised when an outbound request targets a blocked or non-public address."""
    pass

def is_ip_blocked(ip_str: str, allow_private: bool = False) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        # Always block loopback, link-local, and cloud metadata
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
        # If private network is disallowed, block private IPs
        if not allow_private and ip.is_private:
            return True
        for network in BLOCKED_IP_NETWORKS:
            if not allow_private and ip in network:
                return True
            if allow_private and network == ipaddress.ip_network("169.254.0.0/16") and ip in network:
                return True # Cloud metadata always blocked even in private network mode
        return False
    except ValueError:
        return True

def assert_public_url(url: str, allow_private: bool = False) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFViolationError(f"Unsupported URL scheme: {parsed.scheme}. Only HTTP/HTTPS are permitted.")
    hostname = parsed.hostname
    if not hostname:
        raise SSRFViolationError("Invalid URL: hostname missing.")
    
    # Try resolving hostname
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFViolationError(f"Failed to resolve hostname '{hostname}': {str(e)}")
        
    for item in addr_info:
        ip_addr = item[4][0]
        if is_ip_blocked(ip_addr, allow_private=allow_private or settings.ALLOW_PRIVATE_NETWORK):
            raise SSRFViolationError(
                f"Security guard blocked outbound target {hostname} ({ip_addr}). Private/internal endpoints are denied."
            )

async def create_guarded_client(allow_private: bool = False, timeout_seconds: float = 30.0) -> httpx.AsyncClient:
    """Creates an async HTTP client configured for secure outbound provider execution."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=True,
    )

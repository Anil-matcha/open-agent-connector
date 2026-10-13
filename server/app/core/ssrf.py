import socket
import ipaddress
from urllib.parse import urlparse, urljoin
from typing import Optional, Set, Dict, Any, Iterable
import httpx
import httpcore
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
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud metadata (AWS/GCP/Azure)
    ipaddress.ip_network("0.0.0.0/8"),        # This host on this network
    ipaddress.ip_network("::1/128"),          # Loopback IPv6
    ipaddress.ip_network("fc00::/7"),         # Unique local address IPv6
    ipaddress.ip_network("fe80::/10"),        # Link-local IPv6
]

# Standard allowed outbound ports
ALLOWED_PORTS = {80, 443}

class SSRFViolationError(Exception):
    """Raised when an outbound request targets a blocked or non-public address."""
    pass

def is_ip_blocked(ip_str: str, allow_private: bool = False) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        # Always block loopback, link-local, multicast, and cloud metadata
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
        # If private network is disallowed, block private IPs
        if not allow_private and ip.is_private:
            return True
        for network in BLOCKED_IP_NETWORKS:
            if not allow_private and ip in network:
                return True
            if allow_private and network == ipaddress.ip_network("169.254.0.0/16") and ip in network:
                return True # Cloud metadata is always blocked unconditionally
        return False
    except ValueError:
        return True

def assert_public_url(url: str, allow_private: bool = False) -> None:
    """Verifies that an outbound URL does not target loopback, private networks, or metadata endpoints."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFViolationError(f"Unsupported URL scheme: '{parsed.scheme}'. Only HTTP/HTTPS are permitted.")
    
    hostname = parsed.hostname
    if not hostname:
        raise SSRFViolationError("Invalid URL: hostname is missing.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # Block internal services on non-standard ports unless explicitly allowed
    if not (allow_private or settings.ALLOW_PRIVATE_NETWORK) and port not in ALLOWED_PORTS:
        raise SSRFViolationError(f"Port {port} is not permitted for outbound requests. Only standard web ports (80, 443) are allowed.")

    # Try resolving hostname to IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, port)
    except socket.gaierror as e:
        raise SSRFViolationError(f"Failed to resolve target hostname '{hostname}': {str(e)}")

    for item in addr_info:
        ip_addr = item[4][0]
        if is_ip_blocked(ip_addr, allow_private=allow_private or settings.ALLOW_PRIVATE_NETWORK):
            raise SSRFViolationError(
                f"Security guard blocked outbound target {hostname} ({ip_addr}). Private/internal endpoints are denied."
            )

class GuardedAnyIOBackend(httpcore.AnyIOBackend):
    """
    Hardened network backend that resolves destination hostnames, validates
    every returned IP against blocked/private/cloud-metadata networks, and
    pins TCP connection directly to the vetted IP to eliminate DNS-rebinding (TOCTOU).
    Preserves TLS SNI and server certificate validation against destination hostname.
    """
    def __init__(self, allow_private: bool = False):
        super().__init__()
        self.allow_private = allow_private

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Optional[Iterable[Any]] = None,
    ) -> httpcore.AsyncNetworkStream:
        # Check standard port compliance
        if not (self.allow_private or settings.ALLOW_PRIVATE_NETWORK) and port not in ALLOWED_PORTS:
            raise SSRFViolationError(f"Port {port} is not permitted for outbound requests. Only standard web ports (80, 443) are allowed.")

        # Check if host is already an IP address
        try:
            addr_obj = ipaddress.ip_address(host)
            ip_str = str(addr_obj)
            if is_ip_blocked(ip_str, allow_private=self.allow_private or settings.ALLOW_PRIVATE_NETWORK):
                raise SSRFViolationError(f"Security guard blocked outbound target IP {ip_str}. Private/internal endpoints are denied.")
            vetted_ip = ip_str
        except ValueError:
            # Resolve hostname
            try:
                addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            except socket.gaierror as e:
                raise SSRFViolationError(f"Failed to resolve target hostname '{host}': {str(e)}")

            vetted_ips = []
            for item in addr_info:
                ip_cand = item[4][0]
                if is_ip_blocked(ip_cand, allow_private=self.allow_private or settings.ALLOW_PRIVATE_NETWORK):
                    raise SSRFViolationError(
                        f"Security guard blocked outbound target {host} ({ip_cand}). Private/internal endpoints are denied."
                    )
                vetted_ips.append(ip_cand)

            if not vetted_ips:
                raise SSRFViolationError(f"No valid IP addresses resolved for '{host}'.")

            # Pin to the first validated IP address to prevent DNS rebinding TOCTOU drift
            vetted_ip = vetted_ips[0]

        return await super().connect_tcp(
            host=vetted_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options
        )

class GuardedTransport(httpx.AsyncHTTPTransport):
    """
    Custom HTTPX AsyncTransport configured with GuardedAnyIOBackend to ensure
    address pinning and DNS rebinding prevention at socket connection time.
    """
    def __init__(self, allow_private: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=self._pool._ssl_context,
            network_backend=GuardedAnyIOBackend(allow_private=allow_private),
            http1=True,
            http2=False,
        )

async def create_guarded_client(allow_private: bool = False, timeout_seconds: float = 30.0) -> httpx.AsyncClient:
    """Creates an async HTTP client configured with DNS-pinning transport and manual redirect security."""
    return httpx.AsyncClient(
        transport=GuardedTransport(allow_private=allow_private),
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False, # Never blindly follow redirects without re-checking destination
    )

async def execute_guarded_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    data: Optional[Any] = None,
    max_redirects: int = 3,
    allow_private: bool = False,
    max_response_bytes: int = 10 * 1024 * 1024 # 10MB response ceiling
) -> httpx.Response:
    """
    Executes an outbound HTTP request with hop-by-hop SSRF validation,
    cross-origin credential stripping, and maximum response size limits.
    """
    current_url = url
    current_headers = dict(headers or {})
    original_origin = urlparse(url).netloc
    
    redirect_count = 0
    while True:
        assert_public_url(current_url, allow_private=allow_private)

        resp = await client.request(
            method=method,
            url=current_url,
            headers=current_headers,
            params=params if redirect_count == 0 else None,
            json=json_body if redirect_count == 0 else None,
            data=data if redirect_count == 0 else None
        )

        # Handle redirects manually to protect against SSRF and credential leaks
        if resp.is_redirect and "location" in resp.headers:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise SSRFViolationError("Maximum redirect hops exceeded.")

            target_loc = resp.headers["location"]
            next_url = urljoin(current_url, target_loc)
            next_origin = urlparse(next_url).netloc

            # If cross-origin redirect, strip credentials and non-safe headers
            if next_origin.lower() != original_origin.lower():
                current_headers = {
                    k: v for k, v in current_headers.items()
                    if k.lower() in SAFE_CROSS_ORIGIN_HEADERS
                }

            # On 303 or 302/301 from POST, switch to GET as per HTTP spec
            if resp.status_code == 303 or (resp.status_code in (301, 302) and method.upper() == "POST"):
                method = "GET"
                json_body = None
                data = None

            current_url = next_url
            continue

        # Check response content size to avoid OOM
        content_len = resp.headers.get("content-length")
        if content_len and int(content_len) > max_response_bytes:
            raise ValueError(f"Upstream response exceeded maximum permitted size ({max_response_bytes} bytes).")

        return resp

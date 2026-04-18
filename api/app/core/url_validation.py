"""URL safety validator — blocks outbound HTTP requests to internal addresses.

Invoked before any httpx/requests call that takes a user-supplied URL.
Blocks:
- RFC 1918 private ranges (10/8, 172.16/12, 192.168/16)
- Loopback (127/8, ::1)
- Link-local (169.254/16 — includes AWS/Azure/GCP instance metadata at
  169.254.169.254, fe80::/10)
- Carrier-grade NAT (100.64/10)
- Multicast, reserved, unspecified
- Well-known metadata hostnames (metadata.google.internal, localhost, ...)
- Non-http/https schemes (file://, gopher://, etc.)
- IPv4-mapped IPv6 embeddings of any of the above

DNS-rebinding hardening: `resolve_safe_outbound_url()` returns the chosen
safe IP alongside the validated URL so the caller can pin the HTTP connection
to that IP via `app.core.safe_httpx.build_pinned_*_client()`, eliminating the
TOCTOU window between SSRF validation and connect-time resolution.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import NamedTuple
from urllib.parse import urlparse

BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
        "instance-data.ec2.internal",
    }
)

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

_CGNAT_V4 = ipaddress.IPv4Network("100.64.0.0/10")


class UnsafeURLError(ValueError):
    """Raised when a URL targets a private, internal, or disallowed address."""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return True
    if ip.is_reserved or ip.is_unspecified:
        return True
    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_V4:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _is_blocked_ip(ip.ipv4_mapped)
        if ip.sixtofour is not None:
            return _is_blocked_ip(ip.sixtofour)
    return False


class ResolvedURL(NamedTuple):
    """Result of resolving + validating an outbound URL.

    `pinned_ip` is the safe IP the caller must connect to — using this with
    a pinned-IP HTTP transport closes the DNS-rebinding TOCTOU window.
    `host` and `port` carry the original hostname (for Host header / TLS SNI)
    and the explicit port number to bind on.
    """

    url: str
    scheme: str
    host: str
    port: int
    pinned_ip: str


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def validate_outbound_url(url: str, *, require_https: bool = False) -> str:
    """Validate `url` is safe to request. Return the URL on success.

    Raises UnsafeURLError on any policy violation. Kept for callers that do
    not need the pinned IP; new code should prefer `resolve_safe_outbound_url`.
    """
    return resolve_safe_outbound_url(url, require_https=require_https).url


def resolve_safe_outbound_url(
    url: str, *, require_https: bool = False
) -> ResolvedURL:
    """Validate `url` AND return the chosen safe IP for connection pinning.

    Resolves the hostname once, rejects if any answer is blocked, and returns
    the first safe address. Callers must pass the returned `pinned_ip` to a
    pinned-IP HTTP client so that the connect-time resolution cannot be
    rebound to an internal address by a malicious authoritative DNS server.

    Raises UnsafeURLError on any policy violation.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("URL must be a non-empty string")

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"URL scheme '{scheme or ''}' is not allowed")
    if require_https and scheme != "https":
        raise UnsafeURLError("Only https:// URLs are allowed here")

    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise UnsafeURLError("URL has no hostname")
    if host in BLOCKED_HOSTNAMES:
        raise UnsafeURLError(f"URL hostname '{host}' is blocked")

    try:
        port = parsed.port if parsed.port is not None else _default_port(scheme)
    except ValueError as exc:
        raise UnsafeURLError(f"URL port is invalid: {exc}") from exc
    if not 1 <= port <= 65535:
        raise UnsafeURLError(f"URL port {port} is out of range")

    # Literal IP: check directly without DNS
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if _is_blocked_ip(ip):
            raise UnsafeURLError(f"URL targets private/internal address {ip}")
        return ResolvedURL(
            url=url, scheme=scheme, host=host, port=port, pinned_ip=str(ip)
        )

    # Hostname: resolve and check every answer
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(
            f"URL hostname '{host}' could not be resolved: {exc}"
        ) from exc

    if not infos:
        raise UnsafeURLError(f"URL hostname '{host}' resolved to no addresses")

    safe_addrs: list[str] = []
    for _family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        try:
            resolved = ipaddress.ip_address(addr)
        except ValueError as exc:
            raise UnsafeURLError(
                f"URL hostname '{host}' resolved to invalid address {addr!r}"
            ) from exc
        if _is_blocked_ip(resolved):
            # Fail-closed: any blocked answer poisons the entire result.
            # Selecting only the safe ones would let an attacker who controls
            # the DNS round-robin smuggle in a private-IP answer alongside a
            # public one — `safe_addrs` would still be non-empty and the URL
            # would resolve to a usable target on retry.
            raise UnsafeURLError(
                f"URL hostname '{host}' resolves to blocked address {resolved}"
            )
        safe_addrs.append(str(resolved))

    if not safe_addrs:
        raise UnsafeURLError(
            f"URL hostname '{host}' has no usable safe addresses"
        )

    return ResolvedURL(
        url=url, scheme=scheme, host=host, port=port, pinned_ip=safe_addrs[0]
    )

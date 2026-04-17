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

DNS rebinding note: we resolve the hostname here and also reject if any
resolved address is private, but the subsequent httpx call re-resolves, so a
determined attacker with authoritative DNS could still win the race. Pinning
resolved IPs into the HTTP client is a follow-up.
"""

from __future__ import annotations

import ipaddress
import socket
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


def validate_outbound_url(url: str, *, require_https: bool = False) -> str:
    """Validate `url` is safe to request. Return the URL on success.

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

    # Literal IP: check directly without DNS
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if _is_blocked_ip(ip):
            raise UnsafeURLError(f"URL targets private/internal address {ip}")
        return url

    # Hostname: resolve and check every answer
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(
            f"URL hostname '{host}' could not be resolved: {exc}"
        ) from exc

    if not infos:
        raise UnsafeURLError(f"URL hostname '{host}' resolved to no addresses")

    for _family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        try:
            resolved = ipaddress.ip_address(addr)
        except ValueError as exc:
            raise UnsafeURLError(
                f"URL hostname '{host}' resolved to invalid address {addr!r}"
            ) from exc
        if _is_blocked_ip(resolved):
            raise UnsafeURLError(
                f"URL hostname '{host}' resolves to blocked address {resolved}"
            )

    return url

"""Pinned-IP HTTP transports — the second half of the SSRF defense.

`url_validation.resolve_safe_outbound_url()` validates a URL and returns the
specific safe IP it resolved to. This module wraps that IP into an httpx
transport so the actual TCP connect goes to the pinned IP — eliminating the
DNS-rebinding TOCTOU window where an attacker's authoritative DNS could
return a public IP for the validator and a private IP for httpx milliseconds
later.

Mechanism:
  1. The transport rewrites `request.url.host` to the pinned IP before
     connection. httpx then opens the TCP socket directly to that IP.
  2. The original hostname is preserved as the `Host:` header so virtual
     hosts on the target server still route correctly.
  3. `extensions["sni_hostname"]` keeps TLS SNI and certificate validation
     pointed at the original hostname — so the server presents the right
     cert and httpx still validates it.
  4. The transport refuses to rewrite if the request hostname does not match
     the pinned hostname (i.e. caller misuse / cross-origin redirect handed
     to the same client). The request is then sent unmodified — but the
     httpx client passed `follow_redirects=False` by default below should
     keep callers from accidentally chasing such redirects.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.url_validation import ResolvedURL


def _rewritten(request: httpx.Request, pinned: ResolvedURL) -> httpx.Request:
    """Return a new Request whose URL host is the pinned IP, preserving the
    original Host header and TLS SNI hostname."""
    url = request.url
    # Only rewrite when the request actually targets the validated host. Any
    # redirect or follow-up request against a different host bypasses the
    # rewrite — and since callers pass follow_redirects=False, the response
    # surfaces back to caller code which must re-validate before re-issuing.
    if url.host != pinned.host:
        return request

    # httpx.URL auto-brackets IPv6 hosts in the netloc representation when
    # given a bare IPv6 string, so passing the raw IP is correct here.
    new_url = url.copy_with(host=pinned.pinned_ip, port=pinned.port)
    new_headers = httpx.Headers(request.headers)
    # Host header includes the port only if it differs from the scheme default.
    default_port = 443 if pinned.scheme == "https" else 80
    if pinned.port == default_port:
        new_headers["Host"] = pinned.host
    else:
        new_headers["Host"] = f"{pinned.host}:{pinned.port}"

    new_extensions: dict[str, Any] = dict(request.extensions or {})
    new_extensions["sni_hostname"] = pinned.host

    return httpx.Request(
        method=request.method,
        url=new_url,
        headers=new_headers,
        content=request.stream,
        extensions=new_extensions,
    )


class _PinnedMixin:
    """Glue holding the resolved-IP context for both sync and async transports."""

    def __init__(self, pinned: ResolvedURL):
        self._pinned = pinned


class PinnedAsyncHTTPTransport(_PinnedMixin, httpx.AsyncHTTPTransport):
    """AsyncHTTPTransport that connects to a pre-resolved safe IP."""

    def __init__(self, pinned: ResolvedURL, **kwargs: Any):
        # retries=0 because we don't want to silently retry on a redirect or
        # transient failure to a different (potentially unvalidated) host.
        kwargs.setdefault("retries", 0)
        httpx.AsyncHTTPTransport.__init__(self, **kwargs)
        _PinnedMixin.__init__(self, pinned)

    async def handle_async_request(
        self, request: httpx.Request
    ) -> httpx.Response:
        return await super().handle_async_request(_rewritten(request, self._pinned))


class PinnedHTTPTransport(_PinnedMixin, httpx.HTTPTransport):
    """HTTPTransport that connects to a pre-resolved safe IP."""

    def __init__(self, pinned: ResolvedURL, **kwargs: Any):
        kwargs.setdefault("retries", 0)
        httpx.HTTPTransport.__init__(self, **kwargs)
        _PinnedMixin.__init__(self, pinned)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return super().handle_request(_rewritten(request, self._pinned))


def build_pinned_async_client(
    pinned: ResolvedURL, *, timeout: float = 30.0, verify: bool = True
) -> httpx.AsyncClient:
    """Async httpx client whose every request connects to `pinned.pinned_ip`.

    `follow_redirects` is forced off — a 3xx response surfaces to the caller
    so it can re-validate the new URL before re-issuing. Following redirects
    inside the pinned client would re-introduce the rebinding window.
    """
    transport = PinnedAsyncHTTPTransport(pinned, verify=verify)
    return httpx.AsyncClient(
        transport=transport, timeout=timeout, follow_redirects=False
    )


def build_pinned_client(
    pinned: ResolvedURL, *, timeout: float = 30.0, verify: bool = True
) -> httpx.Client:
    """Sync analog of `build_pinned_async_client`."""
    transport = PinnedHTTPTransport(pinned, verify=verify)
    return httpx.Client(
        transport=transport, timeout=timeout, follow_redirects=False
    )

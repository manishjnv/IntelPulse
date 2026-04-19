"""Unit tests for app.core.safe_httpx — pinned-IP transports.

Asserts that the rewriter swaps URL host to the pinned IP, sets the original
Host header, and pins TLS SNI to the original hostname. Uses internal
attribute introspection rather than a real network connection.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from app.core.safe_httpx import (
    PinnedAsyncHTTPTransport,
    PinnedHTTPTransport,
    _rewritten,
    build_pinned_async_client,
    build_pinned_client,
)
from app.core.url_validation import ResolvedURL


def _resolved(host: str, ip: str, port: int = 443, scheme: str = "https"):
    return ResolvedURL(
        url=f"{scheme}://{host}:{port}/test",
        scheme=scheme,
        host=host,
        port=port,
        pinned_ip=ip,
    )


# ── _rewritten — pure rewrite logic ──────────────────────


def test_rewritten_swaps_host_to_pinned_ip():
    pinned = _resolved("example.com", "93.184.216.34")
    req = httpx.Request("GET", "https://example.com/test")
    out = _rewritten(req, pinned)
    assert out.url.host == "93.184.216.34"
    assert out.headers["Host"] == "example.com"
    assert out.extensions.get("sni_hostname") == "example.com"


def test_rewritten_preserves_path_and_query():
    pinned = _resolved("example.com", "93.184.216.34")
    req = httpx.Request("GET", "https://example.com/api/v1?foo=bar")
    out = _rewritten(req, pinned)
    assert out.url.path == "/api/v1"
    assert out.url.query == b"foo=bar"


def test_rewritten_includes_port_in_host_header_for_nondefault_port():
    pinned = _resolved("example.com", "93.184.216.34", port=8443)
    req = httpx.Request("GET", "https://example.com:8443/test")
    out = _rewritten(req, pinned)
    assert out.headers["Host"] == "example.com:8443"


def test_rewritten_default_port_omitted_from_host_header():
    pinned = _resolved("example.com", "93.184.216.34", port=443)
    req = httpx.Request("GET", "https://example.com/test")
    out = _rewritten(req, pinned)
    assert out.headers["Host"] == "example.com"


def test_rewritten_raises_on_host_mismatch():
    # E.g. the caller let a redirect through, or reused the pinned client for
    # a different URL. We refuse to rewrite AND refuse to send — letting the
    # unmodified request flow to the inner transport would re-open the OS
    # resolver and defeat the whole pinned-IP guarantee. follow_redirects=False
    # on the client side prevents this in normal use; the raise here catches
    # bugs and abuse.
    pinned = _resolved("example.com", "93.184.216.34")
    req = httpx.Request("GET", "https://other.example.org/path")
    with pytest.raises(httpx.RequestError, match="host mismatch"):
        _rewritten(req, pinned)


def test_rewritten_host_match_is_case_and_trailing_dot_insensitive():
    # Hostnames in URLs are case-insensitive and trailing-dot tolerant; the
    # mismatch check must normalize before comparing or legitimate traffic
    # tripping case/dot variance would be blocked.
    pinned = _resolved("example.com", "93.184.216.34")
    for variant in ("Example.COM", "example.com.", "EXAMPLE.com."):
        req = httpx.Request("GET", f"https://{variant}/test")
        out = _rewritten(req, pinned)
        assert out.url.host == "93.184.216.34"
        assert out.headers["Host"] == "example.com"


def test_rewritten_ipv6_literal_host_header_is_bracketed():
    # When pinned.host is itself an IPv6 literal (caller passed a literal-IP
    # URL), the Host header must bracket the address so downstream parsers do
    # not confuse the colons for a port separator.
    pinned = ResolvedURL(
        url="https://[2606:4700::1111]/test",
        scheme="https",
        host="2606:4700::1111",
        port=443,
        pinned_ip="2606:4700::1111",
    )
    req = httpx.Request("GET", "https://[2606:4700::1111]/test")
    out = _rewritten(req, pinned)
    assert out.headers["Host"] == "[2606:4700::1111]"


def test_rewritten_ipv6_literal_host_header_with_nondefault_port():
    pinned = ResolvedURL(
        url="https://[2606:4700::1111]:8443/test",
        scheme="https",
        host="2606:4700::1111",
        port=8443,
        pinned_ip="2606:4700::1111",
    )
    req = httpx.Request("GET", "https://[2606:4700::1111]:8443/test")
    out = _rewritten(req, pinned)
    assert out.headers["Host"] == "[2606:4700::1111]:8443"


def test_rewritten_ipv6_pinned():
    pinned = _resolved("example.com", "2001:db8::1")
    req = httpx.Request("GET", "https://example.com/test")
    out = _rewritten(req, pinned)
    # httpx auto-brackets IPv6 in netloc representation
    assert "2001:db8::1" in str(out.url)
    assert out.headers["Host"] == "example.com"


def test_rewritten_request_body_preserved():
    pinned = _resolved("example.com", "93.184.216.34")
    req = httpx.Request("POST", "https://example.com/test", json={"k": "v"})
    out = _rewritten(req, pinned)
    # Body bytes should round-trip through the rewrite
    assert b'"k"' in out.read()


# ── End-to-end through transport — verify parent gets rewritten request ──


def test_pinned_sync_transport_passes_rewritten_to_parent():
    pinned = _resolved("example.com", "93.184.216.34")
    transport = PinnedHTTPTransport(pinned)
    captured: list[httpx.Request] = []

    def fake_parent_handle(self, request):
        captured.append(request)
        return httpx.Response(200, text="ok")

    with patch.object(httpx.HTTPTransport, "handle_request", fake_parent_handle):
        client = httpx.Client(transport=transport)
        try:
            client.get("https://example.com/test")
        finally:
            client.close()

    assert len(captured) == 1
    sent = captured[0]
    assert sent.url.host == "93.184.216.34"
    assert sent.headers["Host"] == "example.com"
    assert sent.extensions.get("sni_hostname") == "example.com"


def test_pinned_async_transport_passes_rewritten_to_parent():
    pinned = _resolved("example.com", "93.184.216.34")
    transport = PinnedAsyncHTTPTransport(pinned)
    captured: list[httpx.Request] = []

    async def fake_parent_handle(self, request):
        captured.append(request)
        return httpx.Response(200, text="ok")

    async def run():
        with patch.object(
            httpx.AsyncHTTPTransport, "handle_async_request", fake_parent_handle
        ):
            client = httpx.AsyncClient(transport=transport)
            try:
                await client.get("https://example.com/test")
            finally:
                await client.aclose()

    asyncio.run(run())

    assert len(captured) == 1
    sent = captured[0]
    assert sent.url.host == "93.184.216.34"
    assert sent.headers["Host"] == "example.com"
    assert sent.extensions.get("sni_hostname") == "example.com"


# ── Client builder behavior ──────────────────────────────


def test_build_pinned_client_disables_redirects():
    pinned = _resolved("example.com", "93.184.216.34")
    client = build_pinned_client(pinned)
    try:
        assert client.follow_redirects is False
    finally:
        client.close()


def test_build_pinned_async_client_disables_redirects():
    pinned = _resolved("example.com", "93.184.216.34")

    async def check():
        client = build_pinned_async_client(pinned)
        try:
            assert client.follow_redirects is False
        finally:
            await client.aclose()

    asyncio.run(check())

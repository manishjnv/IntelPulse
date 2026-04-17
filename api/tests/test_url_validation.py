"""Unit tests for app.core.url_validation.

No network: getaddrinfo is mocked for every hostname case.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from app.core.url_validation import UnsafeURLError, validate_outbound_url


def _fake_addrinfo(ip: str):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 0))]


# ── Literal-IP cases (no DNS) ────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.0.0.1:8080/admin",
        "http://10.0.0.1/",
        "http://10.255.255.255/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # AWS IMDS
        "http://169.254.170.2/",  # AWS ECS task metadata
        "http://100.64.0.1/",  # CGNAT
        "http://0.0.0.0/",
        "http://[::1]/",
        "http://[fe80::1]/",
        "http://[fc00::1]/",
        "http://[::ffff:10.0.0.1]/",  # IPv4-mapped private
        "http://[::ffff:169.254.169.254]/",  # IPv4-mapped AWS metadata
    ],
)
def test_literal_private_ip_rejected(url):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url)


def test_literal_public_ip_allowed():
    assert validate_outbound_url("http://8.8.8.8/") == "http://8.8.8.8/"
    assert validate_outbound_url("https://1.1.1.1/") == "https://1.1.1.1/"


# ── Scheme cases (no DNS) ────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/",
        "gopher://example.com/",
        "javascript:alert(1)",
        "data:text/plain,hello",
        "",
        "   ",
        "not a url",
        "://no-scheme.example",
    ],
)
def test_bad_scheme_rejected(url):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url)


def test_require_https_rejects_http():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")):
        assert validate_outbound_url("https://example.com/", require_https=True)
        with pytest.raises(UnsafeURLError):
            validate_outbound_url("http://example.com/", require_https=True)


# ── Hostname cases (DNS mocked) ──────────────────────────


def test_hostname_resolving_public_allowed():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")):
        assert (
            validate_outbound_url("https://example.com/foo")
            == "https://example.com/foo"
        )


def test_hostname_resolving_private_rejected():
    # Attacker-controlled hostname that resolves internally
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("10.1.2.3")):
        with pytest.raises(UnsafeURLError, match="resolves to blocked"):
            validate_outbound_url("https://evil.example.com/")


def test_hostname_resolving_aws_metadata_rejected():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("169.254.169.254")):
        with pytest.raises(UnsafeURLError, match="blocked"):
            validate_outbound_url("https://my-metadata-proxy.example.com/")


def test_hostname_multi_answer_one_private_rejected():
    # If ANY resolved answer is blocked, the whole URL is rejected
    infos = _fake_addrinfo("8.8.8.8") + _fake_addrinfo("10.0.0.1")
    with patch("socket.getaddrinfo", return_value=infos):
        with pytest.raises(UnsafeURLError, match="blocked"):
            validate_outbound_url("https://mixed.example.com/")


def test_hostname_resolution_failure_rejected():
    with patch(
        "socket.getaddrinfo",
        side_effect=socket.gaierror(-2, "Name or service not known"),
    ):
        with pytest.raises(UnsafeURLError, match="could not be resolved"):
            validate_outbound_url("https://nonexistent.invalid/")


# ── Blocked hostnames ────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://LOCALHOST/",  # case folding
        "http://localhost./",  # trailing dot
        "http://localhost.localdomain/",
        "http://metadata.google.internal/computeMetadata/",
        "http://metadata.goog/",
        "http://instance-data/",
        "http://instance-data.ec2.internal/",
    ],
)
def test_blocked_hostname_rejected(url):
    with pytest.raises(UnsafeURLError, match="blocked"):
        validate_outbound_url(url)


# ── Edge-case inputs ─────────────────────────────────────


@pytest.mark.parametrize("bad", [None, b"http://example.com", 123, [], {}])
def test_non_string_rejected(bad):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(bad)  # type: ignore[arg-type]


def test_whitespace_trimmed():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")):
        assert (
            validate_outbound_url("  https://example.com/  ")
            == "  https://example.com/  "
        )

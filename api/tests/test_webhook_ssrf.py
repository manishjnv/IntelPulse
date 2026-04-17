"""Integration tests: webhook delivery must refuse SSRF targets."""

from __future__ import annotations

import asyncio

import pytest

from app.services.webhook import deliver_webhook_async, deliver_webhook_sync


_NOTIF = {
    "title": "t",
    "message": "m",
    "severity": "info",
    "category": "system",
}


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://localhost/hook",
        "file:///etc/passwd",
        "ftp://evil.example.com/",
    ],
)
def test_deliver_sync_refuses_unsafe(url):
    result = deliver_webhook_sync(url, _NOTIF)
    assert result["success"] is False
    assert "Refused unsafe URL" in result["error"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "",
    ],
)
def test_deliver_async_refuses_unsafe(url):
    result = asyncio.run(deliver_webhook_async(url, _NOTIF))
    assert result["success"] is False
    assert "Refused unsafe URL" in result["error"]

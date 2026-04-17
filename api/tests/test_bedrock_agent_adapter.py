"""Unit tests for BedrockAgentAdapter service.

Tests all key methods of the adapter using unittest-style mocking to match
the repo's existing test conventions in test_bedrock_adapter.py.

asyncio_mode = "auto" is configured in pyproject.toml so async test functions
run automatically without explicit @pytest.mark.asyncio decorators.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: build a fully-configured adapter without hitting AWS
# ---------------------------------------------------------------------------

def _make_adapter():
    """Return a BedrockAgentAdapter with a mocked boto3 client.

    The module-level ``settings`` has non-empty defaults for
    ``bedrock_supervisor_agent_id`` / ``bedrock_supervisor_alias_id``
    so no settings patching is required.
    """
    with patch("app.services.bedrock_agent_adapter.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter
        adapter = BedrockAgentAdapter()
    # Return adapter with its .client already set to the mock
    adapter.client = mock_client
    return adapter, mock_client


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.no_redis_stub
class TestBedrockAgentAdapter:
    """Tests for BedrockAgentAdapter."""

    # ── Fixtures ─────────────────────────────────────────────────────────

    @pytest.fixture(autouse=True)
    def _patch_boto3(self):
        """Patch boto3 for every test so no real AWS calls escape."""
        with patch("app.services.bedrock_agent_adapter.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            self._mock_boto3 = mock_boto3
            self._mock_client = mock_client
            yield

    def _adapter(self):
        """Instantiate a fresh adapter using the patched boto3."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter
        adapter = BedrockAgentAdapter()
        adapter.client = self._mock_client
        return adapter

    # ── 1. _build_input_text ─────────────────────────────────────────────

    def test_build_input_text_combines_prompts(self):
        """_build_input_text should embed both prompts under labelled sections."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        result = BedrockAgentAdapter._build_input_text("sys", "user")

        assert "SYSTEM INSTRUCTIONS:" in result
        assert "REQUEST:" in result
        assert "sys" in result
        assert "user" in result

    # ── 2. _parse_json — strips markdown fences ──────────────────────────

    def test_parse_json_strips_markdown_fences(self):
        """_parse_json should strip ```json fences before parsing."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        result = BedrockAgentAdapter._parse_json('```json\n{"a": 1}\n```', caller="t")

        assert result == {"a": 1}

    # ── 3. _parse_json — bad JSON → None ─────────────────────────────────

    def test_parse_json_returns_none_on_bad_json(self):
        """_parse_json returns None when the text is not valid JSON."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        result = BedrockAgentAdapter._parse_json("not json at all", caller="t")

        assert result is None

    # ── 4. _parse_json — list (not dict) → None ──────────────────────────

    def test_parse_json_returns_none_when_not_a_dict(self):
        """_parse_json returns None when parsed value is a list, not a dict."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        result = BedrockAgentAdapter._parse_json("[1, 2, 3]", caller="t")

        assert result is None

    # ── 5. _drain_stream — chunk accumulation ────────────────────────────

    def test_drain_stream_accumulates_chunks(self):
        """_drain_stream concatenates bytes from chunk events."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        events = [
            {"chunk": {"bytes": b"part1 "}},
            {"chunk": {"bytes": b"part2"}},
        ]
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        text, stats_out = BedrockAgentAdapter._drain_stream(iter(events), stats)

        assert text == "part1 part2"
        assert stats_out["chunks"] == 2

    # ── 6. _drain_stream — action group invocations ───────────────────────

    def test_drain_stream_counts_action_group_invocations(self):
        """_drain_stream increments action_group_invocations for trace events."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        events = [
            {
                "trace": {
                    "trace": {
                        "orchestrationTrace": {
                            "invocationInput": {
                                "actionGroupInvocationInput": {"action": "virustotal_lookup"}
                            }
                        }
                    }
                }
            }
        ]
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        _text, stats_out = BedrockAgentAdapter._drain_stream(iter(events), stats)

        assert stats_out["action_group_invocations"] == 1
        assert stats_out["collaborator_invocations"] == 0

    # ── 7. _drain_stream — collaborator invocations ───────────────────────

    def test_drain_stream_counts_collaborator_invocations(self):
        """_drain_stream increments collaborator_invocations for collaborator trace events."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        events = [
            {
                "trace": {
                    "trace": {
                        "orchestrationTrace": {
                            "invocationInput": {
                                "agentCollaboratorInvocationInput": {"collaborator": "risk-scorer"}
                            }
                        }
                    }
                }
            }
        ]
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        _text, stats_out = BedrockAgentAdapter._drain_stream(iter(events), stats)

        assert stats_out["collaborator_invocations"] == 1
        assert stats_out["action_group_invocations"] == 0

    # ── 8. _drain_stream — returnControl raises ───────────────────────────

    def test_drain_stream_raises_on_return_control(self):
        """_drain_stream raises RuntimeError when stream contains returnControl."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        events = [{"returnControl": {"invocationId": "abc"}}]
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        with pytest.raises(RuntimeError, match="returnControl|dispatch"):
            BedrockAgentAdapter._drain_stream(iter(events), stats)

    # ── 9. _drain_stream — validationException raises ─────────────────────

    def test_drain_stream_raises_on_validation_exception(self):
        """_drain_stream raises RuntimeError containing the error message."""
        from app.services.bedrock_agent_adapter import BedrockAgentAdapter

        events = [{"validationException": {"message": "bad input"}}]
        stats = {"chunks": 0, "action_group_invocations": 0, "collaborator_invocations": 0}

        with pytest.raises(RuntimeError, match="bad input"):
            BedrockAgentAdapter._drain_stream(iter(events), stats)

    # ── 10. ai_analyze_structured_via_agent — happy path ─────────────────

    async def test_ai_analyze_structured_via_agent_happy_path(self):
        """End-to-end: adapter parses structured JSON from a single completion chunk."""
        payload = b'{"category":"cyberattack","summary":"S","executive_brief":"EB"}'
        self._mock_client.invoke_agent.return_value = {
            "completion": iter([{"chunk": {"bytes": payload}}])
        }

        adapter = self._adapter()
        result = await adapter.ai_analyze_structured_via_agent(
            system_prompt="Analyse the article.",
            user_prompt="Article text here.",
            session_id="test-session-001",
        )

        assert result == {
            "category": "cyberattack",
            "summary": "S",
            "executive_brief": "EB",
        }

        self._mock_client.invoke_agent.assert_called_once_with(
            agentId=adapter.agent_id,
            agentAliasId=adapter.alias_id,
            sessionId="test-session-001",
            inputText=adapter._build_input_text("Analyse the article.", "Article text here."),
            enableTrace=True,
        )

    # ── 11. ai_analyze_structured_via_agent — missing required keys → None ─

    async def test_ai_analyze_structured_via_agent_required_keys_missing(self):
        """Returns None when required_keys lists a key absent from the response."""
        # Response has valid JSON but no 'executive_brief'
        payload = b'{"category":"cyberattack","summary":"S"}'
        self._mock_client.invoke_agent.return_value = {
            "completion": iter([{"chunk": {"bytes": payload}}])
        }

        adapter = self._adapter()
        result = await adapter.ai_analyze_structured_via_agent(
            system_prompt="sys",
            user_prompt="user",
            required_keys=["category", "summary", "executive_brief"],
        )

        assert result is None

    # ── 12. ai_analyze_structured_via_agent — retry on ThrottlingException ─

    async def test_ai_analyze_structured_via_agent_retries_on_throttling(self):
        """invoke_agent is called twice when the first attempt raises ThrottlingException."""
        from botocore.exceptions import ClientError

        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeAgent",
        )
        good_payload = b'{"category":"malware","summary":"T","executive_brief":"EB2"}'

        # First call raises, second returns good data
        self._mock_client.invoke_agent.side_effect = [
            throttle_error,
            {"completion": iter([{"chunk": {"bytes": good_payload}}])},
        ]

        adapter = self._adapter()
        result = await adapter.ai_analyze_structured_via_agent(
            system_prompt="sys",
            user_prompt="user",
        )

        assert result == {"category": "malware", "summary": "T", "executive_brief": "EB2"}
        assert self._mock_client.invoke_agent.call_count == 2

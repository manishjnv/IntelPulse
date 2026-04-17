"""Unit tests for virustotal_lookup handler.py.

Run with:
    python -m unittest test_handler.py -v

All tests run in stub mode (get_api_key patched to return "").
No network calls are made.
"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure the handler module can be imported when running from its own directory
sys.path.insert(0, os.path.dirname(__file__))

# Stub out boto3 so the module imports cleanly in any environment (local dev,
# CI) without AWS credentials. urllib is stdlib — no stub needed.
_boto3_stub = MagicMock()
sys.modules.setdefault("boto3", _boto3_stub)

import handler  # noqa: E402  (must come after sys.modules stubs)


# Reusable Bedrock event factory
def _bedrock_event(ioc: str = "8.8.8.8", ioc_type: str = "ip", parameters: list | None = None) -> dict:
    params = parameters if parameters is not None else [
        {"name": "ioc", "value": ioc, "type": "string"},
        {"name": "ioc_type", "value": ioc_type, "type": "string"},
    ]
    return {
        "messageVersion": "1.0",
        "agent": {"name": "test-agent", "id": "ABCDEF", "alias": "live", "version": "1"},
        "actionGroup": "virustotal_lookup",
        "function": "lookup_ioc",
        "parameters": params,
        "sessionId": "sess-001",
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


class TestLegacyShape(unittest.TestCase):

    @patch.object(handler, "get_api_key", return_value="")
    def test_legacy_ip_stub(self, _mock):
        """Legacy IP event in stub mode returns statusCode 200 with stub data."""
        resp = handler.lambda_handler({"ioc": "8.8.8.8", "ioc_type": "ip"}, None)

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertTrue(body.get("stub"))
        self.assertEqual(body["malicious_count"], 3)
        self.assertEqual(body["ioc"], "8.8.8.8")
        self.assertEqual(body["ioc_type"], "ip")

    @patch.object(handler, "get_api_key", return_value="")
    def test_legacy_domain_stub(self, _mock):
        """Legacy domain event in stub mode returns statusCode 200 with stub data."""
        resp = handler.lambda_handler({"ioc": "evil.com", "ioc_type": "domain"}, None)

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertTrue(body.get("stub"))
        self.assertEqual(body["ioc_type"], "domain")
        self.assertEqual(body["ioc"], "evil.com")
        self.assertIn("malicious_count", body)

    @patch.object(handler, "get_api_key", return_value="")
    def test_legacy_hash_normalization(self, _mock):
        """ioc_type='sha256' is normalised to 'hash' before lookup."""
        resp = handler.lambda_handler(
            {"ioc": "abc123deadbeef", "ioc_type": "sha256"}, None
        )

        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertTrue(body.get("stub"))
        self.assertEqual(body["ioc_type"], "hash")

    def test_legacy_missing_params_400(self):
        """Empty legacy event returns 400 with descriptive error."""
        resp = handler.lambda_handler({}, None)

        self.assertEqual(resp["statusCode"], 400)
        body = json.loads(resp["body"])
        self.assertIn("Missing required parameters", body["error"])

    def test_legacy_unsupported_type_400(self):
        """Unsupported ioc_type in legacy event returns 400."""
        resp = handler.lambda_handler({"ioc": "user@example.com", "ioc_type": "email"}, None)

        self.assertEqual(resp["statusCode"], 400)
        body = json.loads(resp["body"])
        self.assertIn("Unsupported IOC type", body["error"])


class TestBedrockShape(unittest.TestCase):

    @patch.object(handler, "get_api_key", return_value="")
    def test_bedrock_ip_stub(self, _mock):
        """Bedrock event returns correct envelope and stub IP body."""
        event = _bedrock_event(ioc="8.8.8.8", ioc_type="ip")
        resp = handler.lambda_handler(event, None)

        # Envelope structure
        self.assertEqual(resp["messageVersion"], "1.0")
        self.assertIn("response", resp)
        self.assertEqual(resp["response"]["actionGroup"], "virustotal_lookup")
        self.assertEqual(resp["response"]["function"], "lookup_ioc")

        # Inner body
        text_body = resp["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        result = json.loads(text_body)
        self.assertTrue(result.get("stub"))
        self.assertEqual(result["ioc_type"], "ip")
        self.assertEqual(result["ioc"], "8.8.8.8")

    @patch.object(handler, "get_api_key", return_value="")
    def test_bedrock_missing_params_returns_error_body_not_400(self, _mock):
        """Bedrock event with empty parameters produces envelope with error in TEXT body."""
        event = _bedrock_event(parameters=[])
        resp = handler.lambda_handler(event, None)

        # Envelope must be present (no HTTP 400)
        self.assertIn("messageVersion", resp)
        self.assertIn("response", resp)

        text_body = resp["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        result = json.loads(text_body)
        self.assertIn("error", result)

    @patch.object(handler, "get_api_key", return_value="")
    def test_bedrock_unsupported_type_error_body(self, _mock):
        """Bedrock event with ioc_type='email' returns envelope with error key in TEXT body."""
        event = _bedrock_event(ioc="user@example.com", ioc_type="email")
        resp = handler.lambda_handler(event, None)

        self.assertIn("messageVersion", resp)
        text_body = resp["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        result = json.loads(text_body)
        self.assertIn("error", result)
        self.assertIn("email", result["error"])


if __name__ == "__main__":
    unittest.main()

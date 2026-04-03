"""Unit tests for Bedrock adapter service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBedrockAdapter:
    """Tests for BedrockAdapter class"""

    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 bedrock-runtime client"""
        with patch("app.services.bedrock_adapter.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for tests"""
        with patch("app.services.bedrock_adapter.settings") as mock_settings:
            mock_settings.aws_region = "us-east-1"
            mock_settings.ai_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
            mock_settings.ai_timeout = 30
            yield mock_settings

    def test_adapter_initialization(self, mock_boto3_client, mock_settings):
        """Test BedrockAdapter initializes with correct configuration"""
        from app.services.bedrock_adapter import BedrockAdapter

        adapter = BedrockAdapter()

        assert adapter.region == "us-east-1"
        assert adapter.model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert adapter.timeout == 30

    def test_adapter_initialization_without_boto3(self):
        """Test BedrockAdapter raises ImportError when boto3 not available"""
        with patch("app.services.bedrock_adapter.BOTO3_AVAILABLE", False):
            from app.services.bedrock_adapter import BedrockAdapter

            with pytest.raises(ImportError, match="boto3 is required"):
                BedrockAdapter()

    @pytest.mark.asyncio
    async def test_ai_analyze_success(self, mock_boto3_client, mock_settings):
        """Test successful text response from Bedrock"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock successful response
        mock_response = {
            "body": MagicMock(),
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": "This is a test response"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze(
            system_prompt="You are a helpful assistant",
            user_prompt="Test prompt",
            max_tokens=100,
            temperature=0.5,
        )

        assert result == "This is a test response"
        mock_boto3_client.invoke_model.assert_called_once()

        # Verify request body structure
        call_args = mock_boto3_client.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["max_tokens"] == 100
        assert body["temperature"] == 0.5
        assert body["system"] == "You are a helpful assistant"
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Test prompt"

    @pytest.mark.asyncio
    async def test_ai_analyze_empty_response(self, mock_boto3_client, mock_settings):
        """Test handling of empty response from Bedrock"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock empty response
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [],
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze(
            system_prompt="Test",
            user_prompt="Test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_analyze_client_error(self, mock_boto3_client, mock_settings):
        """Test handling of ClientError from Bedrock"""
        from app.services.bedrock_adapter import BedrockAdapter
        from botocore.exceptions import ClientError

        # Mock ClientError
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded",
            }
        }
        mock_boto3_client.invoke_model.side_effect = ClientError(
            error_response, "InvokeModel"
        )

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze(
            system_prompt="Test",
            user_prompt="Test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_analyze_botocore_error(self, mock_boto3_client, mock_settings):
        """Test handling of BotoCoreError from Bedrock"""
        from app.services.bedrock_adapter import BedrockAdapter
        from botocore.exceptions import BotoCoreError

        # Mock BotoCoreError
        mock_boto3_client.invoke_model.side_effect = BotoCoreError()

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze(
            system_prompt="Test",
            user_prompt="Test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_analyze_unexpected_error(self, mock_boto3_client, mock_settings):
        """Test handling of unexpected errors"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock unexpected error
        mock_boto3_client.invoke_model.side_effect = ValueError("Unexpected error")

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze(
            system_prompt="Test",
            user_prompt="Test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_analyze_structured_success(self, mock_boto3_client, mock_settings):
        """Test successful structured JSON response from Bedrock"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock successful JSON response
        json_content = {"risk_score": 85, "severity": "high", "confidence": 90}
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": json.dumps(json_content)}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze_structured(
            system_prompt="Return JSON",
            user_prompt="Analyze this",
            required_keys=["risk_score", "severity"],
        )

        assert result == json_content
        assert result["risk_score"] == 85
        assert result["severity"] == "high"

    @pytest.mark.asyncio
    async def test_ai_analyze_structured_with_markdown_fences(
        self, mock_boto3_client, mock_settings
    ):
        """Test parsing JSON from markdown code blocks"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock response with markdown fences
        json_content = {"status": "success", "data": "test"}
        markdown_response = f"```json\n{json.dumps(json_content)}\n```"
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": markdown_response}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze_structured(
            system_prompt="Return JSON",
            user_prompt="Test",
        )

        assert result == json_content

    @pytest.mark.asyncio
    async def test_ai_analyze_structured_missing_required_keys(
        self, mock_boto3_client, mock_settings
    ):
        """Test handling of missing required keys in JSON response"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock response missing required keys
        json_content = {"risk_score": 85}  # Missing 'severity'
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": json.dumps(json_content)}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze_structured(
            system_prompt="Return JSON",
            user_prompt="Test",
            required_keys=["risk_score", "severity"],
        )

        # Should still return partial data
        assert result == json_content
        assert "risk_score" in result
        assert "severity" not in result

    @pytest.mark.asyncio
    async def test_ai_analyze_structured_invalid_json(
        self, mock_boto3_client, mock_settings
    ):
        """Test handling of invalid JSON response"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock response with invalid JSON
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": "This is not valid JSON {"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.ai_analyze_structured(
            system_prompt="Return JSON",
            user_prompt="Test",
        )

        assert result is None

    def test_parse_json_response_clean_json(self, mock_boto3_client, mock_settings):
        """Test parsing clean JSON without markdown"""
        from app.services.bedrock_adapter import BedrockAdapter

        adapter = BedrockAdapter()
        json_str = '{"key": "value", "number": 42}'
        result = adapter._parse_json_response(json_str)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_response_with_markdown(self, mock_boto3_client, mock_settings):
        """Test parsing JSON wrapped in markdown code blocks"""
        from app.services.bedrock_adapter import BedrockAdapter

        adapter = BedrockAdapter()
        json_str = '```json\n{"key": "value"}\n```'
        result = adapter._parse_json_response(json_str)

        assert result == {"key": "value"}

    def test_parse_json_response_invalid(self, mock_boto3_client, mock_settings):
        """Test parsing invalid JSON returns None"""
        from app.services.bedrock_adapter import BedrockAdapter

        adapter = BedrockAdapter()
        result = adapter._parse_json_response("not valid json {")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_health_success(self, mock_boto3_client, mock_settings):
        """Test health check returns healthy status"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock successful health check
        mock_response = {
            "body": MagicMock(),
            "ResponseMetadata": {
                "HTTPHeaders": {"x-amzn-requestid": "test-request-id"}
            },
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": "ok"}],
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        adapter = BedrockAdapter()
        result = await adapter.check_health()

        assert result["healthy"] is True
        assert result["provider"] == "bedrock"
        assert result["region"] == "us-east-1"
        assert result["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"

    @pytest.mark.asyncio
    async def test_check_health_failure(self, mock_boto3_client, mock_settings):
        """Test health check returns unhealthy status on error"""
        from app.services.bedrock_adapter import BedrockAdapter

        # Mock health check failure
        mock_boto3_client.invoke_model.side_effect = Exception("Connection failed")

        adapter = BedrockAdapter()
        result = await adapter.check_health()

        assert result["healthy"] is False
        assert result["provider"] == "bedrock"
        assert "error" in result

    def test_get_bedrock_adapter_singleton(self, mock_boto3_client, mock_settings):
        """Test get_bedrock_adapter returns singleton instance"""
        from app.services.bedrock_adapter import get_bedrock_adapter, _bedrock_adapter

        # Reset global instance
        import app.services.bedrock_adapter as adapter_module
        adapter_module._bedrock_adapter = None

        adapter1 = get_bedrock_adapter()
        adapter2 = get_bedrock_adapter()

        assert adapter1 is adapter2

    @pytest.mark.asyncio
    async def test_bedrock_analyze_convenience_function(
        self, mock_boto3_client, mock_settings
    ):
        """Test convenience function bedrock_analyze"""
        from app.services.bedrock_adapter import bedrock_analyze

        # Mock successful response
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": "Test response"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        result = await bedrock_analyze(
            system_prompt="Test system",
            user_prompt="Test user",
        )

        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_bedrock_analyze_structured_convenience_function(
        self, mock_boto3_client, mock_settings
    ):
        """Test convenience function bedrock_analyze_structured"""
        from app.services.bedrock_adapter import bedrock_analyze_structured

        # Mock successful JSON response
        json_content = {"result": "success"}
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": json.dumps(json_content)}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }).encode()

        mock_boto3_client.invoke_model.return_value = mock_response

        result = await bedrock_analyze_structured(
            system_prompt="Return JSON",
            user_prompt="Test",
        )

        assert result == json_content

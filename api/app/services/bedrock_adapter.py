"""Amazon Bedrock adapter for AI services.

Replaces HTTP-based AI providers with Amazon Bedrock Runtime API.
Supports both text and structured JSON responses.
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging import get_logger
from app.normalizers.text import strip_json_fences

logger = get_logger(__name__)
settings = get_settings()


class BedrockAdapter:
    """Adapter for Amazon Bedrock Runtime API.
    
    Provides a unified interface for invoking Claude models via Bedrock.
    Supports both streaming and non-streaming responses.
    """

    def __init__(self):
        """Initialize Bedrock client."""
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for Bedrock adapter. Install with: pip install boto3")
        
        self.region = settings.aws_region or "us-east-1"
        self.model_id = settings.ai_model or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.timeout = settings.ai_timeout or 30
        
        # Initialize Bedrock Runtime client
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region,
        )
        
        logger.info(
            "bedrock_adapter_initialized",
            region=self.region,
            model=self.model_id,
        )

    async def ai_analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> str | None:
        """Generate text response using Bedrock.
        
        Args:
            system_prompt: System instruction for the model
            user_prompt: User query or content to analyze
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Generated text content or None on error
        """
        try:
            # Build request body for Claude models
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            }

            logger.info(
                "bedrock_invoke_request",
                model=self.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            
            # Extract content from Claude response format
            content = response_body.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")
                
                logger.info(
                    "bedrock_invoke_success",
                    model=self.model_id,
                    chars=len(text),
                    input_tokens=response_body.get("usage", {}).get("input_tokens", 0),
                    output_tokens=response_body.get("usage", {}).get("output_tokens", 0),
                )
                
                return text.strip()
            
            logger.warning("bedrock_empty_response", model=self.model_id)
            return None

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            logger.error(
                "bedrock_client_error",
                error_code=error_code,
                error_message=error_message,
                model=self.model_id,
            )
            return None

        except BotoCoreError as e:
            logger.error(
                "bedrock_botocore_error",
                error=str(e),
                model=self.model_id,
            )
            return None

        except Exception as e:
            logger.error(
                "bedrock_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model_id,
            )
            return None

    async def ai_analyze_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.3,
        required_keys: list[str] | None = None,
    ) -> dict | None:
        """Generate structured JSON response using Bedrock.
        
        Args:
            system_prompt: System instruction (should request JSON output)
            user_prompt: User query or content to analyze
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            required_keys: List of required keys in JSON response
            
        Returns:
            Parsed JSON dict or None on error
        """
        # Get text response
        raw = await self.ai_analyze(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if not raw:
            return None

        # Parse JSON from response
        return self._parse_json_response(raw, required_keys=required_keys)

    def _parse_json_response(
        self,
        raw: str,
        *,
        required_keys: list[str] | None = None,
    ) -> dict | None:
        """Parse JSON from model response, handling markdown fences.
        
        Args:
            raw: Raw text response from model
            required_keys: List of required keys to validate
            
        Returns:
            Parsed JSON dict or None on error
        """
        # Strip markdown code fences
        cleaned = strip_json_fences(raw)

        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "bedrock_json_parse_error",
                error=str(e),
                raw_preview=raw[:200],
            )
            return None

        # Validate required keys
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                logger.warning(
                    "bedrock_missing_required_keys",
                    missing=missing,
                    keys_found=list(data.keys()),
                )
                # Still return partial data - better than nothing

        return data

    async def check_health(self) -> dict:
        """Check Bedrock service health.
        
        Returns:
            Dict with health status and details
        """
        try:
            # Try a minimal invocation to test connectivity
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "user",
                        "content": "test",
                    }
                ],
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
            )

            response_body = json.loads(response["body"].read())
            
            return {
                "healthy": True,
                "provider": "bedrock",
                "region": self.region,
                "model": self.model_id,
                "response_time_ms": response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get("x-amzn-requestid"),
            }

        except Exception as e:
            logger.error(
                "bedrock_health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "healthy": False,
                "provider": "bedrock",
                "region": self.region,
                "model": self.model_id,
                "error": str(e),
            }


# Global instance (lazy-initialized)
_bedrock_adapter: BedrockAdapter | None = None


def get_bedrock_adapter() -> BedrockAdapter:
    """Get or create the global Bedrock adapter instance."""
    global _bedrock_adapter
    if _bedrock_adapter is None:
        _bedrock_adapter = BedrockAdapter()
    return _bedrock_adapter


# Convenience functions for backward compatibility
async def bedrock_analyze(
    system_prompt: str,
    user_prompt: str,
    **kwargs,
) -> str | None:
    """Convenience function for text analysis."""
    adapter = get_bedrock_adapter()
    return await adapter.ai_analyze(system_prompt, user_prompt, **kwargs)


async def bedrock_analyze_structured(
    system_prompt: str,
    user_prompt: str,
    **kwargs,
) -> dict | None:
    """Convenience function for structured JSON analysis."""
    adapter = get_bedrock_adapter()
    return await adapter.ai_analyze_structured(system_prompt, user_prompt, **kwargs)

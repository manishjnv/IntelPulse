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
        model_id: str | None = None,
    ) -> str | None:
        """Generate text response using Bedrock.

        Args:
            system_prompt: System instruction for the model
            user_prompt: User query or content to analyze
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            model_id: Optional per-call model override — lets the tiered
                router pick a different Bedrock model for classifier /
                correlator / narrative / fallback roles without mutating
                global adapter state.

        Returns:
            Generated text content or None on error
        """
        effective_model = model_id or self.model_id
        try:
            # Different Bedrock model families use different request/response
            # schemas. Dispatch on the model family so this adapter can serve
            # Anthropic Claude, Amazon Nova, Meta Llama, and Mistral with the
            # caller using one interface. Llama and Mistral go through the
            # Converse API (unified schema); the older families stay on the
            # per-family invoke_model schemas they were built for.
            family = self._model_family_for(effective_model)
            logger.info(
                "bedrock_invoke_request",
                model=effective_model,
                family=family,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if family in ("meta", "mistral", "deepseek", "ai21", "cohere"):
                text, usage = self._call_converse(
                    effective_model, family, system_prompt, user_prompt,
                    max_tokens, temperature,
                )
            else:
                body = self._build_request_body(
                    family, system_prompt, user_prompt, max_tokens, temperature
                )
                response = self.client.invoke_model(
                    modelId=effective_model,
                    body=json.dumps(body),
                )
                response_body = json.loads(response["body"].read())
                text, usage = self._extract_text_and_usage(family, response_body)

            if text:
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                logger.info(
                    "bedrock_invoke_success",
                    model=effective_model,
                    family=family,
                    chars=len(text),
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                )
                from app.core.ai_telemetry import track_invocation
                await track_invocation(
                    model_id=effective_model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                )
                # Also bump the per-provider Redis counter the Health & Stats
                # UI reads. "bedrock-primary" for the default model, tier-
                # labelled otherwise so the Provider Health card breaks down
                # usage across Classifier / Correlator / Narrative.
                try:
                    from app.services.ai import (
                        _increment_provider_usage,
                        get_ai_db_settings,
                    )
                    db_cfg = await get_ai_db_settings() or {}
                    primary = (db_cfg.get("primary_model") or self.model_id or "").strip()
                    tier_name = "bedrock-primary"
                    if effective_model != primary:
                        if effective_model == (db_cfg.get("model_news_enrichment") or "").strip():
                            tier_name = "bedrock-classifier"
                        elif effective_model == (db_cfg.get("model_intel_enrichment") or "").strip():
                            tier_name = "bedrock-correlator"
                        elif effective_model == (db_cfg.get("model_briefing_gen") or "").strip():
                            tier_name = "bedrock-narrative"
                    await _increment_provider_usage(tier_name)
                except Exception:  # noqa: BLE001
                    pass  # provider-usage telemetry is best-effort
                return text.strip()

            logger.warning("bedrock_empty_response", model=effective_model, family=family)
            return None

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "bedrock_client_error",
                error_code=error_code,
                error_message=error_message,
                model=effective_model,
            )
            return None

        except BotoCoreError as e:
            logger.error(
                "bedrock_botocore_error",
                error=str(e),
                model=effective_model,
            )
            return None

        except Exception as e:
            logger.error(
                "bedrock_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                model=effective_model,
            )
            return None

    def _model_family(self) -> str:
        """Family classification for the globally-configured model."""
        return self._model_family_for(self.model_id)

    @staticmethod
    def _model_family_for(model_id: str) -> str:
        """Classify the model into a request-schema family.

        Historical invoke_model-schema families:
        - "anthropic": Claude 3/4 via Bedrock.
        - "nova":     Amazon Nova (Lite/Micro/Pro/Premier).
        - "titan":    Amazon Titan Text.

        Converse-API families (unified schema, routed through _call_converse):
        - "meta":     Llama 3.x / Llama 4.x Instruct.
        - "mistral":  Mistral Small/Large/Mixtral/Ministral.
        - "deepseek": DeepSeek R1 / V3.
        - "cohere":   Cohere Command R / R+.
        - "ai21":     Jamba 1.5 Mini/Large.

        "unknown": falls back to the Anthropic schema.
        """
        mid = (model_id or "").lower()
        # Strip optional cross-region inference-profile prefix ("us." / "global.")
        bare = mid.split(".", 1)[1] if mid.startswith(("us.", "global.", "eu.", "apac.")) else mid
        if bare.startswith("anthropic.") or "claude" in bare:
            return "anthropic"
        if bare.startswith("amazon.nova") or "nova" in bare:
            return "nova"
        if bare.startswith("amazon.titan"):
            return "titan"
        if bare.startswith("meta.") or "llama" in bare:
            return "meta"
        if bare.startswith("mistral.") or "mistral" in bare or "mixtral" in bare or "magistral" in bare:
            return "mistral"
        if bare.startswith("deepseek."):
            return "deepseek"
        if bare.startswith("cohere."):
            return "cohere"
        if bare.startswith("ai21."):
            return "ai21"
        return "unknown"

    def _call_converse(
        self,
        model_id: str,
        family: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, dict]:
        """Dispatch through the Bedrock Converse API (unified schema).

        Converse normalises request/response across Meta, Mistral,
        DeepSeek, Cohere and AI21 — we use it for every family that
        isn't on a legacy family-specific invoke_model schema.
        """
        request: dict = {
            "modelId": model_id,
            "messages": [
                {"role": "user", "content": [{"text": user_prompt}]}
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            request["system"] = [{"text": system_prompt}]

        response = self.client.converse(**request)

        msg = (response.get("output") or {}).get("message") or {}
        parts = msg.get("content") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))

        # DeepSeek-R1 wraps its chain-of-thought in <think>...</think>.
        # Strip it so callers see the clean final answer.
        if family == "deepseek" and "<think>" in text:
            after = text.split("</think>", 1)
            text = (after[1] if len(after) > 1 else after[0]).strip()

        usage = response.get("usage") or {}
        return text, {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        }

    def _build_request_body(
        self,
        family: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict:
        """Produce the invoke_model body for the given family."""
        if family == "nova":
            msgs: list[dict] = []
            # Nova accepts an optional top-level `system` field as a list of
            # SystemContentBlock; fold the system prompt there so we don't
            # conflate roles.
            body: dict = {
                "messages": [
                    {"role": "user", "content": [{"text": user_prompt}]}
                ],
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                },
            }
            if system_prompt:
                body["system"] = [{"text": system_prompt}]
            return body
        if family == "titan":
            return {
                "inputText": (
                    (system_prompt + "\n\n" if system_prompt else "") + user_prompt
                ),
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                },
            }
        # Default: Anthropic Claude (messages API)
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

    @staticmethod
    def _extract_text_and_usage(family: str, response_body: dict) -> tuple[str, dict]:
        """Pull the generated text + usage metadata out of the response.

        Returns a (text, usage_dict) tuple; both empty on parse failure.
        """
        if family == "nova":
            msg = (response_body.get("output") or {}).get("message") or {}
            parts = msg.get("content") or []
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
            usage = response_body.get("usage") or {}
            return text, {
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
            }
        if family == "titan":
            results = response_body.get("results") or []
            text = results[0].get("outputText", "") if results else ""
            return text, {}
        # Anthropic/default
        content = response_body.get("content") or []
        text = content[0].get("text", "") if content and isinstance(content, list) else ""
        usage = response_body.get("usage") or {}
        return text, {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
        }

    async def ai_analyze_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.3,
        required_keys: list[str] | None = None,
        model_id: str | None = None,
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
            model_id=model_id,
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
            family = self._model_family()
            body = self._build_request_body(
                family, system_prompt="", user_prompt="test",
                max_tokens=10, temperature=0.0,
            )

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

from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.modules.aion_business.providers.model_policy import ModelPolicy


@dataclass(slots=True)
class AnthropicAdapterResult:
    ok: bool
    provider: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class AnthropicAdapter:
    """
    Minimal Anthropic provider adapter for Aion Business v1.
    Mirrors the OpenAI adapter shape so router/policy layers can swap cleanly.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str] = None,
        policy: Optional[ModelPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[str] = None,
        max_tokens: int = 512,
    ) -> AnthropicAdapterResult:
        if policy and policy.byok_required and not self.api_key:
            return AnthropicAdapterResult(
                ok=False,
                provider="anthropic",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="byok_required_missing_anthropic_key",
                raw=None,
            )

        if not self.api_key:
            return AnthropicAdapterResult(
                ok=False,
                provider="anthropic",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_anthropic_api_key",
                raw=None,
            )

        try:
            import anthropic
        except Exception as exc:
            return AnthropicAdapterResult(
                ok=False,
                provider="anthropic",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code=f"anthropic_sdk_import_failed:{exc}",
                raw=None,
            )

        client = anthropic.Anthropic(api_key=self.api_key)
        model_name = preferred_model or self.model

        safe_system_prompt = self._to_safe_text(system_prompt) if system_prompt else None
        safe_prompt = self._to_safe_text(prompt)

        started = time.time()

        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=safe_system_prompt if safe_system_prompt else None,
                messages=[
                    {
                        "role": "user",
                        "content": safe_prompt,
                    }
                ],
            )
            latency_ms = int((time.time() - started) * 1000)

            content = ""
            if getattr(response, "content", None):
                parts = []
                for block in response.content:
                    text = getattr(block, "text", None)
                    if text:
                        parts.append(text)
                content = "\n".join(parts).strip()

            usage = {}
            if getattr(response, "usage", None):
                usage = {
                    "input_tokens": getattr(response.usage, "input_tokens", None),
                    "output_tokens": getattr(response.usage, "output_tokens", None),
                }

            return AnthropicAdapterResult(
                ok=True,
                provider="anthropic",
                model=model_name,
                content=content,
                usage=usage,
                latency_ms=latency_ms,
                error_code=None,
                raw={
                    "id": getattr(response, "id", None),
                    "type": getattr(response, "type", None),
                    "role": getattr(response, "role", None),
                    "stop_reason": getattr(response, "stop_reason", None),
                    "metadata": metadata or {},
                },
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return AnthropicAdapterResult(
                ok=False,
                provider="anthropic",
                model=model_name,
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"anthropic_request_failed:{exc}",
                raw={
                    "metadata": metadata or {},
                    "prompt_preview": safe_prompt[:200],
                },
            )

    @staticmethod
    def _to_safe_text(value: str) -> str:
        text = unicodedata.normalize("NFKC", value)
        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u00a0": " ",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text.encode("utf-8", errors="ignore").decode("utf-8")
from __future__ import annotations

import os
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.modules.aion_business.providers.model_policy import ModelPolicy


@dataclass(slots=True)
class OpenAIAdapterResult:
    ok: bool
    provider: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class OpenAIAdapter:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
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
    ) -> OpenAIAdapterResult:
        if policy and policy.byok_required and not self.api_key:
            return OpenAIAdapterResult(
                ok=False,
                provider="openai",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="byok_required_missing_openai_key",
                raw=None,
            )

        if not self.api_key:
            return OpenAIAdapterResult(
                ok=False,
                provider="openai",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_openai_api_key",
                raw=None,
            )

        try:
            from openai import OpenAI
        except Exception as exc:
            return OpenAIAdapterResult(
                ok=False,
                provider="openai",
                model=preferred_model or self.model,
                content="",
                usage={},
                latency_ms=0,
                error_code=f"openai_sdk_import_failed:{exc}",
                raw=None,
            )

        client = OpenAI(api_key=self.api_key)
        model_name = preferred_model or self.model

        safe_system_prompt = self._to_safe_text(system_prompt) if system_prompt else None
        safe_prompt = self._to_safe_text(prompt)

        messages: List[Dict[str, str]] = []
        if safe_system_prompt:
            messages.append({"role": "system", "content": safe_system_prompt})
        messages.append({"role": "user", "content": safe_prompt})

        started = time.time()

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
            )
            latency_ms = int((time.time() - started) * 1000)

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            content = getattr(message, "content", "") if message else ""

            usage = {}
            if getattr(response, "usage", None):
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(response.usage, "completion_tokens", None),
                    "total_tokens": getattr(response.usage, "total_tokens", None),
                }

            return OpenAIAdapterResult(
                ok=True,
                provider="openai",
                model=model_name,
                content=content or "",
                usage=usage,
                latency_ms=latency_ms,
                error_code=None,
                raw={
                    "id": getattr(response, "id", None),
                    "created": getattr(response, "created", None),
                    "metadata": metadata or {},
                },
            )

        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            return OpenAIAdapterResult(
                ok=False,
                provider="openai",
                model=model_name,
                content="",
                usage={},
                latency_ms=latency_ms,
                error_code=f"openai_request_failed:{exc}",
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
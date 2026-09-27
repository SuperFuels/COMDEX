from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.modules.aion.providers.ollama_provider import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    OllamaProvider,
    OllamaProviderError,
)


@dataclass(slots=True)
class LocalLLMHealthResult:
    ok: bool
    enabled: bool
    model: str
    base_url: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LocalLLMGenerateResult:
    ok: bool
    enabled: bool
    model: str
    provider: str
    response: str
    done: bool
    done_reason: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict)


class LocalLLMServiceError(RuntimeError):
    pass


class LocalLLMService:
    def __init__(
        self,
        *,
        enabled: Optional[bool] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 120,
    ) -> None:
        env_enabled = os.getenv("AION_LOCAL_LLM_ENABLED", "1").strip().lower()
        resolved_enabled = enabled
        if resolved_enabled is None:
            resolved_enabled = env_enabled not in {"0", "false", "no", "off"}

        self.enabled = resolved_enabled
        self.model = (
            model
            or os.getenv("AION_LOCAL_LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or DEFAULT_OLLAMA_MODEL
        )
        self.base_url = (
            base_url
            or os.getenv("AION_LOCAL_LLM_BASE_URL")
            or os.getenv("OLLAMA_BASE_URL")
            or DEFAULT_OLLAMA_BASE_URL
        ).rstrip("/")
        configured_timeout = os.getenv("AION_LOCAL_LLM_TIMEOUT_SECONDS", "").strip()
        if configured_timeout and timeout_seconds == 120:
            try:
                timeout_seconds = max(5, int(configured_timeout))
            except ValueError:
                pass
        self.timeout_seconds = timeout_seconds

        self.provider = OllamaProvider(
            base_url=self.base_url,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
        )

    def health(self) -> LocalLLMHealthResult:
        if not self.enabled:
            return LocalLLMHealthResult(
                ok=False,
                enabled=False,
                model=self.model,
                base_url=self.base_url,
                payload={},
            )

        try:
            payload = self.provider.health()
        except OllamaProviderError as exc:
            raise LocalLLMServiceError(str(exc)) from exc

        return LocalLLMHealthResult(
            ok=True,
            enabled=True,
            model=self.model,
            base_url=self.base_url,
            payload=payload,
        )

    def generate(
        self,
        *,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        think: Optional[bool] = None,
    ) -> LocalLLMGenerateResult:
        if not self.enabled:
            raise LocalLLMServiceError("Local LLM service is disabled.")

        if not prompt or not prompt.strip():
            raise LocalLLMServiceError("Prompt must not be empty.")

        if think is None and os.getenv("AION_LOCAL_LLM_DISABLE_THINK", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }:
            think = False

        try:
            result = self.provider.generate(
                prompt=prompt,
                system=system,
                model=model,
                stream=False,
                options=options,
                think=think,
            )
        except OllamaProviderError as exc:
            raise LocalLLMServiceError(str(exc)) from exc

        return LocalLLMGenerateResult(
            ok=True,
            enabled=True,
            model=result.model,
            provider="ollama",
            response=result.response.strip(),
            done=result.done,
            done_reason=result.done_reason,
            raw=result.raw,
        )

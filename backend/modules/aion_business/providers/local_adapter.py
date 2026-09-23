from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, Optional

from backend.modules.aion.runtime.services.local_llm_tasks import LocalLLMTasks


@dataclass(slots=True)
class LocalAdapterResult:
    ok: bool
    provider: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class LocalAdapter:
    """
    Safe local model adapter for Aion Business.

    Rules:
    - local provider is draft/analysis/classification/summarization only
    - no external writes
    - no business state mutation
    - fail closed if local model runtime is unavailable
    """

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        tasks: Optional[LocalLLMTasks] = None,
        enabled: bool = True,
    ) -> None:
        self.model = model or os.getenv("AION_LOCAL_LLM_MODEL") or os.getenv("OLLAMA_MODEL") or "gemma4:e2b"
        self.tasks = tasks or LocalLLMTasks()
        self.enabled = enabled

    def generate(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str] = None,
        capability: str = "drafting",
        metadata: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[str] = None,
        max_tokens: int = 512,
    ) -> LocalAdapterResult:
        started = perf_counter()
        metadata = dict(metadata or {})
        model = preferred_model or self.model

        if not self.enabled:
            return self._error(
                model=model,
                started=started,
                error_code="local_provider_not_configured",
                metadata=metadata,
            )

        if capability not in {
            "drafting",
            "rewrite",
            "summarization",
            "analysis",
            "classification",
        }:
            return self._error(
                model=model,
                started=started,
                error_code=f"local_capability_not_supported:{capability}",
                metadata=metadata,
            )

        try:
            task_prompt = prompt
            if system_prompt:
                task_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}"

            task_result = self._call_task_method(capability, task_prompt, max_tokens=max_tokens)
            content = self._coerce_task_content(task_result)

            return LocalAdapterResult(
                ok=bool(str(content or "").strip()),
                provider="local",
                model=model,
                content=str(content or ""),
                usage={
                    "provider": "local",
                    "model": model,
                    "max_tokens_requested": int(max_tokens or 0),
                    "local_only": True,
                    "external_writes": "blocked",
                    "business_state_mutation": "blocked",
                },
                latency_ms=self._latency_ms(started),
                raw={
                    "metadata": metadata,
                    "capability": capability,
                    "safe_local_adapter": True,
                },
            )
        except AttributeError as exc:
            return self._error(
                model=model,
                started=started,
                error_code="local_provider_not_implemented",
                metadata={**metadata, "error": str(exc)},
            )
        except Exception as exc:
            return self._error(
                model=model,
                started=started,
                error_code=f"local_provider_error:{type(exc).__name__}",
                metadata={**metadata, "error": str(exc)},
            )


    def _call_task_method(self, capability: str, task_prompt: str, *, max_tokens: int = 512) -> Any:
        """
        Compatibility bridge:
        - supports older test fakes with generate/rewrite methods
        - supports real LocalLLMTasks with draft_reply/extract/json/task methods
        - keeps provider adapter stable while local runtime evolves
        """
        if capability == "summarization":
            return self.tasks.summarize(task_prompt)

        if capability == "classification":
            return self.tasks.classify(task_prompt)

        if capability == "rewrite":
            if hasattr(self.tasks, "rewrite"):
                return self.tasks.rewrite(task_prompt)
            return self.tasks.draft_reply(task_prompt)

        if capability == "analysis":
            if hasattr(self.tasks, "extract"):
                return self.tasks.extract(task_prompt)
            if hasattr(self.tasks, "generate"):
                return self.tasks.generate(task_prompt)
            return self.tasks.summarize(task_prompt)

        if capability == "drafting":
            if hasattr(self.tasks, "generate"):
                return self.tasks.generate(task_prompt)
            return self.tasks.draft_reply(task_prompt, max_tokens=max_tokens)

        raise AttributeError(f"Unsupported local capability: {capability}")

    @staticmethod
    def _coerce_task_content(value: Any) -> str:
        """
        LocalLLMTasks may return plain strings in tests or structured task result
        objects in the real runtime. Normalize both into provider content.
        """
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in ("content", "text", "output", "result", "summary"):
                raw = value.get(key)
                if raw is not None:
                    return str(raw)
            return str(value)

        for key in ("content", "text", "output", "result", "summary"):
            if hasattr(value, key):
                raw = getattr(value, key)
                if raw is not None:
                    return str(raw)

        return str(value)


    def _error(
        self,
        *,
        model: str,
        started: float,
        error_code: str,
        metadata: Dict[str, Any],
    ) -> LocalAdapterResult:
        return LocalAdapterResult(
            ok=False,
            provider="local",
            model=model,
            content="",
            usage={
                "provider": "local",
                "model": model,
                "local_only": True,
                "external_writes": "blocked",
                "business_state_mutation": "blocked",
            },
            latency_ms=self._latency_ms(started),
            error_code=error_code,
            raw={"metadata": metadata, "safe_local_adapter": True},
        )

    @staticmethod
    def _latency_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.modules.aion.runtime.contracts.model_routing import TaskType
from backend.modules.aion.runtime.services.local_llm_service import LocalLLMService


@dataclass(slots=True)
class LocalLLMTaskResult:
    task_type: TaskType
    output: str
    model: Optional[str]
    metadata: Dict[str, Any]


class LocalLLMTasks:
    def __init__(self, service: Optional[LocalLLMService] = None) -> None:
        self.service = service or LocalLLMService()

    def _normalize_result(self, result: Any) -> tuple[str, Optional[str]]:
        if isinstance(result, str):
            return result.strip(), None

        response = getattr(result, "response", "")
        model = getattr(result, "model", None)
        return str(response).strip(), model

    def summarize(
        self,
        text: str,
        *,
        system: Optional[str] = None,
        max_sentences: int = 5,
    ) -> LocalLLMTaskResult:
        prompt = (
            f"Summarise the following text in no more than {max_sentences} sentences.\n\n"
            f"TEXT:\n{text}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You produce concise, faithful summaries.",
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.SUMMARIZE,
            output=output,
            model=model,
            metadata={"max_sentences": max_sentences},
        )

    def classify(
        self,
        text: str,
        *,
        labels: List[str],
        system: Optional[str] = None,
    ) -> LocalLLMTaskResult:
        prompt = (
            "Classify the following text into exactly one of these labels:\n"
            f"{', '.join(labels)}\n\n"
            "Return only the label.\n\n"
            f"TEXT:\n{text}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You are a strict text classifier.",
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.CLASSIFY,
            output=output,
            model=model,
            metadata={"labels": labels},
        )

    def extract(
        self,
        text: str,
        *,
        instruction: str = "Extract the key actions, people, dates, and risks.",
        system: Optional[str] = None,
    ) -> LocalLLMTaskResult:
        prompt = (
            f"{instruction}\n"
            "Return the result as short bullet points.\n\n"
            f"TEXT:\n{text}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You extract structured business-relevant information.",
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.EXTRACT,
            output=output,
            model=model,
            metadata={"instruction": instruction},
        )

    def draft_reply(
        self,
        message: str,
        *,
        tone: str = "polite and professional",
        purpose: str = "respond helpfully",
        system: Optional[str] = None,
        max_tokens: int = 320,
    ) -> LocalLLMTaskResult:
        prompt = (
            f"Write a {tone} reply to the following message.\n"
            f"Purpose: {purpose}.\n"
            "Keep it clear and practical.\n\n"
            f"MESSAGE:\n{message}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You draft business replies clearly and professionally.",
            options={"num_predict": max(32, min(int(max_tokens), 320)), "temperature": 0.2},
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.DRAFT_REPLY,
            output=output,
            model=model,
            metadata={"tone": tone, "purpose": purpose},
        )

    def plan(
        self,
        objective: str,
        *,
        context: Optional[str] = None,
        system: Optional[str] = None,
    ) -> LocalLLMTaskResult:
        prompt = (
            "Create a short practical plan.\n"
            f"OBJECTIVE:\n{objective}\n\n"
            f"CONTEXT:\n{context or 'None provided'}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You create short structured business action plans.",
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.PLAN,
            output=output,
            model=model,
            metadata={"objective": objective},
        )

    def json_mode(
        self,
        text: str,
        *,
        schema_hint: Optional[Dict[str, Any]] = None,
        system: Optional[str] = None,
    ) -> LocalLLMTaskResult:
        schema_text = json.dumps(schema_hint or {}, indent=2, ensure_ascii=False)
        prompt = (
            "Return valid JSON only.\n"
            "Use this schema hint if helpful:\n"
            f"{schema_text}\n\n"
            f"TEXT:\n{text}"
        )
        result = self.service.generate(
            prompt=prompt,
            system=system or "You return strictly valid JSON and no extra prose.",
        )
        output, model = self._normalize_result(result)

        return LocalLLMTaskResult(
            task_type=TaskType.JSON_MODE,
            output=output,
            model=model,
            metadata={"schema_hint": schema_hint or {}},
        )

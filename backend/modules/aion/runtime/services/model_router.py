from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.modules.aion.runtime.contracts.model_routing import (
    ModelRoute,
    RoutingDecision,
    RoutingRequest,
    TaskType,
)
from backend.modules.aion.runtime.services.local_llm_service import (
    LocalLLMHealthResult,
    LocalLLMService,
)
from backend.modules.aion.runtime.services.local_llm_tasks import (
    LocalLLMTaskResult,
    LocalLLMTasks,
)


@dataclass(slots=True)
class ModelRouterResult:
    decision: RoutingDecision
    response_text: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """
    Cheapest-valid-route-wins router.

    Routing ladder:
    1. deterministic
    2. local_llm
    3. cloud_llm
    4. human
    """

    def __init__(
        self,
        *,
        local_llm_service: Optional[LocalLLMService] = None,
        local_llm_tasks: Optional[LocalLLMTasks] = None,
        local_llm_enabled: bool = True,
        cloud_llm_enabled: bool = False,
    ) -> None:
        self.local_llm_service = local_llm_service or LocalLLMService()
        self.local_llm_tasks = local_llm_tasks or LocalLLMTasks(
            service=self.local_llm_service
        )
        self.local_llm_enabled = local_llm_enabled
        self.cloud_llm_enabled = cloud_llm_enabled

    def decide(self, request: RoutingRequest) -> RoutingDecision:
        metadata = dict(request.metadata)

        if request.requires_human_approval or request.risk_level.lower() in {
            "high",
            "critical",
        }:
            return RoutingDecision(
                route=ModelRoute.HUMAN,
                reason="Task is approval-gated or high-risk.",
                metadata=metadata,
            )

        if self._is_deterministic_task(request):
            return RoutingDecision(
                route=ModelRoute.DETERMINISTIC,
                reason="Task should use deterministic logic, not an LLM.",
                metadata=metadata,
            )

        if request.prefers_local and self.local_llm_enabled:
            health = self._safe_local_health()
            if (
                health is not None
                and getattr(health, "ok", False)
                and getattr(health, "enabled", False)
            ):
                fallback_route = (
                    ModelRoute.CLOUD_LLM if request.allow_cloud_fallback else None
                )
                return RoutingDecision(
                    route=ModelRoute.LOCAL_LLM,
                    reason="Routine bounded language task routed to local LLM.",
                    provider="ollama",
                    model=getattr(health, "model", None),
                    fallback_route=fallback_route,
                    metadata=metadata,
                )

        if request.allow_cloud_fallback and self.cloud_llm_enabled:
            return RoutingDecision(
                route=ModelRoute.CLOUD_LLM,
                reason="Local LLM unavailable; cloud fallback permitted.",
                provider="cloud_llm",
                metadata=metadata,
            )

        return RoutingDecision(
            route=ModelRoute.DETERMINISTIC,
            reason="No available model route; fall back to deterministic handling or queue.",
            metadata=metadata,
        )

    def run(self, request: RoutingRequest) -> ModelRouterResult:
        decision = self.decide(request)

        if decision.route == ModelRoute.DETERMINISTIC:
            return ModelRouterResult(
                decision=decision,
                response_text=None,
                raw={
                    "ok": True,
                    "route": decision.route.value,
                    "detail": "Deterministic route selected.",
                },
            )

        if decision.route == ModelRoute.HUMAN:
            return ModelRouterResult(
                decision=decision,
                response_text=None,
                raw={
                    "ok": True,
                    "route": decision.route.value,
                    "detail": "Task requires human review/approval.",
                },
            )

        if decision.route == ModelRoute.CLOUD_LLM:
            return ModelRouterResult(
                decision=decision,
                response_text=None,
                raw={
                    "ok": False,
                    "route": decision.route.value,
                    "detail": "Cloud LLM route not implemented yet.",
                },
            )

        if decision.route == ModelRoute.LOCAL_LLM:
            if not request.prompt:
                raise ValueError("prompt is required for local LLM execution")

            task_result = self._run_local_task(request)

            return ModelRouterResult(
                decision=decision,
                response_text=task_result.output,
                raw={
                    "ok": True,
                    "route": decision.route.value,
                    "provider": decision.provider,
                    "model": task_result.model or decision.model,
                    "task_type": task_result.task_type.value,
                    "metadata": task_result.metadata,
                },
            )

        return ModelRouterResult(
            decision=decision,
            response_text=None,
            raw={
                "ok": False,
                "detail": f"Unhandled route: {decision.route.value}",
            },
        )

    def _is_deterministic_task(self, request: RoutingRequest) -> bool:
        metadata = request.metadata or {}
        return bool(metadata.get("is_deterministic", False))

    def _safe_local_health(self) -> Optional[LocalLLMHealthResult]:
        try:
            return self.local_llm_service.health()
        except Exception:
            return None

    def _run_local_task(self, request: RoutingRequest) -> LocalLLMTaskResult:
        if request.task_type == TaskType.SUMMARIZE:
            max_sentences = int(request.metadata.get("max_sentences", 5))
            return self.local_llm_tasks.summarize(
                request.prompt,
                system=request.system,
                max_sentences=max_sentences,
            )

        if request.task_type == TaskType.CLASSIFY:
            labels = request.metadata.get("labels")
            if not labels:
                raise ValueError(
                    "labels metadata is required for classify task routing"
                )
            return self.local_llm_tasks.classify(
                request.prompt,
                labels=list(labels),
                system=request.system,
            )

        if request.task_type == TaskType.EXTRACT:
            instruction = request.metadata.get(
                "instruction",
                "Extract the key actions, people, dates, and risks.",
            )
            return self.local_llm_tasks.extract(
                request.prompt,
                instruction=instruction,
                system=request.system,
            )

        if request.task_type == TaskType.DRAFT_REPLY:
            tone = request.metadata.get("tone", "polite and professional")
            purpose = request.metadata.get("purpose", "respond helpfully")
            return self.local_llm_tasks.draft_reply(
                request.prompt,
                tone=tone,
                purpose=purpose,
                system=request.system,
            )

        if request.task_type == TaskType.PLAN:
            context = request.metadata.get("context")
            return self.local_llm_tasks.plan(
                request.prompt,
                context=context,
                system=request.system,
            )

        if request.task_type == TaskType.JSON_MODE or request.requires_json:
            schema_hint = request.metadata.get("schema_hint")
            return self.local_llm_tasks.json_mode(
                request.prompt,
                schema_hint=schema_hint,
                system=request.system,
            )

        generate_result = self.local_llm_service.generate(
            prompt=request.prompt,
            system=request.system,
        )
        return LocalLLMTaskResult(
            task_type=request.task_type,
            output=generate_result.response,
            model=generate_result.model,
            metadata={},
        )
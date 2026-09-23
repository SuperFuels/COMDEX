from __future__ import annotations
from backend.modules.workflow_capsules.architect.local_gemma_provider_adapter import LocalGemmaWorkflowBuilderProviderAdapter

from backend.modules.workflow_capsules.architect.openai_provider_adapter import OpenAIWorkflowBuilderProviderAdapter

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.modules.workflow_capsules.architect.build_pack import (
    WorkflowBuildPackAssembler,
)
from backend.modules.workflow_capsules.architect.provider_adapter import (
    MockWorkflowBuilderProviderAdapter,
    PlaceholderWorkflowBuilderProviderAdapter,
    WorkflowBuilderProviderAdapter,
)
from backend.modules.workflow_capsules.architect.review_runner import (
    WorkflowArchitectReviewRunner,
)


@dataclass(slots=True)
class WorkflowArchitectProviderBuildResult:
    ok: bool
    provider: Dict[str, Any] = field(default_factory=dict)
    review: Dict[str, Any] = field(default_factory=dict)
    build_pack: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "review": self.review,
            "build_pack": self.build_pack,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class WorkflowArchitectProviderOrchestrator:
    """
    First provider-facing orchestration seam.

    This still does not call real external APIs by default. It:
      - assembles WorkflowBuildPack
      - calls selected adapter
      - decodes WorkflowBuilderSpec
      - runs validate/compile/dry-run review path
    """

    def __init__(
        self,
        *,
        adapter: WorkflowBuilderProviderAdapter | None = None,
    ) -> None:
        self.adapter = adapter or MockWorkflowBuilderProviderAdapter()

    @staticmethod
    def adapter_for(provider: str, model: str | None = None) -> WorkflowBuilderProviderAdapter:
        provider_key = str(provider or "mock").strip().lower()

        if provider_key == "mock":
            return MockWorkflowBuilderProviderAdapter()

        if provider_key == "openai":
            return OpenAIWorkflowBuilderProviderAdapter(
                model=model or "gpt-5.1",
            )

        if provider_key == "local_gemma":
            return LocalGemmaWorkflowBuilderProviderAdapter(
                model=model or "gemma4:e2b",
            )

        return PlaceholderWorkflowBuilderProviderAdapter(
            provider=provider_key,
            model=model or f"{provider_key}-workflow-builder-placeholder",
        )

    def build_and_review(
        self,
        *,
        workflow_goal: str,
        user_steps: List[Dict[str, Any]] | None = None,
        business_context: Dict[str, Any] | None = None,
        connected_credentials: List[str] | None = None,
        missing_credentials: List[str] | None = None,
        must_not_do: List[str] | None = None,
        inputs: Dict[str, Any] | None = None,
    ) -> WorkflowArchitectProviderBuildResult:
        build_pack = WorkflowBuildPackAssembler().assemble(
            workflow_goal=workflow_goal,
            user_steps=user_steps or [],
            business_context=business_context or {},
            connected_credentials=connected_credentials or [],
            missing_credentials=missing_credentials or [],
            must_not_do=must_not_do or [],
        )

        provider_response = self.adapter.build_spec(build_pack)
        provider_dict = provider_response.to_dict()

        if not provider_response.ok or provider_response.spec is None:
            return WorkflowArchitectProviderBuildResult(
                ok=False,
                provider=provider_dict,
                build_pack=build_pack.to_dict(),
                errors=list(provider_response.errors),
                warnings=list(provider_response.warnings),
            )

        review = WorkflowArchitectReviewRunner().run_review(
            provider_response.spec,
            connected_credentials=connected_credentials or [],
            inputs=inputs or {},
        )

        review_dict = review.to_dict()

        return WorkflowArchitectProviderBuildResult(
            ok=bool(review.ok),
            provider=provider_dict,
            review=review_dict,
            build_pack=build_pack.to_dict(),
            errors=list(provider_response.errors) + list(review.errors),
            warnings=list(provider_response.warnings) + list(review.warnings),
        )

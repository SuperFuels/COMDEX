from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPackAssembler
from backend.modules.workflow_capsules.architect.provider_adapter import (
    MockWorkflowBuilderProviderAdapter,
    WorkflowBuilderProviderAdapter,
)
from backend.modules.workflow_capsules.architect.review_runner import (
    WorkflowArchitectReviewResult,
    run_workflow_architect_review,
)


@dataclass(slots=True)
class WorkflowArchitectRepairLoopResult:
    ok: bool
    review: Dict[str, Any] = field(default_factory=dict)
    clarification_questions: List[Dict[str, str]] = field(default_factory=list)
    repair_attempts: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "review": self.review,
            "clarification_questions": self.clarification_questions,
            "repair_attempts": self.repair_attempts,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def is_vague_workflow_goal(workflow_goal: str) -> bool:
    goal = (workflow_goal or "").strip().lower()

    if len(goal) < 16:
        return True

    vague_phrases = {
        "make workflow",
        "build workflow",
        "automate emails",
        "customer replies",
        "deal with emails",
        "sort my gmail",
        "handle customers",
    }

    if goal in vague_phrases:
        return True

    action_clues = [
        "when ",
        "if ",
        "then ",
        "send",
        "draft",
        "create",
        "extract",
        "update",
        "notify",
        "schedule",
        "gmail",
        "hubspot",
        "calendar",
        "approval",
    ]

    return sum(1 for clue in action_clues if clue in goal) < 2


def clarification_questions_for_goal(workflow_goal: str) -> List[Dict[str, str]]:
    return [
        {
            "id": "trigger",
            "question": "What should trigger this workflow?",
            "example": "A new Gmail email arriving in newcustomer@kevin.com.",
        },
        {
            "id": "steps",
            "question": "What exact steps should happen after the trigger?",
            "example": "Extract customer details, create HubSpot lead, draft welcome email, notify owner.",
        },
        {
            "id": "connectors",
            "question": "Which accounts or tools should Aion use?",
            "example": "Gmail, HubSpot, Calendly, Google Calendar.",
        },
        {
            "id": "approval",
            "question": "Which steps need human approval before they run?",
            "example": "Approve before sending emails, creating invoices, deleting data, or external writes.",
        },
    ]


def extract_provider_spec(response: Any) -> Optional[Dict[str, Any]]:
    if not getattr(response, "ok", False):
        return None

    spec = getattr(response, "spec", None)

    if isinstance(spec, dict):
        return spec

    if hasattr(spec, "to_dict"):
        return spec.to_dict()

    return None


class WorkflowArchitectRepairLoop:
    """
    Safe repair/clarification loop for AI-generated workflow specs.

    Provider output is always treated as an untrusted proposal:
    provider suggests -> Aion validates -> Aion compiles -> Aion dry-runs.
    """

    def __init__(
        self,
        adapter: WorkflowBuilderProviderAdapter | None = None,
        repair_adapter: WorkflowBuilderProviderAdapter | None = None,
        max_repair_attempts: int = 1,
    ) -> None:
        self.adapter = adapter or MockWorkflowBuilderProviderAdapter()
        self.repair_adapter = repair_adapter
        self.max_repair_attempts = max(0, int(max_repair_attempts))

    def build_with_repair(
        self,
        *,
        workflow_goal: str,
        user_steps: Optional[List[Dict[str, Any]]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        connected_credentials: Optional[List[str]] = None,
        missing_credentials: Optional[List[str]] = None,
        must_not_do: Optional[List[str]] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowArchitectRepairLoopResult:
        if is_vague_workflow_goal(workflow_goal) and not user_steps:
            return WorkflowArchitectRepairLoopResult(
                ok=False,
                clarification_questions=clarification_questions_for_goal(workflow_goal),
                errors=["clarification_required:vague_workflow_goal"],
                warnings=["workflow_goal_too_vague_for_safe_generation"],
            )

        build_kwargs = {
            "workflow_goal": workflow_goal,
            "user_steps": user_steps or [],
            "business_context": business_context or {},
            "connected_credentials": connected_credentials or [],
            "missing_credentials": missing_credentials or [],
            "must_not_do": must_not_do or [],
            "inputs": inputs or {},
        }

        build_pack = WorkflowBuildPackAssembler().assemble(
            workflow_goal=build_kwargs["workflow_goal"],
            user_steps=build_kwargs["user_steps"],
            business_context=build_kwargs["business_context"],
            connected_credentials=build_kwargs["connected_credentials"],
            missing_credentials=build_kwargs["missing_credentials"],
            must_not_do=build_kwargs["must_not_do"],
        )

        provider_response = (
            self.adapter.build(**build_kwargs)
            if hasattr(self.adapter, "build")
            else self.adapter.build_spec(build_pack=build_pack)
        )

        spec = extract_provider_spec(provider_response)

        if spec is None:
            return WorkflowArchitectRepairLoopResult(
                ok=False,
                errors=[
                    "provider_output_invalid_or_unavailable",
                    *provider_response.errors,
                ],
                warnings=provider_response.warnings,
            )

        review = run_workflow_architect_review(
            workflow_goal=workflow_goal,
            spec=spec,
            user_steps=user_steps or [],
            business_context=business_context or {},
            connected_credentials=connected_credentials or [],
            missing_credentials=missing_credentials or [],
            must_not_do=must_not_do or [],
            inputs=inputs or {},
        )

        if review.ok:
            return WorkflowArchitectRepairLoopResult(
                ok=True,
                review=review.to_dict(),
                errors=[],
                warnings=provider_response.warnings + review.warnings,
            )

        repair_errors = list(review.errors)
        attempts = 0

        if self.repair_adapter is None or self.max_repair_attempts <= 0:
            return WorkflowArchitectRepairLoopResult(
                ok=False,
                review=review.to_dict(),
                repair_attempts=0,
                errors=["repair_not_attempted", *repair_errors],
                warnings=provider_response.warnings + review.warnings,
            )

        last_review: WorkflowArchitectReviewResult = review

        while attempts < self.max_repair_attempts:
            attempts += 1

            repair_kwargs = {
                "workflow_goal": (
                    workflow_goal
                    + "\n\nRepair the previous WorkflowBuilderSpec. "
                    + "Use only approved Aion node types. "
                    + "Return strict JSON only. "
                    + "Validation errors: "
                    + ", ".join(last_review.errors)
                ),
                "user_steps": user_steps or [],
                "business_context": business_context or {},
                "connected_credentials": connected_credentials or [],
                "missing_credentials": missing_credentials or [],
                "must_not_do": must_not_do or [],
                "inputs": {
                    **(inputs or {}),
                    "previous_errors": last_review.errors,
                    "previous_review": last_review.to_dict(),
                },
            }

            repair_build_pack = WorkflowBuildPackAssembler().assemble(
                workflow_goal=repair_kwargs["workflow_goal"],
                user_steps=repair_kwargs["user_steps"],
                business_context=repair_kwargs["business_context"],
                connected_credentials=repair_kwargs["connected_credentials"],
                missing_credentials=repair_kwargs["missing_credentials"],
                must_not_do=repair_kwargs["must_not_do"],
            )

            repair_response = (
                self.repair_adapter.build(**repair_kwargs)
                if hasattr(self.repair_adapter, "build")
                else self.repair_adapter.build_spec(build_pack=repair_build_pack)
            )

            repaired_spec = extract_provider_spec(repair_response)

            if repaired_spec is None:
                repair_errors.extend(["repair_provider_output_invalid", *repair_response.errors])
                continue

            last_review = run_workflow_architect_review(
                workflow_goal=workflow_goal,
                spec=repaired_spec,
                user_steps=user_steps or [],
                business_context=business_context or {},
                connected_credentials=connected_credentials or [],
                missing_credentials=missing_credentials or [],
                must_not_do=must_not_do or [],
                inputs=inputs or {},
            )

            if last_review.ok:
                return WorkflowArchitectRepairLoopResult(
                    ok=True,
                    review=last_review.to_dict(),
                    repair_attempts=attempts,
                    errors=[],
                    warnings=[
                        *provider_response.warnings,
                        *repair_response.warnings,
                        *last_review.warnings,
                    ],
                )

            repair_errors.extend(last_review.errors)

        return WorkflowArchitectRepairLoopResult(
            ok=False,
            review=last_review.to_dict(),
            repair_attempts=attempts,
            errors=[
                "repair_attempt_limit_reached",
                *repair_errors,
            ],
            warnings=[
                *provider_response.warnings,
                *last_review.warnings,
            ],
        )

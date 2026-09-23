from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.modules.workflow_capsules.architect.builder_spec import WorkflowBuilderSpec
from backend.modules.workflow_capsules.architect.graph_compiler import (
    WorkflowBuilderGraphCompiler,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_dry_run import (
    WorkflowCapsuleDryRunExecutor,
)


@dataclass(slots=True)
class WorkflowArchitectReviewResult:
    ok: bool
    phase: str = "architect_review"
    validation: Dict[str, Any] = field(default_factory=dict)
    canvas: Dict[str, Any] = field(default_factory=dict)
    capsule: Dict[str, Any] = field(default_factory=dict)
    dry_run: Dict[str, Any] = field(default_factory=dict)
    review: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "phase": self.phase,
            "validation": self.validation,
            "canvas": self.canvas,
            "capsule": self.capsule,
            "dry_run": self.dry_run,
            "review": self.review,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class WorkflowArchitectReviewRunner:
    """
    Converts a validated WorkflowBuilderSpec into a reviewable dry-run payload.

    This runner does not execute live actions. It compiles the proposed workflow,
    expands it, runs dry-run preview, and returns the Canvas/Boardroom review data.
    """

    def run_review(
        self,
        spec: WorkflowBuilderSpec,
        *,
        connected_credentials: List[str] | None = None,
        inputs: Dict[str, Any] | None = None,
    ) -> WorkflowArchitectReviewResult:
        compile_result = WorkflowBuilderGraphCompiler().compile(
            spec,
            connected_credentials=connected_credentials or [],
        )

        if not compile_result.ok or compile_result.capsule is None:
            return WorkflowArchitectReviewResult(
                ok=False,
                validation=compile_result.validation,
                canvas=compile_result.canvas,
                errors=list(compile_result.errors),
                warnings=list(compile_result.warnings),
            )

        capsule = compile_result.capsule

        expansion = WorkflowCapsuleExpander().expand(capsule)
        if not expansion.ok:
            return WorkflowArchitectReviewResult(
                ok=False,
                validation=compile_result.validation,
                canvas=compile_result.canvas,
                capsule=self._capsule_summary(capsule),
                errors=list(expansion.errors or []),
                warnings=list(compile_result.warnings) + list(expansion.warnings or []),
            )

        dry = WorkflowCapsuleDryRunExecutor().run(
            capsule,
            expansion,
            available_vault_requirements=[
                f"vault.{name}.credentials" for name in list(connected_credentials or [])
            ],
            cau_state={
                "allow_learn": False,
                "adr_active": False,
                "deny_reason": "architect_review_dry_run_no_learning",
            },
            inputs=inputs or {},
        )

        dry_dict = dry.to_dict() if hasattr(dry, "to_dict") else {}

        review = {
            "workflow_name": spec.workflow_name,
            "goal": spec.goal,
            "step_count": len(spec.steps),
            "edge_count": len(spec.edges),
            "connectors_required": list(spec.connectors_required),
            "missing_connectors": [m.to_dict() for m in spec.missing_connectors],
            "approval_required": bool(dry_dict.get("approval_required")),
            "external_writes_blocked": bool(dry_dict.get("external_writes_blocked")),
            "dry_run_only": True,
            "live_send_enabled": False,
            "canvas_ready": True,
        }

        return WorkflowArchitectReviewResult(
            ok=bool(dry.ok),
            validation=compile_result.validation,
            canvas=compile_result.canvas,
            capsule=self._capsule_summary(capsule),
            dry_run=dry_dict,
            review=review,
            errors=list(compile_result.errors) + list(dry.errors or []),
            warnings=list(compile_result.warnings) + list(dry.warnings or []),
        )

    @staticmethod
    def _capsule_summary(capsule: Any) -> Dict[str, Any]:
        return {
            "canonical_key": getattr(capsule, "canonical_key", ""),
            "display_name": getattr(capsule, "display_name", ""),
            "display_glyph": getattr(capsule, "display_glyph", ""),
            "vault_requirements": list(getattr(capsule, "vault_requirements", []) or []),
            "dry_run_first": bool(getattr(getattr(capsule, "policy", None), "dry_run_first", True)),
        }

def run_workflow_architect_review(
    spec,
    *,
    workflow_goal=None,
    user_steps=None,
    business_context=None,
    connected_credentials=None,
    missing_credentials=None,
    must_not_do=None,
    inputs=None,
):
    """
    Compatibility wrapper for repair-loop callers.

    The repair loop passes extra context so the API shape stays stable, but
    the current review runner only needs the validated WorkflowBuilderSpec,
    connected credentials, and dry-run inputs.
    """
    if isinstance(spec, dict):
        spec = WorkflowBuilderSpec.from_dict(spec)

    return WorkflowArchitectReviewRunner().run_review(
        spec,
        connected_credentials=connected_credentials or [],
        inputs=inputs or {},
    )

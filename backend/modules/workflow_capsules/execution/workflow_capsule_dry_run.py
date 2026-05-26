"""
Workflow Capsule Dry-Run Executor - Aion Workflow Glyph Capsules v1
──────────────────────────────────────────────────────────────────
Produces a safe, inspectable preview of a workflow capsule execution.

No external writes happen here.
No Gmail send happens here.
No memory reinforcement happens here.

This is the first runnable layer after:
  capsule -> registry -> expansion -> policy gate
"""

from __future__ import annotations

from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import attach_goal_engine_manifest_to_dry_result

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional
import time
import uuid

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowExpansionResult,
    WorkflowExpansionStep,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_policy import (
    WorkflowCapsulePolicyGate,
    WorkflowPolicyDecision,
)
from backend.modules.workflow_capsules.permissions.permission_evaluator import (
    PermissionEvaluator,
)
from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionMode,
)
from backend.modules.workflow_capsules.permissions.permission_policy import (
    AgentPermissionProfile,
    WorkflowPermissionPolicy,
)
from backend.modules.workflow_capsules.permissions.workflow_step_permission import (
    permission_context_from_step,
)


DRY_RUN_SCHEMA_VERSION = "aion.workflow_capsule_dry_run.v1"


@dataclass
class WorkflowDryRunStep:
    step_id: str
    kind: str
    label: str
    status: str
    simulated_output_ref: Optional[str] = None
    preview: Dict[str, Any] = field(default_factory=dict)
    blocked_reasons: List[str] = field(default_factory=list)
    permission_decision: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        # Backwards-compatible runner/UI contract:
        # newer dry-run previews carry permission under preview["permission"],
        # older runner metadata tests/UI expect the same decision at
        # step["permission_decision"].
        preview = data.get("preview") if isinstance(data.get("preview"), dict) else {}
        permission = preview.get("permission") if isinstance(preview, dict) else None

        if isinstance(permission, dict):
            data["permission_decision"] = permission
        else:
            data.setdefault("permission_decision", {})

        return data


@dataclass
class WorkflowDryRunResult:
    ok: bool
    run_id: str
    canonical_key: str
    display_name: str
    policy: Dict[str, Any]
    steps: List[WorkflowDryRunStep] = field(default_factory=list)
    approval_required: bool = False
    external_writes_blocked: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = DRY_RUN_SCHEMA_VERSION
        data["steps"] = [s.to_dict() for s in self.steps]
        return data


class WorkflowCapsuleDryRunExecutor:
    """
    Safe dry-run executor.

    This creates previews only. It never performs connector writes.
    """

    def run(
        self,
        capsule: WorkflowCapsule,
        expansion: WorkflowExpansionResult,
        *,
        available_vault_requirements: Optional[List[str]] = None,
        approval_refs: Optional[Dict[str, Any]] = None,
        cau_state: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowDryRunResult:
        run_id = f"wf_dry_{uuid.uuid4().hex[:12]}"
        inputs = inputs or {}

        trace: List[Dict[str, Any]] = [
            {
                "t": time.time(),
                "event": "dry_run_started",
                "run_id": run_id,
                "canonical_key": capsule.canonical_key,
            }
        ]

        policy_decision = WorkflowCapsulePolicyGate().evaluate(
            capsule,
            expansion,
            available_vault_requirements=available_vault_requirements or [],
            approval_refs=approval_refs or {},
            cau_state=cau_state or {},
            phase="dry_run",
        )

        blocked_by_step = {
            b["step_id"]: b.get("reasons", [])
            for b in policy_decision.blocked_steps
        }

        dry_steps: List[WorkflowDryRunStep] = []
        errors: List[str] = list(expansion.errors or [])
        warnings: List[str] = list(expansion.warnings or []) + list(policy_decision.warnings or [])

        if not expansion.ok:
            errors.append("cannot_dry_run_invalid_expansion")

        approval_required = bool(policy_decision.approval_required)

        for step in expansion.steps:
            blocked_reasons = list(blocked_by_step.get(step.step_id, []))
            status = "blocked" if blocked_reasons else "simulated"

            preview = self._preview_step(step, inputs=inputs)

            permission_raw = step.raw.get("permission", {}) if isinstance(step.raw, dict) else {}
            limits_raw = step.raw.get("limits", {}) if isinstance(step.raw, dict) else {}

            if not isinstance(permission_raw, dict):
                permission_raw = {}

            # Limits may be stored either beside permission metadata or nested under it,
            # depending on whether the workflow came from canvas, capsule, or tests.
            nested_limits_raw = permission_raw.get("limits", {}) if isinstance(permission_raw, dict) else {}

            if not isinstance(limits_raw, dict):
                limits_raw = {}
            if not isinstance(nested_limits_raw, dict):
                nested_limits_raw = {}

            merged_limits_raw = {
                **nested_limits_raw,
                **limits_raw,
            }

            confidence = permission_raw.get("confidence")
            risk_flags = (
                list(permission_raw.get("risk_flags") or [])
                if isinstance(permission_raw.get("risk_flags"), list)
                else []
            )

            permission_metadata = (
                dict(permission_raw.get("metadata") or {})
                if isinstance(permission_raw.get("metadata"), dict)
                else {}
            )

            if "max_auto_sends_per_day" in merged_limits_raw:
                permission_metadata["max_auto_sends_per_day"] = merged_limits_raw.get("max_auto_sends_per_day")

            if "allowed_recipient_scope" in merged_limits_raw:
                permission_metadata["allowed_recipient_scope"] = merged_limits_raw.get("allowed_recipient_scope")

            runtime_permission_metadata = (
                dict(inputs.get("permission_metadata") or {})
                if isinstance(inputs.get("permission_metadata"), dict)
                else {}
            )

            runtime_limits = (
                dict(inputs.get("limits") or {})
                if isinstance(inputs.get("limits"), dict)
                else {}
            )

            runtime_context = (
                dict(inputs.get("runtime_context") or {})
                if isinstance(inputs.get("runtime_context"), dict)
                else {}
            )

            for source in [runtime_permission_metadata, runtime_limits, runtime_context]:
                for key in [
                    "auto_sends_today",
                    "max_auto_sends_per_day",
                    "recipient_scope",
                    "allowed_recipient_scope",
                ]:
                    if key in source:
                        permission_metadata[key] = source.get(key)

            permission = self._evaluate_step_permission(
                capsule,
                step,
                confidence=confidence,
                risk_flags=list(risk_flags or []),
                execution_mode="dry_run",
                metadata=permission_metadata,
            )
            permission_dict = permission.to_dict() if hasattr(permission, "to_dict") else dict(permission or {})
            preview["permission"] = permission_dict

            permission_decision = str(permission_dict.get("decision") or "")
            permission_requires_approval = bool(permission_dict.get("requires_approval"))

            if permission_decision == "block":
                status = "blocked"
                if "permission_blocked" not in blocked_reasons:
                    blocked_reasons.append("permission_blocked")

            if permission_requires_approval:
                approval_required = True

            # External writes are always blocked in dry-run even if otherwise policy-valid.
            if self._is_external_write(step):
                status = "blocked"
                if "dry_run_blocks_external_write" not in blocked_reasons:
                    blocked_reasons.append("dry_run_blocks_external_write")

            dry_steps.append(
                WorkflowDryRunStep(
                    step_id=step.step_id,
                    kind=step.kind,
                    label=step.label,
                    status=status,
                    simulated_output_ref=step.output_ref,
                    preview=preview,
                    blocked_reasons=blocked_reasons,
                )
            )
        external_writes_blocked = True

        trace.append(
            {
                "t": time.time(),
                "event": "dry_run_finished",
                "run_id": run_id,
                "step_count": len(dry_steps),
                "blocked_count": len([s for s in dry_steps if s.status == "blocked"]),
                "approval_required": approval_required,
            }
        )

        result = WorkflowDryRunResult(
            ok=not errors and policy_decision.ok,
            run_id=run_id,
            canonical_key=capsule.canonical_key,
            display_name=capsule.display_name,
            policy=policy_decision.to_dict(),
            steps=dry_steps,
            approval_required=approval_required,
            external_writes_blocked=external_writes_blocked,
            errors=errors,
            warnings=warnings,
            trace=trace,
        )

        # GOAL ENGINE DRY-RUN BRIDGE V2
        # Attach Goal Engine manifest, step trace, and Boardroom trace to the
        # final WorkflowDryRunResult, not to per-step permission dictionaries.
        result = attach_goal_engine_manifest_to_dry_result(
            result,
            capsule,
            run_id=run_id,
        )

        return result

    def _evaluate_step_permission(
        self,
        capsule: WorkflowCapsule,
        step: WorkflowExpansionStep,
        *,
        confidence: Any = None,
        risk_flags: Optional[List[str]] = None,
        execution_mode: str = "dry_run",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = step.raw if isinstance(step.raw, dict) else {}
        risk_flags = list(risk_flags or [])
        metadata = dict(metadata or {})
        step_permission = raw.get("permission") if isinstance(raw.get("permission"), dict) else {}

        workflow_graph = capsule.workflow_graph if isinstance(capsule.workflow_graph, dict) else {}
        workflow_mode = (
            raw.get("permission_mode")
            or step_permission.get("node_mode")
            or workflow_graph.get("permission_mode")
            or capsule.meta.get("workflow_permission_mode")
            or "review"
        )

        try:
            mode = PermissionMode(str(workflow_mode))
        except Exception:
            mode = PermissionMode.REVIEW

        permission_policy = workflow_graph.get("permission_policy")
        if not isinstance(permission_policy, dict):
            permission_policy = {}

        policy = WorkflowPermissionPolicy(
            mode=mode,
            workflow_id=capsule.canonical_key,
            allowed_actions=list(permission_policy.get("allowed_actions") or []),
            requires_approval_for=list(permission_policy.get("requires_approval_for") or []),
            blocked_actions=list(permission_policy.get("blocked_actions") or []),
            max_auto_sends_per_day=int(
                metadata.get("max_auto_sends_per_day")
                if metadata.get("max_auto_sends_per_day") is not None
                else permission_policy.get("max_auto_sends_per_day") or 0
            ),
            min_confidence=float(permission_policy.get("min_confidence") or 0.86),
            allowed_recipient_scope=str(
                metadata.get("allowed_recipient_scope")
                or permission_policy.get("allowed_recipient_scope")
                or "original_thread_only"
            ),
            allow_live_execute=bool(permission_policy.get("allow_live_execute") is True),
        )

        agent_id = str(raw.get("agent_id") or permission_policy.get("agent_id") or "agent.default")
        agent_allowed_actions = permission_policy.get("agent_allowed_actions")
        agent_blocked_actions = permission_policy.get("agent_blocked_actions")

        agent = AgentPermissionProfile(
            agent_id=agent_id,
            allowed_actions=list(agent_allowed_actions or []),
            blocked_actions=list(agent_blocked_actions or []),
            can_self_authorise_external_writes=False,
        )

        context = permission_context_from_step(
            raw,
            workspace_id=str(permission_policy.get("workspace_id") or ""),
            agent_id=agent_id,
            workflow_id=capsule.canonical_key,
            execution_mode=execution_mode,
        )

        context.confidence = confidence
        context.risk_flags = risk_flags
        context.metadata = metadata

        result = PermissionEvaluator().evaluate(
            policy=policy,
            agent=agent,
            context=context,
        ).to_dict()

        result["context"] = context.to_dict()
        return result


    def _preview_step(self, step: WorkflowExpansionStep, *, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if step.kind == "connector_read":
            return {
                "description": "Would read from connector.",
                "connector": step.raw.get("connector"),
                "input_refs": step.input_refs,
                "output_ref": step.output_ref,
            }

        if step.kind == "extract":
            return {
                "description": "Would extract structured enquiry intent from email content.",
                "input_refs": step.input_refs,
                "output_ref": step.output_ref,
            }

        if step.kind == "draft_content":
            return {
                "description": "Would draft a Gmail enquiry reply.",
                "draft_preview": {
                    "subject": "Re: your enquiry",
                    "body": "Draft reply preview would be generated here for human review.",
                },
                "input_refs": step.input_refs,
                "output_ref": step.output_ref,
            }

        if step.kind == "approval_checkpoint":
            return {
                "description": "Would create a human approval checkpoint.",
                "approval_required": True,
                "input_refs": step.input_refs,
                "output_ref": step.output_ref,
            }

        if self._is_external_write(step):
            return {
                "description": "External write blocked during dry-run.",
                "connector": step.raw.get("connector"),
                "input_refs": step.input_refs,
                "output_ref": step.output_ref,
            }

        return {
            "description": "Would simulate step.",
            "input_refs": step.input_refs,
            "output_ref": step.output_ref,
        }

    def _is_external_write(self, step: WorkflowExpansionStep) -> bool:
        if step.kind in {"external_write", "send_email", "post_social", "update_crm"}:
            return True
        guard = step.raw.get("guard") if isinstance(step.raw, dict) else {}
        return bool(isinstance(guard, dict) and guard.get("external_write"))


def dry_run_workflow_capsule(
    capsule: WorkflowCapsule,
    expansion: WorkflowExpansionResult,
    **kwargs: Any,
) -> Dict[str, Any]:
    return WorkflowCapsuleDryRunExecutor().run(capsule, expansion, **kwargs).to_dict()

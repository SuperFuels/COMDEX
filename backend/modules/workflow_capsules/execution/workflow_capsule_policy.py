"""
Workflow Capsule Policy Gate - Aion Workflow Glyph Capsules v1
──────────────────────────────────────────────────────────────
Evaluates capsule execution policy before dry-run / approval / execution.

Important model:
- Workflow execution MAY run under capsule policy.
- Workflow learning / feedback / reinforcement MUST require CAU allow_learn.
- External writes MUST be blocked unless policy + approval + vault requirements pass.
- Credentials are never stored in capsules; vault requirements are resolved at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional
import time

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowExpansionResult,
    WorkflowExpansionStep,
)


POLICY_SCHEMA_VERSION = "aion.workflow_capsule_policy_decision.v1"


@dataclass
class WorkflowPolicyDecision:
    ok: bool
    canonical_key: str
    dry_run_required: bool
    approval_required: bool
    external_writes_present: bool
    external_writes_allowed_now: bool
    vault_requirements: List[str] = field(default_factory=list)
    missing_vault_requirements: List[str] = field(default_factory=list)
    blocked_steps: List[Dict[str, Any]] = field(default_factory=list)
    allowed_steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cau: Dict[str, Any] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = POLICY_SCHEMA_VERSION
        return data


class WorkflowCapsulePolicyGate:
    """
    Policy evaluator for capsule-native workflow glyphs.

    This does not execute anything. It only decides what is allowed now.
    """

    def evaluate(
        self,
        capsule: WorkflowCapsule,
        expansion: WorkflowExpansionResult,
        *,
        available_vault_requirements: Optional[List[str]] = None,
        approval_refs: Optional[Dict[str, Any]] = None,
        cau_state: Optional[Dict[str, Any]] = None,
        phase: str = "dry_run",
    ) -> WorkflowPolicyDecision:
        available_vault_requirements = available_vault_requirements or []
        approval_refs = approval_refs or {}
        cau_state = cau_state or {}

        trace: List[Dict[str, Any]] = [
            {
                "t": time.time(),
                "event": "policy_evaluation_started",
                "canonical_key": capsule.canonical_key,
                "phase": phase,
            }
        ]

        errors: List[str] = []
        warnings: List[str] = []

        if not expansion.ok:
            errors.append("expansion_not_ok")

        policy = capsule.policy

        external_steps = [
            s for s in expansion.steps
            if _is_external_write_step(s)
        ]

        external_writes_present = bool(external_steps)
        dry_run_required = bool(policy.dry_run_first)
        approval_required = bool(policy.approval_before_external_write or external_steps)

        capsule_vault = list(capsule.vault_requirements or [])
        step_vault = _collect_step_vault_requirements(expansion.steps)
        all_vault_requirements = sorted(set(capsule_vault + step_vault))

        missing_vault = [
            v for v in all_vault_requirements
            if v not in set(available_vault_requirements)
        ]

        blocked_steps: List[Dict[str, Any]] = []
        allowed_steps: List[Dict[str, Any]] = []

        if phase != "dry_run" and dry_run_required:
            warnings.append("capsule_policy_requires_dry_run_first")

        for step in expansion.steps:
            block_reasons: List[str] = []

            step_requires = _step_requires(step)
            for req in step_requires:
                if req.startswith("vault.") and req not in available_vault_requirements:
                    block_reasons.append(f"missing_vault_requirement:{req}")

            if _is_external_write_step(step):
                if not policy.external_writes_allowed:
                    block_reasons.append("external_writes_disabled_by_capsule_policy")

                if policy.approval_before_external_write:
                    approval_ref = _approval_ref_for_step(step)
                    if approval_ref and not _approval_ref_satisfied(approval_ref, approval_refs):
                        block_reasons.append(f"approval_required:{approval_ref}")
                    elif not approval_ref:
                        block_reasons.append("approval_required")

                if phase == "dry_run":
                    block_reasons.append("dry_run_blocks_external_write")

            if block_reasons:
                blocked_steps.append(
                    {
                        "step_id": step.step_id,
                        "kind": step.kind,
                        "label": step.label,
                        "reasons": block_reasons,
                    }
                )
            else:
                allowed_steps.append(
                    {
                        "step_id": step.step_id,
                        "kind": step.kind,
                        "label": step.label,
                    }
                )

        # CAU governs learning/mutation/reinforcement, not dry-run inspection.
        allow_learn = bool(cau_state.get("allow_learn", False))
        adr_active = bool(cau_state.get("adr_active", False))
        deny_reason = cau_state.get("deny_reason")

        if adr_active:
            warnings.append("ADR active: workflow feedback/reinforcement must be blocked")

        if not allow_learn:
            warnings.append("CAU allow_learn=false: workflow feedback/reinforcement must be blocked")

        external_writes_allowed_now = (
            external_writes_present
            and not any(
                b for b in blocked_steps
                if b.get("kind") == "external_write"
            )
        )

        ok = not errors

        trace.append(
            {
                "t": time.time(),
                "event": "policy_evaluation_finished",
                "ok": ok,
                "blocked_step_count": len(blocked_steps),
                "allowed_step_count": len(allowed_steps),
                "external_writes_present": external_writes_present,
                "external_writes_allowed_now": external_writes_allowed_now,
            }
        )

        return WorkflowPolicyDecision(
            ok=ok,
            canonical_key=capsule.canonical_key,
            dry_run_required=dry_run_required,
            approval_required=approval_required,
            external_writes_present=external_writes_present,
            external_writes_allowed_now=external_writes_allowed_now,
            vault_requirements=all_vault_requirements,
            missing_vault_requirements=missing_vault,
            blocked_steps=blocked_steps,
            allowed_steps=allowed_steps,
            errors=errors,
            warnings=warnings,
            cau={
                "allow_learn": allow_learn,
                "adr_active": adr_active,
                "deny_reason": deny_reason,
                "learning_or_reinforcement_allowed": allow_learn and not adr_active,
            },
            trace=trace,
        )


def _is_external_write_step(step: WorkflowExpansionStep) -> bool:
    if step.kind in {"external_write", "send_email", "post_social", "update_crm"}:
        return True
    guard = step.raw.get("guard") if isinstance(step.raw, dict) else {}
    return bool(isinstance(guard, dict) and guard.get("external_write"))


def _approval_ref_for_step(step: WorkflowExpansionStep) -> Optional[str]:
    guard = step.raw.get("guard") if isinstance(step.raw, dict) else {}
    if isinstance(guard, dict):
        ref = guard.get("requires_approval_ref")
        if ref:
            return str(ref)
    return None


def _approval_ref_satisfied(ref: str, approval_refs: Dict[str, Any]) -> bool:
    value = approval_refs.get(ref)
    if value is True:
        return True
    if isinstance(value, dict):
        return value.get("approved") is True or value.get("status") == "approved"
    return False


def _step_requires(step: WorkflowExpansionStep) -> List[str]:
    raw = getattr(step, "raw", {}) or {}
    reqs = raw.get("requires", []) if isinstance(raw, dict) else []
    if not isinstance(reqs, list):
        return []
    return [str(r) for r in reqs if isinstance(r, str)]


def _collect_step_vault_requirements(steps: List[WorkflowExpansionStep]) -> List[str]:
    out: List[str] = []
    for step in steps:
        for req in _step_requires(step):
            if isinstance(req, str) and req.startswith("vault."):
                out.append(req)
    return out


def evaluate_workflow_capsule_policy(
    capsule: WorkflowCapsule,
    expansion: WorkflowExpansionResult,
    **kwargs: Any,
) -> Dict[str, Any]:
    return WorkflowCapsulePolicyGate().evaluate(capsule, expansion, **kwargs).to_dict()

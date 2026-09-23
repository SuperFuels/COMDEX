from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RESUME_REVALIDATION_SCHEMA_VERSION = "aion.goal_engine.resume_revalidation.v1"


@dataclass(frozen=True)
class ResumeRevalidationContract:
    revalidation_id: str
    run_id: str
    checkpoint_id: str
    approval_still_valid: bool = False
    vault_ready: bool = False
    connectors_ready: bool = False
    parent_goal_still_required: bool = False
    external_state_changed: bool = False
    checked_at: str | None = None
    evidence_refs: list[dict[str, Any]] | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.revalidation_id or "").strip():
            errors.append("revalidation_id is required")

        if not str(self.run_id or "").strip():
            errors.append("run_id is required")

        if not str(self.checkpoint_id or "").strip():
            errors.append("checkpoint_id is required")

        return errors


def build_resume_revalidation_preview(
    contract: ResumeRevalidationContract,
) -> dict[str, Any]:
    validation_errors = contract.validate()
    blocked_reasons: list[str] = []

    if not contract.approval_still_valid:
        blocked_reasons.append("approval_not_valid")

    if not contract.vault_ready:
        blocked_reasons.append("vault_not_ready")

    if not contract.connectors_ready:
        blocked_reasons.append("connectors_not_ready")

    if not contract.parent_goal_still_required:
        blocked_reasons.append("parent_goal_no_longer_required")

    if contract.external_state_changed:
        blocked_reasons.append("external_state_changed")

    for error in validation_errors:
        if error not in blocked_reasons:
            blocked_reasons.append(error)

    safe_stop_required = bool(contract.external_state_changed)
    resume_allowed = not bool(blocked_reasons)

    return {
        "schema_version": RESUME_REVALIDATION_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "resume_revalidation_preview",
        "revalidation_id": contract.revalidation_id,
        "run_id": contract.run_id,
        "checkpoint_id": contract.checkpoint_id,
        "approval_still_valid": contract.approval_still_valid,
        "vault_ready": contract.vault_ready,
        "connectors_ready": contract.connectors_ready,
        "parent_goal_still_required": contract.parent_goal_still_required,
        "external_state_changed": contract.external_state_changed,
        "checked_at": contract.checked_at,
        "evidence_refs": list(contract.evidence_refs or []),
        "valid": not bool(validation_errors),
        "validation_errors": validation_errors,
        "resume_allowed": resume_allowed,
        "resume_blocked": not resume_allowed,
        "safe_stop_required": safe_stop_required,
        "blocked_reasons": blocked_reasons,
        "suggested_next_action": (
            "stop_or_replan_before_resume"
            if safe_stop_required
            else "resume_requires_environment_revalidation"
            if not resume_allowed
            else "resume_can_be_considered_after_human_review"
        ),
        "dry_run_only": True,
        "would_resume": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

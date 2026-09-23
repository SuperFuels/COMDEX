from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import json


CHECKPOINT_SCHEMA_VERSION = "aion.goal_engine.checkpoint.v1"
STATE_DELTA_SCHEMA_VERSION = "aion.goal_engine.state_delta.v1"


@dataclass(frozen=True)
class StateDeltaContract:
    delta_id: str
    run_id: str
    checkpoint_id: str
    changed_fields: dict[str, Any] = field(default_factory=dict)
    full_payload: dict[str, Any] | None = None
    max_delta_bytes: int = 32_000

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.delta_id:
            errors.append("delta_id is required")
        if not self.run_id:
            errors.append("run_id is required")
        if not self.checkpoint_id:
            errors.append("checkpoint_id is required")
        if self.max_delta_bytes < 1024:
            errors.append("max_delta_bytes must be at least 1024")

        try:
            delta_size = len(json.dumps(self.changed_fields or {}, sort_keys=True).encode("utf-8"))
        except Exception:
            delta_size = self.max_delta_bytes + 1

        if delta_size > self.max_delta_bytes:
            errors.append("state_delta_exceeds_max_delta_bytes")

        if self.full_payload:
            errors.append("full_payload_not_allowed")

        return errors


@dataclass(frozen=True)
class CheckpointContract:
    checkpoint_id: str
    run_id: str
    goal_id: str
    loop_id: str
    iteration: int = 0
    parent_run_id: str | None = None
    created_at: str | None = None
    resume_status: str = "waiting_revalidation"
    state_delta_id: str | None = None
    loop_context_snapshot: dict[str, Any] = field(default_factory=dict)
    environment_revalidation_required: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.checkpoint_id:
            errors.append("checkpoint_id is required")
        if not self.run_id:
            errors.append("run_id is required")
        if not self.goal_id:
            errors.append("goal_id is required")
        if not self.loop_id:
            errors.append("loop_id is required")
        if self.iteration < 0:
            errors.append("iteration must be zero or greater")

        return errors


def build_state_delta_preview(delta: StateDeltaContract) -> dict[str, Any]:
    validation_errors = delta.validate()
    blocked_reasons = []

    if delta.full_payload:
        blocked_reasons.append("full_payload_not_allowed")

    if "state_delta_exceeds_max_delta_bytes" in validation_errors:
        blocked_reasons.append("state_delta_exceeds_max_delta_bytes")

    return {
        "schema_version": STATE_DELTA_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "state_delta_preview",
        "delta_id": delta.delta_id,
        "run_id": delta.run_id,
        "checkpoint_id": delta.checkpoint_id,
        "changed_fields": dict(delta.changed_fields or {}),
        "bounded": "state_delta_exceeds_max_delta_bytes" not in validation_errors,
        "stores_full_payload": False,
        "full_payload_blocked": bool(delta.full_payload),
        "max_delta_bytes": delta.max_delta_bytes,
        "valid": not bool(validation_errors),
        "validation_errors": validation_errors,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def build_checkpoint_preview(checkpoint: CheckpointContract) -> dict[str, Any]:
    validation_errors = checkpoint.validate()
    blocked_reasons = []

    resume_blocked_until_revalidated = bool(checkpoint.environment_revalidation_required)
    if resume_blocked_until_revalidated:
        blocked_reasons.append("resume_requires_environment_revalidation")

    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "checkpoint_preview",
        "checkpoint_id": checkpoint.checkpoint_id,
        "run_id": checkpoint.run_id,
        "parent_run_id": checkpoint.parent_run_id,
        "goal_id": checkpoint.goal_id,
        "loop_id": checkpoint.loop_id,
        "iteration": checkpoint.iteration,
        "created_at": checkpoint.created_at,
        "resume_status": checkpoint.resume_status,
        "state_delta_id": checkpoint.state_delta_id,
        "loop_context_snapshot": dict(checkpoint.loop_context_snapshot or {}),
        "environment_revalidation_required": checkpoint.environment_revalidation_required,
        "resume_blocked_until_revalidated": resume_blocked_until_revalidated,
        "valid": not bool(validation_errors),
        "validation_errors": validation_errors,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_resume": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

CHECKPOINT_COMPACTION_SCHEMA_VERSION = "aion.goal_engine.checkpoint_compaction.v1"
CHECKPOINT_PRUNE_SCHEMA_VERSION = "aion.goal_engine.checkpoint_prune.v1"


def build_checkpoint_compaction_preview(
    checkpoints: list[dict[str, Any]],
    *,
    keep_last: int = 3,
) -> dict[str, Any]:
    """
    Dry-run preview for checkpoint compaction.

    This does not delete or mutate checkpoint state. It only reports what would
    be compacted once guarded persistence support exists.
    """
    rows = list(checkpoints or [])
    keep_last = max(1, int(keep_last or 1))

    retained = rows[-keep_last:] if rows else []
    compactable = rows[:-keep_last] if len(rows) > keep_last else []

    return {
        "schema_version": CHECKPOINT_COMPACTION_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "checkpoint_compaction_preview",
        "checkpoint_count": len(rows),
        "retained_count": len(retained),
        "compactable_count": len(compactable),
        "keep_last": keep_last,
        "retained_checkpoint_ids": [
            str(row.get("checkpoint_id") or "") for row in retained if isinstance(row, dict)
        ],
        "compactable_checkpoint_ids": [
            str(row.get("checkpoint_id") or "") for row in compactable if isinstance(row, dict)
        ],
        "would_compact": bool(compactable),
        "would_delete": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "dry_run_only": True,
        "blocked_reasons": ["dry_run_only", "guarded_checkpoint_persistence_required"],
    }


def build_checkpoint_prune_preview(
    checkpoints: list[dict[str, Any]],
    *,
    obsolete_statuses: list[str] | None = None,
) -> dict[str, Any]:
    """
    Dry-run preview for pruning obsolete checkpoints.

    This is visibility only. Actual pruning requires a future guarded mutation
    path and human review.
    """
    rows = list(checkpoints or [])
    obsolete_statuses = obsolete_statuses or ["completed", "failed", "cancelled", "obsolete"]
    obsolete_set = {str(item) for item in obsolete_statuses}

    prune_candidates = []
    retained = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("resume_status") or row.get("status") or "")
        if status in obsolete_set:
            prune_candidates.append(row)
        else:
            retained.append(row)

    return {
        "schema_version": CHECKPOINT_PRUNE_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "checkpoint_prune_preview",
        "checkpoint_count": len(rows),
        "prune_candidate_count": len(prune_candidates),
        "retained_count": len(retained),
        "obsolete_statuses": list(obsolete_statuses),
        "prune_candidate_checkpoint_ids": [
            str(row.get("checkpoint_id") or "") for row in prune_candidates
        ],
        "retained_checkpoint_ids": [
            str(row.get("checkpoint_id") or "") for row in retained
        ],
        "would_prune": bool(prune_candidates),
        "would_delete": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "dry_run_only": True,
        "blocked_reasons": ["dry_run_only", "human_review_required"],
    }

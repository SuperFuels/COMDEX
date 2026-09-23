"""
AION Phase 20N.2 — Plan Diff + Sub-Plan Governance

Locks:
- Any new plan/sub-plan must be reviewable before execution.
- Sub-plans cannot silently expand authority.
- Plan changes produce a deterministic diff.
- Parent safety boundaries cannot be weakened by sub-plans.
- Sub-plan depth and total step ceilings are enforced.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any


CONTROL_ORDER: dict[str, int] = {
    "autonomous": 0,
    "human_approval_required": 1,
    "human_task_required": 2,
    "blocked": 3,
}


RISKY_LANES = {
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _step_map(steps: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(step["step_id"]): step for step in steps}


def _step_risk_summary(step: dict[str, Any]) -> dict[str, Any]:
    lane = step.get("lane", "internal_ops")
    decision = step.get("effective_decision") or step.get("default_decision", "autonomous")
    return {
        "step_id": step.get("step_id"),
        "lane": lane,
        "risk_level": step.get("risk_level", "low"),
        "decision": decision,
        "external_side_effect": bool(step.get("external_side_effect", lane in RISKY_LANES)),
        "estimated_cost": step.get("estimated_cost"),
        "provider": step.get("provider"),
        "payload_required_later": bool(step.get("payload_required_later", False)),
    }


def create_plan_diff(
    *,
    previous_plan: dict[str, Any],
    current_plan: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    previous_steps = _step_map(previous_plan.get("steps", []))
    current_steps = _step_map(current_plan.get("steps", []))

    previous_ids = set(previous_steps)
    current_ids = set(current_steps)

    added_ids = sorted(current_ids - previous_ids)
    removed_ids = sorted(previous_ids - current_ids)
    shared_ids = sorted(previous_ids & current_ids)

    added_steps = [_step_risk_summary(current_steps[step_id]) for step_id in added_ids]
    removed_steps = [_step_risk_summary(previous_steps[step_id]) for step_id in removed_ids]

    modified_steps: list[dict[str, Any]] = []
    for step_id in shared_ids:
        before = previous_steps[step_id]
        after = current_steps[step_id]
        if _canonical_json(before) != _canonical_json(after):
            modified_steps.append(
                {
                    "step_id": step_id,
                    "before": _step_risk_summary(before),
                    "after": _step_risk_summary(after),
                }
            )

    new_approval_gates = [
        step for step in added_steps
        if step["decision"] == "human_approval_required" or step["payload_required_later"]
    ]
    new_human_tasks = [
        step for step in added_steps
        if step["decision"] == "human_task_required"
    ]
    new_external_side_effects = [
        step for step in added_steps
        if step["external_side_effect"]
    ]

    previous_cost = round(
        sum(float(step.get("estimated_cost") or 0) for step in previous_plan.get("steps", [])),
        2,
    )
    current_cost = round(
        sum(float(step.get("estimated_cost") or 0) for step in current_plan.get("steps", [])),
        2,
    )
    estimated_cost_delta = round(current_cost - previous_cost, 2)

    diff = {
        "schema_version": "aion.plan_diff.v0",
        "previous_plan_id": previous_plan.get("plan_id"),
        "previous_plan_version": previous_plan.get("plan_version"),
        "previous_matrix_hash": previous_plan.get("plan_approval_matrix_hash"),
        "current_plan_id": current_plan.get("plan_id"),
        "current_plan_version": current_plan.get("plan_version"),
        "current_matrix_hash": current_plan.get("plan_approval_matrix_hash"),
        "reason": reason,
        "added_steps": added_steps,
        "removed_steps": removed_steps,
        "modified_steps": modified_steps,
        "new_approval_gates": new_approval_gates,
        "new_human_tasks": new_human_tasks,
        "new_external_side_effects": new_external_side_effects,
        "previous_estimated_cost": previous_cost,
        "current_estimated_cost": current_cost,
        "estimated_cost_delta": estimated_cost_delta,
        "requires_re_review": bool(
            added_steps
            or removed_steps
            or modified_steps
            or previous_plan.get("plan_approval_matrix_hash") != current_plan.get("plan_approval_matrix_hash")
        ),
        "plan_diff_hash": "",
    }
    diff["plan_diff_hash"] = _hash({k: v for k, v in diff.items() if k != "plan_diff_hash"})
    return diff


@dataclass(frozen=True)
class SubPlan:
    schema_version: str
    parent_mission_id: str
    parent_mission_run_id: str
    parent_plan_id: str
    subplan_id: str
    subplan_version: int
    subplan_depth: int
    reason_created: str
    inherited_parent_matrix_hash: str
    parent_safety_ceiling: str
    steps: list[dict[str, Any]]
    max_subplan_depth: int
    max_total_steps_across_all_plans: int
    subplan_review_required: bool
    subplan_execution_allowed: bool
    violation_reason: str | None
    subplan_approval_matrix_hash: str


def strictest_decision(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "autonomous"

    max_rank = max(
        CONTROL_ORDER.get(step.get("effective_decision") or step.get("default_decision", "autonomous"), 0)
        for step in steps
    )
    for decision, rank in CONTROL_ORDER.items():
        if rank == max_rank:
            return decision
    return "blocked"


def validate_subplan_authority(
    *,
    parent_steps: list[dict[str, Any]],
    subplan_steps: list[dict[str, Any]],
    parent_safety_ceiling: str | None = None,
) -> dict[str, Any]:
    ceiling = parent_safety_ceiling or strictest_decision(parent_steps)
    ceiling_rank = CONTROL_ORDER[ceiling]

    violations: list[dict[str, Any]] = []
    for step in subplan_steps:
        decision = step.get("effective_decision") or step.get("default_decision", "autonomous")
        lane = step.get("lane", "internal_ops")
        rank = CONTROL_ORDER.get(decision, 0)

        if rank < ceiling_rank and lane in RISKY_LANES:
            violations.append(
                {
                    "step_id": step.get("step_id"),
                    "decision": decision,
                    "parent_safety_ceiling": ceiling,
                    "reason": "subplan_attempted_to_weaken_parent_boundary",
                }
            )

    result = {
        "schema_version": "aion.subplan_authority_validation.v0",
        "parent_safety_ceiling": ceiling,
        "authority_valid": not violations,
        "violations": violations,
        "violation_count": len(violations),
        "validation_hash": "",
    }
    result["validation_hash"] = _hash({k: v for k, v in result.items() if k != "validation_hash"})
    return result


def create_subplan_approval_matrix(
    *,
    parent_mission_id: str,
    parent_mission_run_id: str,
    parent_plan_id: str,
    parent_matrix_hash: str,
    parent_steps: list[dict[str, Any]],
    subplan_id: str,
    reason_created: str,
    subplan_steps: list[dict[str, Any]],
    subplan_version: int = 1,
    subplan_depth: int = 1,
    max_subplan_depth: int = 3,
    max_total_steps_across_all_plans: int = 100,
    current_total_steps_across_all_plans: int | None = None,
) -> dict[str, Any]:
    total_steps = current_total_steps_across_all_plans
    if total_steps is None:
        total_steps = len(parent_steps) + len(subplan_steps)

    depth_violation = subplan_depth > max_subplan_depth
    total_step_violation = total_steps > max_total_steps_across_all_plans

    authority = validate_subplan_authority(
        parent_steps=parent_steps,
        subplan_steps=subplan_steps,
    )

    violation_reason = None
    if depth_violation:
        violation_reason = "max_subplan_depth_exceeded"
    elif total_step_violation:
        violation_reason = "max_total_steps_exceeded"
    elif not authority["authority_valid"]:
        violation_reason = "subplan_authority_violation"

    base = {
        "schema_version": "aion.subplan_approval_matrix.v0",
        "parent_mission_id": parent_mission_id,
        "parent_mission_run_id": parent_mission_run_id,
        "parent_plan_id": parent_plan_id,
        "subplan_id": subplan_id,
        "subplan_version": subplan_version,
        "subplan_depth": subplan_depth,
        "reason_created": reason_created,
        "inherited_parent_matrix_hash": parent_matrix_hash,
        "parent_safety_ceiling": authority["parent_safety_ceiling"],
        "steps": subplan_steps,
        "max_subplan_depth": max_subplan_depth,
        "max_total_steps_across_all_plans": max_total_steps_across_all_plans,
        "current_total_steps_across_all_plans": total_steps,
        "depth_violation": depth_violation,
        "total_step_violation": total_step_violation,
        "authority_validation": authority,
        "subplan_review_required": True,
        "subplan_execution_allowed": False,
        "violation_reason": violation_reason,
        "subplan_approval_matrix_hash": "",
    }
    base["subplan_approval_matrix_hash"] = _hash(
        {k: v for k, v in base.items() if k != "subplan_approval_matrix_hash"}
    )
    return base


def approve_subplan_matrix(
    *,
    subplan_matrix: dict[str, Any],
    approving_human: str,
) -> dict[str, Any]:
    if subplan_matrix.get("violation_reason"):
        approved = False
        reason = subplan_matrix["violation_reason"]
    else:
        approved = True
        reason = "subplan_matrix_approved"

    approval = {
        "schema_version": "aion.subplan_approval.v0",
        "parent_mission_id": subplan_matrix["parent_mission_id"],
        "parent_mission_run_id": subplan_matrix["parent_mission_run_id"],
        "parent_plan_id": subplan_matrix["parent_plan_id"],
        "subplan_id": subplan_matrix["subplan_id"],
        "subplan_version": subplan_matrix["subplan_version"],
        "approving_human": approving_human,
        "approved_subplan_matrix_hash": subplan_matrix["subplan_approval_matrix_hash"],
        "approved": approved,
        "subplan_execution_allowed": approved,
        "reason": reason,
        "subplan_approval_hash": "",
    }
    approval["subplan_approval_hash"] = _hash(
        {k: v for k, v in approval.items() if k != "subplan_approval_hash"}
    )
    return approval


def create_subplan_tree_hash(
    *,
    parent_plan_hash: str,
    subplan_hashes: list[str],
) -> str:
    return _hash(
        {
            "parent_plan_hash": parent_plan_hash,
            "subplan_hashes": sorted(subplan_hashes),
        }
    )

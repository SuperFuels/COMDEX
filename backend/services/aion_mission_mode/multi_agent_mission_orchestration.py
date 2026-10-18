from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List


class MissionOrchestrationViolation(ValueError):
    pass


VALID_AGENT_ROLES = {
    "mission_coordinator",
    "planner_agent",
    "research_agent",
    "content_agent",
    "build_agent",
    "browser_worker_agent",
    "review_agent",
    "proof_agent",
}

VALID_HANDOFF_POLICIES = {
    "coordinator_approves_all",
    "parent_scope_required",
    "proof_required_before_handoff",
}

VALID_CONFLICT_POLICIES = {
    "fail_closed",
    "coordinator_decides_with_review",
    "human_review_required",
}

RISK_ORDER = {
    "autonomous": 0,
    "human_approval_required": 1,
    "human_task_required": 2,
    "blocked": 3,
}


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def strictest_decision(left: str, right: str) -> str:
    if left not in RISK_ORDER or right not in RISK_ORDER:
        raise MissionOrchestrationViolation("Unknown control decision")
    return left if RISK_ORDER[left] >= RISK_ORDER[right] else right


def create_mission_coordinator(meta: Dict[str, Any]) -> Dict[str, Any]:
    coordinator = {
        "mission_id": meta["mission_id"],
        "mission_run_id": meta["mission_run_id"],
        "business_id": meta["business_id"],
        "agent_id": meta.get("mission_coordinator_agent", "agent:mission_coordinator"),
        "agent_role": "mission_coordinator",
        "responsibilities": [
            "decompose_goal",
            "assign_sub_agents",
            "enforce_parent_scope",
            "monitor_handoffs",
            "aggregate_final_receipt",
            "fail_closed_on_scope_violation",
        ],
        "can_execute_live_tools": False,
        "coordinator_state": "active_scope_guard",
    }
    coordinator["coordinator_hash"] = canonical_hash(coordinator)
    return coordinator


def validate_parent_scope(parent_scope: Dict[str, Any]) -> Dict[str, Any]:
    required = [
        "mission_id",
        "mission_run_id",
        "business_id",
        "allowed_lanes",
        "allowed_capabilities",
        "max_sub_agents",
        "max_handoff_depth",
        "default_control_decision",
    ]
    missing = [key for key in required if key not in parent_scope]
    if missing:
        raise MissionOrchestrationViolation(f"Missing parent scope fields: {missing}")

    if parent_scope["default_control_decision"] not in RISK_ORDER:
        raise MissionOrchestrationViolation("Invalid parent default control decision")

    scope = dict(parent_scope)
    scope["allowed_lanes"] = sorted(set(scope["allowed_lanes"]))
    scope["allowed_capabilities"] = sorted(set(scope["allowed_capabilities"]))
    scope["parent_scope_hash"] = canonical_hash({
        k: v for k, v in scope.items() if k != "parent_scope_hash"
    })
    return scope


def create_sub_agent_assignment(
    parent_scope: Dict[str, Any],
    agent_spec: Dict[str, Any],
) -> Dict[str, Any]:
    scope = validate_parent_scope(parent_scope)

    role = agent_spec["agent_role"]
    if role not in VALID_AGENT_ROLES:
        raise MissionOrchestrationViolation(f"Unsupported agent role: {role}")

    requested_lanes = sorted(set(agent_spec.get("requested_lanes", [])))
    requested_caps = sorted(set(agent_spec.get("requested_capabilities", [])))

    lane_violations = [lane for lane in requested_lanes if lane not in scope["allowed_lanes"]]
    cap_violations = [cap for cap in requested_caps if cap not in scope["allowed_capabilities"]]

    if lane_violations or cap_violations:
        return {
            "mission_id": scope["mission_id"],
            "mission_run_id": scope["mission_run_id"],
            "business_id": scope["business_id"],
            "agent_id": agent_spec["agent_id"],
            "agent_role": role,
            "assignment_allowed": False,
            "assignment_state": "scope_violation_blocked",
            "lane_violations": lane_violations,
            "capability_violations": cap_violations,
            "assignment_hash": canonical_hash({
                "agent_id": agent_spec["agent_id"],
                "lane_violations": lane_violations,
                "capability_violations": cap_violations,
            }),
        }

    inherited_decision = strictest_decision(
        scope["default_control_decision"],
        agent_spec.get("requested_control_decision", "autonomous"),
    )

    assignment = {
        "mission_id": scope["mission_id"],
        "mission_run_id": scope["mission_run_id"],
        "business_id": scope["business_id"],
        "parent_scope_hash": scope["parent_scope_hash"],
        "agent_id": agent_spec["agent_id"],
        "agent_role": role,
        "assigned_goal": agent_spec["assigned_goal"],
        "inherited_lanes": requested_lanes,
        "inherited_capabilities": requested_caps,
        "effective_control_decision": inherited_decision,
        "assignment_allowed": True,
        "assignment_state": "assigned_under_parent_scope",
        "may_exceed_parent_permissions": False,
        "may_execute_live_tools_directly": False,
    }
    assignment["assignment_hash"] = canonical_hash(assignment)
    return assignment


def create_handoff_record(
    meta: Dict[str, Any],
    from_agent_id: str,
    to_agent_id: str,
    payload_hash: str,
    handoff_policy: str = "parent_scope_required",
) -> Dict[str, Any]:
    if handoff_policy not in VALID_HANDOFF_POLICIES:
        raise MissionOrchestrationViolation(f"Invalid handoff policy: {handoff_policy}")

    record = {
        "mission_id": meta["mission_id"],
        "mission_run_id": meta["mission_run_id"],
        "business_id": meta["business_id"],
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "payload_hash": payload_hash,
        "handoff_policy": handoff_policy,
        "handoff_state": "pending_coordinator_review",
        "requires_parent_scope_validation": True,
        "requires_receipt_binding": True,
    }
    record["handoff_hash"] = canonical_hash(record)
    return record


def resolve_agent_conflict(
    meta: Dict[str, Any],
    conflict: Dict[str, Any],
    conflict_resolution_policy: str = "fail_closed",
) -> Dict[str, Any]:
    if conflict_resolution_policy not in VALID_CONFLICT_POLICIES:
        raise MissionOrchestrationViolation(
            f"Invalid conflict resolution policy: {conflict_resolution_policy}"
        )

    requires_human = conflict_resolution_policy in {
        "human_review_required",
        "coordinator_decides_with_review",
    }

    blocked = conflict_resolution_policy == "fail_closed"

    result = {
        "mission_id": meta["mission_id"],
        "mission_run_id": meta["mission_run_id"],
        "business_id": meta["business_id"],
        "conflict_type": conflict["conflict_type"],
        "agent_ids": sorted(conflict["agent_ids"]),
        "conflicting_hashes": sorted(conflict["conflicting_hashes"]),
        "conflict_resolution_policy": conflict_resolution_policy,
        "resolution_state": "blocked_for_safety" if blocked else "waiting_human_review" if requires_human else "coordinator_review",
        "requires_human_review": requires_human,
        "execution_blocked": blocked,
    }
    result["conflict_hash"] = canonical_hash(result)
    return result


def compile_agent_hierarchy(
    meta: Dict[str, Any],
    coordinator: Dict[str, Any],
    assignments: List[Dict[str, Any]],
    handoffs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    allowed_assignments = [a for a in assignments if a.get("assignment_allowed")]
    blocked_assignments = [a for a in assignments if not a.get("assignment_allowed")]

    hierarchy = {
        "mission_id": meta["mission_id"],
        "mission_run_id": meta["mission_run_id"],
        "business_id": meta["business_id"],
        "coordinator_hash": coordinator["coordinator_hash"],
        "agent_count": len(allowed_assignments),
        "blocked_agent_count": len(blocked_assignments),
        "assignment_hashes": sorted(a["assignment_hash"] for a in assignments),
        "handoff_hashes": sorted(h["handoff_hash"] for h in handoffs),
        "hierarchy_state": "ready_for_boardroom" if not blocked_assignments else "scope_blocks_visible",
        "boardroom_must_show_agent_hierarchy": True,
    }
    hierarchy["agent_hierarchy_hash"] = canonical_hash(hierarchy)
    return hierarchy


def aggregate_final_receipt(
    meta: Dict[str, Any],
    receipt_hashes: List[str],
    assignment_hashes: List[str],
    handoff_hashes: List[str],
) -> Dict[str, Any]:
    receipt = {
        "mission_id": meta["mission_id"],
        "mission_run_id": meta["mission_run_id"],
        "business_id": meta["business_id"],
        "receipt_hashes": sorted(receipt_hashes),
        "assignment_hashes": sorted(assignment_hashes),
        "handoff_hashes": sorted(handoff_hashes),
        "aggregated_by": "mission_coordinator",
        "aggregation_state": "final_receipt_ready",
    }
    receipt["coordinator_final_receipt_hash"] = canonical_hash(receipt)
    return receipt

from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any


AGENT_ASSIGNMENT_SCHEMA_VERSION = "aion.goal_engine.agent_assignment.v1"
ORCHESTRATOR_SCHEMA_VERSION = "aion.goal_engine.orchestrator.v1"

SUPPORTED_AGENT_ROLES = {
    "research",
    "marketing",
    "sales",
    "support",
    "finance",
    "operations",
    "critic",
    "reviewer",
}

SUPPORTED_COORDINATION_MODES = {
    "sequential",
    "parallel",
    "review_gated",
}

SUPPORTED_CONFLICT_POLICIES = {
    "human_review",
    "majority_vote",
    "highest_confidence",
    "safest_option",
}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(getattr(value, "__dict__", {}) or {})
    return {}


@dataclass(frozen=True)
class AgentAssignmentContract:
    agent_id: str
    role: str
    glyph_code: str
    goal_id: str
    capabilities: list[str] = field(default_factory=list)
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.agent_id or "").strip():
            errors.append("agent_id_required")

        role = str(self.role or "").strip()
        if not role:
            errors.append("role_required")
        elif role not in SUPPORTED_AGENT_ROLES:
            errors.append("unsupported_agent_role")

        if not str(self.glyph_code or "").strip():
            errors.append("glyph_code_required")

        if not str(self.goal_id or "").strip():
            errors.append("goal_id_required")

        return errors


@dataclass(frozen=True)
class OrchestratorContract:
    orchestrator_id: str
    goal_id: str
    agents: list[AgentAssignmentContract] = field(default_factory=list)
    coordination_mode: str = "sequential"
    conflict_policy: str = "human_review"
    max_parallel_agents: int = 1
    child_timeout_seconds: int = 300
    requires_human_approval: bool = False
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.orchestrator_id or "").strip():
            errors.append("orchestrator_id_required")

        if not str(self.goal_id or "").strip():
            errors.append("goal_id_required")

        if not self.agents:
            errors.append("agents_required")

        coordination_mode = str(self.coordination_mode or "").strip()
        if coordination_mode not in SUPPORTED_COORDINATION_MODES:
            errors.append("unsupported_coordination_mode")

        conflict_policy = str(self.conflict_policy or "").strip()
        if conflict_policy not in SUPPORTED_CONFLICT_POLICIES:
            errors.append("unsupported_conflict_policy")

        if int(self.max_parallel_agents or 0) <= 0:
            errors.append("max_parallel_agents_required")

        if int(self.child_timeout_seconds or 0) <= 0:
            errors.append("child_timeout_required")

        for agent in self.agents:
            errors.extend(agent.validate())

        return errors


def build_agent_assignment_preview(agent: AgentAssignmentContract | dict[str, Any]) -> dict[str, Any]:
    if not isinstance(agent, AgentAssignmentContract):
        payload = _as_dict(agent)
        agent = AgentAssignmentContract(
            agent_id=str(payload.get("agent_id") or ""),
            role=str(payload.get("role") or ""),
            glyph_code=str(payload.get("glyph_code") or ""),
            goal_id=str(payload.get("goal_id") or ""),
            capabilities=list(payload.get("capabilities") or []),
            notes=str(payload.get("notes") or ""),
        )

    blocked_reasons = agent.validate()

    return {
        "schema_version": AGENT_ASSIGNMENT_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "agent_assignment_preview",
        "agent_id": agent.agent_id,
        "role": agent.role,
        "glyph_code": agent.glyph_code,
        "goal_id": agent.goal_id,
        "capabilities": list(agent.capabilities or []),
        "valid": not bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def build_orchestrator_preview(contract: OrchestratorContract) -> dict[str, Any]:
    validation_errors = contract.validate()
    blocked_reasons = list(dict.fromkeys(validation_errors))

    agent_assignment_previews = [
        build_agent_assignment_preview(agent)
        for agent in list(contract.agents or [])
    ]

    for preview in agent_assignment_previews:
        for reason in preview.get("blocked_reasons") or []:
            reason_text = str(reason or "").strip()
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

    bounded = bool(
        contract.agents
        and int(contract.max_parallel_agents or 0) > 0
        and int(contract.child_timeout_seconds or 0) > 0
    )

    if not bounded and "unbounded_orchestration_blocked" not in blocked_reasons:
        blocked_reasons.append("unbounded_orchestration_blocked")

    return {
        "schema_version": ORCHESTRATOR_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "orchestrator_preview",
        "orchestrator_id": contract.orchestrator_id,
        "goal_id": contract.goal_id,
        "agent_count": len(contract.agents or []),
        "agents": [preview["agent_id"] for preview in agent_assignment_previews],
        "roles": [preview["role"] for preview in agent_assignment_previews],
        "glyph_codes": [preview["glyph_code"] for preview in agent_assignment_previews],
        "coordination_mode": contract.coordination_mode,
        "conflict_policy": contract.conflict_policy,
        "max_parallel_agents": int(contract.max_parallel_agents or 0),
        "child_timeout_seconds": int(contract.child_timeout_seconds or 0),
        "requires_human_approval": bool(contract.requires_human_approval),
        "bounded": bounded,
        "valid": not bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "agent_assignment_previews": agent_assignment_previews,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

# ---------------------------------------------------------------------------
# AION Goal Engine Orchestrator Parent/Child Aggregation v1
# ---------------------------------------------------------------------------
# Preview-only aggregation. It derives parent visibility from child agents/glyphs
# but does not mutate parent goals, run children, write externally, or grant
# permission.

ORCHESTRATOR_PARENT_CHILD_AGGREGATION_SCHEMA_VERSION = "aion.goal_engine.orchestrator_parent_child_aggregation.v1"


CHILD_AGENT_CONFLICT_SCHEMA_VERSION = "aion.goal_engine.child_agent_conflict.v1"


def _child_ref(child: dict[str, Any]) -> str:
    return str(
        child.get("agent_id")
        or child.get("glyph_code")
        or child.get("run_id")
        or child.get("workflow_id")
        or child.get("id")
        or "child"
    )


def _normalise_recommendation(child: dict[str, Any]) -> str:
    return str(
        child.get("recommendation")
        or child.get("recommended_action")
        or child.get("decision")
        or child.get("outcome")
        or ""
    ).strip().lower()


def build_child_agent_conflict_preview(
    *,
    parent_goal_id: str,
    child_agents: list[dict] | None = None,
    child_glyphs: list[dict] | None = None,
    conflict_policy: str = "human_review",
) -> dict:
    child_agents = list(child_agents or [])
    child_glyphs = list(child_glyphs or [])
    children = child_agents + child_glyphs

    blocked_reasons: list[str] = []
    if not str(parent_goal_id or "").strip():
        blocked_reasons.append("parent_goal_id_required")
    if not children:
        blocked_reasons.append("child_agents_or_glyphs_required")

    recommendation_rows: list[dict[str, Any]] = []
    recommendations: list[str] = []

    for child in children:
        recommendation = _normalise_recommendation(child)
        if recommendation:
            recommendations.append(recommendation)
        recommendation_rows.append(
            {
                "child_ref": _child_ref(child),
                "recommendation": recommendation or "none",
                "confidence": child.get("confidence"),
                "status": child.get("status") or child.get("run_status") or "unknown",
            }
        )

    unique_recommendations = sorted(set(recommendations))
    conflict_detected = len(unique_recommendations) > 1

    if conflict_detected:
        recommended_resolution = "human_review_required"
        manual_review_required = True
        if "child_agent_conflict_requires_review" not in blocked_reasons:
            blocked_reasons.append("child_agent_conflict_requires_review")
    elif blocked_reasons:
        recommended_resolution = "blocked_until_required_inputs_exist"
        manual_review_required = True
    else:
        recommended_resolution = "no_conflict_detected"
        manual_review_required = False

    return {
        "schema_version": CHILD_AGENT_CONFLICT_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "child_agent_conflict_preview",
        "parent_goal_id": str(parent_goal_id or ""),
        "child_count": len(children),
        "child_agents": child_agents,
        "child_glyphs": child_glyphs,
        "recommendations": unique_recommendations,
        "recommendation_rows": recommendation_rows,
        "conflict_detected": conflict_detected,
        "conflict_policy": str(conflict_policy or "human_review"),
        "recommended_resolution": recommended_resolution,
        "manual_review_required": manual_review_required,
        "blocked_reasons": blocked_reasons,
        "valid": bool(parent_goal_id and children),
        "dry_run_only": True,
        "would_auto_resolve": False,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_parent_goal": False,
        "would_grant_permission": False,
    }


def build_parent_goal_update_proposal_preview(
    *,
    parent_goal_id: str,
    current_parent_goal_status: str = "derived_preview",
    aggregate_status: str = "in_progress_review_required",
    completed_child_count: int = 0,
    child_count: int = 0,
    blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    blocked_reasons = list(blocked_reasons or [])

    proposal_blocked_reasons: list[str] = []
    if not str(parent_goal_id or "").strip():
        proposal_blocked_reasons.append("parent_goal_id_required")

    if int(child_count or 0) <= 0:
        proposal_blocked_reasons.append("child_agents_or_glyphs_required")

    all_children_complete = bool(child_count and completed_child_count == child_count)
    if not all_children_complete:
        proposal_blocked_reasons.append("all_children_completed_required")

    for reason in blocked_reasons:
        reason_text = str(reason or "").strip()
        if reason_text and reason_text not in proposal_blocked_reasons:
            proposal_blocked_reasons.append(reason_text)

    if not str(parent_goal_id or "").strip():
        proposed_status = "blocked"
    elif all_children_complete:
        proposed_status = "ready_for_completion_review"
    else:
        proposed_status = "keep_current_status"

    return {
        "schema_version": "aion.goal_engine.parent_goal_update_proposal.v1",
        "runtime": "aion_goal_engine",
        "trace_type": "parent_goal_update_proposal",
        "parent_goal_id": str(parent_goal_id or ""),
        "current_parent_goal_status": str(current_parent_goal_status or ""),
        "aggregate_status": str(aggregate_status or ""),
        "proposed_parent_goal_status": proposed_status,
        "approval_gate": "parent_goal_update_review",
        "execution_mode": "preview_only",
        "requires_human_approval": True,
        "blocked_reasons": proposal_blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_parent_goal": False,
        "would_grant_permission": False,
        "valid": bool(parent_goal_id and all_children_complete),
    }


def build_orchestrator_parent_child_aggregation_preview(
    *,
    parent_goal_id: str,
    child_agents: list[dict] | None = None,
    child_glyphs: list[dict] | None = None,
    parent_goal_status: str = "derived_preview",
) -> dict:
    child_agents = list(child_agents or [])
    child_glyphs = list(child_glyphs or [])

    children = child_agents + child_glyphs
    status_counts: dict[str, int] = {}

    for child in children:
        status = str(child.get("status") or child.get("run_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    waiting_approval_count = (
        status_counts.get("waiting_approval", 0)
        + status_counts.get("pending_approval", 0)
        + status_counts.get("approval_required", 0)
    )
    completed_child_count = status_counts.get("completed", 0)
    failed_child_count = status_counts.get("failed", 0)
    blocked_child_count = (
        status_counts.get("blocked", 0)
        + status_counts.get("cancelled", 0)
        + failed_child_count
    )

    blocked_reasons: list[str] = []
    if not str(parent_goal_id or "").strip():
        blocked_reasons.append("parent_goal_id_required")

    if not children:
        blocked_reasons.append("child_agents_or_glyphs_required")

    if waiting_approval_count:
        blocked_reasons.append("child_approval_required")

    if blocked_child_count:
        blocked_reasons.append("child_blocked_or_failed")

    child_agent_conflict_preview = build_child_agent_conflict_preview(
        parent_goal_id=parent_goal_id,
        child_agents=child_agents,
        child_glyphs=child_glyphs,
    )
    if child_agent_conflict_preview.get("conflict_detected") is True:
        blocked_reasons.append("child_agent_conflict_requires_review")

    if failed_child_count:
        aggregate_status = "failed_child_requires_review"
    elif blocked_child_count:
        aggregate_status = "blocked_child_requires_review"
    elif waiting_approval_count:
        aggregate_status = "waiting_child_approval"
    elif children and completed_child_count == len(children):
        aggregate_status = "all_children_completed_review_required"
        blocked_reasons.append("parent_completion_requires_manual_review")
    else:
        aggregate_status = "in_progress_review_required"

    parent_goal_update_proposal = build_parent_goal_update_proposal_preview(
        parent_goal_id=str(parent_goal_id or ""),
        current_parent_goal_status=str(parent_goal_status or ""),
        aggregate_status=aggregate_status,
        completed_child_count=completed_child_count,
        child_count=len(children),
        blocked_reasons=blocked_reasons,
    )

    return {
        "schema_version": ORCHESTRATOR_PARENT_CHILD_AGGREGATION_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "orchestrator_parent_child_aggregation_preview",
        "parent_goal_id": str(parent_goal_id or ""),
        "parent_goal_status": parent_goal_status,
        "child_count": len(children),
        "child_status_counts": status_counts,
        "child_agents": child_agents,
        "child_glyphs": child_glyphs,
        "blocked_child_count": blocked_child_count,
        "waiting_approval_count": waiting_approval_count,
        "completed_child_count": completed_child_count,
        "failed_child_count": failed_child_count,
        "aggregate_status": aggregate_status,
        "aggregate_blocked_reasons": list(dict.fromkeys(blocked_reasons)),
        "child_agent_conflict_preview": child_agent_conflict_preview,
        "conflict_detected": bool(child_agent_conflict_preview.get("conflict_detected")),

        "parent_goal_update_proposal": parent_goal_update_proposal,
        "proposed_parent_goal_status": parent_goal_update_proposal.get("proposed_parent_goal_status"),
        "approval_gate": "parent_goal_update_review",
        "execution_mode": "preview_only",
        "requires_human_approval": True,
        "manual_review_required": True,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_mutate_parent_goal": False,
        "would_grant_permission": False,
        "valid": bool(parent_goal_id and children),
    }

GUARDED_CHILD_AGENT_EXECUTION_HANDOFF_SCHEMA_VERSION = (
    "aion.goal_engine.guarded_child_agent_execution_handoff.v1"
)


def build_guarded_child_agent_execution_handoff_preview(
    *,
    parent_goal_id: str,
    child_agent: dict | None = None,
    child_goal: dict | None = None,
    requested_action: dict | None = None,
) -> dict:
    """
    Build a guarded child-agent execution handoff preview.

    This is a review packet only. It MUST NOT execute child agents, mutate parent
    goals, grant permissions, or write to external systems.
    """
    child_agent = dict(child_agent or {})
    child_goal = dict(child_goal or {})
    requested_action = dict(requested_action or {})

    parent_goal_id_value = str(parent_goal_id or "").strip()
    child_agent_id = str(
        child_agent.get("agent_id")
        or child_agent.get("id")
        or child_agent.get("child_agent_id")
        or ""
    ).strip()
    child_goal_id = str(
        child_goal.get("goal_id")
        or child_goal.get("id")
        or child_goal.get("child_goal_id")
        or ""
    ).strip()

    requested_execution_mode = str(
        requested_action.get("execution_mode")
        or requested_action.get("mode")
        or "guarded"
    ).strip()

    blocked_reasons: list[str] = []

    if not parent_goal_id_value:
        blocked_reasons.append("parent_goal_id_required")

    if not child_agent_id:
        blocked_reasons.append("child_agent_id_required")

    if not child_goal_id:
        blocked_reasons.append("child_goal_id_required")

    if requested_execution_mode == "autonomous":
        blocked_reasons.append("autonomous_execution_not_allowed")

    valid = not blocked_reasons

    return {
        "schema_version": GUARDED_CHILD_AGENT_EXECUTION_HANDOFF_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "guarded_child_agent_execution_handoff_preview",
        "parent_goal_id": parent_goal_id_value,
        "child_agent_id": child_agent_id,
        "child_goal_id": child_goal_id,
        "child_agent": child_agent,
        "child_goal": child_goal,
        "requested_action": requested_action,
        "requested_execution_mode": requested_execution_mode,
        "execution_mode": "guarded_preview_only",
        "approval_gate": "child_agent_execution_review",
        "handoff_status": "awaiting_human_approval",
        "valid": valid,
        "blocked_reasons": list(dict.fromkeys(blocked_reasons)),
        "manual_review_required": True,
        "requires_human_approval": True,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "would_mutate_parent_goal": False,
        "would_mutate_child_goal": False,
    }

HUMAN_APPROVED_CONFLICT_RESOLUTION_SCHEMA_VERSION = (
    "aion.goal_engine.human_approved_conflict_resolution.v1"
)


def build_human_approved_conflict_resolution_preview(
    *,
    parent_goal_id: str,
    conflict_preview: dict | None = None,
    human_decision: dict | None = None,
) -> dict:
    """
    Build a human-approved conflict resolution preview.

    This records the intended human decision path only. It MUST NOT auto-resolve,
    execute, mutate parent goals, grant permissions, or write externally.
    """
    conflict_preview = dict(conflict_preview or {})
    human_decision = dict(human_decision or {})

    parent_goal_id_value = str(parent_goal_id or "").strip()
    decision = str(human_decision.get("decision") or "").strip()
    reviewer_id = str(
        human_decision.get("reviewer_id")
        or human_decision.get("human_reviewer_id")
        or human_decision.get("operator_id")
        or ""
    ).strip()

    blocked_reasons: list[str] = []

    if not parent_goal_id_value:
        blocked_reasons.append("parent_goal_id_required")

    if not conflict_preview:
        blocked_reasons.append("conflict_preview_required")

    if conflict_preview and conflict_preview.get("conflict_detected") is not True:
        blocked_reasons.append("conflict_detected_required")

    if not decision:
        blocked_reasons.append("human_decision_required")

    if not reviewer_id:
        blocked_reasons.append("reviewer_id_required")

    valid = not blocked_reasons

    return {
        "schema_version": HUMAN_APPROVED_CONFLICT_RESOLUTION_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "human_approved_conflict_resolution_preview",
        "parent_goal_id": parent_goal_id_value,
        "approval_gate": "conflict_resolution_human_review",
        "resolution_status": "approved_for_guarded_application" if valid else "blocked",
        "conflict_preview": conflict_preview,
        "human_decision": decision,
        "reviewer_id": reviewer_id,
        "human_review_record": human_decision,
        "valid": valid,
        "blocked_reasons": list(dict.fromkeys(blocked_reasons)),
        "manual_review_required": not valid,
        "requires_human_approval": not valid,
        "dry_run_only": True,
        "would_auto_resolve": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "would_mutate_parent_goal": False,
        "would_mutate_child_goal": False,
    }

MULTI_AGENT_EXECUTION_REPLAY_HISTORY_SCHEMA_VERSION = (
    "aion.goal_engine.multi_agent_execution_replay_history.v1"
)


def build_multi_agent_execution_replay_history_record(
    source: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a visibility-only replay history record for parent/child orchestration.

    This is a persistence-safe snapshot contract. It records what the Boardroom
    displayed, but it MUST NOT execute child agents, mutate parent goals, resolve
    conflicts, write externally, or grant permissions.
    """

    payload = dict(source or {})

    canonical_payload_keys = [
        "orchestrator_parent_child_aggregation_runtime_summary",
        "parent_child_aggregation_runtime_summary",
        "parent_child_aggregation_previews",
        "orchestrator_parent_child_aggregation_previews",
        "child_agents",
        "child_glyphs",
        "parent_goal_update_proposal",
        "child_agent_conflict_preview",
        "guarded_child_agent_execution_handoff_preview",
        "human_approved_conflict_resolution_preview",
    ]

    canonical_payload = {
        key: payload[key]
        for key in canonical_payload_keys
        if key in payload
    }

    return {
        "schema_version": MULTI_AGENT_EXECUTION_REPLAY_HISTORY_SCHEMA_VERSION,
        "trace_type": "multi_agent_execution_replay_history_record",
        "run_id": str(payload.get("run_id") or ""),
        "workflow_id": str(payload.get("workflow_id") or ""),
        "parent_goal_id": str(payload.get("parent_goal_id") or payload.get("goal_id") or ""),
        "dry_run": True,
        "visibility_only": True,
        "payload": canonical_payload,
        "execution_allowed": False,
        "writes_allowed": False,
        "parent_mutation_allowed": False,
        "child_execution_allowed": False,
        "blocked_reasons": [
            "visibility_only",
            "human_review_required",
            "backend_replay_history_does_not_execute",
        ],
    }


def append_multi_agent_execution_replay_history_record(
    existing_records: list[object] | None,
    record: dict[str, object],
    *,
    limit: int = 25,
) -> list[dict[str, object]]:
    """Prepend a replay record and keep the persisted history bounded."""

    safe_existing = [
        dict(item)
        for item in list(existing_records or [])
        if isinstance(item, dict)
    ]

    return [dict(record), *safe_existing][:limit]

GUARDED_CHILD_RUN_CREATION_REQUEST_SCHEMA_VERSION = (
    "aion.goal_engine.guarded_child_run_creation_request.v1"
)


def build_guarded_child_run_creation_request(
    *,
    handoff_preview: dict[str, Any] | None,
    workflow_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Build a guarded child-run creation request.

    This does not create or start a Workflow Capsule run. It only produces the
    review packet needed to connect a valid guarded child-agent handoff to a
    future executable child-run creation path.
    """

    handoff = dict(handoff_preview or {})
    blocked_reasons: list[str] = []

    workflow_id = str(workflow_id or "").strip()
    run_id = str(run_id or "").strip()

    if not workflow_id:
        blocked_reasons.append("missing_workflow_id")

    if not run_id:
        blocked_reasons.append("missing_run_id")

    if not handoff:
        blocked_reasons.append("missing_guarded_handoff")
    elif not bool(handoff.get("ready_for_execution_handoff")):
        blocked_reasons.append("invalid_guarded_handoff")

    parent_goal_id = str(handoff.get("parent_goal_id") or "").strip()
    child_goal_id = str(handoff.get("child_goal_id") or "").strip()
    child_agent_id = str(handoff.get("child_agent_id") or "").strip()
    child_glyph_id = str(handoff.get("child_glyph_id") or "").strip()

    if not parent_goal_id:
        blocked_reasons.append("missing_parent_goal_id")

    if not child_goal_id:
        blocked_reasons.append("missing_child_goal_id")

    if not child_agent_id:
        blocked_reasons.append("missing_child_agent_id")

    status = "blocked" if blocked_reasons else "waiting_approval"

    return {
        "schema_version": GUARDED_CHILD_RUN_CREATION_REQUEST_SCHEMA_VERSION,
        "trace_type": "guarded_child_run_creation_request",
        "approval_gate": "child_run_creation_review",
        "status": status,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "parent_goal_id": parent_goal_id,
        "child_goal_id": child_goal_id,
        "child_agent_id": child_agent_id,
        "child_glyph_id": child_glyph_id,
        "handoff_trace_type": handoff.get("trace_type"),
        "handoff_schema_version": handoff.get("schema_version"),
        "requested_action": handoff.get("requested_action"),
        "reviewer_id": handoff.get("reviewer_id"),
        "blocked_reasons": blocked_reasons,
        "dry_run": True,
        "visibility_only": True,
        "execution_allowed": False,
        "writes_allowed": False,
        "child_run_created": False,
        "requires_human_approval": True,
    }

HUMAN_APPROVED_CHILD_RUN_CREATION_ACTION_SCHEMA_VERSION = (
    "aion.goal_engine.human_approved_child_run_creation_action.v1"
)


def build_human_approved_child_run_creation_action(
    *,
    child_run_request: dict | None,
    approval_decision: str | None,
    reviewer_id: str | None,
) -> dict:
    """Build a human-approved child-run creation action seed.

    This helper authorizes a downstream runtime executor to create a child run.
    It does not create the run directly, execute child agents, write externally,
    mutate business state, or bypass approval gates.
    """

    request = dict(child_run_request or {})
    blocked_reasons: list[str] = []

    if request.get("schema_version") != GUARDED_CHILD_RUN_CREATION_REQUEST_SCHEMA_VERSION:
        blocked_reasons.append("invalid_child_run_creation_request_schema")

    if not bool(request.get("child_run_creation_request_valid")):
        blocked_reasons.append("invalid_child_run_creation_request")

    for reason in list(request.get("blocked_reasons") or []):
        if reason and reason not in blocked_reasons:
            blocked_reasons.append(str(reason))

    if str(approval_decision or "").strip().lower() != "approved":
        blocked_reasons.append("approval_decision_not_approved")

    reviewer = str(reviewer_id or "").strip()
    if not reviewer:
        blocked_reasons.append("missing_reviewer_id")

    parent_goal_id = str(request.get("parent_goal_id") or "").strip()
    child_goal_id = str(request.get("child_goal_id") or "").strip()
    child_agent_id = str(request.get("child_agent_id") or "").strip()
    child_glyph_id = str(request.get("child_glyph_id") or "").strip()
    workflow_id = str(request.get("target_workflow_id") or "").strip()
    run_id = str(request.get("target_child_run_id") or "").strip()

    if not workflow_id:
        blocked_reasons.append("missing_target_workflow_id")
    if not run_id:
        blocked_reasons.append("missing_target_child_run_id")

    allowed = not blocked_reasons

    return {
        "schema_version": HUMAN_APPROVED_CHILD_RUN_CREATION_ACTION_SCHEMA_VERSION,
        "trace_type": "human_approved_child_run_creation_action",
        "status": "approved_for_child_run_creation" if allowed else "blocked",
        "approval_decision": str(approval_decision or "").strip().lower(),
        "reviewer_id": reviewer,
        "human_approved": allowed,
        "child_run_creation_allowed": allowed,
        "requires_runtime_executor": True,
        "child_run_created": False,
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
        "blocked_reasons": blocked_reasons,
        "parent_goal_id": parent_goal_id,
        "child_goal_id": child_goal_id,
        "child_agent_id": child_agent_id,
        "child_glyph_id": child_glyph_id,
        "target_workflow_id": workflow_id,
        "target_child_run_id": run_id,
        "runtime_seed": {
            "parent_goal_id": parent_goal_id,
            "child_goal_id": child_goal_id,
            "child_agent_id": child_agent_id,
            "child_glyph_id": child_glyph_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "source_request_schema_version": request.get("schema_version"),
            "source_request_trace_type": request.get("trace_type"),
            "created_by": reviewer,
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
        "runtime_seed": {
            "parent_goal_id": parent_goal_id,
            "child_goal_id": child_goal_id,
            "child_agent_id": child_agent_id,
            "child_glyph_id": child_glyph_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "source_request_schema_version": request.get("schema_version"),
            "source_request_trace_type": request.get("trace_type"),
            "created_by": reviewer,
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
        "runtime_seed": {
            "parent_goal_id": parent_goal_id,
            "child_goal_id": child_goal_id,
            "child_agent_id": child_agent_id,
            "child_glyph_id": child_glyph_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "source_request_schema_version": request.get("schema_version"),
            "source_request_trace_type": request.get("trace_type"),
            "created_by": reviewer,
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
        "child_run_seed": {
            "parent_goal_id": parent_goal_id,
            "child_goal_id": child_goal_id,
            "child_agent_id": child_agent_id,
            "child_glyph_id": child_glyph_id,
            "workflow_id": workflow_id,
            "run_id": run_id,
            "source_request_schema_version": request.get("schema_version"),
            "source_request_trace_type": request.get("trace_type"),
            "created_by": reviewer,
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
    }

CHILD_RUN_EXECUTOR_BRIDGE_SCHEMA_VERSION = (
    "aion.goal_engine.child_run_executor_bridge.v1"
)


def build_child_run_executor_bridge_packet(
    action: dict | None,
) -> dict:
    action = dict(action or {})
    seed = action.get("runtime_seed") if isinstance(action.get("runtime_seed"), dict) else {}

    # The executor bridge is the final boundary before a workflow runtime may
    # create a child run. It MUST only trust canonical IDs inside the reviewed
    # runtime_seed. Alias fields and outer action fields are provenance only.
    target_workflow_id = str(seed.get("workflow_id") or "").strip()
    target_child_run_id = str(seed.get("run_id") or "").strip()

    blocked_reasons: list[str] = []

    if action.get("trace_type") != "human_approved_child_run_creation_action":
        blocked_reasons.append("invalid_child_run_creation_action")

    if not bool(action.get("child_run_creation_allowed")):
        blocked_reasons.append("child_run_creation_not_allowed")

    if action.get("approval_decision") != "approved":
        blocked_reasons.append("approval_not_approved")

    if not bool(action.get("requires_runtime_executor")):
        blocked_reasons.append("runtime_executor_not_required")

    if not seed:
        blocked_reasons.append("missing_runtime_seed")

    if not target_workflow_id:
        blocked_reasons.append("missing_workflow_id")

    if not target_child_run_id:
        blocked_reasons.append("missing_child_run_id")

    allowed = not blocked_reasons

    return {
        "schema_version": CHILD_RUN_EXECUTOR_BRIDGE_SCHEMA_VERSION,
        "trace_type": "child_run_executor_bridge_packet",
        "status": "ready_for_workflow_runtime" if allowed else "blocked",
        "workflow_run_creation_allowed": allowed,
        "blocked_reasons": blocked_reasons,
        "workflow_id": target_workflow_id,
        "run_id": target_child_run_id,
        "target_workflow_id": target_workflow_id,
        "target_child_run_id": target_child_run_id,
        "parent_goal_id": action.get("parent_goal_id"),
        "child_goal_id": action.get("child_goal_id"),
        "child_agent_id": action.get("child_agent_id"),
        "child_glyph_id": action.get("child_glyph_id"),
        "reviewer_id": action.get("reviewer_id"),
        "runtime_seed": dict(seed),
        "requires_existing_workflow_runtime": True,
        "creates_external_side_effects": False,
        "autonomous_execution": False,
        "external_writes_allowed": False,
        "business_mutation_allowed": False,
    }

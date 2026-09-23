import pytest

from backend.services.aion_mission_mode.multi_agent_mission_orchestration import (
    MissionOrchestrationViolation,
    aggregate_final_receipt,
    canonical_hash,
    compile_agent_hierarchy,
    create_handoff_record,
    create_mission_coordinator,
    create_sub_agent_assignment,
    resolve_agent_conflict,
    validate_parent_scope,
)


def meta():
    return {
        "mission_id": "mission_homefixed_demo",
        "mission_run_id": "run_001",
        "business_id": "business_homefixed",
        "mission_coordinator_agent": "agent:coordinator:001",
    }


def parent_scope():
    return {
        "mission_id": "mission_homefixed_demo",
        "mission_run_id": "run_001",
        "business_id": "business_homefixed",
        "allowed_lanes": ["creation", "research", "staged_external"],
        "allowed_capabilities": ["draft_copy", "seo_research", "prepare_vercel_deploy"],
        "max_sub_agents": 8,
        "max_handoff_depth": 3,
        "default_control_decision": "human_approval_required",
    }


def test_phase20m_create_mission_coordinator():
    c = create_mission_coordinator(meta())
    assert c["agent_role"] == "mission_coordinator"
    assert c["can_execute_live_tools"] is False
    assert c["coordinator_hash"].startswith("sha256:")


def test_phase20m_parent_scope_hash_is_deterministic():
    a = validate_parent_scope(parent_scope())
    b = validate_parent_scope(parent_scope())
    assert a["parent_scope_hash"] == b["parent_scope_hash"]


def test_phase20m_rejects_missing_parent_scope_fields():
    bad = parent_scope()
    del bad["allowed_capabilities"]
    with pytest.raises(MissionOrchestrationViolation):
        validate_parent_scope(bad)


def test_phase20m_creates_allowed_sub_agent_assignment():
    assignment = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:content:001",
            "agent_role": "content_agent",
            "assigned_goal": "Draft website copy",
            "requested_lanes": ["creation"],
            "requested_capabilities": ["draft_copy"],
            "requested_control_decision": "autonomous",
        },
    )
    assert assignment["assignment_allowed"] is True
    assert assignment["effective_control_decision"] == "human_approval_required"
    assert assignment["may_exceed_parent_permissions"] is False


def test_phase20m_blocks_sub_agent_lane_scope_violation():
    assignment = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:bad:001",
            "agent_role": "browser_worker_agent",
            "assigned_goal": "Buy domain directly",
            "requested_lanes": ["payment"],
            "requested_capabilities": ["buy_domain"],
        },
    )
    assert assignment["assignment_allowed"] is False
    assert "payment" in assignment["lane_violations"]
    assert "buy_domain" in assignment["capability_violations"]


def test_phase20m_rejects_unknown_agent_role():
    with pytest.raises(MissionOrchestrationViolation):
        create_sub_agent_assignment(
            parent_scope(),
            {
                "agent_id": "agent:unknown",
                "agent_role": "superuser_agent",
                "assigned_goal": "Do anything",
                "requested_lanes": ["creation"],
                "requested_capabilities": ["draft_copy"],
            },
        )


def test_phase20m_handoff_record_requires_scope_validation():
    h = create_handoff_record(
        meta(),
        "agent:planner:001",
        "agent:content:001",
        "sha256:payload",
    )
    assert h["handoff_state"] == "pending_coordinator_review"
    assert h["requires_parent_scope_validation"] is True
    assert h["handoff_hash"].startswith("sha256:")


def test_phase20m_rejects_unknown_handoff_policy():
    with pytest.raises(MissionOrchestrationViolation):
        create_handoff_record(
            meta(),
            "a",
            "b",
            "sha256:payload",
            handoff_policy="free_for_all",
        )


def test_phase20m_conflict_fail_closed():
    result = resolve_agent_conflict(
        meta(),
        {
            "conflict_type": "different_payload_for_same_step",
            "agent_ids": ["agent:b", "agent:a"],
            "conflicting_hashes": ["sha256:2", "sha256:1"],
        },
    )
    assert result["execution_blocked"] is True
    assert result["resolution_state"] == "blocked_for_safety"


def test_phase20m_conflict_human_review():
    result = resolve_agent_conflict(
        meta(),
        {
            "conflict_type": "provider_choice_conflict",
            "agent_ids": ["agent:a", "agent:b"],
            "conflicting_hashes": ["sha256:1", "sha256:2"],
        },
        conflict_resolution_policy="human_review_required",
    )
    assert result["requires_human_review"] is True
    assert result["execution_blocked"] is False


def test_phase20m_compile_agent_hierarchy_for_boardroom():
    c = create_mission_coordinator(meta())
    a1 = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:content:001",
            "agent_role": "content_agent",
            "assigned_goal": "Draft copy",
            "requested_lanes": ["creation"],
            "requested_capabilities": ["draft_copy"],
        },
    )
    a2 = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:research:001",
            "agent_role": "research_agent",
            "assigned_goal": "SEO research",
            "requested_lanes": ["research"],
            "requested_capabilities": ["seo_research"],
        },
    )
    h = create_handoff_record(meta(), a1["agent_id"], a2["agent_id"], "sha256:payload")
    hierarchy = compile_agent_hierarchy(meta(), c, [a1, a2], [h])
    assert hierarchy["agent_count"] == 2
    assert hierarchy["blocked_agent_count"] == 0
    assert hierarchy["boardroom_must_show_agent_hierarchy"] is True


def test_phase20m_compile_hierarchy_shows_scope_blocks():
    c = create_mission_coordinator(meta())
    blocked = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:bad:001",
            "agent_role": "build_agent",
            "assigned_goal": "Deploy directly",
            "requested_lanes": ["deployment"],
            "requested_capabilities": ["deploy_to_production"],
        },
    )
    hierarchy = compile_agent_hierarchy(meta(), c, [blocked], [])
    assert hierarchy["blocked_agent_count"] == 1
    assert hierarchy["hierarchy_state"] == "scope_blocks_visible"


def test_phase20m_aggregate_final_receipt():
    receipt = aggregate_final_receipt(
        meta(),
        ["sha256:r2", "sha256:r1"],
        ["sha256:a1"],
        ["sha256:h1"],
    )
    assert receipt["receipt_hashes"] == ["sha256:r1", "sha256:r2"]
    assert receipt["aggregated_by"] == "mission_coordinator"
    assert receipt["coordinator_final_receipt_hash"].startswith("sha256:")


def test_phase20m_hash_changes_when_assignment_changes():
    base = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:content:001",
            "agent_role": "content_agent",
            "assigned_goal": "Draft copy",
            "requested_lanes": ["creation"],
            "requested_capabilities": ["draft_copy"],
        },
    )
    changed = create_sub_agent_assignment(
        parent_scope(),
        {
            "agent_id": "agent:content:001",
            "agent_role": "content_agent",
            "assigned_goal": "Draft different copy",
            "requested_lanes": ["creation"],
            "requested_capabilities": ["draft_copy"],
        },
    )
    assert base["assignment_hash"] != changed["assignment_hash"]

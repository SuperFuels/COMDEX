from backend.modules.aion.goal_engine.orchestrator import (
    build_orchestrator_parent_child_aggregation_preview,
)


def test_parent_goal_update_proposal_is_created_when_all_children_complete():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent_001",
        parent_goal_status="in_progress",
        child_agents=[
            {"agent_id": "agent_sales", "status": "completed"},
        ],
        child_glyphs=[
            {"glyph_code": "MK-001", "status": "completed"},
        ],
    )

    proposal = preview["parent_goal_update_proposal"]

    assert proposal["trace_type"] == "parent_goal_update_proposal"
    assert proposal["parent_goal_id"] == "goal_parent_001"
    assert proposal["current_parent_goal_status"] == "in_progress"
    assert proposal["proposed_parent_goal_status"] == "ready_for_completion_review"
    assert proposal["approval_gate"] == "parent_goal_update_review"
    assert proposal["execution_mode"] == "preview_only"
    assert proposal["requires_human_approval"] is True
    assert proposal["would_mutate_parent_goal"] is False
    assert proposal["would_write_external"] is False
    assert proposal["would_execute"] is False


def test_parent_goal_update_proposal_does_not_exist_for_incomplete_children():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent_002",
        parent_goal_status="in_progress",
        child_agents=[
            {"agent_id": "agent_sales", "status": "running"},
        ],
        child_glyphs=[],
    )

    proposal = preview["parent_goal_update_proposal"]

    assert proposal["proposed_parent_goal_status"] == "keep_current_status"
    assert proposal["approval_gate"] == "parent_goal_update_review"
    assert proposal["requires_human_approval"] is True
    assert proposal["would_mutate_parent_goal"] is False
    assert "all_children_completed_required" in proposal["blocked_reasons"]


def test_parent_goal_update_proposal_blocks_missing_parent_goal():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="",
        child_agents=[
            {"agent_id": "agent_sales", "status": "completed"},
        ],
    )

    proposal = preview["parent_goal_update_proposal"]

    assert proposal["parent_goal_id"] == ""
    assert proposal["proposed_parent_goal_status"] == "blocked"
    assert "parent_goal_id_required" in proposal["blocked_reasons"]
    assert proposal["requires_human_approval"] is True
    assert proposal["would_mutate_parent_goal"] is False


def test_parent_goal_update_proposal_is_mirrored_at_preview_top_level():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent_003",
        child_agents=[
            {"agent_id": "agent_sales", "status": "completed"},
        ],
    )

    assert preview["requires_human_approval"] is True
    assert preview["approval_gate"] == "parent_goal_update_review"
    assert preview["execution_mode"] == "preview_only"
    assert preview["would_mutate_parent_goal"] is False

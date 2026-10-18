from backend.modules.aion.goal_engine.orchestrator import (
    ORCHESTRATOR_PARENT_CHILD_AGGREGATION_SCHEMA_VERSION,
    build_orchestrator_parent_child_aggregation_preview,
)


def test_parent_child_aggregation_counts_child_statuses():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent",
        child_agents=[
            {"agent_id": "agent_marketing", "role": "marketing", "glyph_code": "MK-001", "status": "completed"},
            {"agent_id": "agent_reviewer", "role": "reviewer", "glyph_code": "RV-001", "status": "waiting_approval"},
        ],
        child_glyphs=[
            {"glyph_code": "WD-101", "status": "blocked"},
        ],
    )

    assert preview["schema_version"] == ORCHESTRATOR_PARENT_CHILD_AGGREGATION_SCHEMA_VERSION
    assert preview["trace_type"] == "orchestrator_parent_child_aggregation_preview"
    assert preview["parent_goal_id"] == "goal_parent"
    assert preview["child_count"] == 3
    assert preview["completed_child_count"] == 1
    assert preview["waiting_approval_count"] == 1
    assert preview["blocked_child_count"] == 1
    assert preview["aggregate_status"] == "blocked_child_requires_review"


def test_parent_child_aggregation_never_mutates_or_executes():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent",
        child_agents=[{"agent_id": "agent_1", "status": "completed"}],
    )

    assert preview["manual_review_required"] is True
    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_mutate_parent_goal"] is False
    assert preview["would_grant_permission"] is False


def test_all_children_completed_still_requires_manual_review():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent",
        child_agents=[
            {"agent_id": "agent_1", "status": "completed"},
            {"agent_id": "agent_2", "status": "completed"},
        ],
    )

    assert preview["aggregate_status"] == "all_children_completed_review_required"
    assert "parent_completion_requires_manual_review" in preview["aggregate_blocked_reasons"]


def test_parent_child_aggregation_requires_parent_and_children():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="",
        child_agents=[],
        child_glyphs=[],
    )

    assert preview["valid"] is False
    assert "parent_goal_id_required" in preview["aggregate_blocked_reasons"]
    assert "child_agents_or_glyphs_required" in preview["aggregate_blocked_reasons"]

from backend.modules.aion.goal_engine.orchestrator import (
    build_child_agent_conflict_preview,
    build_orchestrator_parent_child_aggregation_preview,
)


def test_child_agent_conflict_preview_detects_disagreement():
    preview = build_child_agent_conflict_preview(
        parent_goal_id="goal_parent",
        child_agents=[
            {"agent_id": "agent_sales", "recommendation": "approve", "confidence": 0.82},
            {"agent_id": "agent_critic", "recommendation": "reject", "confidence": 0.76},
        ],
        child_glyphs=[
            {"glyph_code": "MK-101", "recommendation": "revise", "confidence": 0.64},
        ],
    )

    assert preview["trace_type"] == "child_agent_conflict_preview"
    assert preview["parent_goal_id"] == "goal_parent"
    assert preview["conflict_detected"] is True
    assert preview["conflict_policy"] == "human_review"
    assert preview["recommended_resolution"] == "human_review_required"
    assert preview["manual_review_required"] is True
    assert preview["would_auto_resolve"] is False
    assert preview["would_execute"] is False
    assert preview["would_mutate_parent_goal"] is False


def test_child_agent_conflict_preview_no_conflict_when_recommendations_match():
    preview = build_child_agent_conflict_preview(
        parent_goal_id="goal_parent",
        child_agents=[
            {"agent_id": "agent_sales", "recommendation": "approve", "confidence": 0.82},
            {"agent_id": "agent_marketing", "recommendation": "approve", "confidence": 0.79},
        ],
        child_glyphs=[],
    )

    assert preview["conflict_detected"] is False
    assert preview["recommended_resolution"] == "no_conflict_detected"
    assert preview["manual_review_required"] is False
    assert preview["would_auto_resolve"] is False
    assert preview["would_mutate_parent_goal"] is False


def test_child_agent_conflict_preview_blocks_missing_parent_and_children():
    preview = build_child_agent_conflict_preview(
        parent_goal_id="",
        child_agents=[],
        child_glyphs=[],
    )

    assert preview["conflict_detected"] is False
    assert "parent_goal_id_required" in preview["blocked_reasons"]
    assert "child_agents_or_glyphs_required" in preview["blocked_reasons"]
    assert preview["valid"] is False
    assert preview["manual_review_required"] is True


def test_parent_child_aggregation_includes_child_conflict_preview():
    preview = build_orchestrator_parent_child_aggregation_preview(
        parent_goal_id="goal_parent",
        child_agents=[
            {"agent_id": "agent_sales", "recommendation": "approve", "confidence": 0.82, "status": "completed"},
            {"agent_id": "agent_critic", "recommendation": "reject", "confidence": 0.76, "status": "completed"},
        ],
        child_glyphs=[],
    )

    conflict = preview["child_agent_conflict_preview"]

    assert conflict["trace_type"] == "child_agent_conflict_preview"
    assert conflict["conflict_detected"] is True
    assert conflict["recommended_resolution"] == "human_review_required"
    assert preview["conflict_detected"] is True
    assert "child_agent_conflict_requires_review" in preview["aggregate_blocked_reasons"]

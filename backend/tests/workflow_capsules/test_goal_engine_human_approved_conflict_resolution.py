from backend.modules.aion.goal_engine.orchestrator import (
    build_human_approved_conflict_resolution_preview,
)


def test_human_approved_conflict_resolution_builds_review_action():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent",
        conflict_preview={
            "trace_type": "child_agent_conflict_preview",
            "conflict_detected": True,
            "recommended_resolution": "human_review_required",
            "child_recommendations": [
                {"source_id": "agent_sales", "recommendation": "approve", "confidence": 0.82},
                {"source_id": "agent_critic", "recommendation": "reject", "confidence": 0.76},
            ],
        },
        human_decision={
            "decision": "revise",
            "reviewer_id": "human_operator",
            "reason": "Needs safer launch copy.",
        },
    )

    assert preview["trace_type"] == "human_approved_conflict_resolution_preview"
    assert preview["parent_goal_id"] == "goal_parent"
    assert preview["approval_gate"] == "conflict_resolution_human_review"
    assert preview["resolution_status"] == "approved_for_guarded_application"
    assert preview["human_decision"] == "revise"
    assert preview["reviewer_id"] == "human_operator"
    assert preview["valid"] is True
    assert preview["manual_review_required"] is False
    assert preview["requires_human_approval"] is False

    assert preview["would_auto_resolve"] is False
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert preview["would_mutate_parent_goal"] is False


def test_human_approved_conflict_resolution_blocks_missing_parent():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="",
        conflict_preview={"conflict_detected": True},
        human_decision={"decision": "approve", "reviewer_id": "human_operator"},
    )

    assert preview["valid"] is False
    assert "parent_goal_id_required" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True
    assert preview["would_mutate_parent_goal"] is False


def test_human_approved_conflict_resolution_blocks_missing_conflict():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent",
        conflict_preview={},
        human_decision={"decision": "approve", "reviewer_id": "human_operator"},
    )

    assert preview["valid"] is False
    assert "conflict_preview_required" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True


def test_human_approved_conflict_resolution_blocks_when_no_conflict_detected():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent",
        conflict_preview={"conflict_detected": False},
        human_decision={"decision": "approve", "reviewer_id": "human_operator"},
    )

    assert preview["valid"] is False
    assert "conflict_detected_required" in preview["blocked_reasons"]
    assert preview["resolution_status"] == "blocked"


def test_human_approved_conflict_resolution_blocks_missing_human_decision():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent",
        conflict_preview={"conflict_detected": True},
        human_decision={"reviewer_id": "human_operator"},
    )

    assert preview["valid"] is False
    assert "human_decision_required" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True


def test_human_approved_conflict_resolution_blocks_missing_reviewer():
    preview = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent",
        conflict_preview={"conflict_detected": True},
        human_decision={"decision": "approve"},
    )

    assert preview["valid"] is False
    assert "reviewer_id_required" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True

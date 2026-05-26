from backend.modules.aion.goal_engine.orchestrator import (
    build_guarded_child_agent_execution_handoff_preview,
)


def test_guarded_child_agent_execution_handoff_builds_review_packet():
    preview = build_guarded_child_agent_execution_handoff_preview(
        parent_goal_id="goal_parent",
        child_agent={
            "agent_id": "agent_sales",
            "role": "sales",
            "recommendation": "approve",
            "confidence": 0.82,
        },
        child_goal={
            "goal_id": "goal_child_sales",
            "title": "Validate sales outreach plan",
            "status": "ready_for_execution_review",
        },
        requested_action={
            "action_type": "execute_child_goal",
            "execution_mode": "guarded",
        },
    )

    assert preview["trace_type"] == "guarded_child_agent_execution_handoff_preview"
    assert preview["parent_goal_id"] == "goal_parent"
    assert preview["child_agent_id"] == "agent_sales"
    assert preview["child_goal_id"] == "goal_child_sales"
    assert preview["approval_gate"] == "child_agent_execution_review"
    assert preview["handoff_status"] == "awaiting_human_approval"
    assert preview["manual_review_required"] is True
    assert preview["requires_human_approval"] is True

    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert preview["would_mutate_parent_goal"] is False


def test_guarded_child_agent_execution_handoff_blocks_missing_parent_goal():
    preview = build_guarded_child_agent_execution_handoff_preview(
        parent_goal_id="",
        child_agent={"agent_id": "agent_sales"},
        child_goal={"goal_id": "goal_child_sales"},
        requested_action={"action_type": "execute_child_goal"},
    )

    assert preview["valid"] is False
    assert "parent_goal_id_required" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True
    assert preview["would_execute"] is False


def test_guarded_child_agent_execution_handoff_blocks_missing_child_agent():
    preview = build_guarded_child_agent_execution_handoff_preview(
        parent_goal_id="goal_parent",
        child_agent={},
        child_goal={"goal_id": "goal_child_sales"},
        requested_action={"action_type": "execute_child_goal"},
    )

    assert preview["valid"] is False
    assert "child_agent_id_required" in preview["blocked_reasons"]
    assert preview["would_execute"] is False


def test_guarded_child_agent_execution_handoff_blocks_missing_child_goal():
    preview = build_guarded_child_agent_execution_handoff_preview(
        parent_goal_id="goal_parent",
        child_agent={"agent_id": "agent_sales"},
        child_goal={},
        requested_action={"action_type": "execute_child_goal"},
    )

    assert preview["valid"] is False
    assert "child_goal_id_required" in preview["blocked_reasons"]
    assert preview["would_execute"] is False


def test_guarded_child_agent_execution_handoff_is_never_autonomous():
    preview = build_guarded_child_agent_execution_handoff_preview(
        parent_goal_id="goal_parent",
        child_agent={"agent_id": "agent_sales"},
        child_goal={"goal_id": "goal_child_sales"},
        requested_action={
            "action_type": "execute_child_goal",
            "execution_mode": "autonomous",
        },
    )

    assert preview["execution_mode"] == "guarded_preview_only"
    assert preview["requested_execution_mode"] == "autonomous"
    assert "autonomous_execution_not_allowed" in preview["blocked_reasons"]
    assert preview["manual_review_required"] is True
    assert preview["would_execute"] is False

from backend.modules.aion.goal_engine.orchestrator import (
    build_child_agent_conflict_preview,
    build_human_approved_conflict_resolution_preview,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def _conflict_preview():
    return build_child_agent_conflict_preview(
        parent_goal_id="goal_parent_001",
        child_agents=[
            {
                "child_agent_id": "agent_marketing",
                "recommendation": "increase_budget",
                "confidence": 0.82,
                "status": "completed",
            },
            {
                "child_agent_id": "agent_finance",
                "recommendation": "hold_budget",
                "confidence": 0.78,
                "status": "completed",
            },
        ],
        conflict_policy="human_review",
    )


def _resolution_preview(conflict_preview=None):
    return build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent_001",
        conflict_preview=conflict_preview or _conflict_preview(),
        human_decision={
            "decision": "hold_budget",
            "reviewer_id": "human_ceo",
            "reason": "finance guardrail wins until revenue evidence improves",
        },
    )


def test_conflict_resolution_end_to_end_builds_human_approved_review_chain():
    conflict = _conflict_preview()
    resolution = _resolution_preview(conflict)

    assert conflict["trace_type"] == "child_agent_conflict_preview"
    assert conflict["conflict_detected"] is True
    assert conflict["manual_review_required"] is True
    assert conflict["would_auto_resolve"] is False
    assert conflict["would_execute"] is False
    assert conflict["would_write_external"] is False
    assert conflict["would_mutate_parent_goal"] is False
    assert conflict["would_grant_permission"] is False

    assert resolution["trace_type"] == "human_approved_conflict_resolution_preview"
    assert resolution["approval_gate"] == "conflict_resolution_human_review"
    assert resolution["resolution_status"] == "approved_for_guarded_application"
    assert resolution["valid"] is True
    assert resolution["reviewer_id"] == "human_ceo"
    assert resolution["human_decision"] == "hold_budget"
    assert resolution["requires_human_approval"] is False
    assert resolution["dry_run_only"] is True

    assert resolution["would_auto_resolve"] is False
    assert resolution["would_execute"] is False
    assert resolution["would_write_external"] is False
    assert resolution["would_grant_permission"] is False
    assert resolution["would_mutate_parent_goal"] is False
    assert resolution["would_mutate_child_goal"] is False


def test_conflict_resolution_end_to_end_blocks_without_real_conflict():
    no_conflict = build_child_agent_conflict_preview(
        parent_goal_id="goal_parent_001",
        child_agents=[
            {
                "child_agent_id": "agent_marketing",
                "recommendation": "increase_budget",
                "confidence": 0.82,
                "status": "completed",
            },
            {
                "child_agent_id": "agent_sales",
                "recommendation": "increase_budget",
                "confidence": 0.76,
                "status": "completed",
            },
        ],
        conflict_policy="human_review",
    )

    resolution = _resolution_preview(no_conflict)

    assert no_conflict["conflict_detected"] is False
    assert resolution["resolution_status"] == "blocked"
    assert resolution["valid"] is False
    assert "conflict_detected_required" in resolution["blocked_reasons"]
    assert resolution["would_auto_resolve"] is False
    assert resolution["would_mutate_parent_goal"] is False


def test_conflict_resolution_end_to_end_blocks_missing_human_decision():
    conflict = _conflict_preview()

    resolution = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent_001",
        conflict_preview=conflict,
        human_decision={"reviewer_id": "human_ceo"},
    )

    assert resolution["resolution_status"] == "blocked"
    assert resolution["valid"] is False
    assert "human_decision_required" in resolution["blocked_reasons"]
    assert resolution["requires_human_approval"] is True
    assert resolution["would_execute"] is False
    assert resolution["would_mutate_parent_goal"] is False


def test_conflict_resolution_end_to_end_blocks_missing_reviewer():
    conflict = _conflict_preview()

    resolution = build_human_approved_conflict_resolution_preview(
        parent_goal_id="goal_parent_001",
        conflict_preview=conflict,
        human_decision={"decision": "hold_budget"},
    )

    assert resolution["resolution_status"] == "blocked"
    assert resolution["valid"] is False
    assert "reviewer_id_required" in resolution["blocked_reasons"]
    assert resolution["requires_human_approval"] is True
    assert resolution["would_grant_permission"] is False


def test_conflict_resolution_end_to_end_preview_bundle_remains_visibility_only():
    conflict = _conflict_preview()
    resolution = _resolution_preview(conflict)

    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_001",
        workflow_id="workflow_parent_001",
        goal_engine_manifest={
            "workflow_id": "workflow_parent_001",
            "runtime": "aion_goal_engine",
            "steps": [],
            "contracts": [conflict, resolution],
            "previews": [conflict, resolution],
        },
    ).to_dict()

    assert bundle["dry_run_only"] is True
    assert bundle["would_execute"] is False
    assert bundle["would_write_external"] is False
    assert bundle["would_grant_permission"] is False
    assert bundle["safety_contract"]["external_writes_require_approval"] is True

    text = str(bundle)
    assert "child_agent_conflict_preview" in text
    assert "human_approved_conflict_resolution_preview" in text
    assert "conflict_resolution_human_review" in text

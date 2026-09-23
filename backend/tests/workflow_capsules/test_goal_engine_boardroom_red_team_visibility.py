from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


def red_team_capsule():
    return {
        "canonical_key": "test.goal_engine.boardroom_red_team_visibility",
        "steps": [
            {
                "id": "goal_unsafe",
                "title": "Unsafe expansion goal",
                "action_id": "goal_engine.goal",
                "config": {
                    "unsafe_goal": True,
                    "safety_classification": "unsafe",
                    "risk_score": 0.92,
                    "blocked_reasons": ["unsafe_goal", "external_write_risk"],
                },
            },
            {
                "id": "loop_safe",
                "title": "Safe bounded loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "risk_score": 0.25,
                },
            },
        ],
    }


def manifest_with_red_team_rows():
    manifest = build_goal_engine_manifest_for_capsule(
        red_team_capsule(),
        run_id="run_boardroom_red_team_1",
    )
    rows = build_goal_engine_step_trace_rows(
        manifest,
        run_id="run_boardroom_red_team_1",
    )
    manifest["goal_engine_step_trace"] = rows
    manifest["steps"] = rows
    return manifest


def test_boardroom_trace_exposes_red_team_summary():
    trace = build_goal_engine_boardroom_trace(manifest_with_red_team_rows())

    assert "red_team_safety_summary" in trace
    summary = trace["red_team_safety_summary"]

    assert summary["schema_version"] == "aion.goal_engine.boardroom_red_team_safety_summary.v1"
    assert summary["unsafe_goal_blocked_count"] >= 1
    assert summary["highest_risk_score"] == 0.92
    assert "unsafe_goal" in summary["blocked_reasons"]
    assert summary["recommended_action"] == "block_before_execution"


def test_boardroom_trace_exposes_red_team_rows():
    trace = build_goal_engine_boardroom_trace(manifest_with_red_team_rows())
    rows = trace["red_team_safety_summary"]["rows"]

    unsafe = next(row for row in rows if row["node_id"] == "goal_unsafe")

    assert unsafe["unsafe_goal_blocked"] is True
    assert unsafe["risk_score"] == 0.92
    assert unsafe["safety_classification"] == "unsafe"
    assert unsafe["external_write_performed"] is False
    assert unsafe["grants_permission"] is False


def test_boardroom_visibility_fields_include_red_team_summary():
    trace = build_goal_engine_boardroom_trace(manifest_with_red_team_rows())

    fields = trace.get("boardroom_visibility_fields") or []

    assert "red_team_safety_summary" in fields


def test_boardroom_events_include_red_team_visibility():
    trace = build_goal_engine_boardroom_trace(manifest_with_red_team_rows())

    event_text = str(trace.get("events", []))

    assert "goal_engine.red_team_safety_visible" in event_text
    assert "block_before_execution" in event_text

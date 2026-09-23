from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_red_team_safety_preview,
    build_goal_engine_step_trace_rows,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def red_team_capsule(unsafe=False):
    return {
        "canonical_key": "test.goal_engine.red_team_safety_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "risk_score": 0.35,
                    "unsafe_goal": unsafe,
                    "safety_classification": "unsafe" if unsafe else "safe",
                    "red_team_checks": [
                        "goal_interpretation",
                        "loop_bounds",
                        "budget_abuse",
                        "memory_policy_bypass",
                    ],
                    "blocked_reasons": ["unsafe_goal_classification"] if unsafe else [],
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "red_team_checks": ["loop_bounds", "resume_stale_state"],
                    "unbounded_execution_blocked": True,
                },
            },
        ],
    }


def test_build_red_team_safety_preview_directly():
    preview = build_goal_engine_red_team_safety_preview(
        {
            "node_id": "goal_1",
            "node_kind": "goal",
            "payload": {
                "risk_score": 0.95,
                "unsafe_goal": True,
                "safety_classification": "unsafe",
                "blocked_reasons": ["unsafe_goal_classification"],
            },
        },
        run_id="run_red_team_1",
    )

    assert preview["schema_version"] == "aion.goal_engine.red_team_safety_preview.v1"
    assert preview["node_id"] == "goal_1"
    assert preview["risk_score"] == 0.95
    assert preview["safety_classification"] == "unsafe"
    assert preview["unsafe_goal_blocked"] is True
    assert preview["recommended_action"] == "block_before_execution"
    assert preview["external_write_performed"] is False
    assert preview["grants_permission"] is False


def test_step_trace_rows_include_red_team_safety_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        red_team_capsule(unsafe=False),
        run_id="run_red_team_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_red_team_2")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    loop_row = next(row for row in rows if row["node_id"] == "loop_1")

    assert goal_row["red_team_safety_preview"]["safety_classification"] == "safe"
    assert goal_row["red_team_safety_preview"]["unsafe_goal_blocked"] is False
    assert loop_row["red_team_safety_preview"]["unbounded_execution_blocked"] is True
    assert loop_row["payload"]["red_team_safety_preview"]["external_write_performed"] is False


def test_red_team_safety_blocks_unsafe_goal():
    manifest = build_goal_engine_manifest_for_capsule(
        red_team_capsule(unsafe=True),
        run_id="run_red_team_3",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_red_team_3")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    preview = goal_row["red_team_safety_preview"]

    assert preview["unsafe_goal_blocked"] is True
    assert "unsafe_goal_classification" in preview["blocked_reasons"]
    assert preview["recommended_action"] == "block_before_execution"
    assert preview["dry_run_only"] is True
    assert preview["grants_permission"] is False


def test_manifest_attach_preserves_red_team_safety_preview_in_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        red_team_capsule(unsafe=True),
        run_id="run_red_team_4",
    )

    payload = result.to_dict()
    goal_row = next(row for row in payload["trace"] if row.get("node_id") == "goal_1")

    assert goal_row["red_team_safety_preview"]["schema_version"] == "aion.goal_engine.red_team_safety_preview.v1"
    assert goal_row["red_team_safety_preview"]["unsafe_goal_blocked"] is True
    assert goal_row["red_team_safety_preview"]["external_write_performed"] is False

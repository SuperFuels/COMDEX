from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
    build_goal_engine_simulation_what_if_preview,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def simulation_capsule():
    return {
        "canonical_key": "test.goal_engine.simulation_what_if_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "metric_target": "10 enquiries",
                    "simulation_scenarios": [
                        "baseline",
                        "low_conversion",
                        "high_cost",
                        "connector_failure",
                    ],
                    "estimated_cost": 12.5,
                    "estimated_runtime_minutes": 20,
                    "success_probability": 0.62,
                    "risk_score": 0.35,
                },
            },
            {
                "id": "experiment_1",
                "title": "A/B test offer",
                "action_id": "goal_engine.experiment",
                "config": {
                    "metric": "reply_rate",
                    "variants": ["A", "B"],
                    "simulation_scenarios": ["baseline", "approval_delay"],
                    "estimated_cost": 5,
                    "estimated_runtime_minutes": 10,
                    "success_probability": 0.7,
                    "risk_score": 0.2,
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "simulation_scenarios": ["baseline", "high_cost"],
                    "estimated_cost": 18,
                    "estimated_runtime_minutes": 30,
                    "success_probability": 0.58,
                    "risk_score": 0.4,
                },
            },
        ],
    }


def test_build_goal_engine_simulation_what_if_preview_directly():
    row = {
        "node_id": "goal_1",
        "node_kind": "goal",
        "source_config": {
            "simulation_scenarios": ["baseline", "low_conversion"],
            "estimated_cost": 9,
            "estimated_runtime_minutes": 15,
            "success_probability": 0.75,
            "risk_score": 0.25,
        },
    }

    preview = build_goal_engine_simulation_what_if_preview(row, run_id="run_sim_1")

    assert preview["schema_version"] == "aion.goal_engine.simulation_what_if_preview.v1"
    assert preview["runtime"] == "aion_goal_engine"
    assert preview["node_id"] == "goal_1"
    assert preview["scenarios"] == ["baseline", "low_conversion"]
    assert preview["estimated_cost"] == 9
    assert preview["estimated_runtime_minutes"] == 15
    assert preview["success_probability"] == 0.75
    assert preview["risk_score"] == 0.25
    assert preview["recommended_action"] == "review_before_live_execution"
    assert preview["dry_run_only"] is True
    assert preview["external_write_performed"] is False


def test_step_trace_rows_include_simulation_what_if_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        simulation_capsule(),
        run_id="run_sim_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_sim_2")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    loop_row = next(row for row in rows if row["node_id"] == "loop_1")

    assert goal_row["simulation_what_if_preview"]["scenarios"][0] == "baseline"
    assert goal_row["simulation_what_if_preview"]["risk_score"] == 0.35
    assert loop_row["simulation_what_if_preview"]["estimated_runtime_minutes"] == 30
    assert loop_row["payload"]["simulation_what_if_preview"]["success_probability"] == 0.58


def test_simulation_preview_recommends_do_not_run_when_risk_too_high():
    row = {
        "node_id": "dangerous_goal",
        "node_kind": "goal",
        "source_config": {
            "simulation_scenarios": ["baseline", "high_cost"],
            "risk_score": 0.95,
            "success_probability": 0.2,
        },
    }

    preview = build_goal_engine_simulation_what_if_preview(row, run_id="run_sim_3")

    assert preview["risk_score"] == 0.95
    assert preview["recommended_action"] == "do_not_run_risk_too_high"
    assert preview["requires_human_review"] is True


def test_manifest_attach_preserves_simulation_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        simulation_capsule(),
        run_id="run_sim_4",
    )

    payload = result.to_dict()
    goal_row = next(row for row in payload["trace"] if row.get("node_id") == "goal_1")

    assert goal_row["simulation_what_if_preview"]["schema_version"] == "aion.goal_engine.simulation_what_if_preview.v1"
    assert goal_row["simulation_what_if_preview"]["scenarios"] == [
        "baseline",
        "low_conversion",
        "high_cost",
        "connector_failure",
    ]
    assert goal_row["simulation_what_if_preview"]["external_write_performed"] is False

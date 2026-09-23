from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
    build_goal_engine_resource_cost_governance_preview,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def governance_capsule():
    return {
        "canonical_key": "test.goal_engine.resource_cost_governance_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads safely",
                "action_id": "goal_engine.goal",
                "config": {
                    "goal_budget": 25.0,
                    "token_quota": 5000,
                    "runtime_quota_minutes": 45,
                    "provider_cost_quota": 12.5,
                    "connector_cost_quota": 5.0,
                    "external_write_quota": 0,
                    "parallel_run_quota": 1,
                    "estimated_cost": 7.25,
                    "estimated_tokens": 1200,
                    "estimated_runtime_minutes": 15,
                    "budget_warning_threshold": 0.8,
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "goal_budget": 30.0,
                    "estimated_cost": 9.0,
                    "estimated_runtime_minutes": 30,
                    "runtime_quota_minutes": 60,
                },
            },
        ],
    }


def test_build_resource_cost_governance_preview_directly():
    row = {
        "node_id": "goal_1",
        "node_kind": "goal",
        "payload": {
            "goal_budget": 25.0,
            "token_quota": 5000,
            "runtime_quota_minutes": 45,
            "provider_cost_quota": 12.5,
            "connector_cost_quota": 5.0,
            "external_write_quota": 0,
            "parallel_run_quota": 1,
            "estimated_cost": 7.25,
            "estimated_tokens": 1200,
            "estimated_runtime_minutes": 15,
            "budget_warning_threshold": 0.8,
        },
    }

    preview = build_goal_engine_resource_cost_governance_preview(row, run_id="run_gov_1")

    assert preview["schema_version"] == "aion.goal_engine.resource_cost_governance_preview.v1"
    assert preview["node_id"] == "goal_1"
    assert preview["goal_budget"] == 25.0
    assert preview["estimated_cost"] == 7.25
    assert preview["budget_remaining"] == 17.75
    assert preview["token_quota"] == 5000
    assert preview["runtime_quota_minutes"] == 45
    assert preview["external_write_quota"] == 0
    assert preview["external_write_allowed"] is False
    assert preview["hard_stop_at_limit"] is True
    assert preview["pause_at_warning_threshold"] is True
    assert preview["dry_run_only"] is True
    assert preview["grants_permission"] is False


def test_step_trace_rows_include_resource_cost_governance_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        governance_capsule(),
        run_id="run_gov_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_gov_2")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    loop_row = next(row for row in rows if row["node_id"] == "loop_1")

    assert goal_row["resource_cost_governance_preview"]["goal_budget"] == 25.0
    assert goal_row["resource_cost_governance_preview"]["estimated_tokens"] == 1200
    assert goal_row["payload"]["resource_cost_governance_preview"]["provider_cost_quota"] == 12.5

    assert loop_row["resource_cost_governance_preview"]["goal_budget"] == 30.0
    assert loop_row["resource_cost_governance_preview"]["estimated_runtime_minutes"] == 30


def test_resource_governance_blocks_budgetless_spend_actions():
    row = {
        "node_id": "unsafe_spend_1",
        "node_kind": "goal",
        "payload": {
            "goal_budget": 0,
            "estimated_cost": 10,
            "external_write_quota": 0,
        },
    }

    preview = build_goal_engine_resource_cost_governance_preview(row, run_id="run_gov_3")

    assert preview["budgetless_spend_blocked"] is True
    assert preview["recommended_action"] == "do_not_run_budget_required"
    assert preview["external_write_allowed"] is False
    assert preview["grants_permission"] is False


def test_manifest_attach_preserves_resource_governance_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        governance_capsule(),
        run_id="run_gov_4",
    )

    payload = result.to_dict()
    goal_row = next(row for row in payload["trace"] if row.get("node_id") == "goal_1")

    assert goal_row["resource_cost_governance_preview"]["schema_version"] == "aion.goal_engine.resource_cost_governance_preview.v1"
    assert goal_row["resource_cost_governance_preview"]["goal_budget"] == 25.0
    assert goal_row["resource_cost_governance_preview"]["budget_remaining"] == 17.75
    assert goal_row["resource_cost_governance_preview"]["external_write_allowed"] is False

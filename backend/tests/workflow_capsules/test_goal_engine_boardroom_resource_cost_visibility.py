from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace
from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


def governance_capsule():
    return {
        "canonical_key": "test.goal_engine.boardroom_resource_cost_visibility",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads safely",
                "action_id": "goal_engine.goal",
                "config": {
                    "goal_budget": 25.0,
                    "estimated_cost": 7.25,
                    "token_quota": 5000,
                    "estimated_tokens": 1200,
                    "runtime_quota_minutes": 45,
                    "estimated_runtime_minutes": 15,
                    "provider_cost_quota": 12.5,
                    "connector_cost_quota": 5.0,
                    "external_write_quota": 0,
                    "parallel_run_quota": 1,
                },
            },
            {
                "id": "loop_1",
                "title": "Budgetless loop should be blocked",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "goal_budget": 0,
                    "estimated_cost": 10,
                    "external_write_quota": 0,
                },
            },
        ],
    }


def trace_for_capsule():
    manifest = build_goal_engine_manifest_for_capsule(
        governance_capsule(),
        run_id="run_boardroom_gov_1",
    )
    manifest["goal_engine_step_trace"] = build_goal_engine_step_trace_rows(
        manifest,
        run_id="run_boardroom_gov_1",
    )
    return build_goal_engine_boardroom_trace(manifest)


def test_boardroom_trace_exposes_budget_resource_summary():
    trace = trace_for_capsule()

    assert "resource_cost_governance" in trace
    governance = trace["resource_cost_governance"]

    assert governance["schema_version"] == "aion.goal_engine.boardroom_resource_cost_governance.v1"
    assert governance["goal_budget_total"] == 25.0
    assert governance["estimated_cost_total"] == 17.25
    assert governance["token_quota_total"] == 5000
    assert governance["estimated_tokens_total"] == 1200
    assert governance["runtime_quota_minutes_total"] == 45
    assert governance["estimated_runtime_minutes_total"] == 15
    assert governance["external_write_allowed"] is False
    assert governance["budgetless_spend_blocked"] is True
    assert governance["hard_stop_at_limit"] is True
    assert governance["dry_run_only"] is True
    assert governance["grants_permission"] is False


def test_boardroom_trace_exposes_budget_status_rows():
    trace = trace_for_capsule()

    rows = trace["resource_cost_governance"]["rows"]

    assert len(rows) == 2
    assert rows[0]["node_id"] == "goal_1"
    assert rows[0]["goal_budget"] == 25.0
    assert rows[0]["estimated_cost"] == 7.25
    assert rows[0]["budget_remaining"] == 17.75

    assert rows[1]["node_id"] == "loop_1"
    assert rows[1]["budgetless_spend_blocked"] is True
    assert rows[1]["recommended_action"] == "do_not_run_budget_required"


def test_boardroom_trace_top_level_budget_fields_for_ui():
    trace = trace_for_capsule()

    assert trace["budget_status"]["estimated_cost_total"] == 17.25
    assert trace["budget_status"]["budgetless_spend_blocked"] is True
    assert trace["budget_status"]["external_write_allowed"] is False
    assert trace["budget_status"]["recommended_action"] in {
        "do_not_run_budget_required",
        "review_before_live_execution",
        "pause_for_budget_review",
    }

    assert "budget_status" in trace["boardroom_visibility_fields"]
    assert "resource_cost_governance" in trace["boardroom_visibility_fields"]


def test_boardroom_trace_resource_cost_events_are_visible():
    trace = trace_for_capsule()

    events = trace["events"]
    event_text = str(events)

    assert "goal_engine.resource_cost_governance_visible" in event_text
    assert "goal_1" in event_text
    assert "loop_1" in event_text

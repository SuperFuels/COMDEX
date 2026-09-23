from backend.modules.aion.goal_engine.preview_bundle import (
    _build_orchestrator_parent_child_aggregation_runtime_summary,
    build_goal_engine_preview_bundle,
)


def _manifest():
    return {
        "valid": True,
        "steps": [
            {
                "step_type": "orchestrator",
                "contract_id": "orch_parent_child_1",
                "contract": {
                    "orchestrator_id": "orch_parent_child_1",
                    "goal_id": "goal_parent_1",
                    "aggregation_policy": "visibility_only",
                    "conflict_policy": "human_review",
                    "child_glyphs": [
                        {"glyph_code": "WD-101", "role": "workflow"},
                        {"glyph_code": "MK-201", "role": "marketing"},
                    ],
                    "agent_assignments": [
                        {"agent_id": "agent_ops", "role": "operations"},
                        {"agent_id": "agent_marketing", "role": "marketing"},
                    ],
                    "child_runs": [
                        {"run_id": "child_run_1", "status": "completed"},
                        {"run_id": "child_run_2", "status": "waiting_approval"},
                    ],
                },
            }
        ],
    }


def test_parent_child_aggregation_runtime_summary_builds_from_orchestrator_contract():
    summary = _build_orchestrator_parent_child_aggregation_runtime_summary(
        run_id="run_1",
        workflow_id="wf_1",
        manifest=_manifest(),
    )

    assert summary["trace_type"] == "orchestrator_parent_child_aggregation_runtime_summary"
    assert summary["aggregation_count"] == 1
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False
    assert summary["would_mutate_parent_goal"] is False

    preview = summary["parent_child_aggregation_previews"][0]
    assert preview["trace_type"] == "orchestrator_parent_child_aggregation_preview"
    assert preview["orchestrator_id"] == "orch_parent_child_1"
    assert preview["parent_goal_id"] == "goal_parent_1"


def test_preview_bundle_exposes_parent_child_aggregation_summary_and_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_1",
        workflow_id="wf_1",
        goal_engine_manifest=_manifest(),
    )

    summary = bundle["parent_child_aggregation_runtime_summary"]

    assert summary["trace_type"] == "orchestrator_parent_child_aggregation_runtime_summary"
    assert summary["aggregation_count"] == 1
    assert bundle["orchestrator_parent_child_aggregation_runtime_summary"] == summary
    assert len(bundle["parent_child_aggregation_previews"]) == 1
    assert len(bundle["orchestrator_parent_child_aggregation_previews"]) == 1


def test_preview_bundle_machine_trace_exposes_parent_child_aggregation_for_boardroom():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_1",
        workflow_id="wf_1",
        goal_engine_manifest=_manifest(),
    )

    machine_trace = bundle["machine_trace"]

    assert "parent_child_aggregation_runtime_summary" in machine_trace
    assert "orchestrator_parent_child_aggregation_runtime_summary" in machine_trace
    assert machine_trace["parent_child_aggregation_runtime_summary"]["aggregation_count"] == 1
    assert len(machine_trace["parent_child_aggregation_previews"]) == 1


def test_empty_manifest_keeps_safe_empty_summary():
    summary = _build_orchestrator_parent_child_aggregation_runtime_summary(
        run_id="run_empty",
        workflow_id="wf_empty",
        manifest={"valid": True, "steps": []},
    )

    assert summary["aggregation_count"] == 0
    assert summary["parent_child_aggregation_previews"] == []
    assert summary["dry_run_only"] is True
    assert summary["would_mutate_parent_goal"] is False

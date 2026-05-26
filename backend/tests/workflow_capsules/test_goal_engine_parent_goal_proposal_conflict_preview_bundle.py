from backend.modules.aion.goal_engine.preview_bundle import (
    _build_orchestrator_parent_child_aggregation_runtime_summary,
    build_goal_engine_preview_bundle,
)


def _manifest():
    return {
        "workflow_id": "workflow_parent_goal_conflict_bundle",
        "runtime": "aion_goal_engine",
        "steps": [
            {
                "step_id": "orchestrator_parent_goal_conflict",
                "step_type": "orchestrator",
                "contract": {
                    "orchestrator_id": "orch_parent_conflict_001",
                    "parent_goal_id": "goal_parent_conflict_001",
                    "goal_id": "goal_parent_conflict_001",
                    "child_runs": [
                        {
                            "run_id": "child_sales",
                            "agent_id": "agent_sales",
                            "status": "completed",
                            "recommendation": "approve",
                            "confidence": 0.82,
                        },
                        {
                            "run_id": "child_critic",
                            "agent_id": "agent_critic",
                            "status": "completed",
                            "recommendation": "reject",
                            "confidence": 0.76,
                        },
                    ],
                    "child_glyphs": [
                        {
                            "glyph_code": "MK-101",
                            "status": "completed",
                            "recommendation": "revise",
                            "confidence": 0.64,
                        }
                    ],
                    "aggregation_policy": "visibility_only",
                    "conflict_policy": "human_review",
                },
            }
        ],
    }


def test_runtime_summary_preserves_parent_goal_proposal_and_child_conflict():
    summary = _build_orchestrator_parent_child_aggregation_runtime_summary(
        run_id="run_parent_conflict_bundle",
        workflow_id="workflow_parent_goal_conflict_bundle",
        manifest=_manifest(),
    )

    assert summary["trace_type"] == "orchestrator_parent_child_aggregation_runtime_summary"
    assert summary["aggregation_count"] == 1

    preview = summary["parent_child_aggregation_previews"][0]

    assert preview["parent_goal_id"] == "goal_parent_conflict_001"
    assert preview["child_agent_conflict_preview"]["trace_type"] == "child_agent_conflict_preview"
    assert preview["child_agent_conflict_preview"]["conflict_detected"] is True
    assert preview["conflict_detected"] is True
    assert "child_agent_conflict_requires_review" in preview["aggregate_blocked_reasons"]

    proposal = preview["parent_goal_update_proposal"]
    assert proposal["trace_type"] == "parent_goal_update_proposal"
    assert proposal["approval_gate"] == "parent_goal_update_review"
    assert proposal["would_mutate_parent_goal"] is False


def test_preview_bundle_to_dict_mirrors_parent_goal_proposal_and_conflict():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_conflict_bundle",
        workflow_id="workflow_parent_goal_conflict_bundle",
        manifest=_manifest(),
    ).to_dict()

    summary = bundle["orchestrator_parent_child_aggregation_runtime_summary"]
    preview = summary["orchestrator_parent_child_aggregation_previews"][0]

    assert preview["parent_goal_update_proposal"]["trace_type"] == "parent_goal_update_proposal"
    assert preview["child_agent_conflict_preview"]["trace_type"] == "child_agent_conflict_preview"
    assert preview["conflict_detected"] is True

    machine_trace = bundle["machine_trace"]
    machine_summary = machine_trace["orchestrator_parent_child_aggregation_runtime_summary"]
    machine_preview = machine_summary["parent_child_aggregation_previews"][0]

    assert machine_preview["parent_goal_update_proposal"]["approval_gate"] == "parent_goal_update_review"
    assert machine_preview["child_agent_conflict_preview"]["recommended_resolution"] == "human_review_required"
    assert machine_preview["would_mutate_parent_goal"] is False


def test_preview_bundle_keeps_aliases_in_sync():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_conflict_bundle",
        workflow_id="workflow_parent_goal_conflict_bundle",
        manifest=_manifest(),
    ).to_dict()

    assert bundle["parent_child_aggregation_runtime_summary"] == bundle["orchestrator_parent_child_aggregation_runtime_summary"]
    assert bundle["parent_child_aggregation_previews"] == bundle["orchestrator_parent_child_aggregation_previews"]

    preview = bundle["parent_child_aggregation_previews"][0]
    alias_preview = bundle["orchestrator_parent_child_aggregation_previews"][0]

    assert preview["child_agent_conflict_preview"] == alias_preview["child_agent_conflict_preview"]
    assert preview["parent_goal_update_proposal"] == alias_preview["parent_goal_update_proposal"]

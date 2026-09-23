from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def _manifest_with_conflicting_orchestrator():
    return {
        "schema_version": "aion.goal_engine.dry_run_manifest.v1",
        "runtime": "aion_goal_engine",
        "run_id": "run_parent_conflict_payload",
        "workflow_id": "workflow_parent_conflict_payload",
        "steps": [
            {
                "step_id": "step_orchestrator_parent_conflict",
                "step_type": "orchestrator",
                "contract": {
                    "node_kind": "orchestrator",
                    "orchestrator_id": "orch_parent_conflict",
                    "parent_goal_id": "goal_parent",
                    "parent_goal_status": "active",
                    "child_runs": [
                        {
                            "child_run_id": "child_sales",
                            "status": "completed",
                            "recommendation": "approve",
                            "confidence": 0.82,
                        },
                        {
                            "child_run_id": "child_critic",
                            "status": "completed",
                            "recommendation": "reject",
                            "confidence": 0.76,
                        },
                    ],
                    "agent_assignments": [
                        {
                            "agent_id": "agent_sales",
                            "status": "completed",
                            "recommendation": "approve",
                            "confidence": 0.82,
                        },
                        {
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
        "safety_contract": {
            "dry_run_only": True,
            "would_execute": False,
            "would_write_external": False,
            "would_mutate_parent_goal": False,
        },
    }


def test_boardroom_payload_has_parent_goal_proposal_conflict_runtime_summary_aliases():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_conflict_payload",
        workflow_id="workflow_parent_conflict_payload",
        manifest=_manifest_with_conflicting_orchestrator(),
    ).to_dict()

    summary = bundle["orchestrator_parent_child_aggregation_runtime_summary"]
    alias = bundle["parent_child_aggregation_runtime_summary"]

    assert summary == alias
    assert summary["trace_type"] == "orchestrator_parent_child_aggregation_runtime_summary"
    assert summary["aggregation_count"] == 1

    preview = summary["orchestrator_parent_child_aggregation_previews"][0]
    assert preview["parent_goal_update_proposal"]["trace_type"] == "parent_goal_update_proposal"
    assert preview["parent_goal_update_proposal"]["approval_gate"] == "parent_goal_update_review"
    assert preview["child_agent_conflict_preview"]["trace_type"] == "child_agent_conflict_preview"
    assert preview["child_agent_conflict_preview"]["conflict_detected"] is True
    assert preview["child_agent_conflict_preview"]["recommended_resolution"] == "human_review_required"
    assert preview["conflict_detected"] is True
    assert "child_agent_conflict_requires_review" in preview["aggregate_blocked_reasons"]


def test_machine_trace_mirrors_parent_goal_proposal_conflict_payload():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_conflict_payload",
        workflow_id="workflow_parent_conflict_payload",
        manifest=_manifest_with_conflicting_orchestrator(),
    ).to_dict()

    top_preview = bundle["orchestrator_parent_child_aggregation_previews"][0]
    machine_preview = bundle["machine_trace"]["orchestrator_parent_child_aggregation_previews"][0]

    assert machine_preview["parent_goal_update_proposal"] == top_preview["parent_goal_update_proposal"]
    assert machine_preview["child_agent_conflict_preview"] == top_preview["child_agent_conflict_preview"]
    assert machine_preview["conflict_detected"] is True


def test_payload_remains_preview_only_and_no_parent_goal_mutation():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_parent_conflict_payload",
        workflow_id="workflow_parent_conflict_payload",
        manifest=_manifest_with_conflicting_orchestrator(),
    ).to_dict()

    summary = bundle["orchestrator_parent_child_aggregation_runtime_summary"]
    preview = summary["orchestrator_parent_child_aggregation_previews"][0]

    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False
    assert summary["would_mutate_parent_goal"] is False

    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_mutate_parent_goal"] is False
    assert preview["requires_human_approval"] is True
    assert preview["manual_review_required"] is True

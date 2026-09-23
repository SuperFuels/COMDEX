from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    GOAL_ENGINE_PREVIEW_BUILDERS,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_preview_bundle_for_row,
    build_goal_engine_step_trace_rows,
)


def registry_capsule():
    return {
        "canonical_key": "test.goal_engine.preview_builder_registry",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {
                    "simulation_scenarios": ["baseline", "low_conversion"],
                    "risk_score": 0.2,
                    "goal_budget": 25,
                    "estimated_cost": 5,
                    "feedback_required": True,
                },
            },
            {
                "id": "experiment_1",
                "title": "A/B test offer",
                "action_id": "goal_engine.experiment",
                "config": {
                    "variants": ["A", "B"],
                    "metric": "reply_rate",
                    "winner_policy": "manual",
                },
            },
            {
                "id": "loop_1",
                "title": "Bounded loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "max_checkpoint_size": 2048,
                    "loop_context_snapshot": {"iteration": 0},
                },
            },
            {
                "id": "outcome_1",
                "title": "Evaluate outcome",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {
                    "metric_name": "enquiries",
                    "metric_target": 10,
                    "metric_actual": 0,
                    "evidence_refs": ["manual:pending"],
                },
            },
            {
                "id": "reflect_1",
                "title": "Reflect",
                "action_id": "goal_engine.reflect_learn",
                "config": {
                    "allow_learn": True,
                    "adr_active": False,
                    "episodic_run_memory": "campaign worked",
                },
            },
            {
                "id": "delta_1",
                "title": "State delta",
                "action_id": "goal_engine.state_delta_accumulator",
                "config": {
                    "max_delta_bytes": 1024,
                    "loop_context_snapshot": {"status": "preview"},
                },
            },
            {
                "id": "revalidate_1",
                "title": "Revalidate",
                "action_id": "goal_engine.environment_revalidation",
                "config": {
                    "requires_vault_revalidation": True,
                    "requires_connector_revalidation": True,
                },
            },
        ],
    }


def test_preview_builder_registry_exists_for_goal_engine_kinds():
    assert "goal" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "experiment" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "loop" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "outcome_evaluation" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "reflect_learn" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "state_delta_accumulator" in GOAL_ENGINE_PREVIEW_BUILDERS
    assert "environment_revalidation" in GOAL_ENGINE_PREVIEW_BUILDERS


def test_preview_builder_registry_values_are_callable():
    for builders in GOAL_ENGINE_PREVIEW_BUILDERS.values():
        assert isinstance(builders, list)
        assert builders
        assert all(callable(builder) for builder in builders)


def test_preview_bundle_for_row_collects_known_previews():
    manifest = build_goal_engine_manifest_for_capsule(
        registry_capsule(),
        run_id="run_registry_1",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_registry_1")

    goal_row = next(row for row in rows if row["node_id"] == "goal_1")
    bundle = build_goal_engine_preview_bundle_for_row(goal_row, run_id="run_registry_1")

    assert bundle["schema_version"] == "aion.goal_engine.preview_bundle.v1"
    assert bundle["runtime"] == "aion_goal_engine"
    assert bundle["node_id"] == "goal_1"
    assert bundle["dry_run_only"] is True
    assert bundle["grants_permission"] is False
    assert "simulation_what_if_preview" in bundle["previews"]
    assert "resource_cost_governance_preview" in bundle["previews"]
    assert "human_feedback_preview" in bundle["previews"]
    assert "red_team_safety_preview" in bundle["previews"]


def test_step_trace_rows_receive_preview_bundle():
    manifest = build_goal_engine_manifest_for_capsule(
        registry_capsule(),
        run_id="run_registry_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_registry_2")

    experiment_row = next(row for row in rows if row["node_id"] == "experiment_1")
    loop_row = next(row for row in rows if row["node_id"] == "loop_1")
    outcome_row = next(row for row in rows if row["node_id"] == "outcome_1")

    assert "goal_engine_preview_bundle" in experiment_row
    assert "experiment_variant_preview" in experiment_row["goal_engine_preview_bundle"]["previews"]

    assert "goal_engine_preview_bundle" in loop_row
    assert "loop_iteration_preview" in loop_row["goal_engine_preview_bundle"]["previews"]
    assert "checkpoint_resume_preview" in loop_row["goal_engine_preview_bundle"]["previews"]

    assert "goal_engine_preview_bundle" in outcome_row
    assert "outcome_score_preview" in outcome_row["goal_engine_preview_bundle"]["previews"]


def test_preview_bundle_is_also_in_payload():
    manifest = build_goal_engine_manifest_for_capsule(
        registry_capsule(),
        run_id="run_registry_3",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_registry_3")

    row = next(row for row in rows if row["node_id"] == "goal_1")

    assert "goal_engine_preview_bundle" in row["payload"]
    assert row["payload"]["goal_engine_preview_bundle"]["node_id"] == "goal_1"

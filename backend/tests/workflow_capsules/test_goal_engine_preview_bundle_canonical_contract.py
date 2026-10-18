from backend.modules.aion.goal_engine.contracts import GoalNodeContract, ExperimentNodeContract
from backend.modules.aion.goal_engine.preview_bundle import (
    GOAL_ENGINE_PREVIEW_BUNDLE_SCHEMA_VERSION,
    GoalEnginePreviewBundle,
    build_goal_engine_preview_bundle,
)


def test_goal_engine_preview_bundle_schema_version_is_locked():
    assert GOAL_ENGINE_PREVIEW_BUNDLE_SCHEMA_VERSION == "aion.goal_engine.preview_bundle.v1"


def test_goal_engine_preview_bundle_contains_canonical_sections():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_001",
        workflow_id="workflow_001",
        contracts=[
            GoalNodeContract(
                goal_id="goal_001",
                goal_name="Generate leads",
                target_metric="lead_count",
                target_value=10,
                max_iterations=3,
            ),
            ExperimentNodeContract(
                experiment_id="exp_001",
                goal_id="goal_001",
                variants=["variant_a", "variant_b"],
                metric="lead_count",
            ),
        ],
    )

    assert isinstance(bundle, GoalEnginePreviewBundle)

    payload = bundle.to_dict()

    assert payload["schema_version"] == "aion.goal_engine.preview_bundle.v1"
    assert payload["runtime"] == "aion_goal_engine"
    assert payload["run_id"] == "run_001"
    assert payload["workflow_id"] == "workflow_001"

    assert isinstance(payload["manifest"], dict)
    assert isinstance(payload["step_trace"], list)
    assert isinstance(payload["boardroom_trace"], dict)
    assert isinstance(payload["safety_contract"], dict)

    assert payload["dry_run_only"] is True
    assert payload["would_execute"] is False
    assert payload["would_write_external"] is False
    assert payload["would_grant_permission"] is False
    assert payload["grants_permission"] is False


def test_goal_engine_preview_bundle_safety_contract_is_canonical():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_002",
        workflow_id="workflow_002",
        contracts=[
            GoalNodeContract(
                goal_id="goal_002",
                goal_name="Improve conversions",
                target_metric="conversion_rate",
                target_value=0.2,
            )
        ],
    )

    safety = bundle.to_dict()["safety_contract"]

    assert safety["goals_grant_permission"] is False
    assert safety["experiments_grant_permission"] is False
    assert safety["loops_grant_permission"] is False
    assert safety["learning_grants_permission"] is False
    assert safety["external_writes_require_approval"] is True
    assert safety["unbounded_loops_allowed"] is False
    assert safety["resume_requires_environment_revalidation"] is True


def test_goal_engine_preview_bundle_has_machine_trace_ready_shape():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_003",
        workflow_id="workflow_003",
        contracts=[
            GoalNodeContract(
                goal_id="goal_003",
                goal_name="Prepare agent-ready fulfilment",
                target_metric="readiness_score",
                target_value=1,
            )
        ],
    )

    payload = bundle.to_dict()

    assert "machine_trace" in payload
    assert payload["machine_trace"]["runtime"] == "aion_goal_engine"
    assert payload["machine_trace"]["trace_type"] == "goal_engine_preview"
    assert payload["machine_trace"]["agent_ready"] is False
    assert payload["machine_trace"]["a2a_deferred"] is True
    assert payload["machine_trace"]["commercial_interface_ready"] is False
    assert payload["machine_trace"]["reason"] == "A2A is deferred until Goal Engine Sprint 1 is stable."

from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)


def test_boardroom_payload_exposes_live_goal_engine_preview_bundle():
    payload = BusinessContainerService().get_boardroom_payload("costa-conexion")

    assert "goal_engine_runtime_preview" in payload
    assert "goal_engine_preview_bundle" in payload

    preview = payload["goal_engine_runtime_preview"]
    bundle = payload["goal_engine_preview_bundle"]

    assert preview["schema_version"] == "aion_goal_engine_boardroom_runtime_preview_v1"
    assert preview["trace_type"] == "goal_engine_runtime_preview"
    assert bundle == preview


def test_boardroom_payload_mirrors_goal_engine_preview_into_runtime_and_summary():
    payload = BusinessContainerService().get_boardroom_payload("costa-conexion")

    runtime = payload.get("runtime") or {}
    summary = payload.get("summary") or {}

    assert runtime.get("goal_engine_preview_bundle")
    assert summary.get("goal_engine_preview_bundle")

    assert runtime["goal_engine_preview_bundle"] == payload["goal_engine_preview_bundle"]
    assert summary["goal_engine_preview_bundle"] == payload["goal_engine_preview_bundle"]


def test_boardroom_payload_exposes_all_runtime_summary_mirrors():
    payload = BusinessContainerService().get_boardroom_payload("costa-conexion")

    required = {
        "goal_runtime_summary": "goal_runtime_summary",
        "goal_engine_goal_runtime_summary": "goal_runtime_summary",
        "checkpoint_runtime_summary": "checkpoint_runtime_summary",
        "goal_engine_checkpoint_runtime_summary": "checkpoint_runtime_summary",
        "resume_revalidation_summary": "resume_revalidation_summary",
        "goal_engine_resume_revalidation_summary": "resume_revalidation_summary",
        "experiment_runtime_summary": "experiment_runtime_summary",
        "goal_engine_experiment_runtime_summary": "experiment_runtime_summary",
        "orchestrator_runtime_summary": "orchestrator_runtime_summary",
        "goal_engine_orchestrator_runtime_summary": "orchestrator_runtime_summary",
        "goal_decomposition_runtime_summary": "goal_decomposition_runtime_summary",
        "goal_engine_decomposition_runtime_summary": "goal_decomposition_runtime_summary",
    }

    for key, trace_type in required.items():
        assert key in payload
        assert payload[key]["trace_type"] == trace_type


def test_boardroom_live_goal_engine_preview_is_dry_run_only():
    payload = BusinessContainerService().get_boardroom_payload("costa-conexion")
    preview = payload["goal_engine_runtime_preview"]

    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False


def test_boardroom_live_goal_engine_preview_contains_visible_warning_states():
    payload = BusinessContainerService().get_boardroom_payload("costa-conexion")

    goal_summary = payload["goal_runtime_summary"]
    checkpoint_summary = payload["checkpoint_runtime_summary"]
    revalidation_summary = payload["resume_revalidation_summary"]
    experiment_summary = payload["experiment_runtime_summary"]
    orchestrator_summary = payload["orchestrator_runtime_summary"]

    assert "outcome_success_requires_evidence" in goal_summary["blocked_reasons"]
    assert "resume_requires_environment_revalidation" in checkpoint_summary["blocked_reasons"]
    assert "external_state_changed" in revalidation_summary["blocked_reasons"]
    assert "unbounded_experiment_plan_blocked" in experiment_summary["blocked_reasons"]
    assert experiment_summary["premature_convergence_blocked"] is True
    assert "unbounded_orchestration_blocked" in orchestrator_summary["blocked_reasons"]

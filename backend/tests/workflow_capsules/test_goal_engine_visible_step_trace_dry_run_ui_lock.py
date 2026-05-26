from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_visible_goal_engine_step_trace_panel_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineStepTracePanelV1" in text
    assert "getAionGoalEngineStepTraceFromDryRunResultV1" in text
    assert 'data-aion-goal-engine-step-trace-panel="true"' in text


def test_visible_goal_engine_step_trace_panel_shows_preview_fields():
    text = read_app()

    assert "Step Trace Preview" in text
    assert "loop_iteration_preview" in text
    assert "experiment_variant_preview" in text
    assert "outcome_score_preview" in text
    assert "checkpoint_resume_preview" in text
    assert "state_delta_preview" in text
    assert "simulation_what_if_preview" in text
    assert "resource_cost_governance_preview" in text
    assert "human_feedback_preview" in text


def test_visible_goal_engine_step_trace_panel_wraps_dry_run_fallback():
    text = read_app()

    assert "installAionGoalEngineStepTraceDryRunPanelV1" in text
    assert "renderAionWorkflowDryRunResultPanelFallbackWithGoalEngineStepTraceV1" in text
    assert "renderAionWorkflowDryRunResultPanelFallback = wrapped" in text
    assert "__aionGoalEngineStepTraceDryRunPanelV1" in text

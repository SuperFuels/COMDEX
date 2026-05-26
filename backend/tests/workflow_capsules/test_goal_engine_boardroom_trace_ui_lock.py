from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_boardroom_trace_panel_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineBoardroomTracePanelV1" in text
    assert "getAionGoalEngineBoardroomTraceFromDryRunResultV1" in text
    assert 'data-aion-goal-engine-boardroom-trace-panel="true"' in text


def test_goal_engine_boardroom_trace_panel_shows_required_fields():
    text = read_app()

    assert "Boardroom Trace" in text
    assert "goal_engine_boardroom_trace" in text
    assert "aion_goal_engine" in text
    assert "Dry-run only" in text
    assert "Grants permission" in text
    assert "Active goals" in text
    assert "Experiments" in text
    assert "Loops" in text
    assert "Outcome score" in text
    assert "Evidence refs" in text
    assert "Blocked reasons / warnings" in text


def test_goal_engine_boardroom_trace_panel_is_added_to_dry_run_result_fallback():
    text = read_app()

    fallback_idx = text.find("renderAionWorkflowDryRunResultPanelFallback")
    panel_call_idx = text.find("renderAionGoalEngineBoardroomTracePanelV1(result)", fallback_idx)

    assert fallback_idx != -1
    assert panel_call_idx != -1
    assert panel_call_idx > fallback_idx

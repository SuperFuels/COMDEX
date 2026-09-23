from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_manifest_panel_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineManifestPanelV1" in text
    assert "getAionGoalEngineManifestFromDryRunResultV1" in text
    assert 'data-aion-goal-engine-manifest-panel="true"' in text


def test_goal_engine_manifest_panel_shows_required_fields():
    text = read_app()

    assert "Dry-run Manifest" in text
    assert "goal_engine_manifest" in text
    assert "Canonical dry-run contract" in text
    assert "Goals grant permission" in text
    assert "approval before external writes" in text
    assert "no unbounded execution" in text
    assert "Advanced Goal Engine manifest payload" in text


def test_goal_engine_manifest_panel_is_added_before_boardroom_trace_panel():
    text = read_app()

    fallback_idx = text.find("renderAionWorkflowDryRunResultPanelFallback")
    manifest_call_idx = text.find("renderAionGoalEngineManifestPanelV1(result)", fallback_idx)
    trace_call_idx = text.find("renderAionGoalEngineBoardroomTracePanelV1(result)", fallback_idx)

    assert fallback_idx != -1
    assert manifest_call_idx != -1
    assert trace_call_idx != -1
    assert fallback_idx < manifest_call_idx < trace_call_idx

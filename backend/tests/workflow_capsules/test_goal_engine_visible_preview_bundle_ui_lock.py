from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_preview_bundle_panel_renderer_exists():
    text = read_app()

    assert "renderAionGoalEnginePreviewBundlePanelV1" in text
    assert "getAionGoalEnginePreviewBundlesFromDryRunResultV1" in text
    assert 'data-aion-goal-engine-preview-bundle-panel="true"' in text


def test_goal_engine_preview_bundle_panel_shows_required_labels():
    text = read_app()

    assert "Preview Bundle" in text
    assert "goal_engine_preview_bundle" in text
    assert "Simulation" in text
    assert "Budget" in text
    assert "Human feedback" in text
    assert "Red-team" in text
    assert "Outcome" in text
    assert "Checkpoint" in text


def test_goal_engine_preview_bundle_panel_is_added_to_dry_run_result_fallback():
    text = read_app()

    fallback_idx = text.find("renderAionWorkflowDryRunResultPanelFallback")
    bundle_call_idx = text.find("renderAionGoalEnginePreviewBundlePanelV1(result)", fallback_idx)

    assert fallback_idx != -1
    assert bundle_call_idx != -1
    assert fallback_idx < bundle_call_idx

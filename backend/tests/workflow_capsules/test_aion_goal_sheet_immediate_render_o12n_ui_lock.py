from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12n_installed():
    assert "BEGIN AION O12N IMMEDIATE GOAL SHEET RENDER FIX" in APP_JS
    assert "immediate Goal Sheet render fix installed" in APP_JS


def test_o12n_syncs_all_render_sources():
    assert "syncGoalSheetGraphToEveryRenderSource" in APP_JS
    assert "window.__aionWorkflowGraph = graph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = graph" in APP_JS
    assert "window.__aionO12BBoardroomGoalSheetGraph = graph" in APP_JS
    assert "window.__aionBoardroomGoalSheetGraph = graph" in APP_JS


def test_o12n_forces_request_render_after_stage():
    assert "forceGoalSheetCanvasRender" in APP_JS
    assert "requestRender()" in APP_JS
    assert "window.dispatchEvent(new Event(\"resize\"))" in APP_JS
    assert "aion:workflow-graph-updated" in APP_JS


def test_o12n_wraps_stage_function():
    assert "wrapStageFunction" in APP_JS
    assert "aionStageBoardroomGoalSheetO12B" in APP_JS
    assert "stageBoardroomGoalSheet" in APP_JS


def test_o12n_stage_button_click_has_delayed_render_safety():
    assert "stage goal sheet" in APP_JS
    assert "window.setTimeout" in APP_JS
    assert "80" in APP_JS
    assert "140" in APP_JS


def test_o12n_exposes_manual_console_repair_hook():
    assert "window.aionForceGoalSheetCanvasRenderO12N" in APP_JS
    assert "window.aionSyncGoalSheetGraphToEveryRenderSourceO12N" in APP_JS

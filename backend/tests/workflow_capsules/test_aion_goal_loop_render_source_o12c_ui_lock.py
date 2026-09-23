from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12c_goal_sheet_render_source_installed():
    assert "BEGIN AION O12C GOAL SHEET RENDER SOURCE OF TRUTH" in APP_JS
    assert "getAionWorkflowRenderGraphO12C" in APP_JS
    assert "getAionActiveGoalSheetWorkflowGraphO12C" in APP_JS
    assert "syncAionGoalSheetGraphIntoWorkflowStateO12C" in APP_JS


def test_o12c_canvas_renderer_prefers_goal_sheet_over_blank_draft():
    assert "const graph =\n    typeof getAionWorkflowRenderGraphO12C" in APP_JS
    assert "window[\"__aionWorkflowGraph\"] = graph" in APP_JS
    assert "const activeGraph = typeof getAionWorkflowRenderGraphO12C" in APP_JS


def test_o12c_goal_sheet_graph_is_synced_to_native_workflow_state():
    assert "window.__aionWorkflowGraph = graph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = graph" in APP_JS
    assert "window.__aionO12BActiveGoalSheetGraph = graph" in APP_JS
    assert "creates_second_canvas = false" in APP_JS
    assert "creates_second_pilot = false" in APP_JS


def test_o12c_goal_sheet_keeps_preview_safety_contract():
    assert "execution_allowed_now = false" in APP_JS
    assert "connector_call_required = false" in APP_JS
    assert "external_side_effects = false" in APP_JS
    assert "actual_live_execution_performed = false" in APP_JS


def test_o12c_recognises_boardroom_goal_sheet_nodes():
    assert "board meeting minutes" in APP_JS
    assert "board decision" in APP_JS
    assert "actual goal" in APP_JS
    assert "success criteria" in APP_JS
    assert "linked department sheets" in APP_JS
    assert "pilot queue preview" in APP_JS

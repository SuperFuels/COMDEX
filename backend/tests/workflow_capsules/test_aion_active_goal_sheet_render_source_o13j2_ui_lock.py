from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o13j2_installed():
    assert "BEGIN AION O13J2 ACTIVE GOAL SHEET RENDER SOURCE LOCK" in APP_JS
    assert "O13J.2 active Goal Sheet render source lock installed" in APP_JS


def test_o13j2_draft_state_prefers_active_goal_sheet_before_main_graph():
    start = APP_JS.index("function getAionWorkflowDraftState()")
    area = APP_JS[start:start + 2200]
    assert "__aionGoalSheetForceRenderGraphO13J2" in area
    assert "__aionGoalLoopLinkedWorkflowRegistry" in area
    assert "__aionWorkflowMainGraph = forced" in area
    assert "return stripAionWorkflowSyntheticChooseNode(forced)" in area

    forced_block_index = area.find("const forced =")
    main_graph_assignment_index = area.find("__aionWorkflowMainGraph = forced")
    assert forced_block_index != -1
    assert main_graph_assignment_index != -1
    assert forced_block_index < main_graph_assignment_index


def test_o13j2_department_opener_sets_main_and_forced_graph():
    assert "window.__aionWorkflowMainGraph = sheet" in APP_JS
    assert "window.__aionGoalSheetForceRenderGraphO13J2 = sheet" in APP_JS
    assert "window.__aionGoalSheetActiveWorkflowIdO13J2 = sheet.workflow_id || sheet.id" in APP_JS


def test_o13j2_boardroom_sync_sets_main_and_forced_graph():
    assert "window.__aionWorkflowMainGraph = graph" in APP_JS
    assert "window.__aionGoalSheetForceRenderGraphO13J2 = graph" in APP_JS
    assert "window.__aionGoalSheetActiveWorkflowIdO13J2 = graph.workflow_id || graph.id" in APP_JS


def test_o13j2_keeps_goal_sheet_preview_safe():
    assert "execution_allowed_now: false" in APP_JS
    assert "connector_call_required: false" in APP_JS
    assert "external_side_effects: false" in APP_JS

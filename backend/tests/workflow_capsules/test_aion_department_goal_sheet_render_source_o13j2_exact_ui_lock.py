from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o13j2_exact_marker_installed():
    assert "BEGIN AION O13J2 EXACT SELECTED GOAL SHEET RENDER SOURCE LOCK" in APP_JS
    assert "exact selected Goal Sheet render source lock installed" in APP_JS


def test_o13j2_selected_workflow_checked_before_boardroom_registry():
    start = APP_JS.index("function getAionActiveGoalSheetWorkflowGraphO12C()")
    end = APP_JS.index("function syncAionGoalSheetGraphIntoWorkflowStateO12C", start)
    block = APP_JS[start:end]

    assert "const selectedWorkflowId = String(" in block
    assert "const activeCandidates = [" in block
    assert "graphId === selectedWorkflowId" in block

    active_index = block.index("const activeCandidates = [")
    normal_candidates_index = block.index("const candidates = [")
    boardroom_index = block.index("window.__aionBoardroomGoalSheetGraph")
    workflow_index = block.index("window.__aionWorkflowGraph")

    assert active_index < normal_candidates_index
    assert workflow_index < boardroom_index


def test_o13j2_render_source_can_select_department_graph_not_boardroom_first():
    start = APP_JS.index("function getAionActiveGoalSheetWorkflowGraphO12C()")
    end = APP_JS.index("function syncAionGoalSheetGraphIntoWorkflowStateO12C", start)
    block = APP_JS[start:end]

    assert "window.__aionWorkflowMainGraph" in block
    assert "window.__aionActiveWorkflowGraph" in block
    assert "window.__aionO12BActiveGoalSheetGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block

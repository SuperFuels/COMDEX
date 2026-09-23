from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o9_retired_and_replaced_by_o11b_clean_native_layout():
    assert "RETIRED BY O11B: AION O9 GOAL LOOP SWIMLANE LAYOUT ENGINE" in APP_JS
    assert "BEGIN AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT" in APP_JS
    assert "aion.o11b.clean_native_goal_loop" in APP_JS


def test_o11b_uses_native_workflow_graph_source_of_truth():
    assert "window.__aionWorkflowGraph = graph" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph = graph" in APP_JS
    assert "getAionWorkflowDraftState" in APP_JS
    assert "persistAionWorkflowDraftState(graph)" not in APP_JS


def test_o11b_removes_inner_sheet_and_viewport_background():
    assert "transformed viewport is transparent and huge" in APP_JS
    assert "width: 12000px" in APP_JS
    assert "height: 6000px" in APP_JS
    assert "background-image: none !important" in APP_JS
    assert ".aion-workflow-canvas-sheet" in APP_JS
    assert ".aion-workflow-canvas-paper" in APP_JS


def test_o11b_preserves_bottom_toolbar_outside_transformed_viewport():
    assert ".aion-workflow-floating-toolbar" in APP_JS
    assert "position: fixed !important" in APP_JS
    assert "z-index: 9000" in APP_JS


def test_o11b_no_repeated_layout_loop_or_mutation_observer():
    o11b = APP_JS.split("BEGIN AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT", 1)[1]
    o11b = o11b.split("END AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT", 1)[0]
    assert "MutationObserver" not in o11b
    assert "setInterval" not in o11b
    assert "window.aionLayoutCurrentGoalLoopWorkflowO11B" in o11b
    assert "window.aionLayoutCurrentGoalLoopWorkflowO9 = window.aionLayoutCurrentGoalLoopWorkflowO11B" in o11b

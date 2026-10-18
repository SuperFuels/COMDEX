from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o13j_exact_fix_marker_exists():
    assert "BEGIN AION O13J EXACT DEPARTMENT RENDER SOURCE FIX" in APP_JS


def test_o13j_department_opener_sets_main_graph_before_render():
    start = APP_JS.index("function openDepartmentGoalSheetO13B(department)")
    end = APP_JS.index("function openBoardroomGoalSheetO13B", start)
    block = APP_JS[start:end]

    assert "window.__aionWorkflowGraph = sheet;" in block
    assert "window.__aionWorkflowMainGraph = sheet;" in block
    assert "window.__aionActiveWorkflowGraph = sheet;" in block
    assert "window.__aionGoalLoopWorkflowGraph = sheet;" in block

    assert block.index("window.__aionWorkflowGraph = sheet;") < block.index("window.__aionWorkflowMainGraph = sheet;")
    assert block.index("window.__aionWorkflowMainGraph = sheet;") < block.index("window.__aionActiveWorkflowGraph = sheet;")


def test_o13j_render_resolver_uses_main_graph_first_so_patch_is_required():
    start = APP_JS.index("function getAionWorkflowDraftState()")
    area = APP_JS[start:start + 1800]
    assert "window.__aionWorkflowMainGraph" in area
    assert "return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph)" in area

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def o11b_block():
    assert "BEGIN AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT" in APP_JS
    return APP_JS.split("BEGIN AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT", 1)[1].split(
        "END AION O11B CLEAN NATIVE WORKFLOW CANVAS GOAL LOOP LAYOUT", 1
    )[0]


def test_o11b_installs_clean_layout_function():
    block = o11b_block()
    assert "installAionO11BCleanNativeWorkflowCanvasGoalLoopLayout" in block
    assert "window.aionLayoutCurrentGoalLoopWorkflowO11B" in block
    assert "applyO11BNodeCoordinates" in block
    assert "fitO11BViewportToGraph" in block


def test_o11b_layout_is_generic_and_department_swimlaned():
    block = o11b_block()
    assert '["marketing", "sales", "finance", "operations", "support"]' in block
    assert "getO11BDepartment" in block
    assert "layout_lane = dept" in block
    assert "Review / Evidence / Audit" in block


def test_o11b_uses_real_native_node_coordinates_not_static_overlay():
    block = o11b_block()
    assert "node.x =" in block
    assert "node.y =" in block
    assert "node.position = { x: node.x, y: node.y }" in block
    assert "data-aion-materialised-goal-loop-workflow" not in block
    assert "aion-o7-native-goal-loop-layer" not in block


def test_o11b_canvas_has_one_visible_grid_surface():
    block = o11b_block()
    assert ".aion-workflow-canvas {" in block
    assert "background-size: 72px 72px, 72px 72px, 18px 18px, 18px 18px" in block
    assert ".aion-workflow-canvas-viewport" in block
    assert "background: transparent !important" in block
    assert "box-shadow: none !important" in block


def test_o11b_does_not_break_toolbar_or_preview_only_status():
    block = o11b_block()
    assert "Goal Loop staged · native Workflow Canvas nodes · preview only" in block
    assert ".aion-workflow-floating-toolbar" in block
    assert "Layout Goal Loop" in block

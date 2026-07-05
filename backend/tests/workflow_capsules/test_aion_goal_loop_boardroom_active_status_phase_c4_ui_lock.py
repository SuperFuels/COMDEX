from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_phase_c4_status_panel_is_mounted_after_create_panel():
    assert "${renderAionBoardroomGoalLoopCreatePanel(snapshot)}" in APP_JS
    assert "${renderAionBoardroomGoalLoopActiveStatusPanel(snapshot)}" in APP_JS

    create_index = APP_JS.index("${renderAionBoardroomGoalLoopCreatePanel(snapshot)}")
    status_index = APP_JS.index("${renderAionBoardroomGoalLoopActiveStatusPanel(snapshot)}")

    assert create_index < status_index


def test_phase_c4_status_helper_reads_active_goal_loop_graph():
    block = function_block("getAionBoardroomActiveGoalLoopStatus")

    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block
    assert "window.__aionGoalLoopCanvasContract" in block
    assert 'graph?.canvas_type === "goal_loop"' in block
    assert 'graph?.active_canvas_intent === "goal_loop"' in block
    assert "node_count" in block
    assert "edge_count" in block
    assert "departments" in block


def test_phase_c4_status_uses_registered_business_identity_and_rejects_stale_metadata():
    block = function_block("getAionBoardroomActiveGoalLoopStatus")

    assert "getAionRegisteredBusinessIdentity()" in block
    assert "getAionWorkflowCanvasHeaderBusinessLabel()" in block
    assert "getAionWorkflowBusinessContainerId()" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "stale_legacy_business_metadata" in block
    assert '"costa-conexion"' not in block
    assert '"Home Fixed"' not in block
    assert '"home_fixed"' not in block


def test_phase_c4_renderer_exposes_visible_boardroom_status_card():
    block = function_block("renderAionBoardroomGoalLoopActiveStatusPanel")

    assert 'data-aion-goal-loop-active-status-panel="true"' in block
    assert 'data-aion-goal-loop-active-business-label="true"' in block
    assert 'data-aion-goal-loop-active-goal-title="true"' in block
    assert 'data-aion-goal-loop-active-status="true"' in block
    assert 'data-aion-goal-loop-active-department-count="true"' in block
    assert 'data-aion-goal-loop-active-graph-counts="true"' in block
    assert 'data-aion-goal-loop-active-safety="true"' in block
    assert "Preview only" in block
    assert "No booking, payment, message or external action" in block


def test_phase_c4_does_not_create_second_canvas_or_second_pilot():
    block = APP_JS[
        APP_JS.index("/* AION GOAL LOOP BOARDROOM PHASE C4"):
        APP_JS.index("/* END AION GOAL LOOP BOARDROOM PHASE C4 */")
    ]

    forbidden = block.lower()
    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block
    assert "existing_workflow_canvas" in block

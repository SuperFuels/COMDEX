from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8", errors="ignore")


def c2_block():
    start = APP_JS.index("/* AION GOAL LOOP BOARDROOM PHASE C2: Visible Boardroom Create Panel */")
    end = APP_JS.index("/* END AION GOAL LOOP BOARDROOM PHASE C2 */", start)
    return APP_JS[start:end]


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_function = APP_JS.find("\nfunction ", start + 10)
    if next_function == -1:
        next_function = len(APP_JS)
    return APP_JS[start:next_function]


def test_phase_c2_boardroom_goal_loop_create_panel_exists():
    block = c2_block()

    assert "function renderAionBoardroomGoalLoopCreatePanel" in block
    assert "function handleAionBoardroomGoalLoopCreateAction" in block
    assert 'data-aion-goal-loop-boardroom-create-panel="true"' in block
    assert 'data-aion-goal-loop-boardroom-create="true"' in block
    assert "Create Goal Loop Canvas" in block
    assert "Boardroom decision → Goal Loop Canvas" in block


def test_phase_c2_boardroom_dashboard_mounts_panel_once():
    block = function_block("renderBoardroomDashboardView")

    assert "renderAionBoardroomGoalLoopCreatePanel(snapshot)" in block
    assert block.count("renderAionBoardroomGoalLoopCreatePanel(snapshot)") == 1


def test_phase_c2_create_action_uses_existing_c1_stager_and_existing_workflow_canvas():
    block = c2_block()

    assert "stageAionBoardroomDecisionGoalLoopIntoWorkflowCanvas" in block
    assert "window.__aionLastBoardroomGoalLoopCanvasStageResult" in block
    assert 'state.activeTab = "operations_agents"' in block
    assert 'focus_reason: "boardroom_visible_create_panel"' in block
    assert "requestRender" in block


def test_phase_c2_click_binding_is_delegated_and_safe():
    block = c2_block()

    assert "document.addEventListener" in block
    assert 'closest?.("[data-aion-goal-loop-boardroom-create]")' in block
    assert "event.preventDefault()" in block
    assert "event.stopPropagation()" in block


def test_phase_c2_exports_debug_helpers():
    block = c2_block()

    assert "window.renderAionBoardroomGoalLoopCreatePanel" in block
    assert "window.handleAionBoardroomGoalLoopCreateAction" in block


def test_phase_c2_does_not_create_second_canvas_or_second_pilot_or_execute():
    block = c2_block().lower()

    forbidden = [
        "function renderaiongoalloopcanvas",
        "data-aion-goal-loop-canvas-root",
        "new aionpilot",
        "runaiondepartmentpilotnextsafetask(",
        "approveaiondepartmentpilotplan(",
        "fetch(",
        "xmlhttprequest",
        "sendbeacon",
        "localstorage.setitem",
        "saveaionworkflowcanvasascapsule(",
        "chargecard(",
        "createpayment(",
        "payment_created",
        "payment_confirmed",
        "booking_confirmed",
        "message_sent",
    ]

    for token in forbidden:
        assert token not in block

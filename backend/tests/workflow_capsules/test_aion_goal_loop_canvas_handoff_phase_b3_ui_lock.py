from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def phase_b1_block() -> str:
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    return APP_JS[start:end]


def test_phase_b3_existing_workflow_canvas_handoff_helper_exists():
    block = phase_b1_block()

    assert "function stageAionGoalLoopCanvasIntoExistingWorkflowCanvas" in block
    assert "createAionGoalLoopCanvasFromBoardGoal(input)" in block
    assert "workflow_canvas_mount_hint" in block
    assert "existing_workflow_canvas" in block
    assert "active_canvas_intent" in block
    assert "goal_loop" in block


def test_phase_b3_handoff_uses_existing_workflow_globals_only():
    block = phase_b1_block()

    assert "window.__aionGoalLoopCanvasContract = contract" in block
    assert "window.__aionGoalLoopWorkflowGraph = graph" in block
    assert "window.__aionWorkflowGraph = graph" in block
    assert "window.__aionWorkflowMainGraph = graph" in block

    assert "window.__aionPendingWorkflowCanvasFocus" in block
    assert "window.__aionRenderWorkflowCanvasTabs" in block
    assert "requestRender" in block


def test_phase_b3_does_not_force_route_or_duplicate_canvas():
    block = phase_b1_block().lower()

    forbidden = [
        "state.activetab",
        "state.activeroute",
        "window.location",
        "history.pushstate",
        "renderaiongoalloopcanvas",
        "function renderaiongoalloop",
        "new workflow canvas",
        "function renderaiongoalloopcanvas",
        "data-aion-goal-loop-canvas-root",
        "class=\"aion-goal-loop-canvas",
        "new pilot",
        "function runaiongoallooppilot",
        "new aionpilot",
    ]

    for token in forbidden:
        assert token not in block


def test_phase_b3_handoff_does_not_persist_or_execute():
    block = phase_b1_block().lower()

    forbidden = [
        "fetch(",
        "xmlhttprequest",
        "sendbeacon",
        "localstorage.setitem",
        "saveaionworkflowcanvasascapsule(",
        "runaiondepartmentpilotnextsafetask(",
        "approveaiondepartmentpilotplan(",
        "chargecard(",
        "createpayment(",
        "payment_created",
        "booking_confirmed",
        "message_sent",
    ]

    for token in forbidden:
        assert token not in block


def test_phase_b3_handoff_is_exported_to_window():
    block = phase_b1_block()

    assert "window.stageAionGoalLoopCanvasIntoExistingWorkflowCanvas = stageAionGoalLoopCanvasIntoExistingWorkflowCanvas" in block

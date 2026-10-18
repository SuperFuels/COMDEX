from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def phase_b1_block() -> str:
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    return APP_JS[start:end]


def test_phase_b4_sample_goal_loop_helper_exists():
    block = phase_b1_block()

    assert "function buildAionGoalLoopCanvasSampleInput" in block
    assert "function stageAionSampleGoalLoopCanvasIntoExistingWorkflowCanvas" in block
    assert "window.buildAionGoalLoopCanvasSampleInput = buildAionGoalLoopCanvasSampleInput" in block
    assert "window.stageAionSampleGoalLoopCanvasIntoExistingWorkflowCanvas = stageAionSampleGoalLoopCanvasIntoExistingWorkflowCanvas" in block


def test_phase_b4_sample_is_generic_not_home_fixed_or_costa():
    block = phase_b1_block().lower()

    assert "home_fixed" not in block
    assert "home fixed" not in block
    assert "costa-conexion" not in block
    assert "costa_conexion" not in block

    assert "sample_business" in block
    assert "increase qualified leads" in block


def test_phase_b4_sample_has_all_core_department_sub_goals():
    block = phase_b1_block()

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'department: "{department}"' in block
        assert f'owner_agent: "{department}_pilot"' in block


def test_phase_b4_sample_stages_only_no_execution_or_persistence():
    block = phase_b1_block().lower()

    assert "stageaiongoalloopcanvasintoexistingworkflowcanvas(sample" in block

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

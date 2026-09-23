from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def c3_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE C3")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE C3 */", start)
    return APP_JS[start:end]


def test_phase_c3_immediate_header_sync_helper_exists():
    block = c3_block()

    assert "function syncAionGoalLoopWorkflowCanvasVisibleHeaderNow" in block
    assert "getAionWorkflowCanvasHeaderBusinessLabel()" in block
    assert "querySelector" in block
    assert ".aion-workflow-breadcrumb span" in block
    assert "textContent = label" in block


def test_phase_c3_stage_helper_calls_visible_header_sync():
    b1_start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1")
    b1_end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", b1_start)
    block = APP_JS[b1_start:b1_end]

    assert "syncAionGoalLoopWorkflowCanvasVisibleHeaderNow();" in block
    assert "setTimeout(syncAionGoalLoopWorkflowCanvasVisibleHeaderNow, 0);" in block


def test_phase_c3_does_not_create_new_canvas_or_pilot():
    block = c3_block().lower()

    forbidden = [
        "function renderaiongoalloopcanvas",
        "data-aion-goal-loop-canvas-root",
        "new aionpilot",
        "fetch(",
        "localstorage.setitem",
        "state.activetab",
    ]

    for token in forbidden:
        assert token not in block

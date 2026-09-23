from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    marker = f"function {name}"
    start = APP_JS.index(marker)
    next_function = APP_JS.find("\nfunction ", start + len(marker))
    if next_function == -1:
        return APP_JS[start:]
    return APP_JS[start:next_function]


def test_phase_b6_header_business_label_helper_exists_and_prefers_goal_loop_identity():
    block = function_block("getAionWorkflowCanvasHeaderBusinessLabel")

    assert "window.__aionGoalLoopWorkflowGraph?.business_container" in block
    assert "window.__aionGoalLoopCanvasContract?.business_id" in block
    assert "window.__aionWorkflowGraph?.goal_loop_contract?.business_id" in block
    assert "window.__aionWorkflowGraph?.business_container" in block
    assert "getAionWorkflowBusinessContainerId()" in block

    goal_loop_index = block.index("window.__aionGoalLoopWorkflowGraph?.business_container")
    fallback_index = block.index("getAionWorkflowBusinessContainerId()")
    assert goal_loop_index < fallback_index


def test_phase_b6_visible_workflow_canvas_header_uses_helper_directly():
    assert '${escapeHtml(getAionWorkflowCanvasHeaderBusinessLabel())}' in APP_JS
    assert '${escapeHtml(workflowBusinessLabel)}' not in APP_JS
    assert '${escapeHtml(state.workspaceId || "costa_conexion")}' not in APP_JS
    assert '${escapeHtml(state.workspaceId || "costa-conexion")}' not in APP_JS


def test_phase_b6_goal_loop_identity_still_locked():
    assert "function getAionWorkflowBusinessContainerId" in APP_JS
    assert "window.__aionGoalLoopWorkflowGraph?.business_container" in APP_JS
    assert "window.__aionGoalLoopCanvasContract?.business_id" in APP_JS
    assert "window.__aionWorkflowGraph?.goal_loop_contract?.business_id" in APP_JS

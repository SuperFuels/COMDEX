from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    marker = f"function {name}"
    start = APP_JS.index(marker)
    next_function = APP_JS.find("\nfunction ", start + len(marker))
    if next_function == -1:
        return APP_JS[start:]
    return APP_JS[start:next_function]


def test_phase_b5_workflow_business_container_prefers_goal_loop_graph_identity():
    block = function_block("getAionWorkflowBusinessContainerId")

    assert "window.__aionGoalLoopWorkflowGraph?.business_container" in block
    assert "window.__aionGoalLoopCanvasContract?.business_id" in block
    assert "window.__aionWorkflowGraph?.business_container" in block
    assert "window.__aionWorkflowGraph?.goal_loop_contract?.business_id" in block

    goal_loop_index = block.index("window.__aionGoalLoopWorkflowGraph?.business_container")
    old_workspace_index = block.index("window.__aionWorkspaceId")
    assert goal_loop_index < old_workspace_index


def test_phase_b5_goal_loop_graph_prevents_old_business_load_override():
    block = function_block("maybeLoadAionWorkflowFromBusinessContainerOnce")

    assert 'window.__aionWorkflowGraph?.canvas_type === "goal_loop"' in block
    assert 'window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"' in block
    assert "return;" in block


def test_phase_b5_goal_loop_sample_identity_is_sample_business():
    assert 'business_id: "sample_business"' in APP_JS
    assert 'workspace_id: "workspace_sample_business"' in APP_JS
    assert "business_container: businessId" in APP_JS


def test_phase_b5_no_goal_loop_home_fixed_or_costa_defaults():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1: Contract + Existing Canvas Adapter")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */", start)
    block = APP_JS[start:end].lower()

    assert "home_fixed" not in block
    assert "home fixed" not in block
    assert "costa-conexion" not in block
    assert "costa_conexion" not in block

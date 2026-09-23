from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_phase_d1_department_canvas_link_helpers_exist():
    build_block = function_block("buildAionGoalLoopDepartmentCanvasLinks")
    apply_block = function_block("applyAionGoalLoopDepartmentCanvasLinks")

    assert "department_child_canvases" in build_block
    assert "department_progress_rollup" in build_block
    assert "master_canvas_id" in build_block
    assert "parent_goal_loop_id" in build_block
    assert "open_department_canvas_action" in build_block
    assert "open_department_canvas" in build_block

    assert "safeGraph.department_child_canvases" in apply_block
    assert "safeGraph.department_progress_rollup" in apply_block
    assert "safeGraph.department_canvas_link_policy" in apply_block


def test_phase_d1_graph_builder_attaches_child_canvas_metadata():
    block = function_block("buildAionGoalLoopWorkflowGraph")

    assert "buildAionGoalLoopDepartmentCanvasLinks" in block
    assert "departmentCanvasLinks" in block
    assert "department_child_canvases: departmentCanvasLinks.child_canvases" in block
    assert "department_progress_rollup: departmentCanvasLinks.department_progress_rollup" in block
    assert "department_canvas_link_policy" in block
    assert "return applyAionGoalLoopDepartmentCanvasLinks(graph, departmentCanvasLinks)" in block


def test_phase_d1_department_assignment_nodes_can_open_child_canvas():
    block = function_block("buildAionGoalLoopWorkflowGraph")

    assert "type: \"department_assignment\"" in block
    assert "child_canvas_id" in block
    assert "parent_canvas_id" in block
    assert "open_department_canvas_action" in block


def test_phase_d1_child_canvas_policy_is_preview_safe():
    block = function_block("buildAionGoalLoopDepartmentCanvasLinks")

    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "route_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "execution_required: false" in block


def test_phase_d1_no_second_canvas_or_second_pilot():
    block = APP_JS[
        APP_JS.index("/* AION GOAL LOOP CANVAS PHASE D1"):
        APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE D1 */")
    ]

    forbidden = block.lower()
    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
    assert "uses_existing_workflow_canvas: true" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

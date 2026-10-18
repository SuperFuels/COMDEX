from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block(marker):
    start = APP_JS.index(marker)
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE D2 */", start)
    return APP_JS[start:end]


def test_phase_d2_helpers_exist_and_read_active_goal_loop_graph():
    block = phase_block("/* AION GOAL LOOP CANVAS PHASE D2")

    assert "function getAionActiveGoalLoopGraphForDepartmentContext" in block
    assert "function buildAionGoalLoopDepartmentPilotContextMap" in block
    assert "function getAionActiveGoalLoopDepartmentContext" in block
    assert "function renderAionDepartmentPilotGoalLoopContextPanel" in block
    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block
    assert "goal_loop_contract" in block


def test_phase_d2_extracts_department_specific_goal_loop_nodes():
    block = function_block("buildAionGoalLoopDepartmentPilotContextMap")

    assert "department_child_canvases" in block
    assert "department_progress_rollup" in block
    assert "department_assignment" in block
    assert "department_sub_goal" in block
    assert "department_plan" in block
    assert "agent_task" in block
    assert "measurement_plan" in block
    assert "execution_result" in block
    assert "evaluation" in block
    assert "ab_test" in block


def test_phase_d2_department_context_is_preview_safe_and_uses_existing_pilot():
    block = phase_block("/* AION GOAL LOOP CANVAS PHASE D2")

    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "route_mutation_required: false" in block
    assert "uses_existing_department_pilot: true" in block
    assert "creates_second_pilot: false" in block
    assert "creates_second_canvas: false" in block


def test_phase_d2_renderer_exposes_visible_department_goal_loop_context_panel():
    block = function_block("renderAionDepartmentPilotGoalLoopContextPanel")

    assert 'data-aion-goal-loop-department-pilot-context="true"' in block
    assert 'data-aion-goal-loop-department-business-label="true"' in block
    assert 'data-aion-goal-loop-department-board-goal="true"' in block
    assert 'data-aion-goal-loop-department-sub-goal="true"' in block
    assert 'data-aion-goal-loop-department-node-count="true"' in block
    assert 'data-aion-goal-loop-department-progress="true"' in block
    assert 'data-aion-goal-loop-department-safety="true"' in block
    assert "No live execution, customer message, booking or payment" in block


def test_phase_d2_is_mounted_inside_existing_department_pilot_surfaces():
    assert "${renderAionDepartmentPilotGoalLoopContextPanel(departmentKey)}" in APP_JS
    assert "${renderAionDepartmentPilotGoalLoopContextPanel(key)}" in APP_JS

    primary_index = APP_JS.index("${renderAionDepartmentPilotGoalLoopContextPanel(departmentKey)}")
    phase25f_primary_index = APP_JS.rfind("${renderAionDepartmentPilotPhase25FPanel(departmentKey)}", 0, primary_index)
    assert phase25f_primary_index != -1
    assert phase25f_primary_index < primary_index

    scoped_index = APP_JS.index("${renderAionDepartmentPilotGoalLoopContextPanel(key)}")
    phase25f_scoped_index = APP_JS.rfind("${renderAionDepartmentPilotPhase25FPanel(key)}", 0, scoped_index)
    assert phase25f_scoped_index != -1
    assert phase25f_scoped_index < scoped_index


def test_phase_d2_no_new_pilot_or_canvas_engine():
    block = phase_block("/* AION GOAL LOOP CANVAS PHASE D2")

    forbidden = block.lower()
    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
    assert "create_event" not in forbidden
    assert "send_email" not in forbidden
    assert "booking_created: true" not in forbidden
    assert "payment_created: true" not in forbidden

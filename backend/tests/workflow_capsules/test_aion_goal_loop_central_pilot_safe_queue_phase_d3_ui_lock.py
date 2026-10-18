from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE D3")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE D3 */", start)
    return APP_JS[start:end]


def test_phase_d3_helpers_exist_and_read_active_goal_loop_graph():
    block = phase_block()

    assert "function getAionActiveGoalLoopGraphForCentralPilotQueue" in block
    assert "function buildAionGoalLoopCentralPilotTaskQueue" in block
    assert "function getAionGoalLoopCentralPilotTaskQueue" in block
    assert "function renderAionGoalLoopCentralPilotTaskQueuePanel" in block
    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block
    assert "goal_loop_contract" in block


def test_phase_d3_extracts_agent_task_nodes_and_groups_by_department():
    block = function_block("buildAionGoalLoopCentralPilotTaskQueue")

    assert "agent_task" in block
    assert "goal_loop_graph_agent_task" in block
    assert "grouped_by_department" in block
    assert "normaliseAionDepartmentPilotKey" in block
    assert "getAionActiveGoalLoopDepartmentContext" in block
    assert "department_child_canvas_id" in block


def test_phase_d3_queue_is_preview_safe_and_approval_required():
    block = phase_block()

    assert "preview_only: true" in block
    assert "approval_required: true" in block
    assert "execution_blocked: true" in block
    assert "no_live_external_action: true" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "persistence_required: false" in block
    assert "route_mutation_required: false" in block


def test_phase_d3_renderer_has_visible_central_queue_panel():
    block = function_block("renderAionGoalLoopCentralPilotTaskQueuePanel")

    assert 'data-aion-goal-loop-central-pilot-safe-queue="true"' in block
    assert 'data-aion-goal-loop-central-business-label="true"' in block
    assert 'data-aion-goal-loop-central-board-goal="true"' in block
    assert 'data-aion-goal-loop-central-task-count="true"' in block
    assert 'data-aion-goal-loop-central-safety="true"' in block
    assert 'data-aion-goal-loop-central-grouped-tasks="true"' in block
    assert 'data-aion-goal-loop-central-preview-boundary="true"' in block
    assert "No live external side effects" in block


def test_phase_d3_is_mounted_inside_existing_central_pilot_area():
    assert "${renderAionCentralApprovedBoardroomActionsPanel(getAionPilotCockpitSnapshot()?.pilot_state?.plan)}" in APP_JS
    assert "${renderAionGoalLoopCentralPilotTaskQueuePanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    approved_index = APP_JS.index("${renderAionCentralApprovedBoardroomActionsPanel(getAionPilotCockpitSnapshot()?.pilot_state?.plan)}")
    d3_index = APP_JS.index("${renderAionGoalLoopCentralPilotTaskQueuePanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert approved_index < d3_index < cockpit_index


def test_phase_d3_no_second_pilot_canvas_or_live_side_effects():
    block = phase_block()
    forbidden = block.lower()

    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "booking_created: true" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "creates_second_pilot: false" in block
    assert "creates_second_canvas: false" in block
    assert "uses_existing_central_pilot: true" in block

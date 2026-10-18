from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE D4")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE D4 */", start)
    return APP_JS[start:end]


def test_phase_d4_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopDepartmentTaskQueueWritebackPatch" in block
    assert "function previewAionGoalLoopDepartmentTaskQueueWriteback" in block
    assert "function renderAionGoalLoopDepartmentTaskQueueWritebackPanel" in block
    assert "AION_GOAL_LOOP_DEPARTMENT_TASK_STATUS_VALUES" in block


def test_phase_d4_task_status_values_are_locked():
    block = phase_block()

    for status in [
        "staged",
        "awaiting_approval",
        "approved",
        "running",
        "blocked",
        "completed",
        "failed",
    ]:
        assert status in block


def test_phase_d4_builds_department_ledger_patch_preview_from_central_queue():
    block = function_block("buildAionGoalLoopDepartmentTaskQueueWritebackPatch")

    assert "getAionGoalLoopCentralPilotTaskQueue" in block
    assert "grouped_by_department" in block
    assert "getAionDepartmentLedgerEntry" in block
    assert "ledger_patch_preview" in block
    assert "goal_loop_graph_patch_preview" in block
    assert "progress_rollup_patch" in block
    assert "node_status_updates" in block
    assert "goal_loop_central_pilot_safe_queue" in block
    assert "goal_loop_graph_agent_task" in block


def test_phase_d4_preview_is_safe_and_does_not_mutate_ledger():
    block = phase_block()

    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "ledger_mutation_required: false" in block
    assert "route_mutation_required: false" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "uses_existing_department_ledger: true" in block
    assert "creates_second_pilot: false" in block
    assert "creates_second_canvas: false" in block

    forbidden = block.lower()
    assert "updateaiondepartmentintelligence(" not in forbidden
    assert "saveaioncentralpilotqueue(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden


def test_phase_d4_renderer_exposes_visible_writeback_preview_panel():
    block = function_block("renderAionGoalLoopDepartmentTaskQueueWritebackPanel")

    assert 'data-aion-goal-loop-department-task-writeback-preview="true"' in block
    assert 'data-aion-goal-loop-writeback-business-label="true"' in block
    assert 'data-aion-goal-loop-writeback-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-writeback-department-count="true"' in block
    assert 'data-aion-goal-loop-writeback-task-count="true"' in block
    assert 'data-aion-goal-loop-writeback-patches="true"' in block
    assert 'data-aion-goal-loop-writeback-preview-boundary="true"' in block
    assert "No ledger mutation" in block


def test_phase_d4_is_mounted_after_d3_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopCentralPilotTaskQueuePanel()}" in APP_JS
    assert "${renderAionGoalLoopDepartmentTaskQueueWritebackPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    d3_index = APP_JS.index("${renderAionGoalLoopCentralPilotTaskQueuePanel()}")
    d4_index = APP_JS.index("${renderAionGoalLoopDepartmentTaskQueueWritebackPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert d3_index < d4_index < cockpit_index

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def o13n_block():
    start = APP_JS.index("BEGIN AION O13N BOARDROOM DRIVEN DEPARTMENT GOAL SHEET DOCUMENTS")
    end = APP_JS.index("END AION O13N BOARDROOM DRIVEN DEPARTMENT GOAL SHEET DOCUMENTS")
    return APP_JS[start:end]


def test_o13n_installed_after_o13m():
    assert "BEGIN AION O13M RICH DEPARTMENT GOAL SHEET NODE DOCUMENTS" in APP_JS
    assert "BEGIN AION O13N BOARDROOM DRIVEN DEPARTMENT GOAL SHEET DOCUMENTS" in APP_JS
    assert APP_JS.index("BEGIN AION O13N BOARDROOM DRIVEN DEPARTMENT GOAL SHEET DOCUMENTS") > APP_JS.index("BEGIN AION O13M RICH DEPARTMENT GOAL SHEET NODE DOCUMENTS")


def test_o13n_documents_are_boardroom_driven_not_static_final_plans():
    block = o13n_block()

    assert "generated_from_boardroom" in block
    assert "boardroom_outcome_linked" in block
    assert "department_discovery_linked" in block
    assert "discovery_required" in block
    assert "waiting_for_department_discovery_and_boardroom_strategy" in block
    assert "placeholder_shell_only" in block
    assert "not_final_plan" in block


def test_o13n_covers_all_department_goal_based_node_types():
    block = o13n_block()

    for node_type in [
        "department_goal",
        "department_plan",
        "pilot_task_queue",
        "department_pilot_tasks",
        "department_measurement",
        "measurement",
        "department_evidence_feedback",
        "evidence_back_to_boardroom",
        "evidence_feedback",
    ]:
        assert node_type in block


def test_o13n_uses_real_sources_when_available():
    block = o13n_block()

    assert "getBoardroomOutcomeO13N" in block
    assert "getDepartmentDiscoveryO13N" in block
    assert "hasRealBoardroomOutcomeO13N" in block
    assert "hasRealDepartmentDiscoveryO13N" in block
    assert "window.__aionDepartmentDiscoveryByDepartment" in block
    assert "window.__aionGoalLoopDepartmentDiscovery" in block


def test_o13n_preempts_older_thin_o13k_o13m_routes():
    block = o13n_block()

    assert '["pointerdown", "mousedown", "click", "dblclick"]' in block
    assert "window.addEventListener(eventName, routeDepartmentNodeO13N, true)" in block
    assert "event.stopImmediatePropagation" in block
    assert "aion-o13k-department-goal-sheet-node-preview" in block
    assert "aion-o13m-department-goal-sheet-node-document" in block


def test_o13n_keeps_preview_safety_and_existing_canvas_pilot_contract():
    block = o13n_block()

    assert "preview_only: true" in block
    assert "execution_allowed_now: false" in block
    assert "connector_call_required: false" in block
    assert "external_side_effects: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block
    assert "Existing canvas only. Existing Pilot only." in block

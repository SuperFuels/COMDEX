from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13K DEPARTMENT GOAL SHEET NODE PREVIEW ROUTER")
    end = APP_JS.index("END AION O13K DEPARTMENT GOAL SHEET NODE PREVIEW ROUTER", start)
    return APP_JS[start:end]


def test_o13k_installed():
    b = block()
    assert "installAionO13KDepartmentGoalSheetNodePreviewRouter" in b
    assert "window.__aionO13KDepartmentGoalSheetNodePreviewRouterInstalled" in b


def test_o13k_centres_o13d_pilot_preview_panel():
    b = block()
    assert "#aion-o13d-live-agents-pilot-preview" in b
    assert "left: 50% !important" in b
    assert "top: 50% !important" in b
    assert "transform: translate(-50%, -50%) !important" in b
    assert "bottom: auto !important" in b


def test_o13k_intercepts_department_goal_sheet_nodes_before_generic_editor():
    b = block()
    assert '["pointerdown", "mousedown", "click", "dblclick"]' in b
    assert 'document.addEventListener(eventName, handleDepartmentGoalSheetNodeClickO13K, true)' in b
    assert 'event.stopImmediatePropagation()' in b
    assert 'closeGenericWorkflowNodeEditorO13K()' in b


def test_o13k_targets_department_goal_sheet_graph_only():
    b = block()
    assert "isDepartmentGoalSheetGraphO13K" in b
    assert 'canvasType === "department_goal_sheet"' in b
    assert 'workflowId.includes("_goal_sheet")' in b


def test_o13k_replaces_generic_parameters_with_preview_panel():
    b = block()
    assert "aion-o13k-department-goal-sheet-node-preview" in b
    assert "Department Goal Sheet" in b
    assert "Preview lock" in b
    assert "No live execution, no booking, no payment, no customer message, no connector call." in b
    assert "WHAT KIND OF STEP IS THIS" in b


def test_o13k_recognises_existing_department_node_types():
    b = block()
    for node_type in [
        "department_goal",
        "department_plan",
        "pilot_task_queue",
        "measurement",
        "evidence_feedback",
    ]:
        assert node_type in b

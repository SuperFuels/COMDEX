from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def o13m_block():
    start = APP_JS.index("BEGIN AION O13M RICH DEPARTMENT GOAL SHEET NODE DOCUMENTS")
    end = APP_JS.index("END AION O13M RICH DEPARTMENT GOAL SHEET NODE DOCUMENTS", start)
    return APP_JS[start:end]


def test_o13m_installs_rich_department_document_modal():
    block = o13m_block()

    assert "aion-o13m-department-goal-sheet-node-document" in block
    assert "aion.department_goal_sheet_document.v1" in block
    assert "Department Goal Sheet ·" in block
    assert "Preview lock" in block


def test_o13m_covers_all_department_node_types():
    block = o13m_block()

    assert "department_goal" in block
    assert "department_plan" in block
    assert "department_pilot_tasks" in block
    assert "pilot_task_queue" in block
    assert "department_measurement" in block
    assert "department_evidence_feedback" in block
    assert "evidence_back_to_boardroom" in block


def test_o13m_covers_all_departments_with_specific_content():
    block = o13m_block()

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert department in block

    assert "Convert generated demand into sales opportunities and revenue" in block
    assert "Check cost, margin, pricing and cash impact" in block
    assert "Turn approved goals into safe fulfilment planning" in block
    assert "Protect customer experience" in block
    assert "Create qualified demand" in block


def test_o13m_intercepts_department_nodes_before_generic_editor():
    block = o13m_block()

    assert 'document.addEventListener("click"' in block
    assert "event.stopImmediatePropagation" in block
    assert "[data-aion-workflow-node-id]" in block
    assert "openDepartmentDocumentO13M(nodeId)" in block
    assert "window.__aionWorkflowInspectorOpen = false" in block


def test_o13m_keeps_preview_safety_contract():
    block = o13m_block()

    assert "execution_allowed_now: false" in block
    assert "connector_call_required: false" in block
    assert "external_side_effects: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "customer_message_sent: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

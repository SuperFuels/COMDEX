from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O14A BOARDROOM PACKAGE TO DEPARTMENT PILOT INBOX")
    end = APP_JS.index("END AION O14A BOARDROOM PACKAGE TO DEPARTMENT PILOT INBOX")
    return APP_JS[start:end]


def test_o14a_installed_and_exports_bridge():
    b = block()

    assert "aion.boardroom_to_department_package.v1" in b
    assert "aionStageBoardroomPackagesToDepartmentPilotsO14A" in b
    assert "aionGetDepartmentBoardroomPackageO14A" in b
    assert "aionGetDepartmentPilotBoardroomStatusO14A" in b


def test_o14a_writes_to_department_intelligence_inbox():
    b = block()

    assert "window.aion.departmentIntelligence" in b
    assert "ledger.inbox" in b
    assert "ledger.goal_loop_assignment" in b
    assert "ledger.active_boardroom_package" in b
    assert "ledger.boardroom_summary" in b


def test_o14a_covers_all_core_departments():
    b = block()

    for dept in ["marketing", "sales", "finance", "operations", "support"]:
        assert dept in b


def test_o14a_package_has_assignment_and_required_discovery():
    b = block()

    assert "package_type: \"department_goal_assignment\"" in b
    assert "required_discovery" in b
    assert "assignment" in b
    assert "expected_output" in b
    assert "evidence_target" in b


def test_o14a_preview_safety_contract_locked():
    b = block()

    assert "preview_only: true" in b
    assert "execution_allowed_now: false" in b
    assert "connector_call_required: false" in b
    assert "external_side_effects: false" in b
    assert "booking_created: false" in b
    assert "payment_created: false" in b
    assert "customer_message_sent: false" in b
    assert "creates_second_canvas: false" in b
    assert "creates_second_pilot: false" in b

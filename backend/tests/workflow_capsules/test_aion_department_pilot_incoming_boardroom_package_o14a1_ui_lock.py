from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O14A1 DEPARTMENT PILOT INCOMING BOARDROOM PACKAGE UI")
    end = APP_JS.index("END AION O14A1 DEPARTMENT PILOT INCOMING BOARDROOM PACKAGE UI")
    return APP_JS[start:end]


def test_o14a1_installs_department_pilot_package_panel():
    b = block()

    assert "Incoming Boardroom Package" in b
    assert "aion-o14a1-incoming-boardroom-package-panel" in b
    assert "aionMountDepartmentPilotIncomingBoardroomPackageO14A1" in b


def test_o14a1_reads_o14a_package_bridge():
    b = block()

    assert "aionGetDepartmentBoardroomPackageO14A" in b
    assert "active_boardroom_package" in b
    assert "goal_loop_assignment" in b
    assert "__aionO14ABoardroomDepartmentPackages" in b


def test_o14a1_displays_assignment_contract_fields():
    b = block()

    for token in [
        "Package type",
        "Target Pilot",
        "Parent Boardroom goal",
        "Child Goal Sheet",
        "Evidence target",
        "Required discovery",
        "Expected outputs",
    ]:
        assert token in b


def test_o14a1_has_actions_without_live_execution():
    b = block()

    assert "Focus discovery" in b
    assert "Open linked Goal Sheet" in b
    assert "Refresh package" in b
    assert "Preview only" in b
    assert "does not execute tasks" in b


def test_o14a1_covers_all_departments():
    b = block()

    for dept in ["marketing", "sales", "finance", "operations", "support"]:
        assert dept in b

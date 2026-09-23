from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O14A2 DEPARTMENT GOAL LOOP CONTEXT PACKAGE SYNC")
    end = APP_JS.index("END AION O14A2 DEPARTMENT GOAL LOOP CONTEXT PACKAGE SYNC")
    return APP_JS[start:end]


def test_o14a2_installs_active_goal_loop_context_panel():
    b = block()

    assert "aion-o14a2-active-goal-loop-context-panel" in b
    assert "Active Boardroom assignment linked" in b
    assert "aionMountDepartmentGoalLoopContextFromPackageO14A2" in b


def test_o14a2_replaces_stale_no_assignment_context():
    b = block()

    assert "No Boardroom goal staged" in b
    assert "No active Goal Loop assignment" in b
    assert "no_goal_loop_assignment" in b
    assert "data-aion-o14a2-stale-goal-loop-context-hidden" in b


def test_o14a2_renders_package_context_fields():
    b = block()

    for token in [
        "Business",
        "Boardroom Goal",
        "Department Sub-goal",
        "Child canvas link",
        "Graph Context",
        "Assignment",
        "Plan",
        "Metrics",
    ]:
        assert token in b


def test_o14a2_reads_o14a_package():
    b = block()

    assert "aionGetDepartmentBoardroomPackageO14A" in b
    assert "active_boardroom_package" in b
    assert "__aionO14ABoardroomDepartmentPackages" in b


def test_o14a2_preview_safety_text_present():
    b = block()

    assert "blocked from live execution" in b
    assert "customer messages" in b
    assert "bookings" in b
    assert "payments" in b
    assert "connector calls" in b

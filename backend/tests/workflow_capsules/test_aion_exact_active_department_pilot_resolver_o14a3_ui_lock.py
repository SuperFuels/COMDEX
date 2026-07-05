from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O14A3 EXACT ACTIVE DEPARTMENT PILOT RESOLVER")
    end = APP_JS.index("END AION O14A3 EXACT ACTIVE DEPARTMENT PILOT RESOLVER")
    return APP_JS[start:end]


def test_o14a3_installed_and_exports_resolver():
    b = block()

    assert "aionResolveActiveDepartmentPilotO14A3" in b
    assert "aionRemountDepartmentPilotPackageForActiveDepartmentO14A3" in b
    assert "exact active Department Pilot resolver" in b


def test_o14a3_ignores_existing_injected_package_panels():
    b = block()

    assert "strippedPageTextO14A3" in b
    assert "aion-o14a1-incoming-boardroom-package-panel" in b
    assert "aion-o14a2-active-goal-loop-context-panel" in b
    assert "clone.querySelector" in b


def test_o14a3_detects_department_from_workspace_text_not_stale_package():
    b = block()

    assert "fromWorkspaceHeadingO14A3" in b
    assert "total\\s+runs" in b
    assert "next step:" in b
    assert "pilot discovery" in b
    assert "aion\\.departmentintelligence" in b


def test_o14a3_removes_wrong_department_panels():
    b = block()

    assert "removeWrongDepartmentPanelsO14A3" in b
    assert "panelDepartment !== activeDepartment" in b
    assert "panel.remove()" in b


def test_o14a3_wraps_o14a1_and_o14a2_mounts():
    b = block()

    assert "aionMountDepartmentPilotIncomingBoardroomPackageO14A1" in b
    assert "aionMountDepartmentGoalLoopContextFromPackageO14A2" in b
    assert "__aionO14A3Wrapped" in b

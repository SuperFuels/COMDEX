from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O14A4 STABLE DEPARTMENT PILOT PACKAGE DOCK")
    end = APP_JS.index("END AION O14A4 STABLE DEPARTMENT PILOT PACKAGE DOCK")
    return APP_JS[start:end]


def test_o14a4_installs_stable_package_dock():
    b = block()

    assert "aion-o14a4-department-pilot-package-dock" in b
    assert "Department Pilot Package Dock" in b
    assert "aionMountDepartmentPilotPackageDockO14A4" in b


def test_o14a4_removes_old_off_page_panels():
    b = block()

    assert "aion-o14a1-incoming-boardroom-package-panel" in b
    assert "aion-o14a2-active-goal-loop-context-panel" in b
    assert "removeOldPanelsO14A4" in b


def test_o14a4_constrains_width_to_avoid_sidebar_overlap():
    b = block()

    assert "max-width: calc(100vw - 112px)" in b
    assert "overflow: hidden" in b
    assert "box-sizing: border-box" in b


def test_o14a4_renders_all_contract_fields():
    b = block()

    for token in [
        "Source",
        "Target Pilot",
        "Child Goal Sheet",
        "Graph Context",
        "Boardroom Goal",
        "Next Action",
        "Required Discovery",
        "Expected Outputs",
    ]:
        assert token in b


def test_o14a4_preview_safety_locked():
    b = block()

    assert "Preview only" in b
    assert "no task execution" in b
    assert "connector calls" in b
    assert "payments" in b
    assert "bookings" in b

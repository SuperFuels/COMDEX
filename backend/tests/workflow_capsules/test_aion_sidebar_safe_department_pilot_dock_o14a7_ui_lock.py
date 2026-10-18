from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def block():
    text = APP.read_text(encoding="utf-8")
    start = text.index("/* BEGIN AION O14A7 SIDEBAR SAFE DEPARTMENT PILOT DOCK POSITION LOCK */")
    end = text.index("/* END AION O14A7 SIDEBAR SAFE DEPARTMENT PILOT DOCK POSITION LOCK */", start)
    return text[start:end]

def test_o14a7_marker_exists():
    b = block()
    assert "O14A.7 exact fix" in b
    assert "sidebar-safe Department Pilot Package Dock position lock installed" in b

def test_o14a7_offsets_dock_right_of_sidebar():
    b = block()
    assert "left: 72px" in b
    assert "width: calc(100vw - 112px)" in b
    assert "max-width: calc(100vw - 112px)" in b
    assert "margin-left: 0" in b

def test_o14a7_targets_existing_o14a4_dock():
    b = block()
    assert "aion-o14a4-department-pilot-package-dock" in b
    assert "data-aion-o14a4-package-dock" in b
    assert "aionMountDepartmentPilotPackageDockO14A4" in b

def test_o14a7_keeps_existing_pilot_boundary():
    b = block()
    assert "Existing Pilot only" in b
    assert "Existing canvas only" in b
    assert "Preview-only" in b

def test_o14a7_exports_runtime_debug_function():
    b = block()
    assert "aionApplySidebarSafeDepartmentPilotDockPositionO14A7" in b

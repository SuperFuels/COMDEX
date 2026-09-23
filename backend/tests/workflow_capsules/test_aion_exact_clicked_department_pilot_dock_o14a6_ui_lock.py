from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def block():
    text = APP.read_text(encoding="utf-8")
    start = text.index("/* BEGIN AION O14A6 EXACT CLICKED DEPARTMENT PILOT DOCK ROUTER */")
    end = text.index("/* END AION O14A6 EXACT CLICKED DEPARTMENT PILOT DOCK ROUTER */")
    return text[start:end]

def test_o14a6_installed_after_o14a4():
    text = APP.read_text(encoding="utf-8")
    assert text.index("/* BEGIN AION O14A4 STABLE DEPARTMENT PILOT PACKAGE DOCK */") < text.index("/* BEGIN AION O14A6 EXACT CLICKED DEPARTMENT PILOT DOCK ROUTER */")
    assert "[AION] O14A.6 exact clicked Department Pilot dock router installed" in text

def test_o14a6_overrides_resolver_and_prefers_clicked_department():
    b = block()
    assert "window.aionResolveActiveDepartmentPilotO14A3 = function resolveActiveDepartmentPilotO14A6" in b
    assert "__aionO14A6ClickedDepartmentPilot" in b
    assert "clickedDepartmentButtonO14A6" in b
    assert "setActiveDepartmentO14A6(dept)" in b

def test_o14a6_does_not_use_freezing_patterns():
    b = block()
    assert "setInterval" not in b
    assert "cloneNode" not in b
    assert "document.body.cloneNode" not in b

def test_o14a6_sidebar_safe_padding_locked():
    b = block()
    assert "margin-left: 72px" in b
    assert "width: calc(100% - 96px)" in b
    assert "max-width: calc(100vw - 112px)" in b

def test_o14a6_remounts_existing_o14a4_only():
    b = block()
    assert "aionMountDepartmentPilotPackageDockO14A4" in b
    assert "aionStageBoardroomPackagesToDepartmentPilotsO14A" in b
    assert "Existing Pilot" in b

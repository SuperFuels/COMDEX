from pathlib import Path

APP = Path("desktop/mac/src/app.js")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")

def block():
    text = APP.read_text(encoding="utf-8")
    start = text.index("/* BEGIN AION O15A1 HIDE LEGACY FLOATING GOAL SHEET ACTION */")
    end = text.index("/* END AION O15A1 HIDE LEGACY FLOATING GOAL SHEET ACTION */", start)
    return text[start:end]

def test_o15a_bad_spatial_patch_removed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O15A DEPARTMENT 1TO1 SPATIAL ROOMS" not in text
    assert "aionMountDepartmentSpatialRoomsO15A" not in text
    assert "requestRenderWithDepartmentSpatialMountO15A" not in text

def test_o15a1_only_hides_legacy_floating_goal_sheet_action():
    b = block()
    assert "#aion-o12b-boardroom-action" in b
    assert ".aion-o12b-boardroom-action" in b
    assert "display: none !important" in b
    assert "pointer-events: none !important" in b

def test_o15a1_no_freezing_patterns():
    b = block()
    assert "setInterval" not in b
    assert "querySelectorAll" not in b
    assert "requestRender" not in b
    assert "addEventListener" not in b

def test_renderer_restored_to_stable_forced_seats():
    text = RENDERER.read_text(encoding="utf-8")
    assert "forcedSeatSource" not in text
    assert "soloDepartmentKey" not in text
    assert "departmentSoloKey" not in text
    assert 'const forcedSeats = [' in text
    assert '["finance", "Finance", "Financial Stewardship"' in text

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"
APP = ROOT / "desktop" / "mac" / "src" / "app.js"

def test_o15j_real_agent_live_state_remains_on_interactive_seats_without_visual_clutter():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15J REAL AGENT LIVE STATUS BADGE LOCK" in text
    assert "group.userData.liveStatusText = liveStatusText" in text
    assert "liveStatusPlate" not in text
    assert '"ALWAYS ON"' in text
    assert '"LIVE"' in text

def test_o15j_redundant_provider_rail_removed():
    text = APP.read_text(encoding="utf-8")
    assert "O15J REMOVE REDUNDANT PROVIDER RAIL LOCK" in text
    assert "aionO15EBoardroomProviderRail" in text
    assert "aionO15DBoardroomConnectedProviderRail" in text
    assert "display: none !important" in text
    assert "window.__debugAionO15JProviderRailRemoved" in text

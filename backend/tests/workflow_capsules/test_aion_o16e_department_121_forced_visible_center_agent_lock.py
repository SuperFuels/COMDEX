from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16e_forced_visible_center_agent_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16E DEPARTMENT 121 FORCED VISIBLE CENTER AGENT LOCK" in text
    assert "isDepartment121ForcedSeatO16E" in text
    assert "const seatX = isDepartment121ForcedSeatO16E ? 0 : x" in text
    assert "const seatZ = isDepartment121ForcedSeatO16E ? -8.15 : z" in text

def test_o16e_forced_visible_seats_enabled_for_121():
    text = RENDERER.read_text(encoding="utf-8")
    assert 'if (teamMode !== "board") {' in text
    assert "addForcedVisibleExecutiveSeats(root, options || {})" in text
    assert "&& !isDepartment121ModeO16C" not in text

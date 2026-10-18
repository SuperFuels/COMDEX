from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16d_visible_center_agent_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16D DEPARTMENT 121 VISIBLE CENTER AGENT LOCK" in text
    # Department portraits now use their dedicated renderer, so the legacy
    # room seat is intentionally parked outside the shared boardroom scene.
    assert '? { x: 0, z: -40 }' in text

def test_o16d_camera_targets_visible_agent_zone():
    text = RENDERER.read_text(encoding="utf-8")
    assert "radius: 4.6" in text
    assert "targetZ: -6.4" in text

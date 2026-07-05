from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16d_visible_center_agent_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16D DEPARTMENT 121 VISIBLE CENTER AGENT LOCK" in text
    assert '? { x: 0, z: -8.25 }' in text

def test_o16d_camera_targets_visible_agent_zone():
    text = RENDERER.read_text(encoding="utf-8")
    assert "radius: 10.8" in text
    assert "targetZ: -7.2" in text

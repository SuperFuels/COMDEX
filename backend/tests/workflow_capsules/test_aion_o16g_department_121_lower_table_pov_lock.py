from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16g_lower_table_pov_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16G DEPARTMENT 121 LOWER TABLE POV LOCK" in text
    assert "radius: 10.9" in text
    assert "y: 3.35" in text
    assert "targetY: 1.35" in text
    assert "targetZ: -7.65" in text

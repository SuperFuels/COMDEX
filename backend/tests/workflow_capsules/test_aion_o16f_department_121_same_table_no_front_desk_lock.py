from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16f_same_table_no_front_desk_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16F DEPARTMENT 121 SAME TABLE CAMERA NO FRONT DESK LOCK" in text
    assert "isDepartment121SameTableViewO16F" in text
    assert "console.visible = !isDepartment121SameTableViewO16F" in text
    assert "switchButton.visible = !isDepartment121SameTableViewO16F" in text
    assert "switchText.visible = !isDepartment121SameTableViewO16F" in text

def test_o16f_department_121_camera_is_raised():
    text = RENDERER.read_text(encoding="utf-8")
    assert "radius: 11.6" in text
    assert "y: 4.35" in text
    assert "targetZ: -7.8" in text

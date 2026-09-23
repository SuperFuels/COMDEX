from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o16c_department_121_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O16C DEPARTMENT 121 CAMERA CENTER AGENT LOCK" in text
    assert "isDepartment121ModeO16C" in text
    assert "isDepartment121CameraO16C" in text

def test_o16c_department_121_agent_is_centered_not_seat_arc():
    text = RENDERER.read_text(encoding="utf-8")
    assert '? { x: 0, z: -4.15 }' in text
    assert 'seatArc(index, seatsToRender.length)' in text
    assert '&& !isDepartment121ModeO16C' in text

def test_o16c_department_121_camera_is_closer():
    text = RENDERER.read_text(encoding="utf-8")
    assert "function setupSimpleOrbitControls(renderer, camera, options = {})" in text
    assert "radius: 10.2" in text
    assert "targetZ: -4.85" in text
    assert "setupSimpleOrbitControls(renderer, camera, opts)" in text
    assert "o16cDepartment121Camera" in text

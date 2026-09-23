from pathlib import Path

APP = Path("desktop/mac/src/app.js")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")

def test_o18c5_app_portrait_window_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18C5 REAL AGENT PORTRAIT WINDOW LOCK" in text
    assert "aion-o18c5-real-agent-portrait-window-style" in text
    assert "__debugAionO18C5RealAgentPortraitWindow" in text
    assert "real_canvas_exists" in text

def test_o18c5_retracts_fake_hud_and_keeps_real_canvas():
    text = APP.read_text(encoding="utf-8")
    assert '[data-aion-o18b-agent-figure="true"]' in text
    assert "display:none !important" in text
    assert "opacity:1 !important" in text
    assert "filter:none !important" in text
    assert "MARKETING AGENT" in text

def test_o18c5_renderer_portrait_camera_values_locked():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18C5 REAL AGENT PORTRAIT CAMERA LOCK" in text
    assert "radius: 4.85" in text
    assert "phi: 0.018" in text
    assert "y: 2.22" in text
    assert "targetY: 1.55" in text
    assert "targetZ: -8.15" in text

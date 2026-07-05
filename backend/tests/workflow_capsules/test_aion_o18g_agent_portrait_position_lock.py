from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18g_renderer_position_fix_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18G AGENT PORTRAIT BODY POSITION LOCK" in text
    assert "camera.position.set(0, 1.72, 7.2)" in text
    assert "camera.lookAt(0, 1.42, 0)" in text
    assert "agentRoot.position.set(0, -0.08, 0)" in text
    assert "scale: 0.92" in text
    assert "label.visible = false" in text

def test_o18g_app_frame_tune_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18G FACETIME FRAME VISIBILITY TUNE LOCK" in text
    assert "aion-o18g-facetime-frame-visibility-tune-style" in text
    assert "__debugAionO18GFaceTimeAgentPosition" in text
    assert "transform:none !important" in text

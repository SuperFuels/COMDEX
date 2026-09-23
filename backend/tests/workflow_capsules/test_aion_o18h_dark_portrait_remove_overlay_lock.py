from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18h_renderer_dark_portrait_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18H DARK PORTRAIT REMOVE OVERLAY LOCK" in text
    assert "scene.background = new THREE.Color(0x020617)" in text
    assert "halo.visible = false" in text
    assert "brightens the real robot_agent.glb material" in text or "Brightens the real agent" in text or "mat.color.setHex(0xf8fafc)" in text
    assert "mat.color.setHex(0xf8fafc)" in text

def test_o18h_app_dark_frame_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18H DARK FACETIME FRAME STYLE LOCK" in text
    assert "aion-o18h-dark-facetime-frame-style" in text
    assert "__debugAionO18HDarkPortraitFrame" in text
    assert "background:#020617" in text
    assert "display:none !important" in text

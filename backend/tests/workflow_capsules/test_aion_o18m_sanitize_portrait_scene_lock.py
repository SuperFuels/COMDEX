from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18m_renderer_sanitizer_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18M SANITIZE PORTRAIT WEBGL SCENE LOCK" in text
    assert "function sanitizePortraitSceneO18M" in text
    assert "ringgeometry" in text
    assert "circlegeometry" in text
    assert "isLargeDarkOverlay" in text
    assert "node.visible = false" in text

def test_o18m_app_style_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18M PORTRAIT FRAME FINAL DARK LOCK" in text
    assert "aion-o18m-portrait-frame-final-dark-style" in text
    assert "__debugAionO18MPortraitSceneSanitizer" in text
    assert "background-image:none !important" in text

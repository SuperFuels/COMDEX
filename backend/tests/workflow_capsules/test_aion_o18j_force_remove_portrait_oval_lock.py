from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18j_renderer_force_remove_oval_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18J FORCE REMOVE PORTRAIT OVAL LOCK" in text
    assert "removed portrait halo/ring mesh completely" in text or "removed halo reference" in text
    assert "removed O18I backGlow overlay completely" in text or "removed scene.add(backGlow)" in text
    assert "camera.position.set(0, 1.72, 6.4)" in text
    assert "agentRoot.position.set(0, 0.08, 0)" in text

def test_o18j_app_css_force_hide_oval_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18J FORCE HIDE CSS OVAL LOCK" in text
    assert "aion-o18j-force-hide-css-oval-style" in text
    assert "__debugAionO18JForceRemovePortraitOval" in text
    assert "background:transparent !important" in text
    assert "mix-blend-mode:normal !important" in text

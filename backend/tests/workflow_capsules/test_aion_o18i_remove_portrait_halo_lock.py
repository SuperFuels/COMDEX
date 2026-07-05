from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18i_renderer_halo_removed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18I REMOVE PORTRAIT HALO COMPLETELY LOCK" in text
    assert "portrait halo removed completely" in text or "Removes the giant circular/halo overlay" in text or "Removes the giant circular/halo overlay" in text
    assert "subtle rectangular video-call glow" in text
    assert "backGlow" in text

def test_o18i_app_css_no_oval():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18I DARK FRAME NO OVAL CSS LOCK" in text
    assert "aion-o18i-dark-frame-no-oval-style" in text
    assert "__debugAionO18INoPortraitHalo" in text
    assert "width:0 !important" in text
    assert "height:0 !important" in text

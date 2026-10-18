from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def portrait_fn(text):
    start = text.index("function mountAionO18FRealAgentOnlyPortrait")
    end = text.index("  function updateBoardroom", start)
    return text[start:end]

def test_o18n2_backdrop_removed_from_portrait_function():
    text = RENDERER.read_text(encoding="utf-8")
    fn = portrait_fn(text)
    assert "BEGIN AION O18N2 ROBUST REMOVE PORTRAIT BACKDROP LOCK" in text
    assert "O18N2_BACKDROP_REMOVED" in fn
    assert "const backdrop" not in fn
    assert "scene.add(backdrop)" not in fn
    assert "const halo" not in fn
    assert "scene.add(halo)" not in fn
    assert "const backGlow" not in fn
    assert "scene.add(backGlow)" not in fn

def test_o18n2_app_plain_css_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18N2 FORCE PLAIN PORTRAIT CSS LOCK" in text
    assert "aion-o18n2-force-plain-portrait-css" in text
    assert "__debugAionO18N2PlainPortrait" in text

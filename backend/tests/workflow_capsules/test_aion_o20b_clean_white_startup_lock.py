from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o20b_clean_white_startup_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O20B CLEAN WHITE STARTUP STYLE LOCK" in text
    assert "BEGIN AION O20B CLEAN WHITE STARTUP DEBUG LOCK" in text
    assert "__debugAionO20BCleanWhiteStartup" in text


def test_o20b_renderer_is_clean_white_not_dark_hud():
    text = APP.read_text(encoding="utf-8")
    fn = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("\n}", 1)[0]
    assert "aion-o20b-clean-startup" in fn
    assert "aion-o20b-main" in fn
    assert "aion-o20b-orb" in fn
    assert "aion-o20a-side" not in fn
    assert "aion-o20a-topbar" not in fn
    assert "Finance gate" not in fn
    assert "Ops gate" not in fn
    assert "Sales gate" not in fn
    assert "Evidence" not in fn
    assert "Local runtime" not in fn
    assert "Approval-gated" not in fn
    assert "No live actions" not in fn
    assert "Evidence first" not in fn


def test_o20b_preserves_routes_and_voice_start_hooks():
    text = APP.read_text(encoding="utf-8")
    fn = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("\n}", 1)[0]
    assert 'data-aion-o19m-start="true"' in fn
    assert 'data-aion-o20b-start="true"' in fn
    assert 'data-aion-business-entry-mode="small_business_growth"' in fn
    assert 'data-aion-business-entry-mode="founder_build_idea"' in fn
    assert 'data-aion-business-entry-mode="founder_generate_idea"' in fn
    assert "I have a business" in fn
    assert "I have an idea" in fn
    assert "Generate an idea" in fn


def test_o20b_css_forces_white_full_width_surface():
    text = APP.read_text(encoding="utf-8")
    assert "background: #ffffff !important" in text
    assert "width: min(1280px, 100%)" in text
    assert "min-height: calc(100vh - 120px)" in text
    assert "display: none !important" in text

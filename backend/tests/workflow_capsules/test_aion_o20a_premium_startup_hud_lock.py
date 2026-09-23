from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o20a_superseded_by_o20b_clean_white_startup():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O20B CLEAN WHITE STARTUP STYLE LOCK" in text
    assert "BEGIN AION O20B CLEAN WHITE STARTUP DEBUG LOCK" in text
    assert "aion-o20b-clean-startup" in text
    assert "__debugAionO20BCleanWhiteStartup" in text


def test_o20a_dark_hud_removed_after_o20b_decision():
    text = APP.read_text(encoding="utf-8")
    fn = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("\n}", 1)[0]
    assert "aion-o20a-startup-hud" not in fn
    assert "aion-o20a-side" not in fn
    assert "aion-o20a-topbar" not in fn
    assert "Finance gate" not in fn
    assert "Ops gate" not in fn
    assert "Sales gate" not in fn


def test_o20a_voice_and_startup_contract_still_preserved_through_o20b():
    text = APP.read_text(encoding="utf-8")
    fn = text.split("function renderBusinessEntryModeSelector()", 1)[1].split("\n}", 1)[0]
    assert 'data-aion-o19m-start="true"' in fn
    assert 'data-aion-business-entry-mode="small_business_growth"' in fn
    assert 'data-aion-business-entry-mode="founder_build_idea"' in fn
    assert 'data-aion-business-entry-mode="founder_generate_idea"' in fn
    assert "I have a business" in fn
    assert "I have an idea" in fn
    assert "Generate an idea" in fn


def test_o20a_visual_intent_kept_but_restyled_white():
    text = APP.read_text(encoding="utf-8")
    assert "aion-o20b-rings" in text
    assert "aion-o20b-orb" in text
    assert "aion-o20b-clean-startup" in text
    assert "background: #ffffff !important" in text

from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19f_real_start_selector_restored():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19F RESTORE REAL BUSINESS ENTRY SELECTOR LOCK" in text
    assert "function renderBusinessEntryModeSelector()" in text
    assert "I have an idea" in text
    assert "I have a business" in text
    assert "Choose a starting point" in text
    assert "O14G emergency recovery" not in text

def test_o19f_small_business_route_renders_selector():
    text = APP.read_text(encoding="utf-8")
    assert 'if (state.activeTab === "small_business_foundation") {' in text
    assert "return renderBusinessEntryModeSelector();" in text
    assert "O19F: small_business_foundation is restored as the real startup selector route" in text
    assert "O19F: old redirect disabled. small_business_foundation renders the real startup selector again." in text

def test_o19f_business_context_subtab_setter_restored():
    text = APP.read_text(encoding="utf-8")
    assert "function setAionBusinessContextSubtab(" in text
    assert "window.setAionBusinessContextSubtab = setAionBusinessContextSubtab" in text
    assert "data-aion-business-context-subtab" in text

def test_o19f_console_route_helpers_exist():
    text = APP.read_text(encoding="utf-8")
    assert "aionOpenStartupSelectorO19F" in text
    assert "__debugAionO19FRestoreRealStartSelector" in text
    assert 'state.activeTab = "small_business_foundation"' in text

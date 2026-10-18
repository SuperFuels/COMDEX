from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def _entry_selector_block() -> str:
    start = APP_JS.index("function renderBusinessEntryModeSelector")
    end = APP_JS.index("if (!window.__aionPhase24ABusinessEntryHandlersInstalled)", start)
    return APP_JS[start:end]


def _render_main_surface_block() -> str:
    start = APP_JS.index("function renderMainSurface")
    end = APP_JS.index("if (state.activeTab === \"vault\")", start)
    return APP_JS[start:end]


def test_phase24a_business_entry_selector_exists():
    assert "function renderBusinessEntryModeSelector" in APP_JS
    assert "data-aion-phase24a-business-entry-selector" in APP_JS
    assert "What are we building?" in APP_JS


def test_phase24a_has_three_starting_paths():
    block = _entry_selector_block()

    assert 'data-aion-business-entry-mode="founder_generate_idea"' in block
    assert 'data-aion-business-entry-mode="founder_build_idea"' in block
    assert 'data-aion-business-entry-mode="small_business_growth"' in block

    assert "Generate me an idea" in block
    assert "I have an idea" in block
    assert "I have a business" in block


def test_phase24a_founder_options_are_grouped_under_one_founder_section():
    block = _entry_selector_block()

    assert "Founder Mode" in block
    assert "Start something new" in block
    assert "For idea-stage founders, early concepts, MVPs and first campaigns." in block
    assert block.index("Founder Mode") < block.index("Generate me an idea")
    assert block.index("Founder Mode") < block.index("I have an idea")


def test_phase24a_small_business_option_has_sharper_positioning():
    block = _entry_selector_block()

    assert "Small Business Mode" in block
    assert "Grow and automate" in block
    assert "For existing businesses with customers, services, revenue, channels, assets or repeatable work." in block
    assert "Let’s automate it and grow it." in block


def test_phase24a_black_card_titles_are_white_but_section_titles_are_black():
    block = _entry_selector_block()

    assert "color:#111111 !important" in block
    assert "-webkit-text-fill-color:#111111 !important" in block
    assert "color:#ffffff !important" in block
    assert "-webkit-text-fill-color:#ffffff !important" in block
    assert "aion-business-entry-card-title" in block


def test_phase24a_entry_cards_force_black_button_background():
    block = _entry_selector_block()

    assert "background:#111111 !important" in block
    assert "background-color:#111111 !important" in block


def test_phase24a_reset_start_has_border_again():
    block = _entry_selector_block()

    assert "data-aion-business-entry-reset" in block
    assert "border:1px solid rgba(17,17,17,0.22)" in block
    assert "border-radius:12px" in block
    assert "background:#ffffff" in block
    assert "Reset start" in block


def test_phase24a_business_entry_mode_persists_in_state():
    assert "function getAionBusinessEntryMode" in APP_JS
    assert "function setAionBusinessEntryMode" in APP_JS
    assert "state.businessEntryMode = value;" in APP_JS
    assert "state.businessEntryModeSelectedAt" in APP_JS


def test_phase24a_render_main_surface_gates_before_normal_app_tabs():
    block = _render_main_surface_block()
    assert "if (!getAionBusinessEntryMode())" in APP_JS
    assert "return renderBusinessEntryModeSelector();" in APP_JS
    assert APP_JS.index("return renderBusinessEntryModeSelector();") < APP_JS.index('if (state.activeTab === "vault")')


def test_phase24a_entry_selection_routes_to_focused_starting_surfaces():
    assert 'if (value === "founder_generate_idea")' in APP_JS
    assert 'state.activeTab = "aion_chat";' in APP_JS
    assert 'if (value === "founder_build_idea")' in APP_JS
    assert 'state.activeTab = "brand_foundation";' in APP_JS
    assert 'if (value === "small_business_growth")' in APP_JS


def test_phase24a_entry_handler_is_installed_once_and_rerenders():
    assert "__aionPhase24ABusinessEntryHandlersInstalled" in APP_JS
    assert "[data-aion-business-entry-mode]" in APP_JS
    assert "setAionBusinessEntryMode(selected);" in APP_JS
    assert "resetAionBusinessEntryMode();" in APP_JS
    assert "render();" in APP_JS


def test_phase24a_workflow_tab_strip_is_removed_from_startup_and_non_workflow_pages():
    block = _entry_selector_block()
    render_block = _render_main_surface_block()

    assert 'document.getElementById("aion-glyph-workflow-top-tabs-v2")?.remove();' in block
    assert 'document.getElementById("aion-glyph-workflow-top-tabs-v2")?.remove();' in render_block
    assert "body.aion-phase24a-entry-visible #aion-glyph-workflow-top-tabs-v2" in block


def test_phase24a_render_main_surface_toggles_chrome_classes_from_active_tab():
    block = _render_main_surface_block()

    assert 'document.body.classList.toggle("aion-phase24a-entry-visible", !getAionBusinessEntryMode())' in block
    assert 'document.body.classList.toggle("aion-phase19c-workflow-visible", activeTabForChrome === "operations_flow")' in block
    assert "Do not infer workflow chrome visibility from stale workflow DOM." in block

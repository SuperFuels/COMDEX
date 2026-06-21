from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def _entry_selector_block() -> str:
    start = APP_JS.index("function renderBusinessEntryModeSelector")
    end = APP_JS.index("if (!window.__aionPhase24ABusinessEntryHandlersInstalled)", start)
    return APP_JS[start:end]


def _render_main_surface_block() -> str:
    start = APP_JS.index("function renderMainSurface")
    end = APP_JS.index("function buildLiveAgentCards", start)
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


def test_phase24a_business_entry_mode_is_session_first_not_local_storage_skipped():
    assert "function getAionBusinessEntryMode" in APP_JS
    assert "function setAionBusinessEntryMode" in APP_JS
    assert "state.businessEntryMode = value;" in APP_JS
    assert "state.businessEntryModeSelectedAt" in APP_JS
    assert 'window.localStorage?.setItem?.("aion.businessEntryMode", value)' not in APP_JS
    assert 'window.localStorage?.getItem?.("aion.businessEntryMode")' not in APP_JS


def test_phase24a_render_main_surface_gates_before_normal_app_tabs():
    block = _render_main_surface_block()

    assert "if (!getAionBusinessEntryMode())" in block
    assert "return renderBusinessEntryModeSelector();" in block
    assert block.index("return renderBusinessEntryModeSelector();") < block.index('if (state.activeTab === "vault")')


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
    assert "render();" in APP_JS


def test_phase24a_founder_options_are_grouped_under_one_founder_section():
    block = _entry_selector_block()

    assert "data-aion-phase24a-founder-mode-section" in block
    assert "Start something new" in block
    assert "Generate me an idea" in block
    assert "I have an idea" in block
    assert "AION suggests opportunities and builds the first test plan." in block
    assert "Shape the offer, brand, MVP assets and first campaign." in block
    assert "No idea yet" not in block
    assert "Idea ready" not in block
    assert block.count("Founder Mode") == 1


def test_phase24a_small_business_option_has_sharper_positioning():
    block = _entry_selector_block()

    assert "data-aion-phase24a-small-business-mode-section" in block
    assert "Grow and automate" in block
    assert "I have a business" in block
    assert "Let’s automate it and grow it." in block
    assert "For existing businesses with customers, services, revenue, channels, assets or repeatable work." in block
    assert "focused loops across Marketing, Sales, Finance, Operations, Support and Builder" not in block


def test_phase24a_entry_cards_force_black_button_background():
    block = _entry_selector_block()

    assert "aion-business-entry-card" in block
    assert "background:#111111 !important;" in block
    assert "background-color:#111111 !important;" in block
    assert "color:#ffffff !important;" in block


def test_phase24a_business_entry_has_reset_start_control():
    assert "function resetAionBusinessEntryMode" in APP_JS
    assert "data-aion-business-entry-reset" in APP_JS
    assert "Reset start" in APP_JS
    assert "resetAionBusinessEntryMode();" in APP_JS


def test_phase24a_polished_layout_uses_balanced_two_column_mode_sections():
    block = _entry_selector_block()

    assert "grid-template-columns:minmax(0, 1.15fr) minmax(0, 1fr)" in block
    assert "border-radius:16px" in block
    assert "border-radius:14px" in block
    assert "font-family:Inter" in block
    assert "font-weight:500" in block


def test_phase24a_main_workflow_chrome_is_hidden_on_entry_screen():
    block = _entry_selector_block()

    assert 'document.getElementById("aion-glyph-workflow-top-tabs-v2")?.remove();' in block
    assert 'document.body.classList.add("aion-phase24a-entry-visible");' in block


def test_phase24a_reset_start_is_deemphasised_text_button():
    block = _entry_selector_block()

    assert "Reset start" in block
    assert "text-transform:uppercase" in block
    assert "border:1px solid rgba(17,17,17,0.22)" in block
    assert "border-radius:12px" in block
    assert "background:#ffffff" in block


def test_phase24a_startup_hides_body_appended_workflow_tabbar_by_id():
    block = _entry_selector_block()

    assert "#aion-glyph-workflow-top-tabs-v2" in block
    assert "visibility:hidden !important;" in block
    assert "pointer-events:none !important;" in block


def test_phase24a_reset_start_has_border_again():
    block = _entry_selector_block()

    assert "data-aion-business-entry-reset" in block
    assert "border:1px solid rgba(17,17,17,0.22)" in block
    assert "border-radius:12px" in block
    assert "background:#ffffff" in block


def test_phase24a_workflow_tab_visibility_uses_active_app_tab_not_stale_dom():
    assert "Phase 24A.5:" in APP_JS
    assert "Do not infer visibility from stale workflow DOM." in APP_JS
    assert 'stateTab === "operations_flow"' in APP_JS
    assert 'document.querySelector(\n      ".aion-workflow-canvas-shell' not in APP_JS


def test_phase24a_founder_generate_button_is_black_again():
    block = _entry_selector_block()
    start = block.index('data-aion-business-entry-mode="founder_generate_idea"')
    end = block.index('data-aion-business-entry-mode="founder_build_idea"', start)
    button = block[start:end]

    assert "background:#111111 !important;" in button
    assert "background-color:#111111 !important;" in button
    assert "color:#ffffff !important;" in button
    assert "GENERATE ME AN IDEA" not in button


def test_phase24a_startup_removes_body_appended_workflow_tabbar():
    block = _entry_selector_block()

    assert 'document.getElementById("aion-glyph-workflow-top-tabs-v2")?.remove();' in block
    assert ".aion-glyph-workflow-top-tabs" in block
    assert ".aion-master-glyph-workflow-tabs" in block
    assert ".aion-glyph-tabs-strip" in block


def test_phase24a_render_main_surface_toggles_chrome_classes_from_active_tab():
    block = _render_main_surface_block()

    assert 'document.body.classList.toggle("aion-phase24a-entry-visible", !getAionBusinessEntryMode())' in block
    assert 'document.body.classList.toggle("aion-phase19c-workflow-visible", activeTabForChrome === "operations_flow")' in block


def test_phase24a_startup_black_card_titles_are_visible_white():
    block = _entry_selector_block()

    assert "Generate me an idea" in block
    assert "I have an idea" in block
    assert "I have a business" in block
    assert "color:#ffffff !important;" in block
    assert "background:#111111 !important;" in block

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text()


def _foundation_block() -> str:
    start = APP_JS.index("function renderSmallBusinessFoundationSetupSurface")
    end = APP_JS.index("if (!window.__aionPhase24BSmallBusinessFoundationHandlersInstalled)", start)
    return APP_JS[start:end]


def _render_main_surface_block() -> str:
    start = APP_JS.index("function renderMainSurface")
    end = APP_JS.index("function buildLiveAgentCards", start)
    return APP_JS[start:end]


def test_phase24b_small_business_foundation_surface_exists():
    block = _foundation_block()

    assert "data-aion-phase24b-small-business-foundation" in block
    assert "Small Business Mode" in block
    assert "Build your business foundation" in block
    assert "Required quick start" in block
    assert "Optional enrichment" in block


def test_phase24b_only_small_set_of_required_fields_blocks_progress():
    assert "function getSmallBusinessFoundationMissingRequired" in APP_JS
    assert '"business_name", "Business name"' in APP_JS
    assert '"business_type", "Business type"' in APP_JS
    assert '"industry", "Industry"' in APP_JS
    assert '"service_area", "Location / service area"' in APP_JS
    assert '"primary_goal", "Main goal"' in APP_JS


def test_phase24b_foundation_form_has_required_and_optional_context():
    block = _foundation_block()

    assert 'renderSmallBusinessFoundationInput("business_name"' in block
    assert 'data-aion-phase24b-foundation-field="website"' in block
    assert 'renderSmallBusinessFoundationSelect("business_type"' in block
    assert 'renderSmallBusinessFoundationInput("industry"' in block
    assert 'renderSmallBusinessFoundationInput("service_area"' in block
    assert 'renderSmallBusinessFoundationSelect("primary_goal"' in block
    assert 'renderSmallBusinessFoundationInput("social_accounts"' in block
    assert 'renderSmallBusinessFoundationTextarea("products_services"' in block
    assert 'renderSmallBusinessFoundationTextarea("target_customers"' in block
    assert 'renderSmallBusinessFoundationTextarea("current_tools"' in block
    assert 'renderSmallBusinessFoundationTextarea("current_pain_points"' in block

    assert 'data-aion-phase24b-foundation-field="${escapeHtml(name)}"' in APP_JS


def test_phase24b_primary_setup_options_are_visible_but_no_right_column():
    block = _foundation_block()

    assert 'data-aion-phase24b-import-option="website"' in block
    assert 'data-aion-phase24b-import-option="documents"' not in block
    assert "Website scan" in block
    assert "Upload documents" not in block
    assert "Other setup options" not in block
    assert "Foundation preview" not in block
    assert "<aside" not in block


def test_phase24b_entry_mode_routes_to_foundation_setup():
    assert 'if (value === "small_business_growth")' in APP_JS
    assert 'state.activeTab = "small_business_foundation";' in APP_JS


def test_phase24b_render_main_surface_mounts_foundation_setup():
    block = _render_main_surface_block()

    assert 'if (state.activeTab === "small_business_foundation")' in block
    assert "return renderSmallBusinessFoundationSetupSurface();" in block
    assert block.index('if (state.activeTab === "small_business_foundation")') < block.index('if (state.activeTab === "vault")')


def test_phase24b_foundation_generates_preview_before_departments():
    assert "data-aion-phase24b-generate-foundation" in APP_JS
    assert "state.smallBusinessFoundationPreviewReady" in APP_JS
    assert "data-aion-phase24b-continue-departments" in APP_JS
    assert 'state.activeTab = "boardroom";' in APP_JS
    assert 'state.smallBusinessFoundationBoardroomStarted = true;' in APP_JS


def test_phase24b_no_live_external_side_effects_in_setup_ui():
    block = _foundation_block().lower()

    assert "publish" not in block
    assert "send email" not in block
    assert "spend" not in block
    assert "book job" not in block


def test_phase24b_foundation_screen_does_not_render_global_app_tabs():
    block = _foundation_block()

    assert "${renderAppTabs()}" not in block
    assert "data-aion-phase24b-hide-global-chrome" in block
    assert "body.aion-phase24a-entry-visible #aion-glyph-workflow-top-tabs-v2" in block


def test_phase24b_website_scan_is_primary_recommended_setup_path():
    block = _foundation_block()

    assert "Recommended fastest setup" in block
    assert "Recommended" in block
    assert "Website scan" in block
    assert "Paste your website and AION can pre-fill services, tone, location, calls to action and business context for you to check." in block
    assert block.index("Website scan") < block.index("Business name")
    assert block.index("Website scan") < block.index("Business name")


def test_phase24b_entry_mode_persists_through_local_storage():
    assert 'window.localStorage?.setItem("aion.businessEntryMode", value)' in APP_JS
    assert 'window.localStorage?.getItem("aion.businessEntryMode")' in APP_JS
    assert 'window.localStorage?.removeItem("aion.businessEntryMode")' in APP_JS


def test_phase24b_website_scan_card_is_forced_visible_dark():
    block = _foundation_block()

    assert "background:#111111 !important" in block
    assert "background-color:#111111 !important" in block
    assert "color:#ffffff !important" in block
    assert "-webkit-text-fill-color:#ffffff !important" in block
    assert "Recommended fastest setup" in block


def test_phase24b_primary_setup_box_contains_website_and_documents():
    block = _foundation_block()

    assert "data-aion-phase24b-primary-setup-box" in block
    assert "Website scan" in block
    assert 'data-aion-phase24b-foundation-field="website"' in block
    assert "Scan website" in block
    assert "Upload documents" not in block
    assert "Brochures, price lists, old adverts and brand files." not in block
    assert block.index("Website scan") < block.index("Business name")


def test_phase24b_foundation_form_is_full_width_single_column_shell():
    block = _foundation_block()

    assert "grid-template-columns:minmax(0, 1fr)" in block
    assert "width:100%;" in block
    assert "grid-template-columns:minmax(0, 1.05fr) minmax(360px, 0.95fr)" not in block


def test_phase24b_additional_information_section_captures_key_details():
    block = _foundation_block()

    assert "Additional information to keep" in block
    assert 'renderSmallBusinessFoundationInput("contact_email"' in block
    assert 'renderSmallBusinessFoundationInput("phone_number"' in block
    assert 'renderSmallBusinessFoundationInput("business_address"' in block
    assert 'renderSmallBusinessFoundationInput("opening_hours"' in block
    assert 'renderSmallBusinessFoundationTextarea("pricing_notes"' in block
    assert 'renderSmallBusinessFoundationTextarea("brand_notes"' in block
    assert 'renderSmallBusinessFoundationTextarea("reviews_or_proof"' in block
    assert 'renderSmallBusinessFoundationTextarea("extra_notes"' in block


def test_phase24b_frontend_scan_calls_backend_extractor_not_hardcoded_business():
    assert "async function applySmallBusinessWebsiteScanDraft" in APP_JS
    assert "/api/local-node/aion/small-business/website-scan" in APP_JS
    assert "await fetch" in APP_JS
    assert "Object.entries(fields).forEach" in APP_JS

    helper_start = APP_JS.index("async function applySmallBusinessWebsiteScanDraft")
    helper_end = APP_JS.index("function renderSmallBusinessFoundationSetupSurface", helper_start)
    helper = APP_JS[helper_start:helper_end].lower()

    assert "homefixed" not in helper
    assert "home fixed" not in helper
    assert "property maintenance and outdoor living improvements" not in helper


def test_phase24b_frontend_scan_calls_openai_backend_without_business_hardcoding():
    assert "async function applySmallBusinessWebsiteScanDraft" in APP_JS
    assert "/api/local-node/aion/small-business/website-scan" in APP_JS
    assert "await fetch" in APP_JS
    assert "Object.entries(fields).ForEach" not in APP_JS
    assert "Object.entries(fields).forEach" in APP_JS

    helper_start = APP_JS.index("async function applySmallBusinessWebsiteScanDraft")
    helper_end = APP_JS.index("function renderSmallBusinessFoundationSetupSurface", helper_start)
    helper = APP_JS[helper_start:helper_end].lower()

    assert "homefixed" not in helper
    assert "home fixed" not in helper
    assert "property maintenance and outdoor living improvements" not in helper


def test_phase24b_generic_small_business_setup_does_not_default_to_home_fixed():
    block = _foundation_block()

    assert "e.g. Your business name" in block
    assert "\"Home Fixed\"" not in block
    assert "Property maintenance and outdoor living improvements" not in block


def test_phase24b_website_scan_uses_local_backend_absolute_url():
    assert "function getAionLocalBackendBaseUrl" in APP_JS
    assert "function buildAionLocalBackendUrl" in APP_JS
    assert "http://127.0.0.1:8000" in APP_JS
    assert "/api/local-node/aion/small-business/website-scan" in APP_JS
    assert 'fetch("/api/aion/small-business/website-scan"' not in APP_JS
    assert "ERR_FILE_NOT_FOUND" not in APP_JS


def test_phase24b_workflow_visibility_guard_does_not_require_scoped_state():
    start = APP_JS.index("function isWorkflowCanvasVisible")
    end = APP_JS.index("function syncWorkflowVisibilityClass", start)
    block = APP_JS[start:end]

    assert 'typeof state !== "undefined"' in block
    assert "window.__aionAppState" in block


def test_phase24b_csp_allows_local_backend_scan_connection():
    assert "http://127.0.0.1:8000" in APP_JS or "http://localhost:8000" in APP_JS
    assert "/api/local-node/aion/small-business/website-scan" in APP_JS


def test_phase24b9_website_scan_loading_state_visible():
    assert "aion-scan-spinner" in APP_JS
    assert "Scanning website" in APP_JS
    assert "AION is reading the website" in APP_JS
    assert "10–15 seconds" in APP_JS
    assert "smallBusinessFoundationWebsiteScanStatus" in APP_JS


def test_phase24b9_website_input_does_not_rerender_on_every_keypress():
    assert 'data-aion-no-live-render="true"' in APP_JS
    assert 'event.target?.closest?.("[data-aion-small-business-foundation-scan-website]")' in APP_JS
    assert 'event.target?.closest?.("[data-aion-phase24b-import-option=\\"website\\"]")' not in APP_JS
    assert "state.smallBusinessFoundationPreviewReady = false;" in APP_JS


def test_phase24b9_scan_button_has_clean_inline_alignment():
    assert "aion-small-business-website-scan-btn" in APP_JS
    assert "min-width:170px" in APP_JS
    assert "display:inline-flex" in APP_JS
    assert "align-items:center" in APP_JS
    assert "justify-content:center" in APP_JS


def test_phase24b9_scan_click_targets_button_not_input_row():
    assert 'event.target?.closest?.("[data-aion-small-business-foundation-scan-website]")' in APP_JS
    assert 'event.target?.closest?.("[data-aion-phase24b-import-option=\\\"website\\\"]")' not in APP_JS


def test_phase24b_quick_start_does_not_include_fake_upload_documents_card():
    assert 'data-aion-phase24b-import-option="documents"' not in APP_JS
    assert "Brochures, price lists, old adverts and brand files." not in APP_JS

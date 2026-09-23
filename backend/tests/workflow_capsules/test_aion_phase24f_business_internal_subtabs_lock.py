from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text()
STORE = Path("desktop/mac/src/lib/desktop-store.js").read_text()


def test_business_internal_subtabs_exist():
    assert "function renderBusinessContextSubtabs()" in APP
    assert "data-aion-business-context-subtabs" in APP
    assert 'data-aion-business-context-subtab="${escapeHtml(key)}"' in APP
    assert '"key_business_info", "Key Business Info"' in APP
    assert '"brand_foundation", "Brand Foundation"' in APP
    assert '"design_system", "Business Design System"' in APP
    assert '"sales", "Sales"' in APP
    assert '"marketing", "Marketing"' in APP
    assert '"finance", "Finance"' in APP
    assert '"operations", "Operations"' in APP
    assert '"support", "Support"' in APP


def test_brand_foundation_reconnected_inside_business_tab():
    assert "function renderBusinessBrandFoundationSubtabContent()" in APP
    assert "renderBrandFoundationSurface()" in APP
    assert '<div class="brand-foundation-layout">' in APP


def test_business_design_system_is_visual_and_canonical():
    assert "function renderBusinessDesignSystemSubtabContent()" in APP
    assert "LIVE BRAND BOARD" in APP
    assert "COLOUR PALETTE" in APP
    assert "TYPE SYSTEM" in APP
    assert "brandMap.visualIdentity.designSystem.primaryColours" in APP
    assert "brandMap.visualIdentity.designSystem.headlineFont" in APP
    assert "font-family:${escapeHtml(design.headlineFont" in APP
    assert "data-aion-brand-asset-upload" in APP
    assert "data-aion-design-scan-website" in APP
    assert "evidence_only: true" in APP


def test_live_brand_board_uses_confirmed_palette_not_tessaris_blue():
    assert "function resolveAionBrandBoardColours(" in APP
    assert 'data-aion-live-brand-board-preview="true"' in APP
    assert 'data-aion-live-brand-board-kicker="true"' in APP
    assert 'data-aion-live-brand-board-body="true"' in APP
    assert 'data-aion-live-brand-board-cta="true"' in APP
    assert "background:${boardColours.background}" in APP
    assert "color:${boardColours.foreground}" in APP
    assert "background:${boardColours.accent}" in APP
    assert "color:${boardColours.foreground} !important;-webkit-text-fill-color:${boardColours.foreground}" in APP

    design_start = APP.index("function renderBusinessDesignSystemSubtabContent()")
    design_end = APP.index("function renderBusinessBrandFoundationSubtabContent()", design_start)
    assert "background:#102a43" not in APP[design_start:design_end]


def test_department_function_tabs_store_context():
    assert "function renderBusinessDepartmentContextSubtab(" in APP
    assert "function getBusinessDepartmentContextDraft()" in APP
    assert "data-aion-business-department-context-field" in APP
    assert "data-aion-business-department-context-save" in APP
    assert "aion.businessDepartmentContextDraft" in APP


def test_department_statuses_are_specific_not_generic_only():
    assert "foundation loaded / task context ready" in APP
    assert "foundation loaded / no active handover yet" in APP
    assert "foundation loaded / no financial model yet" in APP
    assert "foundation loaded / workflow context ready" in APP
    assert "foundation loaded / customer context ready" in APP




def test_business_internal_subtabs_have_capture_click_handler_lock():
    assert "__aionPhase24FBusinessSubtabsInstalled" in APP
    assert "[data-aion-business-context-subtab]" in APP
    assert "event.preventDefault()" in APP
    assert "event.stopPropagation()" in APP
    assert 'document.addEventListener("click", (event) => {' in APP
    assert "setAionBusinessContextSubtab(value)" in APP
    assert "aion.activeBusinessContextSubtab" in APP


def test_business_internal_subtabs_lock_active_tab_to_business_context():
    assert "function getAionBusinessContextSubtab()" in APP
    assert 'function setAionBusinessContextSubtab(rawKey = "key_business_info")' in APP
    assert "state.activeBusinessContextSubtab = key" in APP
    assert 'window.localStorage?.setItem("aion.activeBusinessContextSubtab", key)' in APP
    assert 'if (typeof render === "function") render()' in APP
    assert "window.__aionBusinessContextSubtab = key" in APP
    assert "window.__aionBusinessContextSubtab ||" in APP
    assert 'state.activeTab = "business_context"' in APP
    assert "return true;" in APP
    assert "return false;" in APP

def test_business_brand_foundation_subtab_has_business_info_rows_helper():
    assert "function renderAionBusinessInfoRows(" in APP
    assert "function renderAionBusinessInfoRows(rows = [])" in APP


def test_business_brand_foundation_embedded_renderer_starts_at_brand_section_panel():
    start = APP.index("function renderBusinessBrandFoundationSubtabContent()")
    end = APP.index("function renderBusinessDepartmentContextSubtab", start)
    body = APP[start:end]

    assert "data-aion-business-brand-foundation-clean-embedded" in body
    assert "renderBrandFoundationSurface()" in body
    assert "fullHtml.indexOf(\"1. Brand Overview\")" in body
    assert "fullHtml.lastIndexOf('<div class=\"panel large-panel\"', contentStart)" in body
    assert 'fullHtml.lastIndexOf("<section", contentStart)' not in body
    assert "Do NOT search backwards" in body
    assert "renderAionBusinessKeyInformationCard()" not in body
    assert "renderDashboardMetricCard(" not in body


def test_sidebar_business_route_releases_startup_hold_and_full_renders():
    assert "window.__aionO25ABStartupRouteHold = false;" in APP
    assert 'if (typeof render === "function") render();\n    else if (typeof requestRender === "function") requestRender();' in APP


def test_business_design_system_uses_restored_scope_safe_state():
    start = APP.index("function renderAionBrandAssetCard(")
    end = APP.index("function renderBusinessBrandFoundationSubtabContent()", start)
    body = APP[start:end]

    assert "const appState = getAionRestoredAppStateSafe();" in body
    assert "appState.apiBase" in body
    assert "appState.brandAssistantProvider" in body
    assert "appState.brandFoundationState" in body
    assert "state.apiBase" not in body
    assert "state.brandAssistantProvider" not in body
    assert "state.brandFoundationState" not in body


def test_brand_map_nested_edits_sync_from_the_edited_alias():
    assert "next.brandIntelligenceMap = cloneValue(ensureObject(next.brandMap));" in STORE
    assert "next.brandMap = cloneValue(ensureObject(next.brandIntelligenceMap));" in STORE


def test_design_system_distinguishes_raw_tokens_from_confirmed_identity():
    assert "classifyAionDetectedBrandPalette" in APP
    assert "Raw CSS colours" in APP
    assert "Includes borders, forms and widgets" in APP
    assert "Detected identity proposal — confirmation required" in APP
    assert "data-aion-design-confirm-detected" in APP
    assert 'identityStatus: "detected_requires_confirmation"' in APP
    assert 'identityStatus: "confirmed_by_user"' in APP
    assert "fontRoles.heading" in APP
    assert "fontRoles.body" in APP
    assert "resolveAionBusinessBrandName" in APP

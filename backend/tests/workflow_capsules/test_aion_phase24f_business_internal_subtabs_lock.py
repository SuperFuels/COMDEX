from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text()


def test_business_internal_subtabs_exist():
    assert "function renderBusinessContextSubtabs()" in APP
    assert "data-aion-business-context-subtabs" in APP
    assert 'data-aion-business-context-subtab="${escapeHtml(key)}"' in APP
    assert '"key_business_info", "Key Business Info"' in APP
    assert '"brand_foundation", "Brand Foundation"' in APP
    assert '"sales", "Sales"' in APP
    assert '"marketing", "Marketing"' in APP
    assert '"finance", "Finance"' in APP
    assert '"operations", "Operations"' in APP
    assert '"support", "Support"' in APP


def test_brand_foundation_reconnected_inside_business_tab():
    assert "function renderBusinessBrandFoundationSubtabContent()" in APP
    assert "renderBrandFoundationSurface()" in APP
    assert '<div class="brand-foundation-layout">' in APP


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
    assert "function handleAionBusinessContextSubtabClick(" in APP
    assert "[data-aion-business-context-subtab]" in APP
    assert "event.preventDefault()" in APP
    assert "event.stopPropagation()" in APP
    assert "event.stopImmediatePropagation" in APP
    assert "document.addEventListener(\"click\", handleAionBusinessContextSubtabClick, true)" in APP
    assert "state.activeBusinessContextSubtab = key" in APP
    assert "aion.activeBusinessContextSubtab" in APP


def test_business_internal_subtabs_lock_active_tab_to_business_context():
    assert "function getAionBusinessContextSubtab()" in APP
    assert "function setAionBusinessContextSubtab(rawKey)" in APP
    assert 'state.activeTab = "business_context"' in APP
    assert 'window.localStorage?.setItem("aion.activeTab", "business_context")' in APP
    assert "requestRender(\"business-context-subtab\")" in APP
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


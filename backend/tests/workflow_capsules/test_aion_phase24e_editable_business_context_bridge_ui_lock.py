from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text()


def test_business_context_tab_uses_editable_fields():
    assert "function renderBusinessContextSurface()" in APP
    assert "function renderBusinessContextEditableInput(" in APP
    assert "function renderBusinessContextEditableTextarea(" in APP
    assert 'data-aion-business-context-field="${escapeHtml(name)}"' in APP
    assert 'renderBusinessContextEditableInput("business_name"' in APP
    assert 'renderBusinessContextEditableTextarea("products_services"' in APP
    assert 'renderBusinessContextEditableTextarea("reviews_or_proof"' in APP
    assert "data-aion-business-context-save" in APP


def test_business_context_formats_scan_objects_before_display():
    assert "function formatAionBusinessContextValue(" in APP
    assert "JSON.parse(raw)" in APP
    assert "formatAionBusinessContextValue(JSON.parse(raw))" in APP


def test_business_context_saves_back_to_live_context_sources():
    assert "function saveBusinessContextFoundationFromForm(" in APP
    assert "applySmallBusinessFoundationToBrandingAndBusinessContext(foundation)" in APP
    assert "state.businessContextFoundation" in APP
    assert "state.approvedSmallBusinessFoundation" in APP


def test_business_context_handover_remains_visible():
    assert "Department Handover Context" in APP
    assert "business-context mission map and approval chain" in APP
    assert "Context linked" in APP

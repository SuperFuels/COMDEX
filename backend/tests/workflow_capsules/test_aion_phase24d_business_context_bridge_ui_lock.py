from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text()


def test_business_tab_exists_and_branding_label_replaces_brand_foundation_label():
    assert '{ key: "business_context", label: "Business" }' in APP
    assert '{ key: "brand_foundation", label: "Branding" }' in APP


def test_startup_foundation_bridge_helpers_exist():
    assert "function getApprovedSmallBusinessFoundationContext()" in APP
    assert "function buildBrandingStateFromSmallBusinessFoundation" in APP
    assert "function applySmallBusinessFoundationToBrandingAndBusinessContext" in APP


def test_business_context_surface_renders_approved_foundation():
    assert "function renderBusinessContextSurface()" in APP
    assert "data-aion-business-context-tab" in APP
    assert "data-aion-business-foundation-summary" in APP
    assert "data-aion-branding-context-summary" in APP
    assert "data-aion-department-context-handover" in APP


def test_business_context_routes_from_main_surface():
    assert 'state.activeTab === "business_context"' in APP
    assert "return renderBusinessContextSurface();" in APP


def test_approve_foundation_promotes_to_shared_runtime_context():
    assert "applySmallBusinessFoundationToBrandingAndBusinessContext(draft);" in APP
    assert 'window.localStorage?.setItem("aion.approvedSmallBusinessFoundation"' in APP
    assert 'window.localStorage?.setItem("aion.brandFoundationState"' in APP


def test_continue_to_boardroom_carries_foundation_context():
    assert "applySmallBusinessFoundationToBrandingAndBusinessContext(getSmallBusinessFoundationDraft());" in APP
    assert 'state.activeTab = "boardroom";' in APP


def test_context_is_visible_in_pilot_boardroom_and_department_surfaces():
    assert "function renderAionBusinessContextMiniCard" in APP
    assert 'renderAionBusinessContextMiniCard("pilot")' in APP
    assert 'renderAionBusinessContextMiniCard("boardroom")' in APP
    assert "renderAionBusinessContextMiniCard(departmentKey)" in APP


def test_business_context_declares_safety_boundary():
    assert "No live external sends, public posts, payments, bookings, deployments, escrow or reputation mutation without exact approval." in APP
    assert "The model proposes work, but AION routes work through the business-context mission map and approval chain." in APP

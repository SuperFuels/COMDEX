from pathlib import Path


APP = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def test_existing_boardroom_surface_exposes_nontechnical_map_governance_controls():
    source = APP.read_text(encoding="utf-8")
    assert "Review and correct the business map" in source
    assert 'data-aion-map-fact-action="correct"' in source
    assert 'data-aion-map-relationship-action="approve"' in source
    assert "Merge duplicate" in source
    assert "Recover existing relationships" in source
    assert "confirm(\"Delete this fact from the Business Map? Its audit receipt will remain.\")" in source


def test_live_boardroom_terminal_directly_mounts_original_map_governance():
    source = APP.read_text(encoding="utf-8")
    terminal_start = source.index("function renderBoardroomCouncilSessionTerminal()")
    terminal_end = source.index("/* AION PATCH: Safe Boardroom Council Terminal wrapper v1 */", terminal_start)
    terminal = source[terminal_start:terminal_end]
    assert 'typeof window.aionRenderOriginalBusinessMapGovernanceV2 === "function"' in terminal
    assert "window.aionRenderOriginalBusinessMapGovernanceV2()" in terminal
    assert "window.aionRenderOriginalBusinessMapGovernanceV2 = renderGovernancePanel" in source

    dashboard_start = source.index("function renderBoardroomDashboardView(snapshot)")
    dashboard_end = source.index("function openDepartmentWorkspaceFromBoardroom", dashboard_start)
    dashboard = source[dashboard_start:dashboard_end]
    assert 'typeof window.aionRenderOriginalBusinessMapGovernanceV2 === "function"' in dashboard
    assert "window.aionRenderOriginalBusinessMapGovernanceV2()" in dashboard


def test_boardroom_map_projection_keeps_canonical_relationships_and_revision_checks():
    source = APP.read_text(encoding="utf-8")
    assert "relationships: Array.isArray(payload.relationships) ? payload.relationships : []" in source
    assert 'governMap("relationships/normalize-legacy"' in source
    assert "expected_revision: Number(state.payload?.revision || 0)" in source
    assert "business-map/${encodeURIComponent(businessId())}/governance/queues" in source


def test_boardroom_exposes_one_plain_language_read_only_connector_screen():
    source = APP.read_text(encoding="utf-8")
    assert "Connect your business" in source
    assert "connector-onboarding/${encodeURIComponent(businessId())}" in source
    assert 'data-aion-business-connector="${escapeHtml(card.connector_id || "")}"' in source
    assert "Imported evidence never becomes company truth until it is reviewed." in source
    assert "Credentials remain with the mother brain." in source
    assert "external_write_performed" not in source[source.index("function renderConnectorOnboarding"):source.index("function renderGovernancePanel", source.index("function renderConnectorOnboarding"))]


def test_connector_buttons_reuse_existing_authorities_and_require_a_click():
    source = APP.read_text(encoding="utf-8")
    section = source[source.index("const connectorButton ="):source.index("const toggleManager =", source.index("const connectorButton ="))]
    assert "card.connect.endpoint" in section
    assert "card.connect.http_method" in section
    assert "openExternalUrl" in section
    assert "fileTab?.click?.()" in section

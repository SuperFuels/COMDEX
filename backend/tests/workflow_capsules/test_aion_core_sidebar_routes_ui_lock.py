from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
CONTRACTS = Path("desktop/mac/src/lib/desktop-state-contracts.js").read_text(encoding="utf-8")


def test_core_sidebar_routes_are_accepted_by_the_canonical_state_contract():
    normalizer = CONTRACTS[CONTRACTS.index("function normalizeActiveTab"):CONTRACTS.index("function normalizeActiveZone")]
    assert "communications: true" in normalizer
    assert "work_schedule: true" in normalizer
    assert "business_context: true" in normalizer
    assert "dashboard: true" not in normalizer
    assert 'activeTab: "boardroom"' in CONTRACTS


def test_three_core_routes_remain_visible_sidebar_destinations():
    assert '{ key: "communications", label: "Communications" }' in APP
    assert '{ key: "work_schedule", label: "Work & Schedule" }' in APP
    assert '{ key: "business_context", label: "Business" }' in APP


def test_main_navigation_replaces_every_stale_restored_route():
    setter = APP[APP.index("function setActiveTab"):APP.index("function isAionOrganisationWorkflowTabActive")]

    assert "window.__aionForcedMainTabV2 = nextTab" in setter
    assert '"aion.forcedMainTab.v2"' in setter
    assert '"aionDesktop.activeTab"' in setter
    assert ".setItem(key, nextTab)" in setter
    assert "safeAionDesktopPatch({ activeTab: nextTab })" in setter

    canonical_router = APP[APP.index("/* AION PATCH: Sidebar Canonical Data-Tab Router v3"):APP.index("/* BEGIN AION O18AD")]
    assert 'window.addEventListener("pointerdown", claimAionCanonicalSidebarRouteV3, true)' in canonical_router
    assert 'document.addEventListener("click", claimAionCanonicalSidebarRouteV3, true)' in canonical_router

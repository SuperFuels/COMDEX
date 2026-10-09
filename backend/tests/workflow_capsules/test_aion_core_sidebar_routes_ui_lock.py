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

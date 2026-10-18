from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")
OPERATIONS_RENDERER = (ROOT / "desktop/mac/src/lib/desktop-operations-renderer.js").read_text(encoding="utf-8")


def test_operations_flow_renders_only_the_coo_command_centre() -> None:
    surface_start = APP.index("function renderOperationsFlowSurface()")
    surface_end = APP.index("function readAionBusinessFoundationStorage", surface_start)
    surface = APP[surface_start:surface_end]

    assert "renderAionCooCommandCentreV1()" in surface
    assert "operationsFlowMount" not in surface
    assert "renderOperationsFlowModeToggle()" not in surface
    assert "operating system map" not in surface


def test_coo_snapshot_uses_real_operating_ledgers_and_preserves_unknowns() -> None:
    assert "getAionExecutiveDashboardModelV1()" in APP
    assert "safeArray(state.approvals)" in APP
    assert "safeArray(state.runs)" in APP
    assert "safeArray(state.audit)" in APP
    assert "Disconnected sources remain unknown" in APP
    assert 'external_actions_taken: 0' in APP


def test_coo_loop_exposes_sweep_direct_line_and_department_drill_down() -> None:
    for marker in (
        'data-aion-coo-action="sweep"',
        'data-aion-coo-action="talk"',
        'data-aion-coo-direct-form="true"',
        "data-aion-coo-department",
        "openAionCooConversationV1",
        "runAionCooEvidenceSweepV1",
    ):
        assert marker in APP


def test_coo_command_centre_has_responsive_production_styling() -> None:
    for selector in (
        ".aion-coo-command__hero",
        ".aion-coo-command__metrics",
        ".aion-coo-command__checkins",
        ".aion-coo-command__direct",
    ):
        assert selector in STYLES
    assert "@media (max-width:760px)" in STYLES


def test_supporting_system_map_no_longer_displays_seeded_business_kpis() -> None:
    flat_start = OPERATIONS_RENDERER.index("function renderOperationsFlowHtml")
    flat_end = OPERATIONS_RENDERER.index("function bindEvents", flat_start)
    flat = OPERATIONS_RENDERER[flat_start:flat_end]
    assert "Operating system map" in flat
    assert 'metricCard("Marketing Input"' not in flat
    assert 'metricCard("Cash"' not in flat
    assert 'metricCard("Department Seats"' in flat

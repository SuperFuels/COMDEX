from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    next_fn = TEXT.find("\nfunction ", start + len(f"function {name}"))
    if next_fn == -1:
        return TEXT[start:]
    return TEXT[start:next_fn]


def test_ai_council_mounted_above_boardroom_header_and_dashboard_body():
    surface = function_block("renderBoardroomSurface")
    dashboard = function_block("renderBoardroomDashboardView")

    assert "renderAionProviderCouncilPanel()" in surface
    assert "boardroom-view-toggle" in surface
    assert "surface-header" in surface
    assert "renderAionProviderCouncilPanel()" not in dashboard
    assert surface.index("renderAionProviderCouncilPanel()") < surface.index("renderAppTabs()")
    assert surface.index("boardroom-view-toggle") < surface.index("surface-header")


def test_top_dashboard_no_longer_starts_with_pulse_strip():
    dashboard = function_block("renderBoardroomDashboardView")

    assert "renderBoardroomPulseSummaryStrip(snapshot)" not in dashboard
    assert "renderBoardroomDepartmentIntelligencePanel()" in dashboard


def test_department_ledger_contains_highlights_under_cards():
    ledger = function_block("renderBoardroomDepartmentIntelligencePanel")

    assert "Business Readiness" not in ledger
    assert "Connect the remaining departments" not in ledger
    assert "renderCompactDepartmentStatusBoard()" in ledger
    assert "renderBoardroomPulseSummaryStrip()" in ledger
    assert ledger.index("renderCompactDepartmentStatusBoard()") < ledger.index("renderBoardroomPulseSummaryStrip()")


def test_department_highlights_are_selectable_by_department_card():
    board = function_block("renderCompactDepartmentStatusBoard")

    assert "data-aion-phase25j-department-pulse-select" in board
    assert "data-aion-compact-department-card" in board


def test_department_highlight_helper_supports_business_functions():
    block = function_block("getAionDepartmentPulseSummaryItems")

    for key in ["sales", "marketing", "finance", "operations", "support"]:
        assert f'key === "{key}"' in block

    for label in ["Cash", "Revenue", "Ops", "Debtors", "Margin", "Runs"]:
        assert label in block


def test_department_highlight_click_handler_exists():
    assert "__aionPhase25JDepartmentPulseHandlersInstalled" in TEXT
    assert "setAionBoardroomSelectedDepartmentPulseKey(key)" in TEXT


def test_no_live_external_execution_added_by_layout_change():
    checked = "\n".join([
        function_block("renderBoardroomSurface"),
        function_block("renderBoardroomDashboardView"),
        function_block("renderBoardroomPulseSummaryStrip"),
        function_block("getAionDepartmentPulseSummaryItems"),
    ]).lower()

    for token in [
        "sendemail(",
        "send_email(",
        "publishad(",
        "chargecard(",
        "createbooking(",
        "live_send_enabled: true",
        "external_writes_enabled",
        "fetch(",
    ]:
        assert token not in checked

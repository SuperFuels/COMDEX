from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    next_fn = TEXT.find("\nfunction ", start + len(f"function {name}"))
    if next_fn == -1:
        return TEXT[start:]
    return TEXT[start:next_fn]


def test_boardroom_pulse_strip_helper_exists():
    strip = function_block("renderBoardroomPulseSummaryStrip")
    items = function_block("getAionDepartmentPulseSummaryItems")

    assert 'data-aion-phase25j-boardroom-pulse-strip="true"' in strip
    assert 'data-aion-phase25j-selected-department-highlights="${escapeHtml(key)}"' in strip
    for label in ["Cash", "Revenue", "Ops", "Debtors", "Margin", "Runs"]:
        assert label in items


def test_boardroom_dashboard_does_not_render_top_pulse_strip():
    block = function_block("renderBoardroomDashboardView")

    assert "renderBoardroomPulseSummaryStrip(snapshot)" not in block
    assert "renderBoardroomDepartmentIntelligencePanel()" in block


def test_department_ledger_renders_pulse_strip_under_compact_cards():
    block = function_block("renderBoardroomDepartmentIntelligencePanel")

    assert "renderCompactDepartmentStatusBoard()" in block
    assert "renderBoardroomPulseSummaryStrip()" in block
    assert block.index("renderCompactDepartmentStatusBoard()") < block.index("renderBoardroomPulseSummaryStrip()")


def test_selected_department_highlights_are_visually_linked_and_colour_coded():
    block = function_block("renderBoardroomPulseSummaryStrip")

    assert "getAionDepartmentPulseAccentColor(key)" in block
    assert "data-aion-phase25j-selected-department-connector" in block
    assert "data-aion-phase25j-selected-department-highlight-card" in block
    assert "Click a department card above to switch these business-function highlights." not in block


def test_boardroom_dashboard_removes_workspace_demand_risk_and_business_context_card():
    block = function_block("renderBoardroomDashboardView")

    assert '"Workspace"' not in block
    assert '"Demand Risk"' not in block
    assert 'renderAionBusinessContextMiniCard("boardroom")' not in block
    assert 'data-aion-boardroom-business-pulse-secondary="true"' not in block


def test_boardroom_pulse_strip_no_live_external_execution_added():
    block = function_block("renderBoardroomPulseSummaryStrip").lower()

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
        assert token not in block

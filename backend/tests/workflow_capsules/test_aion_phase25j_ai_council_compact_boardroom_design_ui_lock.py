from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    next_fn = TEXT.find("\nfunction ", start + len(f"function {name}"))
    if next_fn == -1:
        return TEXT[start:]
    return TEXT[start:next_fn]


def block_between(start_token, end_token):
    start = TEXT.index(start_token)
    end = TEXT.index(end_token, start)
    return TEXT[start:end]


def test_ai_council_visual_design_exists():
    block = function_block("renderAionProviderCouncilPanel")

    assert 'data-aion-phase25j-provider-council="true"' in block
    assert 'data-aion-provider-council-seat="${escapeHtml(provider.key)}"' in block
    assert "data-aion-provider-council-add-selected-model" in block

    for label in ["Aion", "Claude", "OpenAI", "Gemini", "Grok", "+ add"]:
        assert label in TEXT or label.lower() in TEXT.lower()


def test_ai_council_is_mounted_as_top_boardroom_panel():
    block = block_between("function renderBoardroomSurface", "function renderBoardroomAgentGrid")

    assert "renderAionProviderCouncilPanel()" in block
    assert "boardroom-view-toggle" in block
    assert "surface-header" in block
    assert block.index("renderAionProviderCouncilPanel()") < block.index("renderAppTabs()")
    assert block.index("boardroom-view-toggle") < block.index("surface-header")


def test_compact_department_board_replaces_sprawling_debug_list():
    block = function_block("renderCompactDepartmentStatusBoard")

    assert 'data-aion-phase25j-compact-department-status-board="true"' in block
    assert 'data-aion-compact-department-card="${escapeHtml(row.key)}"' in block
    assert "Shared context the council assesses before any department plan runs." in block
    assert "active ·" in block
    assert "not started" in block


def test_department_status_copy_is_user_friendly():
    block = function_block("formatAionDepartmentStatusForUser")

    assert "Discovery active" in block
    assert "Not set up" in block
    assert "Results active" in block


def test_business_readiness_panel_removed_from_department_ledger_wrapper():
    block = block_between("function renderBoardroomDepartmentIntelligencePanel", "function renderBoardroomSpatialDepartmentIntelligencePanel")

    assert "Business Readiness" not in block
    assert "Connect the remaining departments" not in block
    assert "renderCompactDepartmentStatusBoard()" in block
    assert "renderBoardroomPulseSummaryStrip()" in block


def test_no_live_external_execution_added_by_design_panel():
    checked = "\n".join([
        function_block("renderAionProviderCouncilPanel"),
        function_block("renderCompactDepartmentStatusBoard"),
        function_block("renderBoardroomDepartmentIntelligencePanel"),
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

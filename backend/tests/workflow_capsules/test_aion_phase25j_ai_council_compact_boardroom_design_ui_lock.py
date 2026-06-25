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
    assert "data-aion-provider-council-add-model" in block

    for label in ["Aion", "Claude", "OpenAI", "Gemini", "Grok", "Add model"]:
        assert label in TEXT


def test_ai_council_is_mounted_before_department_readiness():
    block = block_between("function renderBoardroomDashboardView", "function openDepartmentWorkspaceFromBoardroom")

    assert "renderAionProviderCouncilPanel()" in block
    assert "renderBoardroomDepartmentIntelligencePanel()" in block
    assert block.index("renderAionProviderCouncilPanel()") < block.index("renderBoardroomDepartmentIntelligencePanel()")


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


def test_business_readiness_panel_is_clean_wrapper():
    block = function_block("renderBoardroomDepartmentIntelligencePanel")

    assert "Business Readiness" in block
    assert "renderCompactDepartmentStatusBoard()" in block
    assert "ready_to_plan" not in block
    assert "needs_discovery" not in block
    assert "Confidence: empty" not in block


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

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def finance_route_block() -> str:
    text = read_app()

    start = text.index(
        "function "
        "routeAionBusinessTwinToFinanceOnceV2"
    )

    end = text.index(
        "/* O19F:",
        start,
    )

    return text[start:end]


def startup_owner_block() -> str:
    text = read_app()

    start = text.index(
        "function "
        "applyAionO25ABFreshStartupRouteOwner"
    )

    end = text.index(
        "function "
        "startAionO25ABSelectedTerminalVoice",
        start,
    )

    return text[start:end]


def test_o25av_releases_foundation_terminal():
    block = finance_route_block()

    assert (
        "aion.businessTwin.financeHandoffActive.v1"
        in block
    )

    assert (
        "aion.o25u.current_terminal_open.v1"
        in block
    )

    assert (
        "aion.o25f.intentionalConversationOpen.v1"
        in block
    )

    assert (
        "window.__aionO25UConversationOpen = false"
        in block
    )


def test_o25av_sets_canonical_live_agents_route():
    block = finance_route_block()

    assert (
        'window.__aionForcedMainTabV2 =\n'
        '      "live_agents"'
        in block
    )

    assert (
        'state.activeTab = "live_agents"'
        in block
    )

    assert (
        "window.setAionSidebarActiveTabHardV1"
        in block
    )


def test_o25av_sets_finance_department_authorities():
    block = finance_route_block()

    required_tokens = (
        "__aionO16ASelectedLiveAgentsDepartment",
        "__aionO14A6ClickedDepartmentPilot",
        "__aionO14A6ActiveDepartmentPilot",
        "__aionO14A3ActiveDepartmentPilot",
        "__aionActiveDepartmentPilot",
        "__aionSelectedDepartmentPilot",
        "__aionDepartmentPilotKey",
        "__aionLiveAgentsFocusDepartment",
        "__aionPreferredLiveAgentDepartment",
    )

    for token in required_tokens:
        assert token in block

    assert (
        '"aion.liveAgents.selectedDepartment"'
        in block
    )

    assert (
        '"aion.departmentPilot.selected"'
        in block
    )


def test_o25av_records_route_result():
    block = finance_route_block()

    assert (
        "__aionBusinessTwinFinanceRouteResult"
        in block
    )

    assert (
        'route: "live_agents"'
        in block
    )

    assert (
        'department: "finance"'
        in block
    )

    assert "return true;" in block
    assert "return false;" in block


def test_o25av_startup_owner_respects_finance_handoff():
    block = startup_owner_block()

    assert "financeHandoffActive" in block

    assert (
        "aion.businessTwin.financeHandoffActive.v1"
        in block
    )

    assert (
        "finance_pilot_active"
        not in block
    )

    assert (
        "if (financeHandoffActive)"
        in block
    )

    assert (
        'state.activeTab = "live_agents"'
        in block
    )

    assert (
        'state.selectedLiveAgentDepartment ='
        in block
    )

    assert (
        '"finance"'
        in block
    )


def test_o25av_normal_fresh_start_is_preserved():
    block = startup_owner_block()

    assert (
        '"small_business_foundation"'
        in block
    )

    assert (
        "__aionO25ABStartupRouteClaimed"
        in block
    )

    assert (
        "startupRouteAlreadyClaimed"
        in block
    )

    assert (
        "if (!startupRouteAlreadyClaimed)"
        in block
    )

    assert (
        "one_shot_startup_owner"
        in block
    )

    assert (
        '"aion.activeTab.v1"'
        in block
    )

    assert (
        '"aion.lastActiveTab.v1"'
        in block
    )

    assert (
        '"aion.forcedMainTab.v2"'
        in block
    )

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def function_block(
    text: str,
    function_name: str,
    next_marker: str,
) -> str:
    start = text.index(function_name)
    end = text.index(next_marker, start)
    return text[start:end]


def test_o25aw_manifest_is_not_a_route_lock():
    text = read_app()

    block = function_block(
        text,
        "function applyAionO25ABFreshStartupRouteOwner",
        "function startAionO25ABSelectedTerminalVoice",
    )

    assert (
        "aion.businessTwin.financeHandoffActive.v1"
        in block
    )

    assert (
        "__aionBusinessTwinProgressionManifest"
        not in block
    )


def test_o25aw_finance_handoff_is_consumed_after_render():
    text = read_app()

    assert (
        'sessionStorage.removeItem(\n'
        '            "aion.businessTwin.financeHandoffActive.v1"'
        in text
    )

    assert (
        "__aionBusinessTwinFinanceRouteReleased"
        in text
    )

    assert (
        'reason: "finance_first_render_completed"'
        in text
    )


def test_o25aw_manual_sidebar_navigation_releases_lock():
    text = read_app()

    block = function_block(
        text,
        "function clearAionTransientRouteLocksV3",
        "function setAionSidebarActiveTabHardV1",
    )

    assert (
        "aion.businessTwin.financeHandoffActive.v1"
        in block
    )

    assert "aion.forcedMainTab.v2" in block
    assert 'window.__aionForcedMainTabV2 = "";' in block


def test_o25aw_finance_department_selection_survives():
    text = read_app()

    assert (
        'state.selectedLiveAgentDepartment = "finance";'
        in text
    )

    assert (
        'state.liveAgentsSelectedDepartment = "finance";'
        in text
    )

    assert (
        'state.activeLiveAgentDepartment = "finance";'
        in text
    )


def test_o25aw_finance_route_still_opens_live_agents():
    text = read_app()

    block = function_block(
        text,
        "function routeAionBusinessTwinToFinanceOnceV2",
        "/* O19F: small_business_foundation",
    )

    assert 'state.activeTab = "live_agents";' in block
    assert '"aion.liveAgents.selectedDepartment"' in block
    assert '"finance"' in block

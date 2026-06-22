from __future__ import annotations

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text()


def test_phase24c_continue_to_boardroom_completes_foundation_onboarding():
    assert 'data-aion-phase24b-continue-departments' in APP_JS
    assert 'state.smallBusinessFoundationBoardroomStarted = true' in APP_JS
    assert 'window.localStorage?.setItem("aion.smallBusinessFoundationBoardroomStarted", "true")' in APP_JS
    assert 'state.activeTab = "boardroom"' in APP_JS
    assert "Continue to Boardroom completes the small-business foundation onboarding route" in APP_JS


def test_phase24c_small_business_route_guard_allows_boardroom_after_approval():
    assert "smallBusinessFoundationBoardroomStarted !== true" in APP_JS
    assert 'selectedEntryMode === "small_business_growth"' in APP_JS
    assert 'activeTabForChrome !== "small_business_foundation"' in APP_JS


def test_phase24c_continue_to_boardroom_does_not_route_to_live_agents_first():
    continue_start = APP_JS.index('const continueButton = event.target?.closest?.("[data-aion-phase24b-continue-departments]")')
    continue_block = APP_JS[continue_start:APP_JS.index("    }", continue_start) + 5]
    assert 'state.activeTab = "live_agents"' not in continue_block
    assert 'state.selectedLiveDepartmentKey = "pilot"' not in continue_block


def test_phase24c_continue_to_boardroom_does_not_reset_entry_mode():
    continue_start = APP_JS.index('const continueButton = event.target?.closest?.("[data-aion-phase24b-continue-departments]")')
    continue_block = APP_JS[continue_start:APP_JS.index("    }", continue_start) + 5]
    assert "resetAionBusinessEntryMode()" not in continue_block

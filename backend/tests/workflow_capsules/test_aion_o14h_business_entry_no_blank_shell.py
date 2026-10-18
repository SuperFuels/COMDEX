from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_missing_business_entry_mode_does_not_return_blank_selector():
    assert "O14H shell recovery" in APP
    assert "renderBusinessEntryModeSelector();" not in APP
    assert "window.__aionBusinessEntryModeRecoveredO14H = true" in APP


def test_retired_dashboard_route_is_migrated_to_boardroom():
    assert '{ key: "dashboard", label: "Dashboard" }' not in APP
    assert 'persistedForcedTab === "dashboard" ? "boardroom" : persistedForcedTab' in APP
    assert 'state.activeTab = "boardroom";' in APP


def test_recovery_sets_stable_business_entry_mode_keys():
    assert 'writeBusinessWorkingStateString?.("aion.businessEntryMode.v1", "small_business_growth")' in APP
    assert 'writeBusinessWorkingStateString?.("aion.selectedBusinessEntryMode.v1", "small_business_growth")' in APP
    assert 'writeBusinessWorkingStateString?.("aion.business_entry_mode.v1", "small_business_growth")' in APP

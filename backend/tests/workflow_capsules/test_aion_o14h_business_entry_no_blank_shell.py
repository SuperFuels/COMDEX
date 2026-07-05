from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_missing_business_entry_mode_does_not_return_blank_selector():
    assert "O14H shell recovery" in APP
    assert "renderBusinessEntryModeSelector();" not in APP
    assert "window.__aionBusinessEntryModeRecoveredO14H = true" in APP


def test_dashboard_route_still_reachable_after_recovery():
    assert 'if (state.activeTab === "dashboard")' in APP
    assert "return renderDashboardSurface();" in APP
    assert APP.index("O14H shell recovery") < APP.index('if (state.activeTab === "dashboard")')


def test_recovery_sets_stable_business_entry_mode_keys():
    assert 'localStorage.setItem("aion.businessEntryMode.v1", "small_business_growth")' in APP
    assert 'localStorage.setItem("aion.selectedBusinessEntryMode.v1", "small_business_growth")' in APP
    assert 'localStorage.setItem("aion.business_entry_mode.v1", "small_business_growth")' in APP

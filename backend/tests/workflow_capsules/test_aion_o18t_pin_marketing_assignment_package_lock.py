from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18t_marketing_package_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18T PIN MARKETING BOARDROOM PACKAGE LOCK" in text
    assert "aion-o18t-pin-marketing-boardroom-package-style" in text
    assert "data-aion-o18t-marketing-boardroom-package" in text
    assert "Marketing assignment package" in text
    assert "boardroom_goal_sheet" in text
    assert "marketing_pilot" in text
    assert "discovery_required" in text

def test_o18t_wraps_marketing_cockpit_route():
    text = APP.read_text(encoding="utf-8")
    assert "renderAionO17EMarketingPilotCockpitWithPinnedPackageO18T" in text
    assert "__aionO18TPackageWrapped" in text
    assert "__debugAionO18TMarketingPackage" in text
    assert "data-aion-o18t-open-marketing-package" in text

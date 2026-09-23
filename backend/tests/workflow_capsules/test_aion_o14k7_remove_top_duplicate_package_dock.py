from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k7_duplicate_remover_exists():
    assert "BEGIN AION O14K7 REMOVE TOP DUPLICATE PACKAGE DOCK" in APP
    assert "installAionO14K7RemoveTopDuplicatePackageDock" in APP
    assert "removeTopDuplicatePackageDockO14K7" in APP


def test_o14k7_only_runs_on_live_agents():
    assert 'String(window.state?.activeTab || state?.activeTab || "") === "live_agents"' in APP


def test_o14k7_protects_new_under_boardroom_package():
    assert 'closest("[data-aion-o14k-collapsed-package-dock]")' in APP
    assert 'closest("[data-aion-o14k-package-content]")' in APP
    assert 'closest("[data-aion-o14k-full-package-panel]")' in APP


def test_o14k7_hides_only_package_before_live_agents_header():
    assert "isBeforeLiveAgentsHeaderO14K7" in APP
    assert "data-aion-o14k7-top-duplicate-package-removed" in APP
    assert "looksLikePackageDockO14K7" in APP
    assert "Boardroom assignment active" in APP

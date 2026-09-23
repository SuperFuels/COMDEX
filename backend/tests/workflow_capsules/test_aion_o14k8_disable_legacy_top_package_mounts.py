from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k8_lock_exists():
    assert "BEGIN AION O14K8 LEGACY TOP PACKAGE MOUNT DISABLE LOCK" in APP
    assert "aionDisableLegacyTopPackagePanelsO14K8" in APP
    assert "O14K.8 legacy top package mounts disabled" in APP


def test_legacy_o14a1_mount_is_disabled():
    assert "function mountPackagePanelO14A1()" in APP
    assert "Legacy top Incoming Boardroom Package panel is disabled" in APP
    assert 'document.getElementById("aion-o14a1-incoming-boardroom-package-panel")?.remove()' in APP
    assert "return false;" in APP


def test_legacy_o14a4_mount_is_disabled():
    assert "function mountDockO14A4()" in APP
    assert "Legacy stable top package dock is disabled" in APP
    assert 'document.getElementById("aion-o14a4-department-pilot-package-dock")?.remove()' in APP
    assert 'querySelectorAll(\'[data-aion-o14a4-package-dock="true"]\')' in APP


def test_under_boardroom_o14k_package_dock_still_exists():
    assert "function renderAionO14KCollapsedPackageDockUnderBoardroom" in APP
    assert 'data-aion-o14k-collapsed-package-dock="true"' in APP
    assert 'data-aion-o14k-package-content="true"' in APP
    assert "renderAionO14KFullPackageContent(key)" in APP


def test_marketing_has_only_one_o14k_under_boardroom_call():
    assert APP.count('renderAionO14KCollapsedPackageDockUnderBoardroom("marketing")') == 1

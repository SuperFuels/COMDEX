from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k2_legacy_top_package_dock_removal_exists():
    assert "BEGIN AION O14K2 REMOVE LEGACY TOP PACKAGE DOCK" in APP
    assert "installAionO14K2RemoveLegacyTopPackageDock" in APP
    assert "looksLikeLegacyTopPackageDock" in APP
    assert "removeLegacyTopPackageDocks" in APP


def test_o14k2_removes_old_top_dock_by_visible_text_not_only_attrs():
    assert "DEPARTMENT PILOT PACKAGE DOCK" in APP
    assert "Boardroom assignment active" in APP
    assert "REQUIRED DISCOVERY" in APP
    assert "data-aion-o14k2-legacy-top-package-removed" in APP


def test_o14k2_does_not_remove_new_collapsed_dock_content():
    assert "isInsideCollapsedDock" in APP
    assert '[data-aion-o14k-collapsed-package-dock="true"]' in APP
    assert '[data-aion-o14k-package-content="true"]' in APP
    assert ".aion-o14k-collapsed-package-dock" in APP


def test_o14k2_exported_manual_recovery_function():
    assert "window.removeAionLegacyTopPackageDocksO14K2" in APP

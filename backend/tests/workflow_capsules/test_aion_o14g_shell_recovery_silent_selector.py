from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14g_selector_is_silent_noop_not_visible_shell():
    assert "BEGIN AION O14G BUSINESS ENTRY SELECTOR SILENT SHELL RECOVERY" in APP
    assert "function renderBusinessEntryModeSelector()" in APP
    assert 'return "";' in APP
    assert "data-aion-o14f-business-entry-selector-fallback" not in APP


def test_o14g_keeps_function_exported_for_render_main_surface():
    assert "window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector" in APP
    assert APP.index("function renderBusinessEntryModeSelector()") < APP.index("function renderMainSurface")


def test_o14g_hides_stuck_package_docks():
    assert "BEGIN AION O14G STUCK PACKAGE DOCK HIDE RECOVERY" in APP
    assert "data-aion-o14g-hidden-recovery" in APP
    assert "[data-aion-o14a-department-pilot-package-dock]" in APP
    assert "[data-aion-o14a1-department-pilot-incoming-package]" in APP

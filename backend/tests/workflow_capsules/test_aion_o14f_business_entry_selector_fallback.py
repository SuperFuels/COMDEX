from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14f_fallback_is_installed_before_render_main_surface():
    marker = APP.index("BEGIN AION O14F BUSINESS ENTRY SELECTOR FALLBACK LOCK")
    render_main = APP.index("function renderMainSurface")
    assert marker < render_main


def test_o14f_defines_missing_function_and_exports_window_binding():
    assert "function renderBusinessEntryModeSelector()" in APP
    assert "window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector" in APP
    assert "data-aion-o14f-business-entry-selector-fallback" in APP


def test_o14f_uses_safe_business_context_without_side_effects():
    assert "aion.business_twin.latest.v1" in APP
    assert "aion.business_twin_setup.v1" in APP
    assert "Business not registered" in APP
    assert "escapeHtml(businessName)" in APP

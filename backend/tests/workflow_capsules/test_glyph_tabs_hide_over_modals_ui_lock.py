from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _patch() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    assert "AION PATCH: Glyph Tabs Hide Over Modals Lock v8" in src
    return src.split("AION PATCH: Glyph Tabs Hide Over Modals Lock v8", 1)[1]


def test_glyph_tabs_hide_over_modals_lock_installed():
    patch = _patch()

    assert "window.__syncAionGlyphTabsModalVisibilityV8 = syncGlyphTabsVisibility" in patch
    assert "window.__debugAionGlyphTabsHideOverModalsV8" in patch
    assert "modalIsOpen()" in patch


def test_glyph_tabs_hide_when_module_picker_or_dialog_visible():
    patch = _patch()

    for marker in [
        "[role='dialog']",
        ".aion-module-picker-modal",
        ".aion-workflow-module-picker",
        ".aion-step-module-picker",
        ".aion-architect-module-picker",
        "[data-aion-workflow-module-picker='true']",
    ]:
        assert marker in patch


def test_glyph_tabs_hidden_without_deleting_tabs():
    patch = _patch()

    assert 'el.setAttribute("data-aion-hidden-by-modal-v8", "true")' in patch
    assert 'el.style.setProperty("display", "none", "important")' in patch
    assert "el.remove()" not in patch
    assert "root.remove()" not in patch

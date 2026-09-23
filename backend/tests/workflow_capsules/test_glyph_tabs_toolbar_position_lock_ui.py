from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: Glyph Tabs + Library Toolbar Position Lock v4" in src
    return src.split("AION PATCH: Glyph Tabs + Library Toolbar Position Lock v4", 1)[1]


def test_tabs_are_forced_below_sticky_header():
    patch = _patch()

    assert 'top: 174px !important' in patch
    assert 'height: 42px !important' in patch
    assert 'left: 72px !important' in patch
    assert 'padding-top: 42px !important' in patch
    assert "normaliseTabsPosition" in patch


def test_glyph_library_button_is_force_bound():
    patch = _patch()

    assert "data-aion-glyph-library-force-open-v4" in patch
    assert "forceBindGlyphLibraryButton" in patch
    assert "event.stopImmediatePropagation" in patch
    assert "window.__openAionWorkflowGlyphLibrary = openGlyphLibraryHard" in patch


def test_debug_hook_exists():
    patch = _patch()

    assert "window.__debugAionGlyphTabsToolbarPositionLockV4" in patch
    assert "window.__fixAionGlyphTopTabsAndLibraryButtonV4" in patch

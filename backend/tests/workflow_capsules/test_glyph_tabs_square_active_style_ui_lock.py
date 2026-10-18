from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _patch() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    assert "AION PATCH: Glyph Tabs Square Active Style v6" in src
    return src.split("AION PATCH: Glyph Tabs Square Active Style v6", 1)[1]


def test_square_active_tab_style_installed():
    patch = _patch()

    assert "window.__fixAionGlyphTabsSquareActiveStyleV6 = refreshTabStyle" in patch
    assert "window.__debugAionGlyphTabsSquareActiveStyleV6" in patch
    assert "aion-glyph-tabs-square-active-style-v6" in patch


def test_tabs_are_squared_off():
    patch = _patch()

    assert "border-radius: 0 !important" in patch
    assert "transform: none !important" in patch
    assert "box-shadow: none !important" in patch


def test_active_tab_is_blue_by_default():
    patch = _patch()

    assert "background: #0d8fa3 !important" in patch
    assert "border-color: #0d8fa3 !important" in patch
    assert 'activeColour: "blue"' in patch


def test_square_style_keeps_canonical_tabbar():
    patch = _patch()

    assert 'const TABBAR_ID = "aion-glyph-workflow-top-tabs-v2"' in patch
    assert 'data-aion-glyph-tabs-square-active-v6' in patch

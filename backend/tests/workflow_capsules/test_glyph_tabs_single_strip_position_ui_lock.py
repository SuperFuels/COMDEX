from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _patch() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    assert "AION PATCH: Glyph Tabs Single Strip Position Lock v5" in src
    return src.split("AION PATCH: Glyph Tabs Single Strip Position Lock v5", 1)[1]


def test_single_strip_position_lock_installed():
    patch = _patch()

    assert "window.__fixAionGlyphTabsSingleStripPositionLockV5 = ensureCanonicalTabStrip" in patch
    assert "window.__debugAionGlyphTabsSingleStripPositionLockV5" in patch
    assert "aion-glyph-tabs-single-strip-position-lock-v5-style" in patch


def test_only_canonical_top_tabs_are_visible():
    patch = _patch()

    assert 'const TABBAR_ID = "aion-glyph-workflow-top-tabs-v2"' in patch
    assert 'const GLYPH_PANEL_ID = "aion-master-glyph-workflow-tab-v1"' in patch
    assert "removeLegacyDuplicateTabStrips" in patch
    assert "#aion-master-glyph-workflow-tabs-v2" in patch
    assert ".aion-glyph-workflow-top-tabs" in patch
    assert ".aion-master-glyph-workflow-tabs" in patch
    assert ".aion-glyph-tabs-strip" in patch


def test_tabs_sit_under_locked_workflow_header():
    patch = _patch()

    assert "top: 124px !important" in patch
    assert "left: 64px !important" in patch
    assert "height: 34px !important" in patch
    assert "height: calc(100vh - 158px) !important" in patch


def test_old_full_panel_root_is_not_used_as_tab_strip():
    patch = _patch()

    assert "do NOT style #aion-master-glyph-workflow-tab-v1 as a tab strip" in patch
    assert "#${GLYPH_PANEL_ID}:not(.open)" in patch
    assert "#${GLYPH_PANEL_ID}.open" in patch
    assert "top: 158px !important" in patch

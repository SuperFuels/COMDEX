from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: Glyph Library Button + Top Workflow Tabs v2" in src
    return src.split("AION PATCH: Glyph Library Button + Top Workflow Tabs v2", 1)[1]


def test_glyph_library_button_hard_binding_installed():
    patch = _patch()

    assert "window.__openAionWorkflowGlyphLibrary = hardOpenGlyphLibrary" in patch
    assert "data-aion-glyph-library-hard-open-v2" in patch
    assert "data-aion-glyph-library-v37-open" in patch
    assert "data-aion-workflow-glyph-library-open" in patch
    assert "patchVisibleGlyphButtons" in patch


def test_open_workflow_uses_top_tabs_not_bottom_toolbar_mode():
    patch = _patch()

    assert "window.__openAionGlyphWorkflowTopTab = openGlyphTopTab" in patch
    assert "window.__debugAionGlyphWorkflowTopTabsV2" in patch
    assert "Main workflow" in patch
    assert "data-aion-glyph-top-tab-select" in patch
    assert "data-aion-glyph-top-tab-close" in patch


def test_top_tabs_preserve_glyph_scope_and_read_only_contract():
    patch = _patch()

    assert "glyph_scope" in patch
    assert "scope" in patch
    assert "universal" in patch
    assert "window.__aionGlyphWorkflowTabOpen = true" in patch
    assert "window.__aionOpenedGlyphWorkflow = clone(glyph)" in patch

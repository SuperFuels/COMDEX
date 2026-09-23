from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_glyph_workflow_tab_patch_is_installed():
    src = _src()

    assert "AION PATCH: Master Glyph Workflow Tab v1" in src
    assert "window.__openAionGlyphWorkflowTab" in src
    assert "window.__debugAionGlyphWorkflowTab" in src
    assert "data-aion-glyph-tab-close" in src
    assert "data-aion-glyph-tab-back-main" in src


def test_open_workflow_buttons_mount_real_tab_not_just_toast():
    src = _src()

    assert "[data-aion-auth-open-glyph], [data-aion-glyph-v36-open]" in src
    assert "openGlyphWorkflowTab(code)" in src
    assert "window.__aionOpenedGlyphWorkflow" in src
    assert "window.__aionGlyphWorkflowTabOpen = true" in src


def test_universal_glyph_tab_is_read_only_and_save_as_my():
    src = _src()

    assert "Read-only universal glyph" in src
    assert "Save as My Glyph" in src
    assert "/api/workflow-glyphs/copy" in src
    assert "source_glyph_code: glyph.glyph_code" in src


def test_my_glyph_tab_is_editable_autosave_ready_without_execution():
    src = _src()

    assert "Editable My Glyph" in src
    assert "Autosave Ready" in src
    assert "UI-only: does not execute workflows" in src
    assert "runtime execution is still dry-run locked" in src

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: Glyph Tab Editor Migration Lock v1" in src
    return src.split("AION PATCH: Glyph Tab Editor Migration Lock v1", 1)[1]


def test_glyph_tab_editor_migration_strategy_is_locked():
    patch = _patch()

    assert "masterGlyphCanvasMode: \"legacy_source_only\"" in patch
    assert "editorSurface: \"top_workflow_tabs\"" in patch
    assert "universalGlyphPolicy: \"immutable_template_copy_before_edit\"" in patch
    assert "myGlyphPolicy: \"editable_save_to_backend\"" in patch
    assert "runtimePolicy: \"dry_run_only_until_parent_child_validation\"" in patch


def test_useful_master_glyph_canvas_logic_is_marked_for_migration_before_removal():
    patch = _patch()

    for item in [
        "compileAionWorkflowGraphToGlyph",
        "compileAndAttachAionWorkflowGlyph",
        "getAionWorkflowGlyphCapsuleRegistry",
        "persistAionWorkflowGlyphCapsuleRegistry",
        "upsertAionWorkflowGlyphCapsuleRegistryItem",
        "listAionWorkflowGlyphLibraryItems",
        "stageMasterGlyphToWorkflowCanvas",
        "connection_preview_contract",
    ]:
        assert item in patch


def test_universal_glyph_edit_requires_copy_before_save():
    patch = _patch()

    assert "async function copyUniversalGlyphBeforeEdit" in patch
    assert "/api/workflow-glyphs/copy" in patch
    assert "source_glyph_code: source.glyph_code" in patch
    assert "Universal glyphs are immutable" in patch


def test_my_glyph_save_uses_backend_glyph_store():
    patch = _patch()

    assert "async function saveMyGlyphFromTab" in patch
    assert "/api/workflow-glyphs" in patch
    assert 'scope: "my"' in patch
    assert "rebuild_index: true" in patch


def test_tab_editor_debug_hooks_are_exposed():
    patch = _patch()

    assert "window.__saveAionMyGlyphFromTab = saveMyGlyphFromTab" in patch
    assert "window.__copyAionUniversalGlyphBeforeEdit = copyUniversalGlyphBeforeEdit" in patch
    assert "window.__addOpenedAionGlyphToCurrentWorkflow = addOpenedGlyphToCurrentWorkflow" in patch
    assert "window.__debugAionGlyphTabEditorMigrationLockV1" in patch

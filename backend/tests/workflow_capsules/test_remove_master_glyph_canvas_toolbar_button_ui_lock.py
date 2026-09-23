from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def test_master_glyph_canvas_toolbar_render_block_removed():
    src = _src()

    toolbar_start = src.index("function renderAionWorkflowFloatingToolbar")
    toolbar_end = src.index("function renderAionWorkflowCanvasPanel", toolbar_start)
    toolbar = src[toolbar_start:toolbar_end]

    assert 'data-aion-canvas-mode="master_glyph"' not in toolbar
    assert 'title="Master Glyph Canvas"' not in toolbar
    assert 'aria-label="Master Glyph Canvas"' not in toolbar


def test_workflow_canvas_button_still_exists():
    src = _src()

    toolbar_start = src.index("function renderAionWorkflowFloatingToolbar")
    toolbar_end = src.index("function renderAionWorkflowCanvasPanel", toolbar_start)
    toolbar = src[toolbar_start:toolbar_end]

    assert 'data-aion-canvas-mode="workflow"' in toolbar
    assert 'title="Workflow Canvas"' in toolbar
    assert 'aria-label="Workflow Canvas"' in toolbar


def test_glyph_library_and_clear_buttons_are_preserved():
    src = _src()

    toolbar_start = src.index("function renderAionWorkflowFloatingToolbar")
    toolbar_end = src.index("function renderAionWorkflowCanvasPanel", toolbar_start)
    toolbar = src[toolbar_start:toolbar_end]

    assert 'data-aion-workflow-glyph-library-open="true"' in toolbar
    assert 'title="Workflow Glyph Library"' in toolbar
    assert 'data-aion-master-glyph-clear-staged="true"' in toolbar
    assert 'title="Clear staged glyph nodes"' in toolbar


def test_migration_code_is_not_deleted():
    src = _src()

    assert "compileAionWorkflowGraphToGlyph" in src
    assert "compileAndAttachAionWorkflowGlyph" in src
    assert "stageMasterGlyphToWorkflowCanvas" in src
    assert "Glyph Tab Editor Migration Lock v1" in src

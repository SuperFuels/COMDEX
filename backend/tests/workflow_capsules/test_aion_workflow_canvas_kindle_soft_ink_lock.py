from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def source() -> str:
    return APP.read_text()

def test_workflow_canvas_kindle_soft_ink_lock_exists() -> None:
    text = source()
    assert "AION KINDLE SOFT INK CANVAS LOCK" in text
    assert "installAionWorkflowCanvasKindleSoftInkStyles" in text
    assert "aion-workflow-canvas-kindle-soft-ink-styles" in text

def test_workflow_canvas_kindle_targets_real_active_selectors() -> None:
    text = source()
    assert ".aion-workflow-canvas-shell" in text
    assert ".aion-workflow-canvas" in text
    assert ".aion-workflow-canvas-viewport" in text
    assert "[data-aion-workflow-node-id]" in text
    assert ".aion-workflow-floating-toolbar-consolidated" in text

def test_workflow_canvas_viewport_stays_transparent_not_paper_panel() -> None:
    text = source()
    assert "Do NOT paint .aion-workflow-canvas-viewport as a big paper square" in text
    assert "html body .aion-workflow-canvas-viewport" in text
    assert "background: transparent !important" in text
    assert "box-shadow: none !important" in text

def test_workflow_canvas_does_not_add_extra_node_card_frame() -> None:
    text = source()
    assert "Do not introduce extra node frames" in text
    assert ".aion-workflow-node-card" in text
    assert "border-color: inherit !important" in text
    assert "background: inherit !important" in text
    assert "box-shadow: inherit !important" in text

def test_workflow_canvas_kindle_preserves_execution_controls() -> None:
    text = source()
    assert "data-aion-workflow-dry-run" in text
    assert "data-aion-unified-builder-mode" in text
    assert "data-aion-architect-open-module-picker" in text
    assert "data-aion-workflow-glyph-library-open" in text

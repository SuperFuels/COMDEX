from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_no_separate_master_glyph_canvas_mode_button():
    text = read_app()
    assert 'data-aion-canvas-mode="master_glyph"' not in text
    assert 'data-aion-canvas-mode="master-glyph"' not in text


def test_master_glyph_canvas_renderer_is_retired():
    text = read_app()
    marker = "function renderAionMasterGlyphCanvasPanel()"
    assert marker in text
    block = text[text.index(marker): text.index("function installAionMasterGlyphCanvasControls()", text.index(marker))]
    assert 'return "";' in block
    assert "There is no separate Master Glyph Canvas surface anymore" in block


def test_glyph_library_and_top_tabs_remain_canonical():
    text = read_app()
    assert "Workflow Glyph Library" in text
    assert "__aionGlyphWorkflowTabs" in text
    assert "__aionActiveGlyphWorkflowTabCode" in text
    assert "data-aion-workflow-glyph-library-open" in text


def test_call_workflow_glyph_staging_remains_available():
    text = read_app()
    assert "__stageAionMasterGlyphToWorkflowCanvas" in text
    assert "call_workflow_glyph" in text
    assert "data-aion-master-glyph-stage-to-canvas" in text

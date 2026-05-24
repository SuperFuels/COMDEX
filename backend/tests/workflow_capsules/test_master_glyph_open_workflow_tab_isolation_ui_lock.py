from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def test_open_workflow_builds_isolated_glyph_graph() -> None:
    text = _text()
    assert "function buildOpenedGlyphWorkflowGraph(glyph)" in text
    assert "window.__aionOpenedGlyphWorkflowGraph" in text
    assert "opened_from_glyph_library" in text
    assert "source: \"opened_glyph_workflow\"" in text


def test_open_workflow_does_not_stage_to_parent_canvas() -> None:
    text = _text()
    start = text.index("function openWorkflow(code)")
    end = text.index("async function copyGlyphToMyGlyphs", start)
    block = text[start:end]

    assert "stageGlyphToCanvas" not in block
    assert "__aionOpenedGlyphWorkflowGraph" in block
    assert "__aionActiveWorkflowTab = \"glyph\"" in block
    assert "setActiveWorkflowGraphForTab(openedGraph)" in block


def test_stage_to_canvas_forces_main_graph_path() -> None:
    text = _text()
    assert "__aionActiveWorkflowTab = \"main\"" in text
    assert "__aionWorkflowMainGraph" in text


def test_no_request_render_assignment_false_positive() -> None:
    text = _text()
    idx = text.find("Master Glyph Library Open Workflow Resolution")
    patch = text[idx:] if idx != -1 else text
    assert "requestRender =" not in patch

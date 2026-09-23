from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")

def e9_function_block() -> str:
    text = _text()
    start = text.index("function installAionWorkflowTabActiveGraphIsolationE9()")
    end = text.index("console.log(\"[AION] Workflow Tab Active Graph Isolation E9 installed\");", start)
    return text[start:end]


def test_e9_active_graph_isolation_installed() -> None:
    text = _text()
    assert "Workflow Tab Active Graph Isolation E9" in text
    assert "window.__aionGetActiveWorkflowGraph" in text
    assert "window.__aionSetActiveWorkflowGraph" in text


def test_main_and_glyph_graphs_have_separate_state_slots() -> None:
    text = _text()
    block = text[text.index("Workflow Tab Active Graph Isolation E9"):]
    assert "window.__aionWorkflowMainGraph" in block
    assert "window.__aionOpenedGlyphWorkflowGraph" in block
    assert "window.__aionActiveWorkflowTab === \"glyph\"" in block


def test_stage_to_canvas_forces_main_graph_only() -> None:
    text = _text()
    block = text[text.index("function stageAionGlyphToCanvasMainOnly"):]
    assert "window.__aionActiveWorkflowTab = \"main\"" in block
    assert "window.__aionGlyphWorkflowTabOpen = false" in block
    assert "window.__aionWorkflowMainGraph" in block


def test_open_glyph_workflow_forces_glyph_graph_only() -> None:
    text = _text()
    block = text[text.index("function openAionGlyphWorkflowIsolated"):]
    assert "setActiveGraph(opened, \"glyph\")" in block
    assert "window.__aionOpenedGlyphWorkflowGraph" in block


def test_e9_does_not_replace_request_render_or_use_observer() -> None:
    block = e9_function_block()
    assert "requestRender =" not in block
    assert "window.requestRender =" not in block
    assert "MutationObserver" not in block
    assert 'window["requestRender"]()' in block

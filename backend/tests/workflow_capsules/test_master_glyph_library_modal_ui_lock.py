from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_glyph_library_button_opens_backend_marketplace_modal():
    src = read_app()

    assert "data-aion-workflow-glyph-library-open" in src
    assert "__openAionWorkflowGlyphLibrary" in src
    assert "__refreshAionWorkflowGlyphsFromApi" in src
    assert "/api/workflow-glyphs" in src
    assert "Backend-authoritative glyph marketplace" in src
    assert "__renderAionGlyphMarketplaceModal" in src
    assert "aion-glyph-library-authoritative-modal-v1" in src


def test_clear_staged_glyphs_targets_call_workflow_glyph_nodes_without_broad_canvas_clear():
    src = read_app()

    assert "data-aion-master-glyph-clear-staged" in src
    assert "__clearAionMasterGlyphStagedNodes" in src
    assert "call_workflow_glyph" in src
    assert "workflow.call_workflow_glyph" in src

    # The clear path must filter nodes by staged/call glyph identity,
    # not wipe the whole workflow canvas.
    assert ".filter(isStagedGlyphNode)" in src or ".filter(isMasterGlyphStagedNode)" in src
    assert "graph.nodes = graph.nodes.filter" in src

    clear_sections = [
        section
        for section in src.split("function ")
        if "clearStaged" in section or "clearStagedGlyph" in section or "clearStagedMasterGlyph" in section
    ]

    assert clear_sections, "Expected at least one staged-glyph clear helper"

    for section in clear_sections:
        assert "nodes = []" not in section
        assert "graph.nodes.length = 0" not in section
        assert "window.__aionWorkflowGraph.nodes = []" not in section


def test_workflow_and_master_canvas_toolbar_buttons_survive_render():
    src = read_app()

    assert 'data-aion-canvas-mode="workflow"' in src
    assert 'data-aion-canvas-mode="master_glyph"' in src
    assert 'data-aion-workflow-glyph-library-open="true"' in src
    assert 'data-aion-master-glyph-clear-staged="true"' in src

    # Delegated handlers / render hooks keep these alive after requestRender().
    assert "requestRender" in src
    assert "aion:workflow-rendered" in src

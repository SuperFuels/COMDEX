from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_staged_inspector_close_lock_installed():
    src = _src()

    assert "AION PATCH: Master Glyph Staged Inspector Close Lock v1" in src
    assert "window.__closeAionMasterGlyphStagedInspector = closeStagedGlyphInspector" in src
    assert "window.__debugAionMasterGlyphStagedInspectorCloseLock" in src


def test_staged_inspector_close_does_not_delete_nodes():
    src = _src()
    patch = src.split("AION PATCH: Master Glyph Staged Inspector Close Lock v1", 1)[1]

    assert "window.__aionMasterGlyphSelectedStagedNodeId = null" in patch
    assert "window.__aionMasterGlyphStagedInspectorOpen = false" in patch
    assert "graph.nodes = graph.nodes.filter" not in patch
    assert "window.__aionWorkflowGraph.nodes = []" not in patch


def test_staged_inspector_close_supports_escape_and_button_click():
    src = _src()
    patch = src.split("AION PATCH: Master Glyph Staged Inspector Close Lock v1", 1)[1]

    assert '"click"' in patch
    assert '"keydown"' in patch
    assert 'event.key !== "Escape"' in patch
    assert "looksLikeStagedGlyphInspectorClose" in patch

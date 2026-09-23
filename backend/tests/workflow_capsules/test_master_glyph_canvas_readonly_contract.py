from __future__ import annotations

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_master_glyph_canvas_readonly_renderer_exists() -> None:
    text = _read()

    assert "function listAionMasterGlyphCanvasItems" in text
    assert "function renderAionMasterGlyphCanvasNode" in text
    assert "function renderAionMasterGlyphCanvasPanel" in text
    assert "function renderAionMasterGlyphCanvasLauncher" in text
    assert "function installAionMasterGlyphCanvasControls" in text
    assert "Master Glyph Canvas v1" in text


def test_master_glyph_canvas_lists_callable_saved_workflow_glyphs() -> None:
    text = _read()

    assert "listAionWorkflowGlyphLibraryItems" in text
    assert "listAionWorkflowGlyphCapsules" in text
    assert "item.callable === true" in text
    assert "data-aion-master-glyph-node" in text


def test_master_glyph_canvas_shows_required_glyph_metadata() -> None:
    text = _read()

    required_tokens = [
        "workflow_id",
        "status",
        "callable",
        "risk_tier",
        "required_connectors",
        "inputs_schema",
        "outputs_schema",
        "boardroom_events",
        "Connectors",
        "Inputs",
        "Outputs",
        "Events",
    ]

    for token in required_tokens:
        assert token in text


def test_master_glyph_canvas_is_read_only_and_non_executing() -> None:
    text = _read()
    start = text.index("function renderAionMasterGlyphCanvasPanel")
    block = text[start : start + 9000]

    assert "Read-only" in block or "read-only" in block
    assert "No execution" in block
    assert "No editing" in block
    assert "No wiring" in block
    assert "No external writes" in block
    assert "Current workflow canvas preserved" in block

    forbidden = [
        "executeGraphDryRun(",
        "executeNodeDryRun(",
        "executeCallWorkflowGlyphNode(",
        "call_workflow_glyph(",
        "saveAionWorkflowToBusinessContainer(",
        "loadAionWorkflowFromBusinessContainer(",
        "window.__aionWorkflowGraph =",
    ]

    for token in forbidden:
        assert token not in block


def test_master_glyph_canvas_debug_export_exists() -> None:
    text = _read()

    assert "window.listAionMasterGlyphCanvasItems = listAionMasterGlyphCanvasItems" in text

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_master_glyph_staged_node_inspector_renderer_exists() -> None:
    text = _read()

    assert "Master Glyph Canvas v3 staged glyph node inspector" in text
    assert "function renderAionMasterGlyphStagedNodeInspector" in text
    assert "window.renderAionMasterGlyphStagedNodeInspector = renderAionMasterGlyphStagedNodeInspector" in text
    assert "data-aion-master-glyph-staged-inspector=\"true\"" in text


def test_master_glyph_staged_node_inspector_shows_core_metadata() -> None:
    text = _read()
    start = text.index("function renderAionMasterGlyphStagedNodeInspector")
    block = text[start : start + 9000]

    required_tokens = [
        "workflow_id",
        "child_workflow_id",
        "glyph_id",
        "callable",
        "risk_tier",
        "required_connectors",
        "inputs_schema",
        "outputs_schema",
        "approval_policy",
        "boardroom_events",
    ]

    for token in required_tokens:
        assert token in block


def test_master_glyph_staged_node_inspector_is_read_only() -> None:
    text = _read()
    start = text.index("function renderAionMasterGlyphStagedNodeInspector")
    block = text[start : start + 9000]

    assert "Read-only" in block or "read-only" in block
    assert "No execution" in block
    assert "No editing" in block
    assert "No wiring" in block
    assert "No external writes" in block

    forbidden = [
        "executeGraphDryRun(",
        "executeNodeDryRun(",
        "executeCallWorkflowGlyphNode(",
        "saveAionWorkflowToBusinessContainer(",
        "loadAionWorkflowFromBusinessContainer(",
        "window.__aionWorkflowGraph =",
        ".push(",
    ]

    for token in forbidden:
        assert token not in block


def test_master_glyph_staged_node_inspector_has_compiled_glyph_debug_block() -> None:
    text = _read()
    start = text.index("function renderAionMasterGlyphStagedNodeInspector")
    block = text[start : start + 9000]

    assert "Compiled glyph debug block" in block
    assert "JSON.stringify" in block
    assert "compiled_glyph" in block


def test_master_glyph_staged_node_inspector_click_controls_exist() -> None:
    text = _read()

    assert "data-aion-master-glyph-staged-inspector-close=\"true\"" in text
    assert "data-aion-master-glyph-staged-inspector" in text
    assert "__aionMasterGlyphStagedInspectorOpen" in text or "__aionMasterGlyphSelectedStagedNodeId" in text

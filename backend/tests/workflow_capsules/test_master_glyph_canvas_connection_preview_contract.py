from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    return APP_JS.read_text()


def _v4_block() -> str:
    text = _read()
    start = text.index("Master Glyph Canvas v4 staged glyph connection preview")
    return text[start : start + 14000]


def test_master_glyph_connection_preview_patch_exists() -> None:
    text = _read()

    assert "Master Glyph Canvas v4 staged glyph connection preview" in text
    assert "installAionMasterGlyphConnectionPreviewPatch" in text
    assert "renderAionMasterGlyphConnectionPreview" in text
    assert "buildConnectionPreviewModel" in text
    assert "data-aion-master-glyph-connection-preview" in text


def test_master_glyph_connection_preview_is_preview_only() -> None:
    block = _v4_block()

    assert "Preview-only" in block
    assert "No edge creation" in block
    assert "No execution" in block
    assert "No editing" in block
    assert "No wiring" in block
    assert "No external writes" in block
    assert "Saved glyph preserved" in block

    forbidden = [
        "executeGraphDryRun(",
        "executeNodeDryRun(",
        "executeCallWorkflowGlyphNode(",
        "saveAionWorkflowToBusinessContainer(",
        "loadAionWorkflowFromBusinessContainer(",
        ".edges.push(",
        "graph.edges.push(",
        "fetch(",
    ]

    for token in forbidden:
        assert token not in block


def test_master_glyph_connection_preview_model_has_incoming_and_outgoing_candidates() -> None:
    block = _v4_block()

    required_tokens = [
        "incoming",
        "outgoing",
        "preview_direction",
        "would_create_edge",
        "from:",
        "to:",
        "creates_edges: false",
        "executes_workflow: false",
        "mutates_saved_glyph: false",
        "read_only: true",
    ]

    for token in required_tokens:
        assert token in block


def test_master_glyph_connection_preview_uses_schema_summaries() -> None:
    block = _v4_block()

    assert "summariseSchemaKeys" in block
    assert "inputs_schema" in block
    assert "outputs_schema" in block
    assert "Potential input source for child glyph inputs" in block
    assert "Potential downstream consumer for child glyph outputs" in block


def test_master_glyph_connection_preview_debug_export_exists() -> None:
    text = _read()

    assert "window.renderAionMasterGlyphConnectionPreview = renderAionMasterGlyphConnectionPreview" in text
    assert "window.__syncAionMasterGlyphConnectionPreview = syncPreview" in text
    assert "window.__aionMasterGlyphConnectionPreviewOpen" in text
    assert "Connection preview debug block" in text

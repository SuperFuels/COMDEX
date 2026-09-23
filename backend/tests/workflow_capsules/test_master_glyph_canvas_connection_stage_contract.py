from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    return APP_JS.read_text()


def test_master_glyph_connection_stage_patch_exists() -> None:
    text = _read()

    assert "Master Glyph Canvas v5 staged connection confirm" in text
    assert "installAionMasterGlyphConnectionStagePatch" in text
    assert "stageMasterGlyphDraftConnection" in text
    assert "data-aion-master-glyph-stage-connection" in text


def test_master_glyph_connection_stage_creates_draft_only_edge() -> None:
    text = _read()

    required = [
        'status: "staged"',
        'mode: "draft_only"',
        "staged: true",
        'staged_by: "master_glyph_canvas_v5"',
        "dry_run_only: true",
        "live_send_enabled: false",
        "executes_workflow: false",
        "performs_external_write: false",
        "mutates_saved_glyph: false",
    ]

    for token in required:
        assert token in text


def test_master_glyph_connection_stage_requires_explicit_user_action() -> None:
    text = _read()

    assert 'event.target.closest?.("[data-aion-master-glyph-stage-connection=' in text
    assert "confirmed_by_user: true" in text
    assert "Stage draft edge" in text


def test_master_glyph_connection_stage_does_not_execute_or_call_child_workflow() -> None:
    text = _read()
    start = text.index("function stageMasterGlyphDraftConnection")
    block = text[start : start + 4500]

    forbidden = [
        "executeGraphDryRun(",
        "executeNodeDryRun(",
        "executeCallWorkflowGlyphNode(",
        "call_workflow_glyph(",
        "send_email(",
        "saveAionWorkflowToBusinessContainer(",
        "loadAionWorkflowFromBusinessContainer(",
    ]

    for token in forbidden:
        assert token not in block


def test_master_glyph_connection_stage_debug_exports_exist() -> None:
    text = _read()

    assert "window.stageMasterGlyphDraftConnection = stageMasterGlyphDraftConnection" in text
    assert "window.__aionMasterGlyphLastStagedConnection" in text
    assert "window.__patchAionMasterGlyphConnectionPreviewRows" in text

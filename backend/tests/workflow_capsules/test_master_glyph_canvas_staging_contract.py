from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _master_canvas_block() -> str:
    text = _read()
    start = text.index("function renderAionMasterGlyphCanvasPanel")
    return text[start : start + 14000]


def test_master_glyph_canvas_v2_staging_hook_exists() -> None:
    text = _read()

    required_tokens = [
        "function installAionMasterGlyphCanvasControls",
        "stageMasterGlyphToWorkflowCanvas",
        "window.__stageAionMasterGlyphToWorkflowCanvas",
        "data-aion-master-glyph-stage-to-canvas",
        "data-workflow-id",
    ]

    for token in required_tokens:
        assert token in text


def test_master_glyph_canvas_v2_stages_call_workflow_glyph_node() -> None:
    block = _master_canvas_block()

    required_tokens = [
        'action_id: "call_workflow_glyph"',
        'module_id: "workflow.call_workflow_glyph"',
        'type: "Workflow Glyph"',
        'status: "Staged"',
        'dry_run_only: true',
        'live_send_enabled: false',
    ]

    for token in required_tokens:
        assert token in block


def test_master_glyph_canvas_v2_preserves_child_glyph_metadata() -> None:
    block = _master_canvas_block()

    required_tokens = [
        "child_workflow_id",
        "glyph_id",
        "required_connectors",
        "inputs_schema",
        "outputs_schema",
        "approval_policy",
        "boardroom_events",
        "compiled_glyph",
        "risk_tier",
    ]

    for token in required_tokens:
        assert token in block


def test_master_glyph_canvas_v2_staging_does_not_execute_or_live_write() -> None:
    block = _master_canvas_block()

    forbidden_tokens = [
        "executeGraphDryRun(",
        "executeNodeDryRun(",
        "executeCallWorkflowGlyphNode(",
        "saveAionWorkflowToBusinessContainer(",
        "loadAionWorkflowFromBusinessContainer(",
        "fetch(",
        "send_email",
        "post_social",
        "update_crm",
    ]

    for token in forbidden_tokens:
        assert token not in block


def test_master_glyph_canvas_v2_staged_node_runtime_starts_idle() -> None:
    block = _master_canvas_block()

    required_tokens = [
        "runtime:",
        "input_items: []",
        "output_items: []",
        'execution_status: "idle"',
        "last_run_at: null",
        "error: null",
    ]

    for token in required_tokens:
        assert token in block

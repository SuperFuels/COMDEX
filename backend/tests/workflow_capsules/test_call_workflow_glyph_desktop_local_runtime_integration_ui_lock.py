from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_desktop_local_dry_run_detects_call_workflow_glyph_nodes():
    src = _src()

    assert "function isAionCallWorkflowGlyphNodeForDryRun(node)" in src
    assert "function executeAionCallWorkflowGlyphLocalDryRun(node, parentPayload, parentRunId, index)" in src
    assert "isAionCallWorkflowGlyphNodeForDryRun(node)" in src
    assert "executeAionCallWorkflowGlyphLocalDryRun(node, parentPayload, parentRunId, index)" in src


def test_desktop_local_dry_run_resolves_backend_glyph_registry():
    src = _src()

    for token in [
        "window.__aionBackendWorkflowGlyphs",
        "window.__aionWorkflowGlyphs",
        "window.__aionGlyphRegistry",
        "resolveAionCallWorkflowGlyphForDryRun",
        "glyph_registry_resolution_failed",
    ]:
        assert token in src


def test_desktop_local_dry_run_records_nested_provenance_and_metrics():
    src = _src()

    for token in [
        "nested_glyph_run",
        "parent_run_id",
        "child_run_id",
        "parent_payload_passed_to_child",
        "child_output_returned_to_parent",
        "ai_planning_bypassed",
        "external_writes_performed",
        "steps_executed",
    ]:
        assert token in src


def test_desktop_local_dry_run_remains_dry_run_only():
    src = _src()
    section = src.split("function executeAionCallWorkflowGlyphLocalDryRun", 1)[1].split(
        "function buildAionWorkflowLocalDryRunResult", 1
    )[0]

    for token in [
        "dry_run: true",
        "mode: \"dry_run_only\"",
        "call_workflow_glyph_validation_blocked",
        "call_workflow_glyph_dry_run_completed",
    ]:
        assert token in section

    for forbidden in [
        "fetch(",
        "sendEmail",
        "reply_email",
        "send_draft",
        ".edges.push",
        "graph.edges =",
        "executeWorkflow",
        "runWorkflow",
    ]:
        assert forbidden not in section

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _section() -> str:
    src = _src()
    assert "function executeAionCallWorkflowGlyphLocalDryRun" in src
    return src.split("function executeAionCallWorkflowGlyphLocalDryRun", 1)[1].split(
        "function buildAionWorkflowLocalDryRunResult", 1
    )[0]


def test_desktop_nested_runtime_has_native_efficiency_metrics():
    section = _section()

    for token in [
        "ai_planning_bypassed: true",
        "external_writes_performed: 0",
        "registry_lookup_cached",
        "estimated_cost",
        "compiled_dry_run_zero_cost_v1",
    ]:
        assert token in section


def test_desktop_nested_runtime_emits_boardroom_event_anchor():
    section = _section()

    for token in [
        "boardroom_events",
        "call_workflow_glyph.dry_run",
        "desktop_local_nested_glyph_runtime",
        "child_run_id",
        "parent_run_id",
    ]:
        assert token in section


def test_desktop_native_efficiency_path_does_not_call_ai_or_live_writes():
    section = _section()

    for forbidden in [
        "fetch(",
        "sendEmail",
        "reply_email",
        "send_draft",
        "runWorkflow",
        "executeWorkflow",
        "openai",
        "anthropic",
    ]:
        assert forbidden not in section

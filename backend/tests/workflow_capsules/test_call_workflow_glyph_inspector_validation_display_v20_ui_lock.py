from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _patch() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    assert "AION PATCH: call_workflow_glyph Inspector Contract Display v3" in src
    assert "AION PATCH: call_workflow_glyph Inspector Takeover v4" in src
    return src.split("AION PATCH: call_workflow_glyph Inspector Contract Display v3", 1)[1].split(
        "AION PATCH: call_workflow_glyph Inspector Takeover v4", 1
    )[0]


def test_inspector_has_parent_child_validation_summary():
    patch = _patch()

    assert "function validateCallWorkflowGlyphForInspectorV20(node, model)" in patch
    assert "function renderValidationSummaryV20(validation)" in patch
    assert "data-aion-call-glyph-validation-v20" in patch
    assert "parent_child_validation" in patch


def test_validation_summary_shows_blocking_status_and_missing_connectors():
    patch = _patch()

    for label in [
        "runtime_blocked",
        "missing_connectors",
        "validation_errors",
        "validation_warnings",
        "missing_required_connectors",
    ]:
        assert label in patch


def test_validation_summary_preserves_dry_run_runtime_guard():
    patch = _patch()

    assert "Runtime remains dry-run only until parent/child validation is complete." in patch
    assert "runtime_blocked: errors.length > 0" in patch
    assert "live_send_enabled_ignored_in_dry_run" in patch


def test_validation_display_is_ui_only_and_does_not_execute_or_mutate_graph():
    patch = _patch()

    forbidden = [
        "fetch(",
        ".edges.push",
        "graph.edges =",
        "runWorkflow",
        "executeWorkflow",
        "executeCompiled",
        "sendEmail",
    ]

    validation_section = patch.split("function validateCallWorkflowGlyphForInspectorV20", 1)[1].split(
        "function renderContractInspector", 1
    )[0]

    for token in forbidden:
        assert token not in validation_section

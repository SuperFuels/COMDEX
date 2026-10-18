from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: call_workflow_glyph Dry Run Block Guard v21" in src
    return src.split("AION PATCH: call_workflow_glyph Dry Run Block Guard v21", 1)[1]


def test_dry_run_guard_installed_before_legacy_execute_handlers_can_run():
    patch = _patch()

    assert "window.__aionCallWorkflowGlyphDryRunBlockGuardV21Installed" in patch
    assert "[data-aion-workflow-dry-run='true']" in patch
    assert 'document.addEventListener("click"' in patch
    assert "event.stopImmediatePropagation?.()" in patch


def test_dry_run_guard_validates_call_workflow_glyph_contract_fields():
    patch = _patch()

    for token in [
        "function isCallWorkflowGlyphNode(node)",
        "function validateCallWorkflowGlyphNodeForDryRun(node, graph)",
        "missing_glyph_code",
        "missing_child_workflow_id",
        "pinned_glyph_version_mismatch",
        "pinned_glyph_hash_mismatch",
        "missing_required_connectors",
        "approval_policy_mismatch",
        "live_send_requires_approval_policy",
    ]:
        assert token in patch


def test_dry_run_guard_blocks_runtime_without_execution_or_external_writes():
    patch = _patch()

    assert "runtime_blocked: true" in patch
    assert "preflight_validation" in patch
    assert "call_workflow_glyph_preflight_guard_v21" in patch
    assert "Dry-run blocked because one or more call_workflow_glyph nodes failed validation." in patch

    validation_section = patch.split("function validateGraphForDryRun(graph)", 1)[1].split(
        "function notifyBlocked(validation)", 1
    )[0]

    for forbidden in [
        "fetch(",
        ".edges.push",
        "graph.edges =",
        "runWorkflow",
        "executeWorkflow",
        "executeCompiled",
        "sendEmail",
        "reply_email",
        "send_draft",
    ]:
        assert forbidden not in validation_section


def test_dry_run_guard_exposes_debug_and_validation_functions():
    patch = _patch()

    assert "window.__validateAionCallWorkflowGlyphGraphForDryRunV21 = validateGraphForDryRun" in patch
    assert "window.__debugAionCallWorkflowGlyphDryRunBlockGuardV21" in patch
    assert "window.__aionCallWorkflowGlyphLastDryRunValidationV21" in patch

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: Master Glyph Staged Inspector Contract Display v2" in src
    return src.split("AION PATCH: Master Glyph Staged Inspector Contract Display v2", 1)[1]


def test_staged_inspector_contract_display_patch_installed():
    patch = _patch()

    assert "window.__renderAionMasterGlyphContractInspectorV2 = renderContractInspector" in patch
    assert "window.__debugAionMasterGlyphContractInspectorV2" in patch
    assert "data-aion-master-glyph-contract-inspector-v2" in patch


def test_staged_inspector_prefers_real_call_workflow_glyph_contract_fields():
    patch = _patch()

    for field in [
        "node.glyph_code",
        "node.glyph_version",
        "node.glyph_scope",
        "node.child_workflow_id",
        "node.source_glyph_code",
        "node.version_hash",
        "node.input_schema",
        "node.output_schema",
        "node.required_connectors",
        "node.approval_policy",
        "node.runtime_plan",
    ]:
        assert field in patch


def test_staged_inspector_renders_contract_rows():
    patch = _patch()

    for label in [
        "glyph_code",
        "glyph_version",
        "glyph_scope",
        "child_workflow_id",
        "source_glyph_code",
        "version_hash",
        "risk_tier",
        "required_connectors",
        "missing_connectors",
        "dry_run_only",
        "live_send_enabled",
        "input_schema",
        "output_schema",
        "approval_policy",
        "runtime_plan",
    ]:
        assert label in patch


def test_staged_inspector_warns_for_missing_connectors_without_runtime_execution():
    patch = _patch()

    assert "function missingConnectors(required)" in patch
    assert "Missing connector" in patch
    assert "Runtime remains dry-run only until validation is complete" in patch
    assert "does not execute workflows" in patch
    assert "graph.nodes = graph.nodes.filter" not in patch
    assert "window.__aionWorkflowGraph.nodes = []" not in patch

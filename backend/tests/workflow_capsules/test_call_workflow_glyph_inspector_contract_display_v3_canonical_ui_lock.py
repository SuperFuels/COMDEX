from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: call_workflow_glyph Inspector Contract Display v3" in src
    assert "AION PATCH: call_workflow_glyph Inspector Takeover v4" in src
    return src.split("AION PATCH: call_workflow_glyph Inspector Contract Display v3", 1)[1].split(
        "AION PATCH: call_workflow_glyph Inspector Takeover v4", 1
    )[0]


def test_canonical_call_workflow_glyph_inspector_is_active_renderer():
    patch = _patch()

    assert "function readCallWorkflowGlyphContract(node)" in patch
    assert "function renderContractInspector(node)" in patch
    assert "data-aion-call-workflow-glyph-contract-inspector-v3" in patch
    assert "window.__readAionCallWorkflowGlyphContractV3 = readCallWorkflowGlyphContract" in patch
    assert "window.__renderAionCallWorkflowGlyphContractInspectorV3 = renderContractInspector" in patch

    # Legacy render paths must delegate to the canonical renderer.
    assert "window.__renderAionMasterGlyphContractInspectorV2 = renderContractInspector" in patch
    assert "window.renderAionMasterGlyphStagedNodeInspector = renderContractInspector" in patch


def test_canonical_inspector_reads_top_level_contract_before_config_or_compiled_fallbacks():
    patch = _patch()

    for field in [
        "node?.glyph_code",
        "node?.glyph_version",
        "node?.glyph_scope",
        "node?.child_workflow_id",
        "node?.input_schema",
        "node?.output_schema",
        "node?.required_connectors",
        "node?.approval_policy",
        "node?.runtime_plan",
        "node?.version_hash",
        "node?.risk_tier",
    ]:
        assert field in patch


def test_canonical_inspector_renders_all_required_contract_fields():
    patch = _patch()

    for label in [
        "CALL_WORKFLOW_GLYPH CONTRACT",
        "glyph_code",
        "glyph_version",
        "glyph_scope",
        "child_workflow_id",
        "glyph_id",
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
        "compiled_glyph debug",
    ]:
        assert label in patch


def test_canonical_inspector_includes_missing_connector_warning_and_dry_run_guard():
    patch = _patch()

    assert "function missingConnectors(required)" in patch
    assert "Missing connectors:" in patch
    assert "Required connectors available or not required." in patch
    assert "Runtime remains dry-run only until parent/child validation is complete." in patch
    assert "no external writes" in patch


def test_canonical_inspector_embeds_connection_preview_without_edge_creation():
    patch = _patch()

    assert "function renderConnectionPreviewSectionV11(node, model)" in patch
    assert "connection_preview" in patch
    assert "Preview-only · No edge creation · No execution · No editing · No wiring · No external writes" in patch
    assert "Possible inputs into staged glyph" in patch
    assert "Possible outputs from staged glyph" in patch

    # Inspector preview must not mutate graph edges.
    assert ".edges.push" not in patch
    assert "graph.edges =" not in patch
    assert "createEdge" not in patch


def test_canonical_inspector_close_and_scroll_locks_are_present():
    src = _src()

    for marker in [
        "AION PATCH: call_workflow_glyph Native Outer Scroll Stable v14",
        "AION PATCH: call_workflow_glyph Native Trackpad Scroll v15",
        "AION PATCH: call_workflow_glyph Inspector Details Click Isolation v16",
        "AION PATCH: call_workflow_glyph Source Close Fix v19",
    ]:
        assert marker in src

    assert "data-aion-call-workflow-glyph-close-v19" in src or "data-aion-call-workflow-glyph-close-v17" in src
    assert "data-aion-call-workflow-glyph-node-id" in src

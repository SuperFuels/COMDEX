from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    marker = "AION PATCH: call_workflow_glyph Inspector Contract Display v3"
    assert marker in src
    return src.split(marker, 1)[1]


def test_call_workflow_glyph_inspector_v3_patch_installed():
    patch = _patch()

    assert "window.__readAionCallWorkflowGlyphContractV3" in patch
    assert "window.__renderAionCallWorkflowGlyphContractInspectorV3" in patch
    assert "window.__debugAionCallWorkflowGlyphInspectorContractDisplayV3" in patch


def test_call_workflow_glyph_inspector_v3_shows_full_contract_fields():
    patch = _patch()

    required = [
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
    ]

    for field in required:
        assert field in patch


def test_call_workflow_glyph_inspector_v3_warns_missing_connectors():
    patch = _patch()

    assert "function missingConnectors" in patch
    assert "Missing connectors" in patch
    assert "Required connectors available or not required" in patch


def test_call_workflow_glyph_inspector_v3_preserves_safety_copy():
    patch = _patch()

    assert "Runtime remains dry-run only until parent/child validation is complete" in patch
    assert "dry-run only" in patch
    assert "no external writes" in patch


def test_call_workflow_glyph_inspector_v3_overrides_legacy_renderers():
    patch = _patch()

    assert "window.__renderAionMasterGlyphContractInspectorV2 = renderContractInspector" in patch
    assert "window.renderAionMasterGlyphStagedNodeInspector = renderContractInspector" in patch

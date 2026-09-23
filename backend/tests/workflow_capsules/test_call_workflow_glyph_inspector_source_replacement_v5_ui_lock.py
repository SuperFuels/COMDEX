from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def test_legacy_v3_sync_inspector_delegates_to_canonical_renderer():
    src = _src()

    assert "SOURCE FIX: Master Glyph Canvas v3 legacy inspector must no longer render" in src
    assert 'typeof window.__renderAionCallWorkflowGlyphContractInspectorV3 === "function"' in src
    assert "window.__renderAionCallWorkflowGlyphContractInspectorV3(node)" in src


def test_legacy_fallback_still_exists_for_safe_boot_order():
    src = _src()

    assert "wrapper.innerHTML = renderAionMasterGlyphStagedNodeInspector(node)" in src


def test_old_legacy_panel_text_still_exists_only_as_fallback_source():
    src = _src()

    assert "Master Glyph Canvas v3" in src
    assert "Staged workflow glyph" in src
    assert "call_workflow_glyph Inspector Contract Display v3" in src

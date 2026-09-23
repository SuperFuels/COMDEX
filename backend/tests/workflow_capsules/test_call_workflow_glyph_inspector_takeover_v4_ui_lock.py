from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    marker = "AION PATCH: call_workflow_glyph Inspector Takeover v4"
    assert marker in src
    return src.split(marker, 1)[1]


def test_takeover_v4_installed():
    patch = _patch()

    assert "window.__syncAionCallWorkflowGlyphInspectorTakeoverV4" in patch
    assert "window.__debugAionCallWorkflowGlyphInspectorTakeoverV4" in patch


def test_takeover_v4_removes_legacy_panels():
    patch = _patch()

    assert "removeLegacyInspectorPanels" in patch
    assert ".aion-master-glyph-staged-inspector:not([data-aion-call-workflow-glyph-contract-inspector-v3='true'])" in patch
    assert ".aion-master-glyph-connection-preview" in patch


def test_takeover_v4_renders_canonical_v3_panel():
    patch = _patch()

    assert "window.__renderAionCallWorkflowGlyphContractInspectorV3" in patch
    assert "data-aion-call-workflow-glyph-contract-inspector-v3" in patch
    assert "canonicalPanelCount" in patch


def test_takeover_v4_moves_panels_below_header():
    patch = _patch()

    assert "top: 156px !important" in patch
    assert "max-height: calc(100vh - 180px) !important" in patch


def test_takeover_v4_has_no_observer_or_interval_loop():
    patch = _patch()

    assert "MutationObserver" not in patch
    assert "setInterval" not in patch

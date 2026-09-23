from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def _v4_block() -> str:
    src = _src()
    start = src.index("AION PATCH: Master Glyph Canvas v4 staged glyph connection preview")
    end = src.index("AION PATCH: Master Glyph Canvas v5 staged connection confirm", start)
    return src[start:end]


def test_legacy_v4_connection_preview_is_source_disabled():
    block = _v4_block()

    assert "SOURCE DISABLE: legacy Master Glyph Canvas v4 connection preview is retired" in block
    assert "panel.remove();" in block
    assert "document.body.appendChild(panel);" not in block


def test_canonical_call_workflow_inspector_remains_active():
    src = _src()

    assert "AION PATCH: call_workflow_glyph Inspector Contract Display v3" in src
    assert "AION PATCH: call_workflow_glyph Inspector Takeover v4" in src
    assert "window.__renderAionCallWorkflowGlyphContractInspectorV3" in src

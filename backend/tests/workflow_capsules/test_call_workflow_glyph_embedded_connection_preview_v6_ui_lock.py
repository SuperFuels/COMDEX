from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def test_v4_left_preview_is_not_appended_as_separate_panel():
    src = _src()
    start = src.index("AION PATCH: Master Glyph Canvas v4 staged glyph connection preview")
    end = src.index("AION PATCH: Master Glyph Canvas v5 staged connection confirm", start)
    block = src[start:end]

    assert "SOURCE MERGE: v4 connection preview is now rendered inside" in block
    assert "panel.remove();" in block


def test_connection_preview_is_embedded_in_right_contract_inspector():
    src = _src()

    assert "function renderConnectionPreviewSection(node, model)" in src
    assert "readConnectionPreview(node, model)" in src
    assert "Possible inputs into staged glyph" in src
    assert "Possible outputs from staged glyph" in src
    assert "renderConnectionPreviewSection(node, model)" in src


def test_embedded_preview_keeps_no_execution_safety_copy():
    src = _src()

    assert "Preview-only · No edge creation · No execution · No editing · No wiring · No external writes" in src
    assert ".aion-call-glyph-connection-preview-v6" in src

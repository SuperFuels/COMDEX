from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def test_e10_glyph_button_restore_installed() -> None:
    text = _text()
    assert "Glyph Library Button Direct Restore E10" in text
    assert "window.__openAionGlyphLibraryCanonical = openCanonicalGlyphLibrary" in text
    assert "window.__openAionWorkflowGlyphLibrary = openCanonicalGlyphLibrary" in text


def test_e10_button_uses_canonical_marketplace_modal_first() -> None:
    text = _text()
    start = text.index("Glyph Library Button Direct Restore E10")
    end = text.find("Glyph Library Button Direct Restore E11", start)
    block = text[start:end if end != -1 else len(text)]
    assert "__renderAionGlyphMarketplaceModal" in block
    assert "__openAionWorkflowGlyphLibrary" in block


def test_e10_binds_legacy_and_current_button_attrs() -> None:
    text = _text()
    start = text.index("Glyph Library Button Direct Restore E10")
    end = text.find("Glyph Library Button Direct Restore E11", start)
    block = text[start:end if end != -1 else len(text)]
    assert "data-aion-workflow-glyph-library-open" in block
    assert "data-aion-glyph-library-v37-open" in block
    assert "data-aion-glyph-library-force-open-v4" in block
    assert "data-aion-glyph-library-direct-restore-e10" in block


def test_e10_does_not_touch_graph_or_request_render() -> None:
    text = _text()
    start = text.index("Glyph Library Button Direct Restore E10")
    end = text.find("Glyph Library Button Direct Restore E11", start)
    block = text[start:end if end != -1 else len(text)]
    assert "__aionWorkflowGraph =" not in block
    assert "__aionOpenedGlyphWorkflowGraph =" not in block
    assert "__aionWorkflowMainGraph =" not in block
    assert "requestRender =" not in block
    assert "DOM watch hook" not in block

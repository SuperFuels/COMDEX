from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def test_glyph_library_button_restore_installed() -> None:
    text = _text()
    assert "Glyph Library Button Canonical Restore v1" in text
    assert "window.__openAionGlyphLibraryCanonical" in text
    assert "installAionGlyphLibraryButtonCanonicalRestoreV1" in text


def test_glyph_library_button_has_multiple_legacy_selector_fallbacks() -> None:
    text = _text()
    block = text[text.index("Glyph Library Button Canonical Restore v1"):]
    assert "[data-aion-open-glyph-library]" in block
    assert "[data-aion-glyph-library-open]" in block
    assert "[data-aion-master-glyph-library-open]" in block
    assert "[data-workflow-toolbar-glyph-library]" in block


def test_glyph_library_button_does_not_assign_request_render() -> None:
    text = _text()
    block = text[text.index("Glyph Library Button Canonical Restore v1"):]
    assert "requestRender =" not in block
    assert "MutationObserver" not in block


def test_glyph_library_button_does_not_call_contract_inspector() -> None:
    text = _text()
    block = text[text.index("Glyph Library Button Canonical Restore v1"):]
    assert "CALL_WORKFLOW_GLYPH CONTRACT" not in block
    assert "contract inspector" not in block.lower()

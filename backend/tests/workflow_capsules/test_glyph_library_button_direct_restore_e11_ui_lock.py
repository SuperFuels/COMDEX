from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def _e11_block() -> str:
    text = _text()
    marker = "AION PATCH: Glyph Library Button Direct Restore E11"
    assert marker in text
    start = text.index(marker)
    end = text.find("\n})();", start)
    assert end != -1
    return text[start:end + len("\n})();")]


def test_e11_restore_installed_and_non_recursive() -> None:
    block = _e11_block()
    assert "window.__openAionWorkflowGlyphLibrary = openCanonicalGlyphLibrary" in block
    assert "window.__openAionGlyphLibraryCanonical = openCanonicalGlyphLibrary" in block
    assert "window.__openAionWorkflowGlyphLibrary();" not in block


def test_e11_matches_real_toolbar_button_attrs() -> None:
    block = _e11_block()
    assert "data-aion-workflow-glyph-library-open" in block
    assert "data-aion-glyph-library-open" in block
    assert "data-aion-glyph-library-direct-restore-e11" in block


def test_toolbar_simplify_keeps_real_button_visible() -> None:
    text = _text()
    assert '.aion-workflow-floating-toolbar-consolidated [data-aion-workflow-glyph-library-open="true"]' in text
    assert '.aion-workflow-floating-toolbar-consolidated [data-aion-glyph-library-direct-restore-e11="true"]' in text


def test_render_card_uses_glyph_not_undefined_item() -> None:
    text = _text()
    assert 'data-glyph-code="${esc(glyph.glyph_code || glyph.glyphCode || glyph.code || \'\')}"' in text
    assert 'data-glyph-code="${esc(item.glyph_code || item.glyphCode || item.code || \'\')}"' not in text

from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def _e12_block() -> str:
    text = _text()
    marker = "AION PATCH: Glyph Library Button Hard Bind E12"
    assert marker in text
    start = text.index(marker)
    end = text.find("\n})();", start)
    assert end != -1
    return text[start:end + len("\n})();")]


def test_e12_installed() -> None:
    block = _e12_block()
    assert "installAionGlyphLibraryButtonHardBindE12" in block
    assert "window.__debugAionGlyphLibraryButtonE12" in block


def test_e12_uses_window_capture_before_old_document_handlers() -> None:
    block = _e12_block()
    assert 'window.addEventListener("click", handleGlyphLibraryClick, true)' in block


def test_e12_directly_binds_real_button_onclick() -> None:
    block = _e12_block()
    assert 'button.onclick = function onGlyphLibraryButtonDirectClick' in block
    assert 'data-aion-glyph-library-hard-bind-e12' in block


def test_e12_opens_marketplace_renderer_not_recursive_opener() -> None:
    block = _e12_block()
    assert "__renderAionGlyphMarketplaceModal" in block
    assert "window.__openAionWorkflowGlyphLibrary();" not in block
    assert "window.__openAionGlyphLibraryCanonical();" not in block


def test_e12_does_not_mutate_workflow_graphs() -> None:
    block = _e12_block()
    assert "__aionWorkflowGraph =" not in block
    assert "__aionWorkflowMainGraph =" not in block
    assert "__aionOpenedGlyphWorkflowGraph =" not in block

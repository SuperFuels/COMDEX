from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def test_call_workflow_glyph_inspector_scroll_lock_installed():
    src = _src()

    assert "AION PATCH: call_workflow_glyph Inspector Scroll Lock v7" in src
    assert "window.__debugAionCallWorkflowGlyphInspectorScrollLockV7" in src


def test_inspector_owns_internal_scroll():
    src = _src()

    assert "overflow-y: auto !important" in src
    assert "overscroll-behavior: contain !important" in src
    assert "document.addEventListener(\"wheel\", stopPanelScrollSteal" in src
    assert "document.addEventListener(\"touchmove\", stopPanelScrollSteal" in src
    assert "event.stopImmediatePropagation?.()" in src


def test_embedded_connection_preview_remains_reachable():
    src = _src()

    assert ".aion-call-glyph-connection-preview-v6" in src
    assert "connectionPreviewCount" in src

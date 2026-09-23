from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_glyph_library_instant_open_lock_installed():
    src = _src()

    assert "AION PATCH: Glyph Library Instant Open Lock v7" in src
    assert "window.__openAionWorkflowGlyphLibrary = openGlyphLibraryInstantly" in src
    assert "window.__debugAionGlyphLibraryInstantOpenV7" in src


def test_glyph_library_open_does_not_block_on_refresh():
    src = _src()
    patch = src.split("AION PATCH: Glyph Library Instant Open Lock v7", 1)[1]

    assert "renderLibraryNow();" in patch
    assert "refreshInBackground();" in patch
    assert "await window.__refreshAionWorkflowGlyphsFromApi" not in patch
    assert "await refresh" not in patch


def test_glyph_library_button_captures_all_legacy_selectors():
    src = _src()
    patch = src.split("AION PATCH: Glyph Library Instant Open Lock v7", 1)[1]

    for marker in [
        "data-aion-workflow-glyph-library-open",
        "data-aion-glyph-library-v37-open",
        "data-aion-glyph-library-hard-open-v2",
        "data-aion-glyph-library-force-open-v3",
        "data-aion-glyph-library-force-open-v4",
        "data-aion-glyph-library-instant-open-v7",
    ]:
        assert marker in patch

    assert "event.stopImmediatePropagation" in patch

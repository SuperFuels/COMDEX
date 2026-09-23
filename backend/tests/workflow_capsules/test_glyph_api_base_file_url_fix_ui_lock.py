from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    assert "AION PATCH: Glyph API Base File URL Fix v3" in src
    return src.split("AION PATCH: Glyph API Base File URL Fix v3", 1)[1]


def test_file_url_api_base_is_rejected():
    patch = _patch()

    assert "function isBadApiBase(value)" in patch
    assert 'text.startsWith("file:")' in patch
    assert 'text.includes("file:///")' in patch
    assert '"http://127.0.0.1:8080"' in patch
    assert '"http://localhost:8080"' in patch


def test_refresh_function_is_overridden_to_hard_refresh():
    patch = _patch()

    assert "window.__refreshAionWorkflowGlyphsFromApi = hardRefreshGlyphs" in patch
    assert "window.__openAionWorkflowGlyphLibrary = hardOpenGlyphLibrary" in patch
    assert "window.__forceOpenBackendGlyphLibrary = hardOpenGlyphLibrary" in patch
    assert "window.__debugAionGlyphApiBaseFileUrlFixV3" in patch


def test_glyph_library_button_force_bound():
    patch = _patch()

    assert "data-aion-glyph-library-force-open-v3" in patch
    assert "forceBindGlyphLibraryButtons" in patch
    assert "event.stopImmediatePropagation" in patch

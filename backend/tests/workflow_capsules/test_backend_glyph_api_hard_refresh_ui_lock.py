from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_backend_glyph_hard_refresh_patch_installed():
    src = _src()

    assert "AION PATCH: Backend Glyph API Hard Refresh v2" in src
    assert "window.__refreshAionWorkflowGlyphsFromApi = hardRefreshBackendGlyphs" in src
    assert "window.__debugAionBackendGlyphHardRefreshV2" in src


def test_backend_glyph_hard_refresh_tries_local_api_bases():
    src = _src()

    assert "http://127.0.0.1:8080" in src
    assert "http://localhost:8080" in src
    assert 'localStorage.setItem("aion.apiBase", result.base)' in src
    assert 'cache: "no-store"' in src


def test_backend_glyph_hard_refresh_marks_backend_source():
    src = _src()

    assert 'source: "backend_glyph_store"' in src
    assert "glyph_codes: result.glyphs.map((g) => g.glyph_code)" in src
    assert "Glyph Library opened with" in src

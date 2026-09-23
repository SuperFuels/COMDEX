from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def test_master_glyph_phase1_single_mode_lock_installed() -> None:
    text = APP_JS.read_text(encoding="utf-8")

    assert "installAionMasterGlyphPhase1SingleModeLock" in text
    assert "window.__setAionCanvasMode = setCanvasMode" in text
    assert 'window.__aionCanvasMode === "master_glyph"' in text
    assert "window.__aionMasterGlyphCanvasOpen = window.__aionCanvasMode === \"master_glyph\"" in text


def test_master_glyph_toolbar_has_only_primary_canvas_switch_buttons() -> None:
    text = APP_JS.read_text(encoding="utf-8")

    assert 'data-aion-canvas-mode="workflow"' in text
    assert 'data-aion-canvas-mode="master_glyph"' in text

    # Legacy overlay launcher should be disabled by the Phase 1 lock.
    assert "renderAionMasterGlyphCanvasLauncherPhase1Disabled" in text
    assert "return \"\";" in text


def test_master_glyph_mode_controls_are_delegated_after_rerender() -> None:
    text = APP_JS.read_text(encoding="utf-8")

    assert 'document.addEventListener("click", (event) =>' in text
    assert 'event.target.closest?.("[data-aion-canvas-mode]")' in text
    assert 'window.addEventListener("aion:workflow-rendered", syncAfterRender)' in text
    assert 'button.setAttribute("aria-pressed", active ? "true" : "false")' in text


def test_master_glyph_canvas_is_separate_mode_not_overlay_source() -> None:
    text = APP_JS.read_text(encoding="utf-8")

    assert 'body.aion-master-glyph-canvas-mode' in text
    assert "window.__openAionMasterGlyphCanvas = () => setCanvasMode(\"master_glyph\")" in text
    assert "window.__closeAionMasterGlyphCanvas = () => setCanvasMode(\"workflow\")" in text

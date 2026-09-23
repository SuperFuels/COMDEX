from pathlib import Path


APP = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_zoom_controls_are_owned_by_the_single_workflow_footer():
    text = source()
    toolbar_start = text.index("function renderAionWorkflowFloatingToolbar()")
    toolbar_end = text.index("function renderAionWorkflowCanvasPanel", toolbar_start)
    toolbar = text[toolbar_start:toolbar_end]

    assert 'class="aion-workflow-footer-zoom"' in toolbar
    assert 'data-aion-canvas-zoom="fit"' in toolbar
    assert 'data-aion-canvas-zoom="in"' in toolbar
    assert 'data-aion-canvas-zoom="out"' in toolbar
    assert 'data-aion-workflow-dark-mode-toggle="true"' in toolbar
    assert '<div class="aion-workflow-zoom"' not in text


def test_footer_has_one_final_fixed_visual_system():
    text = source()
    start = text.index("/* AION PATCH: unified workflow footer v32")
    lock = text[start:]

    assert 'position: fixed !important;' in lock
    assert 'bottom: 16px !important;' in lock
    assert 'border-top: 2px solid #8ecbff !important;' in lock
    assert 'background: rgba(255,255,255,0.97) !important;' in lock
    assert 'height: 38px !important;' in lock
    assert 'background: #111827 !important;' in lock
    assert 'background: #eaf4ff !important;' in lock


def test_every_visible_footer_control_has_one_exact_outer_height():
    text = source()
    start = text.index("/* AION PATCH: unified workflow footer exact-height lock v33")
    lock = text[start:]

    assert "Every visible control container is exactly 48px tall" in lock
    assert "> .aion-workflow-footer-zoom," in lock
    assert "> button.aion-workflow-execute-btn," in lock
    assert "> button.aion-workflow-mode-btn," in lock
    assert "> button.aion-workflow-publish-toolbar-btn," in lock
    assert "> button.aion-phase19d-note-toolbar-button," in lock
    assert 'data-aion-phase19d-add-canvas-note="true"' in lock
    assert "height: 48px !important;" in lock
    assert "min-height: 48px !important;" in lock
    assert "max-height: 48px !important;" in lock


def test_compact_footer_keeps_note_visible_and_shortens_clear_glyphs():
    text = source()
    toolbar_start = text.index("function renderAionWorkflowFloatingToolbar()")
    toolbar_end = text.index("function renderAionWorkflowCanvasPanel", toolbar_start)
    toolbar = text[toolbar_start:toolbar_end]
    compact_start = text.index("/* AION PATCH: compact workflow footer widths v34")
    compact = text[compact_start:]

    assert ">Clear staged glyphs<" not in toolbar
    assert "Clear glyphs" in toolbar
    assert 'data-aion-unified-builder-mode="assisted"' in compact
    assert 'data-aion-unified-builder-mode="describe"' in compact
    assert "width: 104px !important;" in compact
    assert "width: 154px !important;" in compact
    assert 'data-aion-master-glyph-clear-staged="true"' in compact
    assert "width: 106px !important;" in compact
    assert 'data-aion-phase19d-add-canvas-note="true"' in compact
    assert "order: 8 !important;" in compact


def test_note_insertion_targets_the_direct_footer_add_button():
    text = source()
    assert 'toolbar.querySelector(":scope > .aion-workflow-floating-add")' in text

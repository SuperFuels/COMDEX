from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_tabs_are_not_deleted_after_render():
    assert 'document.getElementById("aion-glyph-workflow-top-tabs-v2")?.remove();' not in TEXT
    assert "renderWorkflowTabOverlay" in TEXT
    assert "window.__aionRenderWorkflowCanvasTabs" in TEXT


def test_phase25k_final_top_margin_lock_exists():
    assert "aion-phase25k-workflow-tabs-and-top-margin-final-lock" in TEXT
    assert "top: 0 !important" in TEXT
    assert "left: 56px !important" in TEXT
    assert "width: calc(100vw - 56px) !important" in TEXT


def test_phase25k_workflow_tabs_forced_visible_after_sidebar():
    assert "html body.aion-phase19c-workflow-visible #aion-glyph-workflow-top-tabs-v2" in TEXT
    assert "html body.aion-phase19c-workflow-visible [data-aion-workflow-tab-strip='true']" in TEXT
    assert "display: flex !important" in TEXT
    assert "visibility: visible !important" in TEXT
    assert "opacity: 1 !important" in TEXT
    assert "top: 116px !important" in TEXT


def test_phase25k_sidebar_padding_is_zero_in_workflow_canvas():
    assert "html body.aion-phase19c-workflow-visible .aion-main-sidebar" in TEXT
    assert "width: 56px !important" in TEXT
    assert "padding: 0 !important" in TEXT
    assert "gap: 0 !important" in TEXT

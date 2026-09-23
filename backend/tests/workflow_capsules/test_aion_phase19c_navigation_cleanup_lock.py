from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def phase19c_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19C Workflow Canvas Navigation Cleanup Lock")
    end = text.index("console.log(\"[AION] Phase 19C workflow canvas navigation cleanup lock installed\");", start)
    return text[start:end]


def test_phase19c_lock_installed() -> None:
    block = phase19c_block()
    assert "installAionPhase19CWorkflowCanvasNavigationCleanupLock" in block
    assert "__syncAionPhase19CNavigationCleanup" in block
    assert "aion-phase19c-workflow-visible" in block


def test_phase19c_workflow_tab_strip_only_visible_on_workflow_canvas() -> None:
    block = phase19c_block()
    assert "body:not(.aion-phase19c-workflow-visible) #aion-glyph-workflow-top-tabs-v2" in block
    assert "display: none !important" in block
    assert "body.aion-phase19c-workflow-visible #aion-glyph-workflow-top-tabs-v2" in block
    assert "isWorkflowCanvasVisible" in block


def test_phase19c_sidebar_logo_overlap_guard_exists() -> None:
    block = phase19c_block()
    assert ".aion-workflow-sidebar" in block
    assert ".aion-workflow-logo" in block
    assert "z-index: 40 !important" in block
    assert "z-index: 90 !important" in block


def test_phase19c_sidebar_icons_are_restyled() -> None:
    block = phase19c_block()
    assert ".aion-workflow-nav-btn" in block
    assert ".aion-workflow-nav-icon" in block
    assert "border-radius: 16px !important" in block
    assert "place-items: center !important" in block


def test_phase19c_empty_orchestrated_glyphs_panel_hidden() -> None:
    block = phase19c_block()
    assert "hideEmptyOrchestratedGlyphsPanel" in block
    assert "Orchestrated Glyphs" in block
    assert "No orchestrated child glyphs attached yet" in block
    assert "aion-phase19c-hidden-empty-orchestrated-glyphs" in block


def test_phase19c_does_not_enable_live_execution() -> None:
    block = phase19c_block()
    forbidden = [
        "fetch(",
        "sendEmail",
        "payment_created = true",
        "booking_created = true",
        "external_writes_enabled = true",
    ]
    for token in forbidden:
        assert token not in block

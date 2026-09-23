from __future__ import annotations

from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text()


def test_phase24c_foundation_review_panel_exists():
    assert "function renderSmallBusinessFoundationReviewPanel" in APP_JS
    assert 'data-aion-phase24c-foundation-review' in APP_JS
    assert "Foundation review" in APP_JS
    assert "Approve foundation" in APP_JS
    assert "Revise foundation" in APP_JS


def test_phase24c_generate_foundation_renders_review_panel():
    assert "${renderSmallBusinessFoundationReviewPanel(draft)}" in APP_JS
    assert "state.smallBusinessFoundationPreviewReady =" in APP_JS
    assert "getSmallBusinessFoundationMissingRequired(draft).length === 0" in APP_JS


def test_phase24c_approve_and_revise_controls_are_wired():
    assert 'event.target?.closest?.("[data-aion-phase24c-approve-foundation]")' in APP_JS
    assert 'event.target?.closest?.("[data-aion-phase24c-revise-foundation]")' in APP_JS
    assert "state.smallBusinessFoundationApproved = state.smallBusinessFoundationPreviewReady" in APP_JS
    assert "state.smallBusinessFoundationApproved = false" in APP_JS


def test_phase24c_boardroom_continue_requires_approved_review():
    review_start = APP_JS.index("function renderSmallBusinessFoundationReviewPanel")
    review_block = APP_JS[review_start:APP_JS.index("function renderSmallBusinessFoundationSetupSurface")]
    assert "Continue to Boardroom" in review_block
    assert "approved" in review_block
    assert 'data-aion-phase24b-continue-departments' in review_block

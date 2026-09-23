from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12i_patch_installed():
    assert "BEGIN AION O12I REAL ADD STEP STYLE GOAL DOCUMENT MODAL" in APP_JS
    assert "real Add Step-style Goal Sheet document modal installed" in APP_JS


def test_o12i_targets_real_document_card_not_old_drawer_shell():
    assert "findActualDocumentCard" in APP_JS
    assert "candidateScore" in APP_JS
    assert "Prefer the real document card, not the huge empty wrapper" in APP_JS
    assert "area > 900000" in APP_JS
    assert "width > 1150" in APP_JS


def test_o12i_forces_add_step_modal_geometry():
    assert "data-aion-o12i-goal-document-modal" in APP_JS
    assert 'width: min(1080px, calc(100vw - 220px)) !important' in APP_JS
    assert 'height: min(680px, calc(100vh - 160px)) !important' in APP_JS
    assert 'transform: translate(-50%, -50%) !important' in APP_JS
    assert 'border-radius: 20px !important' in APP_JS


def test_o12i_header_and_body_are_full_width():
    assert "data-aion-o12i-goal-document-header" in APP_JS
    assert "data-aion-o12i-goal-document-body" in APP_JS
    assert "markHeaderAndBody" in APP_JS
    assert "width: 100% !important" in APP_JS
    assert "max-width: none !important" in APP_JS


def test_o12i_neutralises_old_blank_wrapper_and_backdrop():
    assert "neutraliseOldWrappers" in APP_JS
    assert "data-aion-o12i-goal-document-backdrop" in APP_JS
    assert "background: transparent !important" in APP_JS
    assert "backdrop-filter: none !important" in APP_JS


def test_o12i_exposes_console_helper():
    assert "window.aionApplyRealAddStepStyleGoalDocumentModalO12I" in APP_JS

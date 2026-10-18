from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/rfc/aion_phase13_home_fixed_vertical_workflow_regression_lock.tex"


def _doc() -> str:
    return DOC.read_text()


def test_phase13_home_fixed_doc_exists():
    assert DOC.exists()


def test_phase13_home_fixed_doc_has_title_and_status():
    text = _doc()
    assert "Phase 13I" in text
    assert "Home Fixed Vertical Workflow Regression v0" in text
    assert "Status:" in text


def test_phase13_home_fixed_doc_lists_identity_terms():
    text = _doc()
    for term in [
        "home\\_fixed",
        "home\\_repair",
        "Home Fixed",
    ]:
        assert term in text


def test_phase13_home_fixed_doc_lists_preview_contract():
    text = _doc()
    for term in [
        "preview-only",
        "human\\_review\\_required",
        "would\\_create\\_payment",
        "would\\_create\\_booking",
        "would\\_create\\_escrow",
        "would\\_send\\_external\\_message",
    ]:
        assert term in text


def test_phase13_home_fixed_doc_lists_forbidden_side_effects():
    text = _doc()
    for term in [
        "auto\\_confirm\\_booking",
        "auto\\_dispatch\\_job",
        "capture\\_payment",
        "release\\_escrow",
        "send\\_email",
        "send\\_sms",
        "live\\_job\\_created",
        "booking\\_confirmed",
        "payment\\_captured",
        "escrow\\_released",
        "external\\_message\\_sent",
    ]:
        assert term in text


def test_phase13_home_fixed_doc_has_validation_commands_and_footer():
    text = _doc()
    assert "test_aion_phase13_home_fixed_vertical_workflow_regression_lock.py" in text
    assert "run_goal_engine_focused_lock_suite.sh" in text
    assert "AION-PHASE13I-HOME-FIXED-VERTICAL-WORKFLOW-REGRESSION-V0" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/rfc/aion_phase13_negotiation_boundary_regression_lock.tex"


def _doc() -> str:
    return DOC.read_text().lower()


def test_phase13_negotiation_boundary_lock_doc_exists():
    assert DOC.exists()


def test_phase13_negotiation_boundary_lock_doc_status_locked():
    text = _doc()
    assert "status: locked" in text
    assert "negotiation boundary" in text


def test_phase13_negotiation_boundary_lock_doc_mentions_regression_boundary():
    text = _doc()
    assert "regression boundary" in text
    assert "safety contract" in text


def test_phase13_negotiation_boundary_lock_doc_mentions_no_live_side_effects():
    text = _doc()
    for term in [
        "must not",
        "live payment capture",
        "escrow release",
        "booking confirmation",
        "external messages",
    ]:
        assert term in text


def test_phase13_negotiation_boundary_lock_doc_has_validation_commands():
    text = _doc()
    assert "python -m pytest -q" in text
    assert "scripts/run_goal_engine_focused_lock_suite.sh" in text


def test_phase13_negotiation_boundary_lock_doc_has_footer():
    text = _doc()
    for term in [
        "lock id: aion-phase13-negotiation-boundary-v0.1",
        "maintainer: tessaris ai",
        "author: kevin robinson",
    ]:
        assert term in text

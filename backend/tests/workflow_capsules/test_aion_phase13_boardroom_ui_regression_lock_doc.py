from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/rfc/aion_phase13_boardroom_ui_regression_lock.tex"


def _doc() -> str:
    return DOC.read_text().lower()


def test_phase13_boardroom_ui_lock_doc_exists():
    assert DOC.exists()


def test_phase13_boardroom_ui_lock_doc_status_locked():
    text = _doc()
    assert "status: locked" in text
    assert "boardroom ui regression" in text


def test_phase13_boardroom_ui_lock_doc_mentions_parallel_twin():
    text = _doc()
    assert "parallel business twin" in text
    assert "home fixed" in text


def test_phase13_boardroom_ui_lock_doc_mentions_safety_contract():
    text = _doc()
    for term in [
        "must not",
        "capture payment",
        "release escrow",
        "confirm bookings",
        "send external messages",
    ]:
        assert term in text


def test_phase13_boardroom_ui_lock_doc_has_validation_commands():
    text = _doc()
    assert "python -m pytest -q" in text
    assert "scripts/run_goal_engine_focused_lock_suite.sh" in text


def test_phase13_boardroom_ui_lock_doc_has_footer():
    text = _doc()
    for term in [
        "lock id: aion-phase13-boardroom-ui-regression-v0.1",
        "maintainer: tessaris ai",
        "author: kevin robinson",
    ]:
        assert term in text

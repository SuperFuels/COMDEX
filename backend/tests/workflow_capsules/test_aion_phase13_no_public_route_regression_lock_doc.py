from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_no_public_route_regression_lock.tex")


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_no_public_route_doc_exists():
    assert DOC.exists()


def test_phase13_no_public_route_doc_names_phase():
    text = _text()
    assert "Phase 13F --- No-Public-Route Regression v0" in text


def test_phase13_no_public_route_doc_lists_forbidden_routes():
    text = _text()
    for term in [
        "/api/aion-gateway/intent",
        "/api/aion\\_gateway/intent",
        "/aion-gateway/intent",
        "/aion\\_gateway/intent",
        "/api/public/aion-gateway",
        "/api/public/aion\\_gateway",
        "/api/embed/aion",
        "/api/widget/aion",
    ]:
        assert term in text


def test_phase13_no_public_route_doc_lists_safety_flags():
    text = _text()
    for term in [
        "preview_only = true",
        "human_review_required = true",
        "public_route_mounted = false",
        "unauthenticated_public_write_route_exposed = false",
        "would_create_booking = false",
        "would_create_live_job = false",
        "would_execute_goal_engine = false",
        "would_move_money = false",
        "would_create_payment = false",
        "would_create_escrow = false",
        "would_release_funds = false",
        "would_send_external_messages = false",
    ]:
        assert term in text


def test_phase13_no_public_route_doc_lists_validation_commands():
    text = _text()
    assert "test_aion_phase13_no_public_route_regression_lock.py" in text
    assert "test_aion_phase13_no_public_route_regression_lock_doc.py" in text
    assert "bash scripts/run_goal_engine_focused_lock_suite.sh" in text
    assert "python -m compileall backend/modules/aion_gateway" in text


def test_phase13_no_public_route_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text

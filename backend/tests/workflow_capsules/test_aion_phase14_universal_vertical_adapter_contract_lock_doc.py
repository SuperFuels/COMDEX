from pathlib import Path


DOC = Path("docs/rfc/aion_phase14_universal_vertical_adapter_contract_lock.tex")


def _text() -> str:
    assert DOC.exists()
    return DOC.read_text().lower()


def test_phase14b_doc_has_status_and_lock_footer():
    text = _text()

    assert "status: locked" in text
    assert "lock id:" in text
    assert "aion-phase14b-universal-vertical-adapter-contract-v0.1" in text
    assert "maintainer:} tessaris ai" in text
    assert "author:} kevin robinson" in text


def test_phase14b_doc_mentions_required_contract_terms():
    text = _text()

    for term in [
        "universal vertical adapter",
        "home fixed",
        "home repair",
        "not a trade-only",
        "future verticals",
        "legal",
        "ecommerce",
        "hospitality",
        "clinic",
        "property",
        "b2b supplier",
        "adapter_hash",
        "summary_hash",
        "preview-only",
        "human review",
    ]:
        assert term in text


def test_phase14b_doc_locks_safety_boundary_terms():
    text = _text()

    for term in [
        "would_create_booking = false",
        "would_create_live_job = false",
        "would_execute_goal_engine = false",
        "would_move_money = false",
        "would_move_pho = false",
        "would_require_wallet = false",
        "would_create_payment = false",
        "would_create_escrow = false",
        "would_release_funds = false",
        "would_send_external_messages = false",
        "would_dispatch_job = false",
        "would_write_live_chain = false",
        "public_route_mounted = false",
    ]:
        assert term in text


def test_phase14b_doc_names_implementation_and_tests():
    text = _text()

    assert "backend/modules/aion_gateway/universal_vertical_adapter.py" in text
    assert "test_aion_phase14_universal_vertical_adapter_contract_lock.py" in text
    assert "test_aion_phase14_universal_vertical_adapter_contract_lock_doc.py" in text
    assert "scripts/run_goal_engine_focused_lock_suite.sh" in text

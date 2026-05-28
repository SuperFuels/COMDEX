from pathlib import Path


DOC = Path("docs/rfc/aion_phase13_trust_reputation_regression_lock.tex")


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_phase13_trust_reputation_doc_exists():
    assert DOC.exists()


def test_phase13_trust_reputation_doc_title_and_status():
    text = _doc()
    assert "Phase 13H --- Trust/Reputation Regression v0" in text
    assert "Status: LOCKED" in text


def test_phase13_trust_reputation_doc_lists_contract_terms():
    text = _doc()
    for term in [
        "read-model",
        "preview-only",
        "human review",
        "deterministic",
    ]:
        assert term in text


def test_phase13_trust_reputation_doc_lists_forbidden_side_effects():
    text = _doc()
    for term in [
        "create\\_payment",
        "capture\\_payment",
        "release\\_payment",
        "release\\_escrow",
        "transfer\\_funds",
        "create\\_booking",
        "book\\_job",
        "dispatch\\_job",
        "send\\_external\\_message",
        "auto\\_approve\\_by\\_reputation",
    ]:
        assert term in text


def test_phase13_trust_reputation_doc_lists_random_identity_forbidden_terms():
    text = _doc()
    for term in [
        "uuid.uuid4",
        "random.uuid",
        "secrets.token",
        "random\\_id",
        "runtime\\_random",
    ]:
        assert term in text


def test_phase13_trust_reputation_doc_has_lock_footer():
    text = _doc()
    assert "Lock ID: AION-PHASE13H-TRUST-REPUTATION-REGRESSION-V0" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text

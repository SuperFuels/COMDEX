from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_a2a_contract_schemas_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_a2a_contract_schema_lock_doc_exists():
    assert DOC.exists()
    assert "AION Gateway A2A Contract Schemas v0.1 Lock" in _text()


def test_a2a_contract_schema_lock_doc_lists_all_contracts():
    text = _text()
    for name in [
        "CapabilityContract",
        "AvailabilityContract",
        "QuoteContract",
        "ExecutionContract",
        "TraceContract",
        "EvidenceContract",
        "ExceptionContract",
        "SettlementReadinessContract",
        "ProofCommitmentContract",
    ]:
        assert name in text


def test_a2a_contract_schema_lock_doc_keeps_safety_boundary():
    text = _text()
    assert "MUST NOT expose public routes" in text
    assert "MUST NOT execute workflows" in text
    assert "MUST NOT create payments" in text
    assert "MUST NOT commit to GlyphChain" in text
    assert "MUST NOT grant permissions" in text


def test_a2a_contract_schema_lock_doc_states_hash_rule():
    text = _text()
    assert "json.dumps" in text
    assert "sort_keys=True" in text
    assert "hashlib.sha256" in text
    assert "MUST NOT grant permission" in text
    assert "MUST NOT trigger execution" in text


def test_a2a_contract_schema_lock_doc_states_fiat_and_proof_boundary():
    text = _text()
    assert "fiat-first" in text
    assert "MUST NOT require PHO, token, wallet, or blockchain settlement" in text
    assert "proof/documentation rail, not a payment rail" in text


def test_a2a_contract_schema_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text

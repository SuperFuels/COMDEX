from backend.modules.aion_gateway.glyphchain_proof_commit import preview_job_proof_commit
from backend.modules.chain_sim.aion_proof_commit_store import reset_aion_proof_commit_store
from backend.modules.chain_sim.aion_proof_receipts import (
    AION_PROOF_RECEIPT_VERSION,
    internal_commit_aion_proof_and_build_receipt,
    internal_lookup_aion_proof_receipt,
    internal_verify_aion_proof_receipt,
)


def setup_function():
    reset_aion_proof_commit_store()


def _preview(job_id="job_001"):
    return preview_job_proof_commit(
        business_id="BIZ_123",
        job_id=job_id,
        job_proof_hash=f"jobhash_{job_id}",
        evidence_proof_hashes=["ev1", "ev2"],
        settlement_readiness_proof_hash="settlehash",
    )


def _commit(job_id="job_001"):
    preview = _preview(job_id)
    committed = internal_commit_aion_proof_and_build_receipt(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )
    return preview, committed


def test_internal_commit_builds_verified_receipt():
    preview, committed = _commit()

    assert committed["ok"] is True
    assert committed["verified"] is True
    assert committed["proof_commitment_id"].startswith("aion_proof_")

    receipt = committed["receipt"]
    assert receipt["receipt_version"] == AION_PROOF_RECEIPT_VERSION
    assert receipt["proof_commitment_id"] == committed["proof_commitment_id"]
    assert receipt["proof_commitment_hash"] == preview["proof_commitment_hash"]
    assert receipt["proof_type"] == "AION_JOB_PROOF_V1"
    assert receipt["business_id"] == "biz_123"
    assert receipt["job_id"] == "job_001"
    assert receipt["receipt_status"] == "verified"


def test_internal_lookup_returns_committed_receipt():
    _preview, committed = _commit()

    found = internal_lookup_aion_proof_receipt(
        proof_commitment_id=committed["proof_commitment_id"],
    )

    assert found["ok"] is True
    assert found["status"] == "found"
    assert found["verified"] is True
    assert found["receipt"]["proof_commitment_id"] == committed["proof_commitment_id"]


def test_internal_lookup_missing_receipt_returns_not_found():
    found = internal_lookup_aion_proof_receipt(
        proof_commitment_id="aion_proof_missing",
    )

    assert found["ok"] is False
    assert found["status"] == "not_found"
    assert found["verified"] is False
    assert found["receipt"] is None


def test_internal_verify_receipt_passes_for_expected_hash():
    preview, committed = _commit()

    verified = internal_verify_aion_proof_receipt(
        proof_commitment_id=committed["proof_commitment_id"],
        expected_proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert verified["ok"] is True
    assert verified["verified"] is True
    assert verified["status"] == "verified"
    assert verified["receipt"]["proof_commitment_hash"] == preview["proof_commitment_hash"]


def test_internal_verify_receipt_fails_for_tampered_hash():
    _preview, committed = _commit()

    verified = internal_verify_aion_proof_receipt(
        proof_commitment_id=committed["proof_commitment_id"],
        expected_proof_commitment_hash="0" * 64,
    )

    assert verified["ok"] is True
    assert verified["verified"] is False
    assert verified["status"] == "failed"
    assert verified["receipt"] is None


def test_internal_commit_blocks_invalid_envelope():
    committed = internal_commit_aion_proof_and_build_receipt(
        envelope={},
        proof_commitment_hash="",
    )

    assert committed["ok"] is False
    assert committed["status"] == "blocked"
    assert "unsupported_proof_type" in committed["blocked_reasons"]
    assert "missing_business_id" in committed["blocked_reasons"]
    assert "missing_job_id" in committed["blocked_reasons"]


def test_receipt_does_not_expose_public_route_or_move_money():
    _preview, committed = _commit()
    receipt = committed["receipt"]

    assert receipt["public_route_exposed"] is False
    assert receipt["would_move_money"] is False
    assert receipt["would_require_pho"] is False
    assert receipt["would_require_token"] is False
    assert receipt["would_require_wallet"] is False
    assert receipt["would_create_payment"] is False
    assert receipt["would_create_escrow"] is False


def test_receipt_is_not_live_block_transaction_yet():
    _preview, committed = _commit()
    receipt = committed["receipt"]

    assert receipt["block_height"] is None
    assert receipt["tx_id"] is None
    assert receipt["tx_hash"] is None


def test_multiple_receipts_have_distinct_commitment_ids():
    _p1, c1 = _commit("job_001")
    _p2, c2 = _commit("job_002")

    assert c1["ok"] is True
    assert c2["ok"] is True
    assert c1["proof_commitment_id"] != c2["proof_commitment_id"]

from backend.modules.aion_gateway.glyphchain_proof_commit import preview_job_proof_commit
from backend.modules.chain_sim.aion_proof_commit_store import (
    AION_PROOF_COMMIT_STORE_VERSION,
    commit_aion_proof_record,
    get_aion_proof_commit_record,
    list_aion_proof_commit_records,
    reset_aion_proof_commit_store,
    verify_aion_proof_commit_record,
)


def _preview():
    return preview_job_proof_commit(
        business_id="BIZ_123",
        job_id="job_001",
        job_proof_hash="jobhash",
        evidence_proof_hashes=["ev1", "ev2"],
        settlement_readiness_proof_hash="settlehash",
    )


def setup_function():
    reset_aion_proof_commit_store()


def test_commit_aion_proof_record_persists_dedicated_proof_record():
    preview = _preview()
    out = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert out["ok"] is True
    assert out["status"] == "committed"
    assert out["proof_commitment_id"].startswith("aion_proof_")

    record = out["record"]
    assert record["store_version"] == AION_PROOF_COMMIT_STORE_VERSION
    assert record["proof_type"] == "AION_JOB_PROOF_V1"
    assert record["business_id"] == "biz_123"
    assert record["job_id"] == "job_001"
    assert record["proof_commitment_hash"] == preview["proof_commitment_hash"]
    assert record["status"] == "committed"


def test_commit_is_idempotent_for_same_proof_commitment():
    preview = _preview()

    first = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )
    second = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["proof_commitment_id"] == second["proof_commitment_id"]
    assert second["status"] == "already_committed"


def test_get_aion_proof_commit_record_roundtrip():
    preview = _preview()
    committed = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    found = get_aion_proof_commit_record(committed["proof_commitment_id"])

    assert found["ok"] is True
    assert found["status"] == "found"
    assert found["record"]["proof_commitment_hash"] == preview["proof_commitment_hash"]


def test_verify_aion_proof_commit_record_passes_for_expected_hash():
    preview = _preview()
    committed = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    verified = verify_aion_proof_commit_record(
        proof_commitment_id=committed["proof_commitment_id"],
        expected_proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert verified["ok"] is True
    assert verified["verified"] is True
    assert verified["status"] == "verified"


def test_verify_aion_proof_commit_record_fails_for_wrong_hash():
    preview = _preview()
    committed = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    verified = verify_aion_proof_commit_record(
        proof_commitment_id=committed["proof_commitment_id"],
        expected_proof_commitment_hash="0" * 64,
    )

    assert verified["ok"] is True
    assert verified["verified"] is False
    assert verified["status"] == "failed"


def test_commit_blocks_unsupported_proof_type():
    preview = _preview()
    env = dict(preview["envelope"])
    env["proof_type"] = "BAD_PROOF"

    out = commit_aion_proof_record(
        envelope=env,
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "unsupported_proof_type" in out["blocked_reasons"]


def test_commit_blocks_missing_required_fields():
    out = commit_aion_proof_record(
        envelope={},
        proof_commitment_hash="",
    )

    assert out["ok"] is False
    assert "unsupported_proof_type" in out["blocked_reasons"]
    assert "missing_business_id" in out["blocked_reasons"]
    assert "missing_job_id" in out["blocked_reasons"]
    assert "missing_proof_payload_hash" in out["blocked_reasons"]
    assert "missing_proof_commitment_hash" in out["blocked_reasons"]


def test_commit_blocks_payment_or_wallet_coupling():
    preview = _preview()
    env = dict(preview["envelope"])
    env["would_move_money"] = True
    env["would_require_pho"] = True
    env["would_require_token"] = True
    env["would_require_wallet"] = True
    env["would_create_payment"] = True
    env["would_create_escrow"] = True

    out = commit_aion_proof_record(
        envelope=env,
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert out["ok"] is False
    for reason in [
        "proof_commit_must_not_move_money",
        "proof_commit_must_not_require_pho",
        "proof_commit_must_not_require_token",
        "proof_commit_must_not_require_wallet",
        "proof_commit_must_not_create_payment",
        "proof_commit_must_not_create_escrow",
    ]:
        assert reason in out["blocked_reasons"]


def test_list_aion_proof_commit_records_returns_committed_records():
    first = _preview()
    commit_aion_proof_record(
        envelope=first["envelope"],
        proof_commitment_hash=first["proof_commitment_hash"],
    )

    second = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_002",
        job_proof_hash="jobhash2",
    )
    commit_aion_proof_record(
        envelope=second["envelope"],
        proof_commitment_hash=second["proof_commitment_hash"],
    )

    listed = list_aion_proof_commit_records()

    assert listed["ok"] is True
    assert listed["count"] == 2
    assert len(listed["records"]) == 2


def test_commit_store_does_not_create_bank_or_staking_tx():
    preview = _preview()
    committed = commit_aion_proof_record(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    record = committed["record"]
    assert record["tx_id"] is None
    assert record["tx_hash"] is None
    assert record["block_height"] is None
    assert record["dry_run_chain_tx"] is True
    assert record["would_move_money"] is False
    assert record["would_require_pho"] is False
    assert record["would_require_token"] is False
    assert record["would_require_wallet"] is False

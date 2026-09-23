from backend.modules.aion_gateway.glyphchain_proof_commit import (
    AION_JOB_PROOF_V1,
    AION_EVIDENCE_PROOF_V1,
    AION_SETTLEMENT_READINESS_PROOF_V1,
    build_aion_proof_envelope,
    preview_glyphchain_proof_commit,
    preview_job_proof_commit,
    verify_aion_proof_commitment,
)


def test_build_aion_proof_envelope_uses_supported_proof_type_and_payload_hash():
    env = build_aion_proof_envelope(
        proof_type=AION_JOB_PROOF_V1,
        business_id="BIZ_123",
        job_id="job_001",
        proof_payload={"job_proof_hash": "abc"},
    )

    assert env["proof_type"] == AION_JOB_PROOF_V1
    assert env["business_id"] == "biz_123"
    assert env["job_id"] == "job_001"
    assert len(env["proof_payload_hash"]) == 64
    assert env["dry_run_only"] is True
    assert env["would_submit_chain_tx"] is False
    assert env["would_move_money"] is False


def test_preview_job_proof_commit_is_dry_run_only_and_uses_existing_chainsim_codec():
    preview = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_001",
        job_proof_hash="jobhash",
        evidence_proof_hashes=["ev1", "ev2"],
        settlement_readiness_proof_hash="settlehash",
    )

    assert preview["ok"] is True
    assert preview["glyphchain_commit_status"] == "dry_run_preview_only"
    assert len(preview["proof_commitment_hash"]) == 64
    assert preview["safety"]["dry_run_only"] is True
    assert preview["safety"]["would_submit_chain_tx"] is False
    assert preview["safety"]["would_move_money"] is False
    assert preview["safety"]["would_require_pho"] is False
    assert preview["safety"]["would_require_token"] is False
    assert preview["safety"]["would_require_wallet"] is False
    assert preview["safety"]["uses_existing_chain_sim_canonical_codec"] is True
    assert preview["chain_sim"]["live_tx_submit"] is False


def test_preview_supports_all_aion_proof_envelope_types():
    for proof_type in [
        AION_JOB_PROOF_V1,
        AION_EVIDENCE_PROOF_V1,
        AION_SETTLEMENT_READINESS_PROOF_V1,
    ]:
        preview = preview_glyphchain_proof_commit(
            proof_type=proof_type,
            business_id="biz_123",
            job_id="job_001",
            proof_payload={"hash": "abc"},
        )
        assert preview["ok"] is True
        assert preview["envelope"]["proof_type"] == proof_type


def test_unsupported_proof_type_blocks_preview():
    preview = preview_glyphchain_proof_commit(
        proof_type="BAD_PROOF",
        business_id="biz_123",
        job_id="job_001",
        proof_payload={"hash": "abc"},
    )

    assert preview["ok"] is False
    assert preview["glyphchain_commit_status"] == "blocked"
    assert "unsupported_proof_type" in preview["blocked_reasons"]
    assert preview["safety"]["would_submit_chain_tx"] is False


def test_missing_required_fields_block_preview():
    preview = preview_glyphchain_proof_commit(
        proof_type=AION_JOB_PROOF_V1,
        business_id="",
        job_id="",
        proof_payload={},
    )

    assert preview["ok"] is False
    assert "missing_business_id" in preview["blocked_reasons"]
    assert "missing_job_id" in preview["blocked_reasons"]
    assert "missing_proof_payload" in preview["blocked_reasons"]


def test_verify_aion_proof_commitment_roundtrip_passes():
    preview = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_001",
        job_proof_hash="jobhash",
        evidence_proof_hashes=["ev1"],
        settlement_readiness_proof_hash="settlehash",
    )

    verified = verify_aion_proof_commitment(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert verified["ok"] is True
    assert verified["verified"] is True
    assert verified["payload_hash_matches"] is True
    assert verified["commitment_hash_matches"] is True


def test_verify_aion_proof_commitment_detects_tampered_payload():
    preview = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_001",
        job_proof_hash="jobhash",
    )

    tampered = dict(preview["envelope"])
    tampered["proof_payload"] = dict(tampered["proof_payload"])
    tampered["proof_payload"]["job_proof_hash"] = "changed"

    verified = verify_aion_proof_commitment(
        envelope=tampered,
        proof_commitment_hash=preview["proof_commitment_hash"],
    )

    assert verified["verified"] is False
    assert verified["payload_hash_matches"] is False


def test_verify_aion_proof_commitment_detects_tampered_commitment_hash():
    preview = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_001",
        job_proof_hash="jobhash",
    )

    verified = verify_aion_proof_commitment(
        envelope=preview["envelope"],
        proof_commitment_hash="0" * 64,
    )

    assert verified["verified"] is False
    assert verified["commitment_hash_matches"] is False


def test_proof_commit_adapter_never_requires_payment_or_wallet():
    preview = preview_job_proof_commit(
        business_id="biz_123",
        job_id="job_001",
        job_proof_hash="jobhash",
    )

    safety = preview["safety"]
    assert safety["would_move_money"] is False
    assert safety["would_require_pho"] is False
    assert safety["would_require_token"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False

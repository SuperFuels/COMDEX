from backend.modules.aion_gateway.settlement_readiness import (
    SETTLEMENT_SCHEMA_VERSION,
    PAYMENT_MODES,
    SETTLEMENT_STATES,
    build_settlement_readiness,
    stable_fiat_payment_reference_hash,
)


def _settlement(**overrides):
    payload = {
        "job_id": "job_001",
        "business_id": "biz_costa_001",
        "state": "payment_ready",
        "payment_requested": True,
        "deposit_paid": True,
        "payment_ready": True,
        "payment_mode": "revolut",
        "currency": "EUR",
        "quoted_amount": 120.0,
        "deposit_amount": 30.0,
        "final_amount_due": 90.0,
        "payment_reference": "REV-123",
    }
    payload.update(overrides)
    return build_settlement_readiness(**payload)


def test_settlement_readiness_schema_constants_exist():
    assert SETTLEMENT_SCHEMA_VERSION == "aion.gateway.settlement_readiness.v0.1"
    assert "payment_ready" in SETTLEMENT_STATES
    assert "disputed" in SETTLEMENT_STATES
    assert "refund_recommended" in SETTLEMENT_STATES
    assert "revolut" in PAYMENT_MODES
    assert "bank_transfer" in PAYMENT_MODES


def test_payment_ready_settlement_is_proof_ready_but_moves_no_money():
    row = _settlement()

    assert row["schema_version"] == SETTLEMENT_SCHEMA_VERSION
    assert row["job_id"] == "job_001"
    assert row["business_id"] == "biz_costa_001"
    assert row["state"] == "payment_ready"
    assert row["payment_requested"] is True
    assert row["deposit_paid"] is True
    assert row["payment_ready"] is True
    assert row["proof_ready"] is True
    assert row["blocked_reasons"] == []

    assert row["dry_run_only"] is True
    assert row["would_move_money"] is False
    assert row["would_create_payment"] is False
    assert row["would_create_escrow"] is False
    assert row["would_commit_glyphchain"] is False
    assert row["requires_human_review"] is True


def test_fiat_payment_reference_hash_is_stable_and_order_independent():
    first = stable_fiat_payment_reference_hash(
        business_id="BIZ_COSTA_001",
        job_id="job_001",
        payment_reference="REV-123",
        payment_mode="revolut",
        amount=90.0,
        currency="eur",
    )
    second = stable_fiat_payment_reference_hash(
        currency="EUR",
        amount=90.0,
        payment_mode="REVOLUT",
        payment_reference="REV-123",
        job_id="job_001",
        business_id="biz_costa_001",
    )

    assert first == second
    assert len(first) == 64


def test_changed_payment_reference_changes_hashes():
    first = _settlement(payment_reference="REV-123")
    second = _settlement(payment_reference="REV-999")

    assert first["fiat_payment_reference_hash"] != second["fiat_payment_reference_hash"]
    assert first["settlement_readiness_hash"] != second["settlement_readiness_hash"]


def test_missing_job_or_business_blocks_settlement_readiness():
    row = _settlement(job_id="", business_id="")

    assert row["proof_ready"] is False
    assert "missing_job_id" in row["blocked_reasons"]
    assert "missing_business_id" in row["blocked_reasons"]
    assert row["would_move_money"] is False


def test_invalid_state_and_unsupported_payment_mode_block():
    row = _settlement(state="paid_on_chain", payment_mode="pho_token")

    assert row["proof_ready"] is False
    assert "invalid_settlement_state" in row["blocked_reasons"]
    assert "unsupported_payment_mode" in row["blocked_reasons"]
    assert row["metadata"]["requires_pho"] is False
    assert row["metadata"]["requires_token"] is False
    assert row["metadata"]["requires_wallet"] is False


def test_payment_ready_and_disputed_cannot_both_be_true():
    row = _settlement(payment_ready=True, disputed=True)

    assert row["proof_ready"] is False
    assert "payment_ready_conflicts_with_disputed" in row["blocked_reasons"]


def test_refund_recommended_requires_dispute():
    row = _settlement(refund_recommended=True, disputed=False, payment_ready=False)

    assert row["proof_ready"] is False
    assert "refund_recommended_requires_disputed" in row["blocked_reasons"]


def test_disputed_settlement_can_be_proof_ready_without_payment_ready():
    row = _settlement(
        state="disputed",
        payment_ready=False,
        disputed=True,
        refund_recommended=False,
    )

    assert row["proof_ready"] is True
    assert row["disputed"] is True
    assert row["payment_ready"] is False
    assert row["would_move_money"] is False


def test_metadata_locks_fiat_first_boundary():
    row = _settlement()

    assert row["metadata"]["fiat_first"] is True
    assert row["metadata"]["proof_only"] is True
    assert row["metadata"]["glyphchain_payment_rail"] is False
    assert row["metadata"]["requires_wallet"] is False
    assert row["metadata"]["requires_token"] is False
    assert row["metadata"]["requires_pho"] is False

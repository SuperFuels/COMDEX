from backend.modules.aion_gateway.a2a_contracts import (
    A2A_CONTRACT_SCHEMA_VERSION,
    CapabilityContract,
    AvailabilityContract,
    QuoteContract,
    ExecutionContract,
    TraceContract,
    EvidenceContract,
    ExceptionContract,
    SettlementReadinessContract,
    ProofCommitmentContract,
    build_empty_a2a_contract_bundle,
    stable_contract_hash,
)


def test_all_a2a_contracts_use_schema_version():
    contracts = [
        CapabilityContract("biz_1", ["plumbing"], ["Albox"]).to_dict(),
        AvailabilityContract("biz_1", "plumbing", "Albox").to_dict(),
        QuoteContract("biz_1", "job_1", "EUR", 100.0).to_dict(),
        ExecutionContract("biz_1", "job_1").to_dict(),
        TraceContract("biz_1", "job_1", "requested", "human_review").to_dict(),
        EvidenceContract("biz_1", "job_1").to_dict(),
        ExceptionContract("biz_1", "job_1", "none").to_dict(),
        SettlementReadinessContract("biz_1", "job_1").to_dict(),
        ProofCommitmentContract("biz_1", "job_1", "hash_1").to_dict(),
    ]

    for contract in contracts:
        assert contract["schema_version"] == A2A_CONTRACT_SCHEMA_VERSION
        assert contract["contract_type"]
        assert contract["contract_hash"]


def test_contract_hash_is_order_independent():
    first = stable_contract_hash("trace", {"b": 2, "a": 1})
    second = stable_contract_hash("trace", {"a": 1, "b": 2})
    assert first == second


def test_capability_contract_describes_business_execution_capacity():
    contract = CapabilityContract(
        business_id="biz_homefix",
        service_types=["handyman", "plumbing"],
        locations=["Albox", "Arboleas"],
        limitations=["human_review_required"],
    ).to_dict()

    assert contract["contract_type"] == "capability"
    assert "handyman" in contract["service_types"]
    assert "Albox" in contract["locations"]
    assert contract["can_provide_evidence"] is True


def test_quote_contract_is_fiat_first():
    contract = QuoteContract(
        business_id="biz_homefix",
        job_id="job_001",
        fiat_currency="EUR",
        quoted_amount=125.50,
        assumptions=["subject to inspection"],
    ).to_dict()

    assert contract["contract_type"] == "quote"
    assert contract["fiat_currency"] == "EUR"
    assert contract["quoted_amount"] == 125.50
    assert contract["requires_human_acceptance"] is True


def test_execution_contract_is_dry_run_first_and_review_gated():
    contract = ExecutionContract(
        business_id="biz_homefix",
        job_id="job_001",
        workflow_run_id="run_001",
        goal_id="goal_001",
        stages=["requested", "quoted", "scheduled"],
    ).to_dict()

    assert contract["contract_type"] == "execution"
    assert contract["dry_run_first"] is True
    assert contract["requires_human_review"] is True
    assert contract["workflow_run_id"] == "run_001"


def test_trace_contract_aligns_machine_boardroom_state():
    contract = TraceContract(
        business_id="biz_homefix",
        job_id="job_001",
        current_stage="quoted",
        next_expected_event="customer_acceptance",
        blocked_reason="waiting_for_customer",
    ).to_dict()

    assert contract["contract_type"] == "trace"
    assert contract["current_stage"] == "quoted"
    assert contract["next_expected_event"] == "customer_acceptance"
    assert contract["blocked_reason"] == "waiting_for_customer"


def test_evidence_contract_contains_confidence_freshness_and_provenance():
    contract = EvidenceContract(
        business_id="biz_homefix",
        job_id="job_001",
        evidence_refs=[{"evidence_id": "ev_1", "type": "photo"}],
        evidence_confidence=0.75,
        evidence_freshness="fresh",
        evidence_provenance={"source": "operator_upload"},
    ).to_dict()

    assert contract["contract_type"] == "evidence"
    assert contract["evidence_refs"][0]["evidence_id"] == "ev_1"
    assert contract["evidence_confidence"] == 0.75
    assert contract["evidence_freshness"] == "fresh"
    assert contract["evidence_provenance"]["source"] == "operator_upload"


def test_exception_contract_is_recovery_oriented_and_review_gated():
    contract = ExceptionContract(
        business_id="biz_homefix",
        job_id="job_001",
        exception_type="provider_late",
        recovery_actions=["reschedule", "backup_provider"],
    ).to_dict()

    assert contract["contract_type"] == "exception"
    assert contract["requires_human_review"] is True
    assert "backup_provider" in contract["recovery_actions"]


def test_settlement_readiness_is_fiat_first_not_crypto_required():
    contract = SettlementReadinessContract(
        business_id="biz_homefix",
        job_id="job_001",
        payment_requested=True,
        fiat_payment_reference_hash="fiat_ref_hash",
    ).to_dict()

    assert contract["contract_type"] == "settlement_readiness"
    assert contract["payment_requested"] is True
    assert contract["requires_crypto_payment"] is False


def test_proof_commitment_is_proof_not_payment():
    contract = ProofCommitmentContract(
        business_id="biz_homefix",
        job_id="job_001",
        job_proof_hash="job_hash",
        evidence_proof_hashes=["ev_hash"],
    ).to_dict()

    assert contract["contract_type"] == "proof_commitment"
    assert contract["job_proof_hash"] == "job_hash"
    assert contract["proof_is_payment"] is False


def test_empty_a2a_bundle_contains_all_contracts_and_safety_flags():
    bundle = build_empty_a2a_contract_bundle(
        business_id="biz_homefix",
        job_id="job_001",
    )

    expected = {
        "capability",
        "availability",
        "quote",
        "execution",
        "trace",
        "evidence",
        "exception",
        "settlement_readiness",
        "proof_commitment",
    }

    assert set(bundle["contracts"]) == expected
    assert bundle["dry_run_only"] is True
    assert bundle["safety"]["would_execute_workflow"] is False
    assert bundle["safety"]["would_create_payment"] is False
    assert bundle["safety"]["would_commit_to_glyphchain"] is False
    assert bundle["safety"]["would_grant_permission"] is False
    assert bundle["bundle_hash"]

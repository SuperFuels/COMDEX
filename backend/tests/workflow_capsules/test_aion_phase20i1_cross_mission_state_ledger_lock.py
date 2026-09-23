from backend.services.aion_mission_mode.cross_mission_state_ledger import (
    assert_cache_eviction_completed,
    bind_ledger_to_replay,
    create_cache_eviction_contract,
    create_consensus_snapshot,
    create_ledger_entry,
    verify_ledger_chain,
)


def test_phase20i1_creates_deterministic_ledger_entry() -> None:
    first = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:receipt",
        sequence_number=0,
    )
    second = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:receipt",
        sequence_number=0,
    )
    assert first["entry_hash"] == second["entry_hash"]


def test_phase20i1_rejects_unknown_entry_type() -> None:
    try:
        create_ledger_entry(
            mission_id="m1",
            mission_run_id="r1",
            business_id="home_fixed",
            entry_type="unknown",
            source_hash="sha256:x",
            sequence_number=0,
        )
    except ValueError as exc:
        assert "invalid ledger entry type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i1_verifies_valid_ledger_chain() -> None:
    e0 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:r0",
        sequence_number=0,
    )
    e1 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="proof_update",
        source_hash="sha256:r1",
        sequence_number=1,
        previous_entry_hash=e0["entry_hash"],
    )
    result = verify_ledger_chain([e0, e1])
    assert result["ledger_valid"] is True
    assert result["verification_state"] == "ledger_chain_valid"


def test_phase20i1_detects_ledger_chain_break() -> None:
    e0 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:r0",
        sequence_number=0,
    )
    e1 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="proof_update",
        source_hash="sha256:r1",
        sequence_number=1,
        previous_entry_hash="sha256:not_previous",
    )
    result = verify_ledger_chain([e0, e1])
    assert result["ledger_valid"] is False
    assert "ledger_chain_break:1" in result["reasons"]


def test_phase20i1_detects_tampered_entry_hash() -> None:
    entry = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="proof_update",
        source_hash="sha256:r1",
        sequence_number=0,
    )
    entry["source_hash"] = "sha256:tampered"
    result = verify_ledger_chain([entry])
    assert result["ledger_valid"] is False
    assert "entry_hash_mismatch:0" in result["reasons"]


def test_phase20i1_consensus_snapshot_is_deterministic() -> None:
    e0 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:r0",
        sequence_number=0,
    )
    first = create_consensus_snapshot(business_id="home_fixed", entries=[e0])
    second = create_consensus_snapshot(business_id="home_fixed", entries=[e0])
    assert first["consensus_hash"] == second["consensus_hash"]
    assert first["consensus_state"] == "cross_mission_ledger_consensus_formed"


def test_phase20i1_consensus_orders_parallel_entries_deterministically() -> None:
    e1 = create_ledger_entry(
        mission_id="m2",
        mission_run_id="r2",
        business_id="home_fixed",
        entry_type="state_summary",
        source_hash="sha256:b",
        sequence_number=2,
    )
    e0 = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="state_summary",
        source_hash="sha256:a",
        sequence_number=1,
    )
    snapshot = create_consensus_snapshot(business_id="home_fixed", entries=[e1, e0])
    assert snapshot["mission_ids"] == ["m1", "m2"]
    assert snapshot["entry_hashes"] == [e0["entry_hash"], e1["entry_hash"]]


def test_phase20i1_create_cache_eviction_contract() -> None:
    contract = create_cache_eviction_contract(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        cache_scope="browser_session",
        cache_key_hash="sha256:session",
        reason="mission_boundary_closed",
        dependent_hashes=["sha256:b", "sha256:a"],
    )
    assert contract["dependent_hashes"] == ["sha256:a", "sha256:b"]
    assert contract["eviction_state"] == "eviction_required"
    assert contract["eviction_contract_hash"].startswith("sha256:")


def test_phase20i1_rejects_invalid_cache_scope() -> None:
    try:
        create_cache_eviction_contract(
            mission_id="m1",
            mission_run_id="r1",
            business_id="home_fixed",
            cache_scope="global_memory",
            cache_key_hash="sha256:x",
            reason="invalid",
        )
    except ValueError as exc:
        assert "invalid cache scope" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i1_cache_eviction_assertion_passes() -> None:
    contract = create_cache_eviction_contract(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        cache_scope="mission_vfs",
        cache_key_hash="sha256:vfs",
        reason="mission_closed",
    )
    result = assert_cache_eviction_completed(
        contract=contract,
        observed_evicted_hash="sha256:vfs",
    )
    assert result["eviction_completed"] is True
    assert result["assertion_state"] == "cache_eviction_confirmed"


def test_phase20i1_cache_eviction_assertion_fails_on_hash_mismatch() -> None:
    contract = create_cache_eviction_contract(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        cache_scope="mission_vfs",
        cache_key_hash="sha256:vfs",
        reason="mission_closed",
    )
    result = assert_cache_eviction_completed(
        contract=contract,
        observed_evicted_hash="sha256:wrong",
    )
    assert result["eviction_completed"] is False
    assert "evicted_hash_mismatch" in result["reasons"]


def test_phase20i1_ledger_binds_to_replay() -> None:
    entry = create_ledger_entry(
        mission_id="m1",
        mission_run_id="r1",
        business_id="home_fixed",
        entry_type="capability_receipt",
        source_hash="sha256:r",
        sequence_number=0,
    )
    snapshot = create_consensus_snapshot(business_id="home_fixed", entries=[entry])
    binding = bind_ledger_to_replay(
        consensus_snapshot=snapshot,
        replay_hash="sha256:replay",
        proof_hash="sha256:proof",
    )
    assert binding["allowed"] is True
    assert binding["binding_state"] == "ledger_bound_to_replay"


def test_phase20i1_ledger_replay_binding_blocks_invalid_hash() -> None:
    snapshot = {
        "business_id": "home_fixed",
        "consensus_hash": "sha256:consensus",
    }
    binding = bind_ledger_to_replay(
        consensus_snapshot=snapshot,
        replay_hash="bad",
        proof_hash="sha256:proof",
    )
    assert binding["allowed"] is False
    assert "invalid_replay_hash" in binding["reasons"]

from backend.services.aion_mission_mode.cross_mission_memory_boundary import (
    approve_memory_promotion,
    block_accidental_memory_leakage,
    create_memory_promotion_proposal,
    create_mission_memory_record,
    evaluate_memory_access,
    hash_memory_value,
)


def test_phase20s_memory_value_hash_is_deterministic() -> None:
    first = hash_memory_value({"customer": "example"})
    second = hash_memory_value({"customer": "example"})

    assert first == second
    assert first.startswith("sha256:")


def test_phase20s_create_mission_memory_record() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="draft_angle",
        value={"angle": "roof repair"},
        memory_scope="mission",
        source_step_id="step_research",
    )

    assert record["mission_id"] == "mission_a"
    assert record["memory_scope"] == "mission"
    assert record["record_hash"].startswith("sha256:")


def test_phase20s_same_mission_access_allowed() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="draft_angle",
        value={"angle": "roof repair"},
        memory_scope="mission",
    )

    result = evaluate_memory_access(
        source_record=record,
        requesting_mission_id="mission_a",
    )

    assert result["access_allowed"] is True
    assert result["decision"] == "allowed_within_mission"


def test_phase20s_cross_mission_access_blocked_by_default() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="customer_note",
        value={"note": "private mission data"},
        memory_scope="mission",
    )

    result = evaluate_memory_access(
        source_record=record,
        requesting_mission_id="mission_b",
    )

    assert result["access_allowed"] is False
    assert result["decision"] == "blocked_cross_mission"


def test_phase20s_forbidden_scope_is_always_forbidden() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="secret",
        value={"secret": "do not use"},
        memory_scope="forbidden",
    )

    result = evaluate_memory_access(
        source_record=record,
        requesting_mission_id="mission_a",
    )

    assert result["access_allowed"] is False
    assert result["decision"] == "forbidden"


def test_phase20s_business_proposal_requires_approval_cross_mission() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="business_learning",
        value={"learning": "use roof proof photos"},
        memory_scope="business_proposal",
        data_retention_policy="business_proposal",
    )

    result = evaluate_memory_access(
        source_record=record,
        requesting_mission_id="mission_b",
    )

    assert result["access_allowed"] is False
    assert result["decision"] == "proposal_required"


def test_phase20s_business_proposal_allowed_with_approved_transfer_hash() -> None:
    record = create_mission_memory_record(
        mission_id="mission_a",
        mission_run_id="run_001",
        key="business_learning",
        value={"learning": "use roof proof photos"},
        memory_scope="business_proposal",
        data_retention_policy="business_proposal",
    )

    result = evaluate_memory_access(
        source_record=record,
        requesting_mission_id="mission_b",
        approved_transfer_hash="sha256:approved",
    )

    assert result["access_allowed"] is True
    assert result["decision"] == "promotion_allowed"


def test_phase20s_create_memory_promotion_proposal() -> None:
    proposal = create_memory_promotion_proposal(
        source_mission_id="mission_a",
        target_business_id="home_fixed",
        key="campaign_learning",
        value={"learning": "before/after photos work well"},
        reason="Reusable campaign insight",
    )

    assert proposal["approval_state"] == "pending_human_approval"
    assert proposal["proposal_hash"].startswith("sha256:")


def test_phase20s_approve_memory_promotion() -> None:
    proposal = create_memory_promotion_proposal(
        source_mission_id="mission_a",
        target_business_id="home_fixed",
        key="campaign_learning",
        value={"learning": "before/after photos work well"},
        reason="Reusable campaign insight",
    )

    approved = approve_memory_promotion(
        proposal=proposal,
        approving_human="kevin",
    )

    assert approved["approval_state"] == "approved"
    assert approved["approving_human"] == "kevin"
    assert approved["approval_hash"].startswith("sha256:")


def test_phase20s_blocks_realistic_accidental_leakage() -> None:
    result = block_accidental_memory_leakage(
        source_mission_id="mission_a",
        target_mission_id="mission_b",
        candidate_context={
            "summary": "Copied note from mission_a should not appear in mission_b",
            "data": {"mission_id": "mission_a"},
        },
    )

    assert result["leakage_blocked"] is True
    assert result["context_allowed"] is False


def test_phase20s_allows_same_mission_context() -> None:
    result = block_accidental_memory_leakage(
        source_mission_id="mission_a",
        target_mission_id="mission_a",
        candidate_context={"summary": "mission_a context"},
    )

    assert result["leakage_blocked"] is False
    assert result["context_allowed"] is True


def test_phase20s_allows_cross_mission_context_with_approved_transfer() -> None:
    result = block_accidental_memory_leakage(
        source_mission_id="mission_a",
        target_mission_id="mission_b",
        candidate_context={"summary": "mission_a context"},
        approved_transfer_hash="sha256:approved",
    )

    assert result["leakage_blocked"] is False
    assert result["context_allowed"] is True

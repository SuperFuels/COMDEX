from backend.services.aion_mission_mode.mission_outcome_ets_preview import (
    assert_no_live_reputation_mutation,
    classify_mission_outcome,
    compile_mission_outcome_metrics,
    compile_outcome_packet,
    create_ets_preview,
)


def _metrics(**overrides):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        total_steps=10,
        completed_steps=10,
        autonomous_steps=8,
        human_approval_count=2,
        human_task_count=0,
        blocked_action_count=0,
        receipt_count=3,
        failed_steps=0,
        estimated_minutes_saved=120.125,
    )
    base.update(overrides)
    return compile_mission_outcome_metrics(**base)


def _preview(metrics_hash="sha256:metrics"):
    return create_ets_preview(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        agent_id="pilot",
        outcome_metrics_hash=metrics_hash,
        receipt_hashes=["sha256:b", "sha256:a"],
        proof_hash="sha256:proof",
        replay_packet_hash="sha256:replay",
        proposed_score_delta=0.123456,
        rationale="Safe autonomous work completed with approvals.",
    )


def test_phase20i3_classifies_fully_autonomous_success() -> None:
    assert classify_mission_outcome(
        completed_steps=10,
        failed_steps=0,
        blocked_for_safety_count=0,
        human_approval_count=0,
        human_task_count=0,
        total_steps=10,
    ) == "fully_autonomous_success"


def test_phase20i3_classifies_checkpointed_success() -> None:
    assert classify_mission_outcome(
        completed_steps=10,
        failed_steps=0,
        blocked_for_safety_count=0,
        human_approval_count=2,
        human_task_count=0,
        total_steps=10,
    ) == "checkpointed_success"


def test_phase20i3_classifies_human_guided_success() -> None:
    assert classify_mission_outcome(
        completed_steps=10,
        failed_steps=0,
        blocked_for_safety_count=0,
        human_approval_count=1,
        human_task_count=1,
        total_steps=10,
    ) == "human_guided_success"


def test_phase20i3_classifies_partial_failure() -> None:
    assert classify_mission_outcome(
        completed_steps=8,
        failed_steps=1,
        blocked_for_safety_count=0,
        human_approval_count=0,
        human_task_count=0,
        total_steps=10,
    ) == "partial_failure"


def test_phase20i3_classifies_blocked_for_safety() -> None:
    assert classify_mission_outcome(
        completed_steps=8,
        failed_steps=0,
        blocked_for_safety_count=1,
        human_approval_count=0,
        human_task_count=0,
        total_steps=10,
    ) == "blocked_for_safety"


def test_phase20i3_metrics_are_deterministic() -> None:
    first = _metrics()
    second = _metrics()

    assert first["metrics_hash"] == second["metrics_hash"]
    assert first["autonomy_percentage"] == 80.0
    assert first["estimated_minutes_saved"] == 120.12
    assert first["outcome_category"] == "checkpointed_success"


def test_phase20i3_metrics_reject_invalid_total_steps() -> None:
    try:
        _metrics(total_steps=0)
    except ValueError as exc:
        assert "total_steps must be positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i3_ets_preview_is_preview_only() -> None:
    preview = _preview()

    assert preview["ets_state"] == "preview_only"
    assert preview["live_reputation_mutation_allowed"] is False
    assert preview["receipt_hashes"] == ["sha256:a", "sha256:b"]
    assert preview["ets_preview_hash"].startswith("sha256:")


def test_phase20i3_ets_preview_rejects_malformed_hashes() -> None:
    try:
        _preview(metrics_hash="bad")
    except ValueError as exc:
        assert "outcome_metrics_hash must be sha256-prefixed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i3_mutation_guard_allows_preview_payload() -> None:
    result = assert_no_live_reputation_mutation({"ets_state": "preview_only"})

    assert result["allowed"] is True
    assert result["guard_state"] == "ets_preview_only_verified"


def test_phase20i3_mutation_guard_blocks_live_reputation_write() -> None:
    result = assert_no_live_reputation_mutation({
        "ets_state": "preview_only",
        "write_live_reputation": True,
    })

    assert result["allowed"] is False
    assert result["guard_state"] == "live_mutation_blocked"
    assert "live_reputation_mutation_field_blocked:write_live_reputation" in result["violations"]


def test_phase20i3_mutation_guard_blocks_non_preview_state() -> None:
    result = assert_no_live_reputation_mutation({"ets_state": "live_commit"})

    assert result["allowed"] is False
    assert "ets_state_not_preview_only" in result["violations"]


def test_phase20i3_compile_valid_outcome_packet() -> None:
    metrics = _metrics()
    preview = _preview(metrics["metrics_hash"])

    packet = compile_outcome_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        metrics=metrics,
        ets_preview=preview,
        replay_packet_hash="sha256:replay",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is True
    assert packet["packet_state"] == "mission_outcome_packet_ready"
    assert packet["outcome_category"] == "checkpointed_success"
    assert packet["autonomy_percentage"] == 80.0


def test_phase20i3_packet_blocks_tampered_metrics() -> None:
    metrics = _metrics()
    metrics["autonomy_percentage"] = 99.0
    preview = _preview(metrics["metrics_hash"])

    packet = compile_outcome_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        metrics=metrics,
        ets_preview=preview,
        replay_packet_hash="sha256:replay",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is False
    assert "metrics_hash_mismatch" in packet["reasons"]


def test_phase20i3_packet_blocks_live_ets_mutation() -> None:
    metrics = _metrics()
    preview = _preview(metrics["metrics_hash"])
    preview["live_reputation_mutation_allowed"] = True

    packet = compile_outcome_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        metrics=metrics,
        ets_preview=preview,
        replay_packet_hash="sha256:replay",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is False
    assert "ets_preview_hash_mismatch" in packet["reasons"]
    assert "live_reputation_mutation_not_blocked" in packet["reasons"]


def test_phase20i3_packet_hash_is_deterministic() -> None:
    metrics = _metrics()
    preview = _preview(metrics["metrics_hash"])

    first = compile_outcome_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        metrics=metrics,
        ets_preview=preview,
        replay_packet_hash="sha256:replay",
        proof_hash="sha256:proof",
    )
    second = compile_outcome_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        metrics=metrics,
        ets_preview=preview,
        replay_packet_hash="sha256:replay",
        proof_hash="sha256:proof",
    )

    assert first["packet_hash"] == second["packet_hash"]

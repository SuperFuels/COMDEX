from backend.services.aion_mission_mode.agent_reputation_demo_narrative import (
    REQUIRED_DEMO_MESSAGE,
    assert_reputation_preview_only,
    compile_blocked_action_demo_metrics,
    compile_demo_summary_packet,
    create_demo_narrative,
    create_reputation_governance_requirement,
)


def _narrative(**overrides):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        outcome_packet_hash="sha256:outcome",
        ets_preview_hash="sha256:ets",
        autonomy_percentage=82.345,
        checkpoint_count=3,
        blocked_action_count=2,
        receipt_count=5,
        estimated_minutes_saved=141.229,
    )
    base.update(overrides)
    return create_demo_narrative(**base)


def _blocked():
    return compile_blocked_action_demo_metrics(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        blocked_actions=[
            {
                "action_type": "publish_facebook_post",
                "reason": "public_content_requires_approval",
                "what_would_have_happened": "post would have gone live",
                "safe_alternative": "show approval card",
            },
            {
                "action_type": "buy_domain",
                "reason": "payment_requires_approval",
                "what_would_have_happened": "domain checkout would have committed",
                "safe_alternative": "stage checkout preview",
            },
        ],
    )


def _governance(**overrides):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        agent_id="pilot",
        ets_preview_hash="sha256:ets",
        requested_live_mutation=None,
    )
    base.update(overrides)
    return create_reputation_governance_requirement(**base)


def test_phase20u1_preview_guard_allows_preview_only() -> None:
    result = assert_reputation_preview_only({"ets_state": "preview_only"})

    assert result["allowed"] is True
    assert result["reputation_state"] == "ets_preview_only"


def test_phase20u1_preview_guard_blocks_live_mutation_field() -> None:
    result = assert_reputation_preview_only({
        "ets_state": "preview_only",
        "commit_ets": True,
    })

    assert result["allowed"] is False
    assert "live_reputation_mutation_blocked:commit_ets" in result["violations"]


def test_phase20u1_preview_guard_blocks_non_preview_state() -> None:
    result = assert_reputation_preview_only({"ets_state": "live_commit"})

    assert result["allowed"] is False
    assert "ets_state_must_remain_preview_only" in result["violations"]


def test_phase20u1_demo_narrative_contains_required_visible_message() -> None:
    narrative = _narrative()

    assert narrative["required_visible_message"] == REQUIRED_DEMO_MESSAGE
    assert narrative["no_payment_created"] is True
    assert narrative["no_booking_created"] is True
    assert narrative["no_external_message_sent"] is True
    assert narrative["no_live_reputation_mutation"] is True


def test_phase20u1_demo_narrative_rounds_metrics_deterministically() -> None:
    narrative = _narrative()

    assert narrative["autonomy_percentage"] == 82.34
    assert narrative["estimated_minutes_saved"] == 141.23


def test_phase20u1_demo_narrative_requires_hashes() -> None:
    try:
        _narrative(outcome_packet_hash="bad")
    except ValueError as exc:
        assert "outcome_packet_hash must be sha256-prefixed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20u1_blocked_action_metrics_are_sorted_and_hashed() -> None:
    metrics = _blocked()

    assert metrics["blocked_action_count"] == 2
    assert metrics["blocked_actions"][0]["action_type"] == "buy_domain"
    assert metrics["metrics_hash"].startswith("sha256:")


def test_phase20u1_blocked_action_requires_action_type_and_reason() -> None:
    try:
        compile_blocked_action_demo_metrics(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="home_fixed",
            blocked_actions=[{"action_type": "buy_domain"}],
        )
    except ValueError as exc:
        assert "blocked action requires action_type and reason" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20u1_governance_requirement_blocks_live_now() -> None:
    requirement = _governance()

    assert requirement["governance_required_before_live_mutation"] is True
    assert requirement["live_mutation_allowed_now"] is False
    assert requirement["requirement_state"] == "governance_required"


def test_phase20u1_governance_requirement_records_guard_for_mutation_attempt() -> None:
    requirement = _governance(requested_live_mutation={"write_live_reputation": True})

    assert requirement["guard_allowed"] is False
    assert requirement["live_mutation_allowed_now"] is False


def test_phase20u1_demo_summary_packet_allows_valid_inputs() -> None:
    narrative = _narrative()
    blocked = _blocked()
    governance = _governance()

    packet = compile_demo_summary_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        narrative=narrative,
        blocked_metrics=blocked,
        governance_requirement=governance,
    )

    assert packet["allowed"] is True
    assert packet["summary_state"] == "demo_summary_ready"
    assert packet["visible_message"] == REQUIRED_DEMO_MESSAGE


def test_phase20u1_demo_summary_blocks_tampered_narrative() -> None:
    narrative = _narrative()
    narrative["no_live_reputation_mutation"] = False

    packet = compile_demo_summary_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        narrative=narrative,
        blocked_metrics=_blocked(),
        governance_requirement=_governance(),
    )

    assert packet["allowed"] is False
    assert "narrative_hash_mismatch" in packet["reasons"]
    assert "live_reputation_mutation_not_blocked" in packet["reasons"]


def test_phase20u1_demo_summary_blocks_missing_required_message() -> None:
    narrative = _narrative()
    narrative["required_visible_message"] = "Different message"

    packet = compile_demo_summary_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        narrative=narrative,
        blocked_metrics=_blocked(),
        governance_requirement=_governance(),
    )

    assert packet["allowed"] is False
    assert "required_demo_message_missing" in packet["reasons"]


def test_phase20u1_summary_hash_is_deterministic() -> None:
    narrative = _narrative()
    blocked = _blocked()
    governance = _governance()

    first = compile_demo_summary_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        narrative=narrative,
        blocked_metrics=blocked,
        governance_requirement=governance,
    )
    second = compile_demo_summary_packet(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        narrative=narrative,
        blocked_metrics=blocked,
        governance_requirement=governance,
    )

    assert first["summary_hash"] == second["summary_hash"]

from backend.services.aion_mission_mode.approval_expiry import (
    boardroom_expiry_notice,
    evaluate_approval_expiry,
    invalidate_pending_payload_if_expired,
    is_approval_expired,
)
from backend.services.aion_mission_mode.canonical_payload_hashing import (
    payload_sha256_normalized,
)


def make_decision(**overrides):
    payload = {"message": "Draft advert", "limit": 100}
    data = {
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "checkpoint_id": "checkpoint_publish",
        "step_id": "step_publish",
        "action_type": "publish_advert",
        "approval_hash": "sha256:approval",
        "approved_payload_hash": payload_sha256_normalized(payload),
        "current_payload": payload,
        "expires_at": "2026-06-07T13:00:00",
        "now_iso": "2026-06-07T12:59:59",
    }
    data.update(overrides)
    return evaluate_approval_expiry(**data)


def test_phase20r_expiry_false_before_expiry() -> None:
    assert is_approval_expired(
        expires_at="2026-06-07T13:00:00",
        now_iso="2026-06-07T12:59:59",
    ) is False


def test_phase20r_expiry_true_after_expiry() -> None:
    assert is_approval_expired(
        expires_at="2026-06-07T13:00:00",
        now_iso="2026-06-07T13:00:01",
    ) is True


def test_phase20r_no_expiry_timestamp_does_not_expire() -> None:
    assert is_approval_expired(expires_at=None, now_iso="2026-06-07T13:00:01") is False


def test_phase20r_valid_approval_allows_execution() -> None:
    decision = make_decision()

    assert decision["approval_valid"] is True
    assert decision["runtime_state"] == "approval_valid_execution_allowed"
    assert decision["requires_fresh_approval"] is False
    assert decision["event_type"] == "approval_valid"
    assert decision["decision_hash"].startswith("sha256:")


def test_phase20r_expired_approval_pauses_runtime() -> None:
    decision = make_decision(now_iso="2026-06-07T13:00:01")

    assert decision["approval_expired"] is True
    assert decision["approval_valid"] is False
    assert decision["runtime_state"] == "paused_at_checkpoint"
    assert decision["event_type"] == "approval_expired"
    assert decision["requires_fresh_approval"] is True


def test_phase20r_expired_approval_invalidates_pending_payload() -> None:
    decision = make_decision(now_iso="2026-06-07T13:00:01")
    invalidation = invalidate_pending_payload_if_expired(decision)

    assert invalidation["pending_payload_valid"] is False
    assert invalidation["event_type"] == "approval_expired"
    assert invalidation["requires_fresh_approval"] is True
    assert invalidation["reason"] == "expired_approval_invalidates_pending_action_payload"


def test_phase20r_changed_payload_requires_fresh_approval() -> None:
    decision = make_decision(current_payload={"message": "Edited advert", "limit": 100})

    assert decision["payload_changed"] is True
    assert decision["approval_valid"] is False
    assert decision["runtime_state"] == "paused_at_checkpoint"
    assert decision["event_type"] == "approval_payload_changed"
    assert decision["requires_fresh_approval"] is True


def test_phase20r_expired_and_changed_payload_still_reports_expiry_first() -> None:
    decision = make_decision(
        current_payload={"message": "Edited advert", "limit": 100},
        now_iso="2026-06-07T13:00:01",
    )

    assert decision["approval_expired"] is True
    assert decision["payload_changed"] is True
    assert decision["event_type"] == "approval_expired"


def test_phase20r_boardroom_notice_freezes_controls_for_expired_approval() -> None:
    decision = make_decision(now_iso="2026-06-07T13:00:01")
    notice = boardroom_expiry_notice(decision)

    assert notice["controls_enabled"] is False
    assert notice["show_approval_expired"] is True
    assert notice["requires_fresh_approval"] is True
    assert "expired" in notice["message"].lower()


def test_phase20r_boardroom_notice_explains_payload_changed() -> None:
    decision = make_decision(current_payload={"message": "Edited advert", "limit": 100})
    notice = boardroom_expiry_notice(decision)

    assert notice["controls_enabled"] is False
    assert notice["show_payload_changed"] is True
    assert "exact" in notice["user_explanation"].lower()


def test_phase20r_decision_hash_is_deterministic() -> None:
    first = make_decision()
    second = make_decision()

    assert first["decision_hash"] == second["decision_hash"]


def test_phase20r_decision_hash_changes_when_expiry_state_changes() -> None:
    first = make_decision()
    second = make_decision(now_iso="2026-06-07T13:00:01")

    assert first["decision_hash"] != second["decision_hash"]


def test_phase20r1_time_anchor_is_deterministic_and_immutable() -> None:
    from backend.services.aion_mission_mode.approval_expiry import create_atomic_time_anchor

    first = create_atomic_time_anchor(eval_time="2026-06-07T12:59:59")
    second = create_atomic_time_anchor(eval_time="2026-06-07T12:59:59")

    assert first["t_eval"] == "2026-06-07T12:59:59"
    assert first["immutable_within_checkpoint"] is True
    assert first["time_anchor_hash"] == second["time_anchor_hash"]
    assert first["time_anchor_hash"].startswith("sha256:")


def test_phase20r1_anchor_drives_expiry_without_resampling() -> None:
    from backend.services.aion_mission_mode.approval_expiry import (
        create_atomic_time_anchor,
        evaluate_approval_expiry_with_time_anchor,
    )

    payload = {"message": "Draft advert", "limit": 100}
    anchor = create_atomic_time_anchor(eval_time="2026-06-07T13:00:01")

    decision = evaluate_approval_expiry_with_time_anchor(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        approval_hash="sha256:approval",
        approved_payload_hash=payload_sha256_normalized(payload),
        current_payload=payload,
        expires_at="2026-06-07T13:00:00",
        time_anchor=anchor,
    )

    assert decision["approval_expired"] is True
    assert decision["event_type"] == "approval_expired"
    assert decision["t_eval"] == "2026-06-07T13:00:01"
    assert decision["time_anchor_hash"] == anchor["time_anchor_hash"]


def test_phase20r1_temporal_decision_hash_changes_when_time_anchor_changes() -> None:
    from backend.services.aion_mission_mode.approval_expiry import temporal_decision_hash

    first = temporal_decision_hash(
        approved_payload_hash="sha256:a",
        current_payload_hash="sha256:a",
        t_eval="2026-06-07T12:59:59",
        payload_changed=False,
        approval_expired=False,
        runtime_state="approval_valid_execution_allowed",
        event_type="approval_valid",
        checkpoint_id="checkpoint_publish",
    )

    second = temporal_decision_hash(
        approved_payload_hash="sha256:a",
        current_payload_hash="sha256:a",
        t_eval="2026-06-07T13:00:01",
        payload_changed=False,
        approval_expired=True,
        runtime_state="paused_at_checkpoint",
        event_type="approval_expired",
        checkpoint_id="checkpoint_publish",
    )

    assert first != second
    assert first.startswith("sha256:")
    assert second.startswith("sha256:")


def test_phase20r1_rejects_mutable_or_missing_time_anchor() -> None:
    import pytest
    from backend.services.aion_mission_mode.approval_expiry import evaluate_approval_expiry_with_time_anchor

    payload = {"message": "Draft advert", "limit": 100}

    with pytest.raises(ValueError):
        evaluate_approval_expiry_with_time_anchor(
            mission_id="mission_001",
            mission_run_id="run_001",
            checkpoint_id="checkpoint_publish",
            step_id="step_publish",
            action_type="publish_advert",
            approval_hash="sha256:approval",
            approved_payload_hash=payload_sha256_normalized(payload),
            current_payload=payload,
            expires_at="2026-06-07T13:00:00",
            time_anchor={"t_eval": "2026-06-07T12:59:59", "immutable_within_checkpoint": False},
        )


def test_phase20r1_detects_time_anchor_resampling() -> None:
    from backend.services.aion_mission_mode.approval_expiry import (
        create_atomic_time_anchor,
        verify_time_anchor_not_resampled,
    )

    initial = create_atomic_time_anchor(eval_time="2026-06-07T12:59:59")
    runtime = create_atomic_time_anchor(eval_time="2026-06-07T13:00:01")

    assert verify_time_anchor_not_resampled(
        initial_time_anchor=initial,
        runtime_time_anchor=initial,
    ) is True

    assert verify_time_anchor_not_resampled(
        initial_time_anchor=initial,
        runtime_time_anchor=runtime,
    ) is False

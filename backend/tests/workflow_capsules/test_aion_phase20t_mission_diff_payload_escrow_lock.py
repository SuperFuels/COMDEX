from backend.services.aion_mission_mode.canonical_payload_hashing import payload_sha256_normalized
from backend.services.aion_mission_mode.mission_diff_payload_escrow import (
    bind_approval_to_escrow,
    build_mission_diff,
    create_payload_escrow_record,
    validate_escrow_payload_unchanged,
)


def test_phase20t_diff_is_deterministic() -> None:
    template = [{"step_id": "draft", "action_type": "draft_offer", "lane": "creation"}]
    proposed = [{"step_id": "draft", "action_type": "draft_offer", "lane": "creation"}]

    first = build_mission_diff(template_steps=template, proposed_steps=proposed)
    second = build_mission_diff(template_steps=template, proposed_steps=proposed)

    assert first["diff_hash"] == second["diff_hash"]


def test_phase20t_diff_detects_added_external_step() -> None:
    template = [{"step_id": "draft", "action_type": "draft_offer", "lane": "creation"}]
    proposed = [
        {"step_id": "draft", "action_type": "draft_offer", "lane": "creation"},
        {"step_id": "publish", "action_type": "publish_advert", "lane": "external_action"},
    ]

    diff = build_mission_diff(template_steps=template, proposed_steps=proposed)

    assert diff["risk_added"] is True
    assert diff["entries"][0]["change_type"] == "added_step"
    assert diff["entries"][0]["risk_flag"] is True


def test_phase20t_diff_detects_modified_lane_to_financial() -> None:
    template = [{"step_id": "pay", "action_type": "preview_payment", "lane": "internal_ops"}]
    proposed = [{"step_id": "pay", "action_type": "take_payment", "lane": "financial_action"}]

    diff = build_mission_diff(template_steps=template, proposed_steps=proposed)

    assert diff["risk_added"] is True
    assert diff["entries"][0]["change_type"] == "modified_step"


def test_phase20t_diff_detects_removed_step() -> None:
    template = [{"step_id": "draft", "action_type": "draft_offer", "lane": "creation"}]
    proposed = []

    diff = build_mission_diff(template_steps=template, proposed_steps=proposed)

    assert diff["entries"][0]["change_type"] == "removed_step"


def test_phase20t_create_payload_escrow_record() -> None:
    payload = {"message": "Draft advert", "cta": "Call"}
    record = create_payload_escrow_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        payload_type="publish_payload",
        payload=payload,
    )

    assert record["payload_hash"] == payload_sha256_normalized(payload)
    assert record["escrow_state"] == "pending_approval"
    assert record["escrow_hash"].startswith("sha256:")


def test_phase20t_rejects_unknown_escrow_payload_type() -> None:
    import pytest

    with pytest.raises(ValueError):
        create_payload_escrow_record(
            mission_id="mission_001",
            mission_run_id="run_001",
            checkpoint_id="checkpoint_publish",
            step_id="step_publish",
            action_type="publish_advert",
            payload_type="unknown",
            payload={"message": "Draft"},
        )


def test_phase20t_bind_approval_to_exact_escrow_payload_hash() -> None:
    payload = {"message": "Draft advert", "cta": "Call"}
    record = create_payload_escrow_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        payload_type="publish_payload",
        payload=payload,
    )

    bound = bind_approval_to_escrow(
        escrow_record=record,
        approval_hash="sha256:approval",
        approved_payload_hash=record["payload_hash"],
    )

    assert bound["approval_bound"] is True
    assert bound["escrow_state"] == "approval_bound"
    assert bound["requires_fresh_approval"] is False


def test_phase20t_rejects_approval_with_wrong_payload_hash() -> None:
    payload = {"message": "Draft advert", "cta": "Call"}
    record = create_payload_escrow_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        payload_type="publish_payload",
        payload=payload,
    )

    bound = bind_approval_to_escrow(
        escrow_record=record,
        approval_hash="sha256:approval",
        approved_payload_hash="sha256:wrong",
    )

    assert bound["approval_bound"] is False
    assert bound["escrow_state"] == "approval_payload_hash_mismatch"
    assert bound["requires_fresh_approval"] is True


def test_phase20t_unchanged_escrow_payload_allows_execution_when_bound() -> None:
    payload = {"message": "Draft advert", "cta": "Call"}
    record = create_payload_escrow_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        payload_type="publish_payload",
        payload=payload,
    )
    bound = bind_approval_to_escrow(
        escrow_record=record,
        approval_hash="sha256:approval",
        approved_payload_hash=record["payload_hash"],
    )

    result = validate_escrow_payload_unchanged(
        escrow_record=bound,
        current_payload=payload,
    )

    assert result["payload_unchanged"] is True
    assert result["execution_allowed"] is True
    assert result["validation_hash"].startswith("sha256:")


def test_phase20t_changed_escrow_payload_requires_fresh_approval() -> None:
    payload = {"message": "Draft advert", "cta": "Call"}
    edited = {"message": "Edited advert", "cta": "Call"}
    record = create_payload_escrow_record(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        action_type="publish_advert",
        payload_type="publish_payload",
        payload=payload,
    )
    bound = bind_approval_to_escrow(
        escrow_record=record,
        approval_hash="sha256:approval",
        approved_payload_hash=record["payload_hash"],
    )

    result = validate_escrow_payload_unchanged(
        escrow_record=bound,
        current_payload=edited,
    )

    assert result["payload_unchanged"] is False
    assert result["execution_allowed"] is False
    assert result["requires_fresh_approval"] is True
    assert result["reason"] == "escrow_payload_changed_requires_fresh_approval"

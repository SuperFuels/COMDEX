import pytest

from backend.services.aion_mission_mode.mission_approval import (
    approval_expired,
    canonical_payload_hash,
    create_checkpoint_approval,
    create_mission_approval,
    reject_broad_checkpoint_approval,
    validate_checkpoint_approval_scope,
    validate_checkpoint_payload_unchanged,
    validate_mission_approval_scope,
)


def test_phase20f_canonical_payload_hash_is_stable_with_sorted_keys() -> None:
    first = canonical_payload_hash({"b": 2, "a": 1})
    second = canonical_payload_hash({"a": 1, "b": 2})

    assert first == second
    assert first.startswith("sha256:")


def test_phase20f_mission_approval_approves_boundaries_only() -> None:
    approval = create_mission_approval(
        mission_id="mission_001",
        mission_run_id="run_001",
        approved_by="kevin_robinson",
        approved=True,
        approved_contract_hash="sha256:contract",
        approved_lanes=["research", "creation", "internal_ops"],
        approved_hard_blocked_lanes=["external_action", "financial_action"],
        max_runtime_seconds=1800,
        max_tool_calls=40,
        max_cost=0.0,
    )

    assert approval["approval_scope"] == "mission_boundary_only"
    assert approval["live_side_effects_enabled"] is False
    assert "payload_hash" not in approval
    assert validate_mission_approval_scope(approval) is True
    assert approval["approval_hash"].startswith("sha256:")


def test_phase20f_checkpoint_approval_binds_exact_payload_hash() -> None:
    payload = {"message": "Draft advert", "cta": "Call Home Fixed"}
    payload_hash = canonical_payload_hash(payload)

    approval = create_checkpoint_approval(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        approved_by="kevin_robinson",
        approved=True,
        payload_hash=payload_hash,
        action_type="publish_advert",
        risk_level="high",
    )

    assert approval["approval_scope"] == "exact_payload_only"
    assert approval["payload_hash"] == payload_hash
    assert validate_checkpoint_approval_scope(approval) is True
    assert approval["approval_hash"].startswith("sha256:")


def test_phase20f_checkpoint_approval_requires_payload_hash() -> None:
    with pytest.raises(ValueError):
        create_checkpoint_approval(
            mission_id="mission_001",
            mission_run_id="run_001",
            checkpoint_id="checkpoint_publish",
            step_id="step_publish",
            approved_by="kevin_robinson",
            approved=True,
            payload_hash="",
            action_type="publish_advert",
            risk_level="high",
        )


def test_phase20f_broad_checkpoint_approval_is_rejected() -> None:
    assert reject_broad_checkpoint_approval(
        {
            "approval_scope": "exact_payload_only",
            "payload_hash": "*",
        }
    ) is True

    assert reject_broad_checkpoint_approval(
        {
            "approval_scope": "mission_boundary_only",
            "payload_hash": "sha256:payload",
        }
    ) is True


def test_phase20f_exact_checkpoint_approval_is_not_rejected() -> None:
    assert reject_broad_checkpoint_approval(
        {
            "approval_scope": "exact_payload_only",
            "payload_hash": "sha256:payload",
        }
    ) is False


def test_phase20f_edited_payload_invalidates_checkpoint_approval() -> None:
    original = {"message": "Draft advert", "cta": "Call Home Fixed"}
    edited = {"message": "Draft advert changed", "cta": "Call Home Fixed"}

    approval = create_checkpoint_approval(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        approved_by="kevin_robinson",
        approved=True,
        payload_hash=canonical_payload_hash(original),
        action_type="publish_advert",
        risk_level="high",
    )

    assert validate_checkpoint_payload_unchanged(
        approval=approval,
        current_payload=original,
    ) is True

    assert validate_checkpoint_payload_unchanged(
        approval=approval,
        current_payload=edited,
    ) is False


def test_phase20f_invalid_risk_level_rejected() -> None:
    with pytest.raises(ValueError):
        create_checkpoint_approval(
            mission_id="mission_001",
            mission_run_id="run_001",
            checkpoint_id="checkpoint_publish",
            step_id="step_publish",
            approved_by="kevin_robinson",
            approved=True,
            payload_hash="sha256:payload",
            action_type="publish_advert",
            risk_level="unknown",
        )


def test_phase20f_approval_expiry_check() -> None:
    approval = create_checkpoint_approval(
        mission_id="mission_001",
        mission_run_id="run_001",
        checkpoint_id="checkpoint_publish",
        step_id="step_publish",
        approved_by="kevin_robinson",
        approved=True,
        payload_hash="sha256:payload",
        action_type="publish_advert",
        risk_level="high",
        expires_at="2026-06-07T12:00:00",
    )

    assert approval_expired(approval=approval, now_iso="2026-06-07T11:59:59") is False
    assert approval_expired(approval=approval, now_iso="2026-06-07T12:00:01") is True

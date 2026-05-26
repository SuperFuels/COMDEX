from backend.modules.aion.goal_engine.checkpointing import (
    CHECKPOINT_SCHEMA_VERSION,
    STATE_DELTA_SCHEMA_VERSION,
    CheckpointContract,
    StateDeltaContract,
    build_checkpoint_preview,
    build_state_delta_preview,
)


def test_checkpoint_contract_exists_and_schema_is_locked():
    assert CHECKPOINT_SCHEMA_VERSION == "aion.goal_engine.checkpoint.v1"
    assert STATE_DELTA_SCHEMA_VERSION == "aion.goal_engine.state_delta.v1"


def test_state_delta_preview_is_bounded_and_does_not_store_full_payload():
    delta = StateDeltaContract(
        delta_id="delta_001",
        run_id="run_001",
        checkpoint_id="chk_001",
        changed_fields={"metric_actual": 3, "remaining_iterations": 7},
        full_payload={"large": "payload"},
        max_delta_bytes=4096,
    )

    preview = build_state_delta_preview(delta)

    assert preview["schema_version"] == STATE_DELTA_SCHEMA_VERSION
    assert preview["bounded"] is True
    assert preview["stores_full_payload"] is False
    assert preview["full_payload_blocked"] is True
    assert preview["changed_fields"]["metric_actual"] == 3
    assert "full_payload_not_allowed" in preview["blocked_reasons"]


def test_checkpoint_preview_preserves_loop_context_snapshot():
    checkpoint = CheckpointContract(
        checkpoint_id="chk_001",
        run_id="run_001",
        parent_run_id="run_parent_001",
        goal_id="goal_001",
        loop_id="loop_001",
        iteration=4,
        resume_status="waiting_approval",
        state_delta_id="delta_001",
        loop_context_snapshot={
            "current_best_variant": "variant_whatsapp",
            "remaining_budget": 12.5,
            "remaining_iterations": 6,
        },
        environment_revalidation_required=True,
    )

    preview = build_checkpoint_preview(checkpoint)

    assert preview["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert preview["checkpoint_id"] == "chk_001"
    assert preview["loop_context_snapshot"]["current_best_variant"] == "variant_whatsapp"
    assert preview["environment_revalidation_required"] is True
    assert preview["resume_status"] == "waiting_approval"
    assert preview["dry_run_only"] is True
    assert preview["would_resume"] is False


def test_checkpoint_preview_requires_environment_revalidation_for_resume():
    checkpoint = CheckpointContract(
        checkpoint_id="chk_resume_001",
        run_id="run_001",
        goal_id="goal_001",
        loop_id="loop_001",
        iteration=2,
        resume_status="ready",
        environment_revalidation_required=True,
    )

    preview = build_checkpoint_preview(checkpoint)

    assert preview["resume_blocked_until_revalidated"] is True
    assert "resume_requires_environment_revalidation" in preview["blocked_reasons"]


def test_checkpoint_contract_blocks_invalid_iteration():
    checkpoint = CheckpointContract(
        checkpoint_id="chk_bad_001",
        run_id="run_001",
        goal_id="goal_001",
        loop_id="loop_001",
        iteration=-1,
    )

    preview = build_checkpoint_preview(checkpoint)

    assert preview["valid"] is False
    assert "iteration must be zero or greater" in preview["validation_errors"]

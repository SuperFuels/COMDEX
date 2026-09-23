from backend.modules.aion.goal_engine.checkpointing import (
    CheckpointContract,
    StateDeltaContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_checkpoint_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_checkpoint_bundle_001",
        workflow_id="workflow_checkpoint_bundle",
        contracts=[
            StateDeltaContract(
                delta_id="delta_001",
                run_id="run_checkpoint_bundle_001",
                checkpoint_id="chk_001",
                changed_fields={"remaining_iterations": 4},
                full_payload={"blocked": True},
            ),
            CheckpointContract(
                checkpoint_id="chk_001",
                run_id="run_checkpoint_bundle_001",
                goal_id="goal_001",
                loop_id="loop_001",
                iteration=3,
                state_delta_id="delta_001",
                loop_context_snapshot={"remaining_iterations": 4},
                environment_revalidation_required=True,
            ),
        ],
    )

    payload = bundle.to_dict()

    assert "checkpoint_runtime_summary" in payload

    summary = payload["checkpoint_runtime_summary"]
    assert summary["trace_type"] == "checkpoint_runtime_summary"
    assert summary["checkpoint_count"] == 1
    assert summary["state_delta_count"] == 1
    assert summary["resume_blocked_count"] == 1
    assert summary["full_payload_blocked_count"] == 1
    assert "resume_requires_environment_revalidation" in summary["blocked_reasons"]
    assert "full_payload_not_allowed" in summary["blocked_reasons"]


def test_preview_bundle_checkpoint_summary_preserves_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_checkpoint_bundle_002",
        workflow_id="workflow_checkpoint_bundle",
        contracts=[
            StateDeltaContract(
                delta_id="delta_002",
                run_id="run_checkpoint_bundle_002",
                checkpoint_id="chk_002",
                changed_fields={"current_best_variant": "variant_email"},
            ),
            CheckpointContract(
                checkpoint_id="chk_002",
                run_id="run_checkpoint_bundle_002",
                goal_id="goal_001",
                loop_id="loop_001",
                iteration=2,
                state_delta_id="delta_002",
                loop_context_snapshot={"current_best_variant": "variant_email"},
            ),
        ],
    )

    summary = bundle.to_dict()["checkpoint_runtime_summary"]

    assert len(summary["checkpoint_previews"]) == 1
    assert len(summary["state_delta_previews"]) == 1
    assert summary["checkpoint_previews"][0]["checkpoint_id"] == "chk_002"
    assert summary["state_delta_previews"][0]["delta_id"] == "delta_002"
    assert summary["state_delta_previews"][0]["changed_fields"]["current_best_variant"] == "variant_email"


def test_checkpoint_summary_remains_dry_run_only():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_checkpoint_bundle_003",
        workflow_id="workflow_checkpoint_bundle",
        contracts=[
            CheckpointContract(
                checkpoint_id="chk_003",
                run_id="run_checkpoint_bundle_003",
                goal_id="goal_001",
                loop_id="loop_001",
            ),
        ],
    )

    summary = bundle.to_dict()["checkpoint_runtime_summary"]

    assert summary["dry_run_only"] is True
    assert summary["would_resume"] is False
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False

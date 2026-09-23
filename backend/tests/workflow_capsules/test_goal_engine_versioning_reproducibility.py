from backend.modules.aion.goal_engine.reproducibility import (
    GOAL_ENGINE_REPRODUCIBILITY_SCHEMA_VERSION,
    build_goal_engine_reproducibility_block,
    stable_checksum,
)
from backend.modules.aion.goal_engine.preview_bundle import _build_machine_trace


def test_reproducibility_block_has_required_versions_and_checksums():
    block = build_goal_engine_reproducibility_block(
        source_capsule={"workflow_id": "wf_1", "steps": [{"id": "a"}]},
        goal_contract={"goal_id": "goal_1", "target_metric": "leads"},
        child_glyph_versions=[{"glyph_code": "WD-001", "version": "1.0.0"}],
    )

    assert block["schema_version"] == GOAL_ENGINE_REPRODUCIBILITY_SCHEMA_VERSION
    assert block["trace_type"] == "goal_engine_reproducibility"
    assert block["goal_version"] == "goal.v1"
    assert block["experiment_version"] == "experiment.v1"
    assert block["loop_version"] == "loop.v1"
    assert block["outcome_schema_version"] == "outcome.v1"
    assert block["memory_schema_version"] == "memory.v1"
    assert block["checkpoint_schema_version"] == "checkpoint.v1"
    assert len(block["source_capsule_checksum"]) == 64
    assert len(block["goal_contract_checksum"]) == 64
    assert block["versions_pinned"] is True
    assert block["preserve_old_versions"] is True
    assert block["rollback_supported"] is False
    assert block["dry_run_only"] is True


def test_stable_checksum_is_order_independent():
    left = {"b": 2, "a": {"z": 1, "y": 0}}
    right = {"a": {"y": 0, "z": 1}, "b": 2}

    assert stable_checksum(left) == stable_checksum(right)


def test_preview_bundle_machine_trace_includes_reproducibility_block():
    manifest = {
        "valid": True,
        "steps": [
            {
                "step_type": "goal",
                "contract_id": "goal_1",
                "contract": {
                    "goal_id": "goal_1",
                    "goal_name": "Increase leads",
                    "target_metric": "leads",
                    "target_value": 10,
                },
            }
        ],
    }

    machine_trace = _build_machine_trace(
        run_id="run_1",
        workflow_id="wf_1",
        manifest=manifest,
        step_trace=[],
    )

    block = machine_trace["reproducibility"]

    assert machine_trace["goal_engine_reproducibility"] == block
    assert block["trace_type"] == "goal_engine_reproducibility"
    assert block["versions_pinned"] is True
    assert len(block["source_capsule_checksum"]) == 64
    assert len(block["goal_contract_checksum"]) == 64

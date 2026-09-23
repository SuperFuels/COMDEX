from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    attach_goal_engine_manifest_to_dry_result,
    build_goal_engine_manifest_for_capsule,
    build_goal_engine_step_trace_rows,
)


class DummyDryResult:
    def to_dict(self):
        return {
            "schema_version": "aion.workflow_capsule_dry_run_result.v1",
            "status": "dry_run_completed",
            "trace": [],
        }


def checkpoint_capsule():
    return {
        "canonical_key": "test.goal_engine.checkpoint_state_delta_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {"metric_target": "10 enquiries"},
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {
                    "max_iterations": 3,
                    "checkpoint_every": 1,
                    "max_checkpoint_size": 2048,
                    "checkpoint_summary": "Track lead generation loop state only.",
                },
            },
            {
                "id": "state_delta_1",
                "title": "Accumulate bounded state delta",
                "action_id": "goal_engine.state_delta_accumulator",
                "config": {
                    "max_delta_bytes": 1024,
                    "state_delta_strategy": "bounded_delta_only",
                    "loop_context_snapshot": {"iteration": 0, "status": "preview"},
                },
            },
            {
                "id": "revalidate_1",
                "title": "Revalidate environment before resume",
                "action_id": "goal_engine.environment_revalidation",
                "config": {
                    "revalidate_approval": True,
                    "revalidate_vault": True,
                    "revalidate_connectors": True,
                    "revalidate_parent_goal": True,
                },
            },
        ],
    }


def test_loop_trace_contains_checkpoint_resume_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        checkpoint_capsule(),
        run_id="run_checkpoint_1",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_checkpoint_1")

    loop_row = next(row for row in rows if row["node_id"] == "loop_1")
    preview = loop_row["checkpoint_resume_preview"]

    assert preview["schema_version"] == "aion.goal_engine.checkpoint_resume_preview.v1"
    assert preview["node_id"] == "loop_1"
    assert preview["checkpoint_required"] is True
    assert preview["checkpoint_every"] == 1
    assert preview["max_checkpoint_size"] == 2048
    assert preview["checkpoint_summary"] == "Track lead generation loop state only."
    assert preview["resume_requires_environment_revalidation"] is True
    assert preview["external_write_performed"] is False


def test_state_delta_trace_contains_bounded_delta_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        checkpoint_capsule(),
        run_id="run_checkpoint_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_checkpoint_2")

    delta_row = next(row for row in rows if row["node_id"] == "state_delta_1")
    preview = delta_row["state_delta_preview"]

    assert preview["schema_version"] == "aion.goal_engine.state_delta_preview.v1"
    assert preview["node_id"] == "state_delta_1"
    assert preview["state_delta_strategy"] == "bounded_delta_only"
    assert preview["max_delta_bytes"] == 1024
    assert preview["append_full_history"] is False
    assert preview["bounded_delta_only"] is True
    assert preview["external_write_performed"] is False
    assert preview["loop_context_snapshot"]["iteration"] == 0


def test_environment_revalidation_trace_contains_resume_guards():
    manifest = build_goal_engine_manifest_for_capsule(
        checkpoint_capsule(),
        run_id="run_checkpoint_3",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_checkpoint_3")

    revalidate_row = next(row for row in rows if row["node_id"] == "revalidate_1")
    preview = revalidate_row["environment_revalidation_preview"]

    assert preview["schema_version"] == "aion.goal_engine.environment_revalidation_preview.v1"
    assert preview["node_id"] == "revalidate_1"
    assert preview["revalidate_approval"] is True
    assert preview["revalidate_vault"] is True
    assert preview["revalidate_connectors"] is True
    assert preview["revalidate_parent_goal"] is True
    assert preview["stop_if_external_state_changed"] is True
    assert preview["external_write_performed"] is False


def test_manifest_attach_preserves_checkpoint_and_state_delta_previews():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        checkpoint_capsule(),
        run_id="run_checkpoint_4",
    )

    payload = result.to_dict()
    rows = payload["trace"]

    loop_row = next(row for row in rows if row.get("node_id") == "loop_1")
    delta_row = next(row for row in rows if row.get("node_id") == "state_delta_1")
    revalidate_row = next(row for row in rows if row.get("node_id") == "revalidate_1")

    assert loop_row["checkpoint_resume_preview"]["checkpoint_required"] is True
    assert delta_row["state_delta_preview"]["bounded_delta_only"] is True
    assert revalidate_row["environment_revalidation_preview"]["stop_if_external_state_changed"] is True

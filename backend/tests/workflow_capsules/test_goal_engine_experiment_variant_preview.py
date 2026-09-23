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


def experiment_capsule(variants=None):
    return {
        "canonical_key": "test.goal_engine.experiment_variant_preview",
        "steps": [
            {
                "id": "goal_1",
                "title": "Grow local leads",
                "action_id": "goal_engine.goal",
                "config": {"metric_target": "10 enquiries"},
            },
            {
                "id": "experiment_1",
                "title": "A/B test offer",
                "action_id": "goal_engine.experiment",
                "config": {
                    "metric": "reply_rate",
                    "variants": variants or ["Offer A", "Offer B"],
                    "winner_policy": "manual",
                    "exploration_factor": 0.15,
                    "min_exploration_floor": 0.05,
                    "confidence_threshold": 0.95,
                },
            },
        ],
    }


def test_experiment_step_trace_contains_variant_preview():
    manifest = build_goal_engine_manifest_for_capsule(
        experiment_capsule(),
        run_id="run_experiment_preview_1",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_experiment_preview_1")

    experiment_row = next(row for row in rows if row["node_kind"] == "experiment")
    preview = experiment_row["experiment_variant_preview"]

    assert preview["schema_version"] == "aion.goal_engine.experiment_variant_preview.v1"
    assert preview["runtime"] == "aion_goal_engine"
    assert preview["node_id"] == "experiment_1"
    assert preview["metric"] == "reply_rate"
    assert preview["winner_policy"] == "manual"
    assert preview["dry_run_only"] is True
    assert preview["grants_permission"] is False
    assert preview["external_write_performed"] is False
    assert preview["requires_manual_winner"] is True
    assert preview["exploration_factor"] == 0.15
    assert preview["min_exploration_floor"] == 0.05
    assert preview["confidence_threshold"] == 0.95
    assert len(preview["variants"]) == 2
    assert preview["variants"][0]["label"] == "Offer A"
    assert preview["variants"][0]["allocation_percent"] > 0


def test_experiment_variant_preview_is_also_in_payload():
    manifest = build_goal_engine_manifest_for_capsule(
        experiment_capsule(variants=["A", "B", "C"]),
        run_id="run_experiment_preview_2",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_experiment_preview_2")

    experiment_row = next(row for row in rows if row["node_kind"] == "experiment")
    preview = experiment_row["payload"]["experiment_variant_preview"]

    assert len(preview["variants"]) == 3
    assert preview["variants"][2]["label"] == "C"
    assert preview["winner_policy"] == "manual"


def test_manifest_attach_preserves_experiment_preview_in_dry_result_trace():
    result = attach_goal_engine_manifest_to_dry_result(
        DummyDryResult(),
        experiment_capsule(),
        run_id="run_experiment_preview_3",
    )

    payload = result.to_dict()
    experiment_row = next(row for row in payload["trace"] if row.get("node_kind") == "experiment")

    assert experiment_row["node_id"] == "experiment_1"
    assert experiment_row["experiment_variant_preview"]["metric"] == "reply_rate"
    assert experiment_row["experiment_variant_preview"]["requires_manual_winner"] is True
    assert experiment_row["experiment_variant_preview"]["external_write_performed"] is False


def test_experiment_preview_never_allocates_100_percent_without_policy():
    manifest = build_goal_engine_manifest_for_capsule(
        experiment_capsule(variants=["A", "B"]),
        run_id="run_experiment_preview_4",
    )
    rows = build_goal_engine_step_trace_rows(manifest, run_id="run_experiment_preview_4")
    experiment_row = next(row for row in rows if row["node_kind"] == "experiment")
    preview = experiment_row["experiment_variant_preview"]

    allocations = [variant["allocation_percent"] for variant in preview["variants"]]

    assert max(allocations) < 100
    assert preview["auto_allocate_full_winner"] is False
    assert preview["manual_review_required_before_winner"] is True

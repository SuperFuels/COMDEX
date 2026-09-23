from backend.modules.workflow_capsules.execution.goal_engine_dry_run_bridge import (
    build_goal_engine_manifest_for_capsule,
)
from backend.modules.aion.goal_engine.boardroom_trace import (
    build_goal_engine_boardroom_trace,
)


def goal_capsule():
    return {
        "canonical_key": "test.goal_engine.manifest_trace_alignment",
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
                "config": {"variants": ["A", "B"]},
            },
            {
                "id": "loop_1",
                "title": "Bounded improvement loop",
                "action_id": "goal_engine.loop",
                "config": {"max_iterations": 3},
            },
            {
                "id": "outcome_1",
                "title": "Evaluate outcome",
                "action_id": "goal_engine.outcome_evaluation",
                "config": {"metric": "enquiries"},
            },
        ],
    }


def test_boardroom_trace_preserves_manifest_runtime_safety_contract():
    manifest = build_goal_engine_manifest_for_capsule(
        goal_capsule(),
        run_id="run_manifest_alignment_1",
    )
    trace = build_goal_engine_boardroom_trace(manifest)

    assert trace["runtime"] == manifest["runtime"]
    assert trace["dry_run_only"] == manifest["dry_run_only"]
    assert trace["grants_permission"] is False
    assert trace["would_grant_permission"] == manifest["would_grant_permission"]

    safety = manifest["safety_contract"]
    assert safety["goals_grant_permission"] is False
    assert safety["experiments_grant_permission"] is False
    assert safety["loops_grant_permission"] is False
    assert safety["external_writes_require_approval"] is True
    assert safety["unbounded_loops_allowed"] is False


def test_boardroom_trace_covers_manifest_goal_engine_step_kinds():
    manifest = build_goal_engine_manifest_for_capsule(
        goal_capsule(),
        run_id="run_manifest_alignment_2",
    )
    trace = build_goal_engine_boardroom_trace(manifest)

    manifest_kinds = {
        str(step.get("step_type") or "")
        for step in manifest.get("steps", [])
        if str(step.get("step_type") or "")
    }

    trace_text = repr(trace).lower()

    for kind in manifest_kinds:
        assert kind in trace_text, f"Boardroom trace missing manifest step kind: {kind}"


def test_boardroom_trace_does_not_hide_manifest_validation_or_blocked_state():
    manifest = build_goal_engine_manifest_for_capsule(
        goal_capsule(),
        run_id="run_manifest_alignment_3",
    )
    trace = build_goal_engine_boardroom_trace(manifest)

    manifest_errors = manifest.get("validation_errors") or []
    trace_text = repr(trace)

    if manifest_errors:
        for error in manifest_errors:
            assert str(error) in trace_text

    assert "blocked" in trace_text.lower() or "warning" in trace_text.lower() or trace.get("valid") is manifest.get("valid")

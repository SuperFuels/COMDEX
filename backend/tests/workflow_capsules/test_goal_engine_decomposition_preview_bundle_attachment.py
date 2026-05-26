import inspect

from backend.modules.aion.goal_engine.decomposition import (
    GoalDecompositionContract,
    SubGoalContract,
)
from backend.modules.aion.goal_engine.preview_bundle import (
    _build_goal_decomposition_runtime_summary,
    build_goal_engine_preview_bundle,
)


def _sub_goal(**overrides):
    values = {
        "sub_goal_id": "sub_goal_1",
        "parent_goal_id": "goal_parent_1",
        "objective": "Collect customer request details",
        "assigned_agent_id": "agent_ops",
        "glyph_code": "WD-101",
        "status": "preview_only",
        "metadata": {"source": "decomposition_preview_bundle_test"},
    }
    values.update(overrides)

    import inspect
    accepted = set(inspect.signature(SubGoalContract).parameters)
    return SubGoalContract(**{key: value for key, value in values.items() if key in accepted})


def _contract():
    return GoalDecompositionContract(
        decomposition_id="decomp_preview_bundle_1",
        parent_goal_id="goal_parent_1",
        parent_goal_title="Grow CostaConnect local supply",
        decomposition_strategy="sequential",
        max_depth=3,
        max_sub_goals=3,
        current_depth=0,
        approval_required_before_expansion=True,
        risk_tier="medium",
        sub_goals=[
            _sub_goal(
                sub_goal_id="sub_goal_trades_1",
                parent_goal_id="goal_parent_1",
                objective="Onboard 10 plumbers",
                title="Onboard 10 plumbers",
                goal_title="Onboard 10 plumbers",
                description="Get 10 local plumbing suppliers claimed and evidence-backed.",
                suggested_glyph_code="WD-101",
                glyph_code="WD-101",
                owner_agent_id="agent_marketing",
                agent_id="agent_marketing",
                success_metric="10 claimed listings",
                metadata={"evidence_required": True},
            ),
            _sub_goal(
                sub_goal_id="sub_goal_reviews_1",
                parent_goal_id="goal_parent_1",
                objective="Collect supplier proof",
                title="Collect supplier proof",
                goal_title="Collect supplier proof",
                description="Collect review and reply evidence.",
                suggested_glyph_code="EV-201",
                glyph_code="EV-201",
                owner_agent_id="agent_reviewer",
                agent_id="agent_reviewer",
                success_metric="review evidence attached",
                metadata={"evidence_required": True},
            ),
        ],
    )


def test_decomposition_runtime_summary_preserves_preview_only_child_rows():
    summary = _build_goal_decomposition_runtime_summary(contracts=[_contract()])

    assert summary["trace_type"] == "goal_decomposition_runtime_summary"
    assert summary["decomposition_count"] == 1
    assert summary["sub_goal_count"] == 2
    assert summary["dry_run_only"] is True
    assert summary["would_create_child_goals"] is False
    assert summary["would_mutate_parent_goal"] is False
    assert summary["would_grant_permission"] is False

    preview = summary["goal_decomposition_previews"][0]
    assert preview["trace_type"] == "goal_decomposition_preview"
    assert preview["parent_goal_id"] == "goal_parent_1"
    assert preview["would_create_child_goals"] is False
    assert preview["would_mutate_parent_goal"] is False
    assert preview["would_grant_permission"] is False
    assert len(preview["sub_goal_previews"]) == 2


def test_preview_bundle_exposes_decomposition_top_level_and_machine_trace():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_decomp_bundle_1",
        workflow_id="wf_decomp_bundle_1",
        contracts=[_contract()],
    )
    payload = bundle.to_dict()

    assert "goal_decomposition_runtime_summary" in payload
    assert "goal_engine_decomposition_runtime_summary" in payload
    assert "goal_decomposition_previews" in payload
    assert len(payload["goal_decomposition_previews"]) == 1

    machine_trace = payload["machine_trace"]
    assert "goal_decomposition_runtime_summary" in machine_trace
    assert "goal_engine_decomposition_runtime_summary" in machine_trace
    assert "goal_decomposition_previews" in machine_trace
    assert machine_trace["goal_decomposition_runtime_summary"]["decomposition_count"] == 1
    assert len(machine_trace["goal_decomposition_previews"]) == 1


def test_preview_bundle_mapping_access_supports_decomposition_fields():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_decomp_mapping_1",
        workflow_id="wf_decomp_mapping_1",
        contracts=[_contract()],
    )

    assert bundle["goal_decomposition_runtime_summary"]["decomposition_count"] == 1
    assert bundle["goal_decomposition_previews"][0]["decomposition_id"] == "decomp_preview_bundle_1"
    assert bundle.get("goal_decomposition_previews")[0]["parent_goal_id"] == "goal_parent_1"


def test_empty_contracts_keep_safe_empty_decomposition_summary():
    summary = _build_goal_decomposition_runtime_summary(contracts=[])

    assert summary["decomposition_count"] == 0
    assert summary["sub_goal_count"] == 0
    assert summary["goal_decomposition_previews"] == []
    assert summary["child_goal_previews"] == []
    assert summary["dry_run_only"] is True
    assert summary["would_create_child_goals"] is False
    assert summary["would_mutate_parent_goal"] is False
    assert summary["would_grant_permission"] is False

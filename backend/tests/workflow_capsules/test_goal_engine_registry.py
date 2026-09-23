from backend.modules.aion.goal_engine.contracts import GoalNodeContract
from backend.modules.aion.goal_engine.registry import (
    get_goal_engine_node_spec,
    list_goal_engine_node_types,
    registry_manifest,
    serialize_contract,
)


def test_registry_contains_core_goal_engine_nodes():
    node_types = list_goal_engine_node_types()

    assert "goal" in node_types
    assert "experiment" in node_types
    assert "loop" in node_types
    assert "outcome_evaluation" in node_types
    assert "reflect_learn" in node_types
    assert "state_delta_accumulator" in node_types
    assert "environment_revalidation" in node_types


def test_registry_nodes_do_not_grant_permission():
    for node_type in list_goal_engine_node_types():
        spec = get_goal_engine_node_spec(node_type)
        assert spec["grants_permission"] is False


def test_registry_defaults_to_dry_run_visibility():
    for node_type in list_goal_engine_node_types():
        spec = get_goal_engine_node_spec(node_type)
        assert spec["dry_run_only_default"] is True


def test_registry_manifest_exposes_safety_contract():
    manifest = registry_manifest()

    assert manifest["runtime"] == "aion_goal_engine"
    assert manifest["safety_contract"]["goals_grant_permission"] is False
    assert manifest["safety_contract"]["experiments_grant_permission"] is False
    assert manifest["safety_contract"]["loops_grant_permission"] is False
    assert manifest["safety_contract"]["learning_grants_permission"] is False
    assert manifest["safety_contract"]["external_writes_require_approval"] is True
    assert manifest["safety_contract"]["unbounded_loops_allowed"] is False
    assert manifest["safety_contract"]["resume_requires_environment_revalidation"] is True


def test_serialize_contract_includes_validation_errors():
    contract = GoalNodeContract(
        goal_id="goal_001",
        goal_name="Generate leads",
        target_metric="lead_count",
        target_value=50,
    )

    payload = serialize_contract(contract)

    assert payload["contract_type"] == "GoalNodeContract"
    assert payload["goal_id"] == "goal_001"
    assert payload["validation_errors"] == []

from backend.modules.aion.goal_engine.contracts import (
    EnvironmentRevalidationContract,
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
    ReflectionLearningContract,
    StateDeltaAccumulatorContract,
)


def test_goal_node_contract_validates_required_fields():
    contract = GoalNodeContract(
        goal_id="goal_leads_001",
        goal_name="Generate leads",
        target_metric="lead_count",
        target_value=50,
        max_iterations=10,
    )
    assert contract.validate() == []


def test_goal_node_does_not_allow_invalid_thresholds():
    contract = GoalNodeContract(
        goal_id="goal_bad",
        goal_name="Bad goal",
        target_metric="lead_count",
        target_value=50,
        success_threshold=0.2,
        failure_threshold=0.8,
    )
    assert "success_threshold must be greater than failure_threshold" in contract.validate()


def test_experiment_requires_at_least_two_variants():
    contract = ExperimentNodeContract(
        experiment_id="exp_001",
        goal_id="goal_001",
        variants=["variant_a"],
        metric="ctr",
    )
    assert "experiment requires at least 2 variants" in contract.validate()


def test_experiment_has_exploration_floor_and_decay_guards():
    contract = ExperimentNodeContract(
        experiment_id="exp_001",
        goal_id="goal_001",
        variants=["a", "b"],
        metric="ctr",
        exploration_factor=0.15,
        exploration_decay=0.98,
        min_exploration_floor=0.05,
    )
    assert contract.validate() == []


def test_loop_contract_requires_hard_bounds():
    contract = LoopNodeContract(
        loop_id="loop_001",
        goal_id="goal_001",
        loop_mode="until_goal_achieved",
        max_iterations=20,
        max_runtime_minutes=60,
        max_external_writes=0,
    )
    assert contract.validate() == []


def test_loop_contract_blocks_unbounded_iterations():
    contract = LoopNodeContract(loop_id="loop_bad", max_iterations=0)
    assert "max_iterations must be at least 1" in contract.validate()


def test_outcome_contract_tracks_score_and_evidence():
    contract = OutcomeEvaluationContract(
        outcome_id="outcome_001",
        goal_id="goal_001",
        run_id="run_001",
        status="success",
        quality_score=0.92,
        metric_actual=53,
        metric_target=50,
        confidence=0.9,
        evidence=[{"source": "manual", "value": 53}],
    )
    assert contract.validate() == []


def test_reflection_learning_requires_allow_learn_and_advisory_only():
    contract = ReflectionLearningContract(
        reflection_id="reflect_001",
        source_run_id="run_001",
        source_workflow_id="workflow_001",
        allow_learn=True,
        advisory_only=True,
    )
    assert contract.validate() == []


def test_reflection_learning_blocks_adr_active():
    contract = ReflectionLearningContract(
        reflection_id="reflect_001",
        source_run_id="run_001",
        source_workflow_id="workflow_001",
        allow_learn=True,
        adr_active=True,
    )
    assert "learning blocked while adr_active=true" in contract.validate()


def test_state_delta_accumulator_is_bounded():
    contract = StateDeltaAccumulatorContract(
        accumulator_id="acc_001",
        run_id="run_001",
        checkpoint_id="chk_001",
        loop_context_snapshot={"iteration": 3},
        deltas=[{"iteration": 3, "score": 0.71}],
    )
    assert contract.validate() == []


def test_environment_revalidation_must_pass_before_resume():
    contract = EnvironmentRevalidationContract(
        revalidation_id="reval_001",
        run_id="run_001",
        checkpoint_id="chk_001",
        parent_goal_id="goal_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=False,
    )
    assert contract.validate() == []


def test_environment_revalidation_blocks_stale_external_state():
    contract = EnvironmentRevalidationContract(
        revalidation_id="reval_bad",
        run_id="run_001",
        checkpoint_id="chk_001",
        approval_still_valid=True,
        vault_ready=True,
        connectors_ready=True,
        parent_goal_still_required=True,
        external_state_changed=True,
    )
    assert "external state changed; resume must stop or re-plan" in contract.validate()

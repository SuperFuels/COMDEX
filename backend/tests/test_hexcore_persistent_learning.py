from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.modules.hexcore.integrated_learning_benchmark import run_benchmark
from backend.modules.hexcore.active_causal_discovery import (
    CausalHypothesis,
    GovernedActiveCausalLearner,
)
from backend.modules.hexcore.active_causal_discovery_benchmark import (
    run_active_causal_benchmark,
)
from backend.modules.hexcore.governed_runtime import HexCoreGovernedRuntime
from backend.modules.hexcore.multi_domain_learning_benchmark import (
    run_multi_domain_benchmark,
)
from backend.modules.hexcore.open_causal_graph_benchmark import (
    run_open_causal_graph_benchmark,
)
from backend.modules.hexcore.open_causal_graph_discovery import (
    GovernedOpenCausalGraphLearner,
    MultiVariableBooleanEnvironment,
)
from backend.modules.hexcore.latent_causal_state_benchmark import (
    run_latent_state_benchmark,
)
from backend.modules.hexcore.latent_causal_state_discovery import (
    GovernedLatentStateLearner,
    HiddenModeLampEnvironment,
)
from backend.modules.hexcore.stochastic_multilatent_benchmark import (
    run_stochastic_multilatent_benchmark,
)
from backend.modules.hexcore.cross_domain_causal_transfer_benchmark import (
    run_cross_domain_transfer_benchmark,
)
from backend.modules.hexcore.outcome_driven_causal_evolution_benchmark import (
    run_outcome_evolution_benchmark,
)
from backend.modules.hexcore.causal_efficiency_evolution_benchmark import (
    run_causal_efficiency_benchmark,
)
from backend.modules.hexcore.multigeneration_causal_evolution_benchmark import (
    run_multigeneration_causal_evolution,
)
from backend.modules.hexcore.online_reliability_causal_benchmark import (
    run_online_reliability_benchmark,
)
from backend.modules.hexcore.governed_causal_policy_bank_benchmark import (
    run_governed_policy_bank_benchmark,
)
from backend.modules.hexcore.causal_failure_diagnosis_benchmark import (
    run_causal_failure_diagnosis_benchmark,
)
from backend.modules.hexcore.continuous_causal_change_benchmark import (
    run_continuous_change_benchmark,
)
from backend.modules.hexcore.adaptive_change_diagnostics_benchmark import (
    run_adaptive_change_diagnostics_benchmark,
)
from backend.modules.hexcore.anticipatory_temporal_reasoning_benchmark import (
    run_anticipatory_temporal_benchmark,
)
from backend.modules.hexcore.prospective_temporal_planning_benchmark import (
    run_prospective_temporal_planning_benchmark,
)
from backend.modules.hexcore.counterfactual_plan_repair_benchmark import (
    run_counterfactual_plan_repair_benchmark,
)
from backend.modules.hexcore.open_grammar_hierarchical_transfer_benchmark import (
    run_open_grammar_hierarchical_transfer_benchmark,
)
from backend.modules.hexcore.compositional_goal_graph_benchmark import (
    run_compositional_goal_graph_benchmark,
)
from backend.modules.hexcore.open_ontology_invention_benchmark import (
    run_open_ontology_invention_benchmark,
)
from backend.modules.hexcore.skill_contract_invention_benchmark import (
    run_skill_contract_invention_benchmark,
)
from backend.modules.hexcore.meta_abstraction_invention_benchmark import (
    run_meta_abstraction_invention_benchmark,
)
from backend.modules.hexcore.autonomous_concept_curriculum_benchmark import (
    run_autonomous_concept_curriculum_benchmark,
)
from backend.modules.hexcore.multigeneration_theory_revision_benchmark import (
    run_multigeneration_theory_revision_benchmark,
)
from backend.modules.hexcore.learned_experiment_policy_benchmark import (
    run_learned_experiment_policy_benchmark,
)
from backend.modules.hexcore.structural_analogy_benchmark import (
    run_structural_analogy_benchmark,
)
from backend.modules.hexcore.relational_program_induction_benchmark import (
    run_relational_program_induction_benchmark,
)
from backend.modules.hexcore.cognitive_program_evolution_benchmark import (
    run_cognitive_program_evolution_benchmark,
)
from backend.modules.hexcore.executable_knowledge_grounding_benchmark import (
    run_executable_knowledge_grounding_benchmark,
)
from backend.modules.hexcore.tool_grounded_task_learning_benchmark import (
    run_tool_grounded_task_learning_benchmark,
)
from backend.modules.hexcore.integrated_cognitive_workspace_benchmark import (
    run_integrated_cognitive_workspace_benchmark,
)
from backend.modules.hexcore.neural_consolidation_benchmark import (
    run_neural_consolidation_benchmark,
)
from backend.modules.hexcore.continual_neural_improvement_benchmark import (
    run_continual_neural_improvement_benchmark,
)
from backend.modules.hexcore.open_world_cognitive_runtime_benchmark import (
    run_open_world_cognitive_runtime_benchmark,
)
from backend.modules.hexcore.natural_goal_graph_runtime_benchmark import (
    run_natural_goal_graph_runtime_benchmark,
)
from backend.modules.hexcore.open_relation_reasoning_benchmark import (
    run_open_relation_reasoning_benchmark,
)
from backend.modules.hexcore.cost_aware_open_document_benchmark import (
    run_cost_aware_open_document_benchmark,
)
from backend.modules.hexcore.natural_document_comprehension_benchmark import (
    run_natural_document_comprehension_benchmark,
)
from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    LearningAuthorityError,
    TransitionObservation,
)


def _allow(_goal):
    return {"allow_learn": True, "S": 1.0, "H": 0.0}


def test_open_world_runtime_integrates_real_contracts_and_survives_restart(
    tmp_path,
):
    result = run_open_world_cognitive_runtime_benchmark(
        state_path=tmp_path / "phase36_state.json",
        result_path=tmp_path / "phase36_result.json",
        sealed_projects=12,
    )

    assert result["passed"] is True
    assert result["gate"]["accuracy"] == 1.0
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["provider_invariance"] == 1.0
    assert result["gate"]["unsafe_provider_acceptances"] == 0
    assert result["gate"]["tool_failure_recovery"] == 1.0
    assert result["gate"]["ledger_chain_valid"] is True
    assert result["restart"]["relearning_projects"] == 0


def test_natural_goal_graph_runtime_induces_revises_and_executes_graphs(
    tmp_path,
):
    result = run_natural_goal_graph_runtime_benchmark(
        state_path=tmp_path / "phase37_state.json",
        result_path=tmp_path / "phase37_result.json",
        provider_artifact_path=tmp_path / "phase37_providers.json",
        sealed_projects=8,
        live_providers=False,
    )

    assert result["passed"] is True
    assert result["gate"]["goal_success"] == 1.0
    assert result["gate"]["native_graph_accuracy"] == 1.0
    assert result["gate"]["provider_disabled_success"] == 1.0
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["live_pattern_coverage"] == 1.0
    assert result["restart"]["relearning_projects"] == 0


def test_open_relation_reasoning_learns_invents_and_clarifies(tmp_path):
    result = run_open_relation_reasoning_benchmark(
        state_path=tmp_path / "phase38_state.json",
        result_path=tmp_path / "phase38_result.json",
        corpus_path=tmp_path / "phase38_corpus.jsonl",
        sealed_projects=16,
    )

    assert result["passed"] is True
    assert result["gate"]["goal_success"] >= 0.95
    assert result["gate"]["edge_accuracy"] >= 0.90
    assert result["gate"]["latent_subgoal_recovery"] == 1.0
    assert result["gate"]["ambiguity_detection_recall"] == 1.0
    assert result["gate"]["unnecessary_question_rate"] == 0.0
    assert result["gate"]["unsafe_assumptions"] == 0
    assert result["restart"]["relearning_projects"] == 0


def test_cost_aware_open_document_reasoning_routes_and_cites(tmp_path):
    result = run_cost_aware_open_document_benchmark(
        state_path=tmp_path / "phase39_state.json",
        artifact_dir=tmp_path / "phase39_artifacts",
        result_path=tmp_path / "phase39_result.json",
        sealed_projects=10,
    )

    assert result["passed"] is True
    assert result["gate"]["goal_success"] == 1.0
    assert result["gate"]["weakest_domain_success"] == 1.0
    assert result["gate"]["cost_reduction"] >= 0.50
    assert result["gate"]["action_route_accuracy"] == 1.0
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["gate"]["unverified_rumor_acceptances"] == 0
    assert result["restart"]["relearning_projects"] == 0


def test_knowledge_revision_supersedes_obsolete_claim_with_provenance(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "state.json",
        authority_provider=_allow,
    )
    runtime.knowledge.ingest(
        EvidenceCapsule(
            capsule_id="old",
            source_uri="test://old",
            content="Old value",
            claims=[
                {
                    "subject": "device",
                    "predicate": "limit",
                    "object": "5",
                    "revision": 1,
                }
            ],
        )
    )
    result = runtime.knowledge.ingest(
        EvidenceCapsule(
            capsule_id="new",
            source_uri="test://new",
            content="Corrected value",
            claims=[
                {
                    "subject": "device",
                    "predicate": "limit",
                    "object": "4",
                    "revision": 2,
                }
            ],
        )
    )
    query = runtime.knowledge.query_claim("device", "limit")

    assert query["claim"]["object"] == "4"
    assert query["provenance_complete"] is True
    assert result["superseded_claim_ids"]
    assert runtime.status()["contradictions"] == 1


def test_world_rules_are_inferred_from_observed_consequences(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "state.json",
        authority_provider=_allow,
    )
    for index, energy in enumerate([0, 2, 4], start=1):
        runtime.world.observe(
            TransitionObservation(
                observation_id=f"obs-{index}",
                world_id="world",
                state={"energy": energy},
                action="charge",
                next_state={"energy": energy + 2},
                evidence_id=f"sim:{index}",
            )
        )
    rules = runtime.world.infer_effect_rules(world_id="world")
    active = [rule for rule in rules if rule["status"] == "active"]

    assert len(active) == 1
    assert active[0]["effect"] == {"kind": "delta", "value": 2.0}
    assert active[0]["support_count"] == 3
    assert active[0]["contradiction_count"] == 0


def test_persistent_mutation_fails_closed_when_cau_denies(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "state.json",
        authority_provider=lambda _goal: {
            "allow_learn": False,
            "deny_reason": "LOW_STABILITY",
        },
    )

    with pytest.raises(LearningAuthorityError, match="LOW_STABILITY"):
        runtime.knowledge.ingest(
            EvidenceCapsule(
                capsule_id="denied",
                source_uri="test://denied",
                content="Denied",
                claims=[
                    {
                        "subject": "x",
                        "predicate": "is",
                        "object": "y",
                    }
                ],
            )
        )
    assert not (tmp_path / "state.json").exists()


def test_integrated_learning_benchmark_improves_and_survives_restart(tmp_path):
    result_path = tmp_path / "result.json"
    result = run_benchmark(
        state_path=tmp_path / "persistent_state.json",
        result_path=result_path,
    )

    assert result["passed"] is True
    assert result["baseline"]["composite_score"] == 0.0
    assert result["after_learning"]["composite_score"] == 1.0
    assert result["improvement_delta"] == 1.0
    assert result["knowledge"]["contradiction_resolved"] is True
    assert result["world"]["threshold_rule"]["condition"]["value"] == 4.0
    assert result["skill"]["candidate"]["steps"] == ["charge", "charge", "open"]
    assert result["skill"]["held_out_restart_result"]["success"] is True
    assert result["persistence"]["second_cycle_required_relearning"] is False
    assert json.loads(result_path.read_text())["passed"] is True

    governed = HexCoreGovernedRuntime(
        authority_provider=_allow,
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *_args: False,
        foundation_root=tmp_path / "tpu",
        learning_state_path=tmp_path / "persistent_state.json",
    )
    context = governed.begin_turn(
        turn_id="turn-recall",
        session_id="session-recall",
        user_text="What minimum energy opens the lumen vault?",
    )
    persistent_hits = [
        item
        for item in context.recalled_knowledge
        if item["source"] == "hexcore_persistent_knowledge"
    ]
    assert persistent_hits
    assert any("minimum_energy 4" in item["answer"] for item in persistent_hits)


def test_unchanged_learning_algorithms_transfer_across_three_domains(tmp_path):
    result = run_multi_domain_benchmark(
        state_path=tmp_path / "multi_domain_state.json",
        result_path=tmp_path / "multi_domain_result.json",
    )

    assert result["passed"] is True
    assert result["domain_count"] == 3
    assert result["baseline_success_rate"] == 0.0
    assert result["learned_success_rate"] == 1.0
    assert result["restart_success_rate"] == 1.0
    assert result["total_probe_count_cycle_1"] == 27
    assert result["total_probe_count_cycle_2"] == 0
    assert result["domain_specific_learning_code_used"] is False
    assert all(row["held_out_success"] for row in result["restart_results"])


def test_information_gain_selector_prefers_equally_informative_lower_cost_probe(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "causal.json",
        authority_provider=_allow,
    )
    learner = GovernedActiveCausalLearner(runtime.store)
    hypotheses = [
        CausalHypothesis(
            hypothesis_id="a",
            action_outcomes={"cheap": "positive", "expensive": "positive"},
            action_deltas={"cheap": 1.0, "expensive": 1.0},
        ),
        CausalHypothesis(
            hypothesis_id="b",
            action_outcomes={"cheap": "negative", "expensive": "negative"},
            action_deltas={"cheap": -1.0, "expensive": -1.0},
        ),
    ]
    selected = learner.select_experiment(
        belief={"a": 0.5, "b": 0.5},
        hypotheses=hypotheses,
        actions=["cheap", "expensive"],
        action_costs={"cheap": 0.1, "expensive": 0.9},
    )
    assert selected["selected"]["action"] == "cheap"
    assert selected["selected"]["expected_information_gain"] > 0


def test_active_causal_discovery_handles_noise_change_and_restart(tmp_path):
    result = run_active_causal_benchmark(
        state_path=tmp_path / "active_causal.json",
        result_path=tmp_path / "active_causal_result.json",
        seeds_per_mode=20,
    )

    assert result["passed"] is True
    assert result["independent_seed_audit"]["mode_identification_accuracy"] >= 0.9
    assert result["independent_seed_audit"]["average_experiment_count"] <= 5.0
    assert result["change"]["detected"] is True
    assert result["alpha"]["verification"]["success_rate"] >= 0.95
    assert result["beta"]["verification"]["success_rate"] >= 0.95
    assert result["restart"]["alpha_verified_after_restart"] is True
    assert result["restart"]["beta_verified_after_restart"] is True
    assert result["restart"]["relearning_experiments"] == 0


def test_open_causal_graph_discovery_constructs_novel_bounded_structure(tmp_path):
    result = run_open_causal_graph_benchmark(
        state_path=tmp_path / "open_graph_state.json",
        result_path=tmp_path / "open_graph_result.json",
    )

    assert result["passed"] is True
    assert result["initial_hypothesis_set_supplied"] is False
    assert result["gates"]["inadequate_model_rejected"] is True
    assert result["gates"]["novel_structure_constructed"] is True
    assert result["gates"]["complexity_bounded"] is True
    assert result["restart"]["relearning_experiments"] == 0
    assert result["restart"]["evaluation"]["transition_accuracy"] >= 0.95


def test_open_causal_graph_expansion_fails_closed_above_complexity_cap(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "bounded_graph_state.json",
        authority_provider=_allow,
    )
    learner = GovernedOpenCausalGraphLearner(runtime.store)
    environment = MultiVariableBooleanEnvironment()
    session = learner.discover(
        world_id="complexity_limited_world",
        variables=["signal", "gate", "output"],
        actions=["flip_signal", "flip_gate", "pulse", "idle"],
        action_costs={},
        experiment_runner=environment.step,
        initial_state=environment.state,
        experiments=48,
        maximum_graph_complexity=4,
        persist=True,
    )

    assert session["accepted"] is False
    assert "COMPLEXITY_CAP_EXCEEDED" in session["errors"]
    assert "complexity_limited_world" not in runtime.store.state["causal_graphs"]
    assert runtime.store.state["hypothesis_expansions"][-1]["accepted"] is False


def test_latent_state_is_constructed_then_revised_after_world_change(tmp_path):
    result = run_latent_state_benchmark(
        state_path=tmp_path / "latent_state.json",
        result_path=tmp_path / "latent_result.json",
    )

    assert result["passed"] is True
    assert result["hidden_state_labels_supplied"] is False
    assert result["gates"]["latent_state_constructed"] is True
    assert result["gates"]["latent_dynamics_revised"] is True
    assert result["graphs"]["phase_a"]["latent_toggle_action"] == "toggle_mode"
    assert result["graphs"]["phase_b"]["latent_toggle_action"] == "switch_mode"
    assert result["restart"]["retained_revision"] == 2
    assert result["restart"]["relearning_experiments"] == 0


def test_latent_state_construction_respects_authority_cap(tmp_path):
    runtime = HexCorePersistentLearningRuntime(
        state_path=tmp_path / "latent_cap.json",
        authority_provider=_allow,
    )
    learner = GovernedLatentStateLearner(runtime.store)
    actions = ["toggle_mode", "pulse", "idle"]
    sequences = learner.design_diagnostic_sequences(
        actions=actions,
        episode_count=24,
        steps_per_episode=10,
    )

    def factory(_episode_index):
        return HiddenModeLampEnvironment(
            toggle_action="toggle_mode"
        ).step

    rows = learner.collect(
        experiment_runner_factory=factory,
        sequences=sequences,
        phase="latent_cap",
    )
    session = learner.discover_or_revise(
        world_id="latent_cap_world",
        visible_variables=["lamp"],
        actions=actions,
        rows=rows,
        adequacy_gate=0.98,
        minimum_held_out_gain=0.01,
        maximum_latent_variables=0,
        persist=True,
    )

    assert session["accepted"] is False
    assert "LATENT_VARIABLE_CAP_EXCEEDED" in session["errors"]
    assert "latent_cap_world" not in runtime.store.state["causal_graphs"]


def test_stochastic_multilatent_discovery_drives_active_planning(tmp_path):
    result = run_stochastic_multilatent_benchmark(
        state_path=tmp_path / "multilatent.json",
        result_path=tmp_path / "multilatent_result.json",
        audit_episodes=40,
    )

    assert result["passed"] is True
    assert result["gates"]["two_factor_structure_selected"] is True
    assert result["gates"]["active_information_gain_enabled"] is True
    assert result["independent_audit"]["factor_state_accuracy"] >= 0.90
    assert result["independent_audit"]["goal_success_rate"] >= 0.90
    assert result["restart"]["relearning_experiments"] == 0


def test_cross_domain_operator_transfer_reduces_learning_experiments(tmp_path):
    result = run_cross_domain_transfer_benchmark(
        state_path=tmp_path / "cross_domain.json",
        result_path=tmp_path / "cross_domain_result.json",
        audit_episodes=30,
    )

    assert result["passed"] is True
    assert result["symbol_dictionary_supplied"] is False
    assert result["gates"]["all_transfer_structures_correct"] is True
    assert result["aggregate"][
        "minimum_structure_experiment_reduction"
    ] >= 0.50
    assert result["gates"]["abstract_skill_promoted"] is True
    assert result["restart"]["abstract_champion_retained"] is True


def test_outcome_memory_mutates_and_promotes_better_causal_policy(tmp_path):
    result = run_outcome_evolution_benchmark(
        state_path=tmp_path / "evolution.json",
        result_path=tmp_path / "evolution_result.json",
        development_worlds=8,
        sealed_worlds=10,
        development_episodes=24,
        sealed_episodes=30,
    )

    assert result["passed"] is True
    assert result["gates"]["failure_taxonomy_recorded"] is True
    assert result["gates"]["challengers_created_from_outcomes"] is True
    assert result["gates"]["sealed_mean_goal_improved"] is True
    assert result["gates"]["challenger_promoted"] is True
    assert result["restart"]["mutation_cycles"] == 1
    assert result["restart"]["relearning_worlds"] == 0


def test_efficiency_mutation_preserves_success_with_fewer_probes(tmp_path):
    result = run_causal_efficiency_benchmark(
        state_path=tmp_path / "efficiency.json",
        result_path=tmp_path / "efficiency_result.json",
    )

    assert result["passed"] is True
    assert result["gates"]["mean_goal_preserved_or_improved"] is True
    assert result["gates"]["at_least_one_experiment_removed"] is True
    assert result["gates"]["challenger_promoted"] is True
    assert result["restart"]["champion_retained"] is True


def test_natural_document_comprehension_is_gold_isolated_and_persistent(
    tmp_path: Path,
) -> None:
    result = run_natural_document_comprehension_benchmark(
        state_path=tmp_path / "phase40_state.json",
        artifact_dir=tmp_path / "phase40_artifacts",
        result_path=tmp_path / "phase40_result.json",
        sealed_projects=12,
    )
    assert result["passed"] is True
    assert result["gate"]["goal_success"] >= 0.90
    assert result["gate"]["claim_f1"] >= 0.90
    assert result["gate"]["decomposition_exact"] >= 0.90
    assert result["gate"]["contradiction_revision_accuracy"] >= 0.95
    assert result["gate"]["unverified_acceptances"] == 0
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["gold_isolation"]["solver_receives_gold_claims"] is False
    assert result["restart"]["champion_retained"] is True


def test_multigeneration_evolution_uses_total_cost_and_external_family(
    tmp_path,
):
    result = run_multigeneration_causal_evolution(
        state_path=tmp_path / "multigeneration.json",
        result_path=tmp_path / "multigeneration_result.json",
        generations=2,
        development_worlds=10,
        sealed_worlds=12,
        episodes_per_world=40,
        external_world_count=8,
    )

    assert result["gates"]["total_action_cost_accounted"] is True
    assert result["gates"]["goal_relevant_calibration_used"] is True
    assert result["gates"]["external_family_passed"] is True
    for generation in result["generations"]:
        if generation["promotion"] is not None:
            assert generation["sealed"]["gate"]["accepted"] is True
    assert result["restart"]["relearning_worlds"] == 0


def test_online_reliability_is_learned_without_exposing_true_channels(
    tmp_path,
):
    result = run_online_reliability_benchmark(
        state_path=tmp_path / "online_reliability.json",
        result_path=tmp_path / "online_reliability_result.json",
        development_worlds=10,
        sealed_worlds=12,
        episodes_per_world=35,
    )

    assert result["true_channel_reliability_supplied_to_aion"] is False
    assert result["gates"]["online_estimation_recorded"] is True
    assert result["restart"]["relearning_worlds"] == 0
    if result["promotion"]["decision"].get("promoted"):
        assert result["sealed"]["gate"]["accepted"] is True


def test_governed_policy_bank_routes_or_falls_back_without_self_approval(
    tmp_path,
):
    result = run_governed_policy_bank_benchmark(
        state_path=tmp_path / "policy_bank.json",
        result_path=tmp_path / "policy_bank_result.json",
        development_worlds=6,
        sealed_worlds=8,
        episodes_per_world=20,
    )

    assert result["gates"]["three_development_folds"] is True
    assert result["gates"]["router_has_explicit_fallback"] is True
    assert result["restart"]["relearning_worlds"] == 0
    if result["promotion"]["decision"].get("promoted"):
        assert result["sealed"]["gate"]["accepted"] is True


def test_causal_failure_diagnosis_separates_repair_queues(tmp_path):
    result = run_causal_failure_diagnosis_benchmark(
        state_path=tmp_path / "failure_diagnosis.json",
        result_path=tmp_path / "failure_diagnosis_result.json",
        development_worlds=9,
        sealed_worlds=12,
        diagnostic_trials=8,
        planning_episodes=10,
    )

    assert result["gates"]["separate_failure_queues"] is True
    assert result["restart"]["relearning_worlds"] == 0
    if result["promotion"]["decision"].get("promoted"):
        assert result["sealed"]["gate"]["accepted"] is True


def test_continuous_change_maintains_graph_lineage_without_boundaries(
    tmp_path,
):
    result = run_continuous_change_benchmark(
        state_path=tmp_path / "continuous_change.json",
        result_path=tmp_path / "continuous_change_result.json",
        development_worlds_per_family=2,
        sealed_worlds_per_family=2,
        blocks=20,
    )

    assert result["early_late_boundaries_supplied"] is False
    assert result["gates"]["competing_hypotheses_retained"] is True
    assert result["restart"]["graph_lineages_retained"] is True
    assert result["restart"]["relearning_worlds"] == 0
    if result["promotion"]["decision"].get("promoted"):
        assert result["sealed"]["gate"]["accepted"] is True


def test_adaptive_change_diagnostics_escalate_on_surprise(tmp_path):
    result = run_adaptive_change_diagnostics_benchmark(
        state_path=tmp_path / "adaptive_diagnostics.json",
        result_path=tmp_path / "adaptive_diagnostics_result.json",
        development_worlds_per_family=2,
        sealed_worlds_per_family=2,
        blocks=20,
    )

    assert result["gates"]["surprise_triggered_escalation"] is True
    assert result["restart"]["relearning_worlds"] == 0
    if result["promotion"]["decision"].get("promoted"):
        assert result["sealed"]["gate"]["accepted"] is True


def test_anticipatory_temporal_rules_require_confirmation_and_persist(
    tmp_path,
):
    result = run_anticipatory_temporal_benchmark(
        state_path=tmp_path / "anticipatory.json",
        result_path=tmp_path / "anticipatory_result.json",
        development_worlds_per_family=2,
        sealed_worlds_per_family=2,
        blocks=60,
        evaluation_start=30,
    )

    assert result["gates"]["prediction_requires_confirmation"] is True
    assert result["restart"]["temporal_motifs_retained"] is True
    assert result["restart"]["relearning_worlds"] == 0


def test_prospective_temporal_planning_is_governed_and_persistent(
    tmp_path: Path,
) -> None:
    result = run_prospective_temporal_planning_benchmark(
        state_path=tmp_path / "prospective.json",
        result_path=tmp_path / "prospective_result.json",
    )
    assert result["passed"] is True
    assert result["sealed"]["gate"]["accepted"] is True
    assert (
        result["sealed"]["result"]["prospective_goal_success"]
        > result["sealed"]["result"]["reactive_goal_success"]
    )
    assert result["restart"]["champion_retained"] is True
    assert result["restart"]["prospective_memory_retained"] is True


def test_counterfactual_plan_repair_is_promoted_only_after_sealed_gain(
    tmp_path: Path,
) -> None:
    result = run_counterfactual_plan_repair_benchmark(
        state_path=tmp_path / "counterfactual.json",
        result_path=tmp_path / "counterfactual_result.json",
    )
    assert result["passed"] is True
    assert result["sealed"]["gate"]["accepted"] is True
    assert (
        result["sealed"]["result"]["prospective_goal_success"]
        > result["sealed"]["result"]["reactive_goal_success"]
    )
    assert result["restart"]["champion_retained"] is True
    assert result["restart"]["planning_memory_retained"] is True


def test_open_grammar_hierarchical_transfer_is_persistent_and_governed(
    tmp_path: Path,
) -> None:
    result = run_open_grammar_hierarchical_transfer_benchmark(
        state_path=tmp_path / "open_grammar.json",
        result_path=tmp_path / "open_grammar_result.json",
        development_episodes=8,
        sealed_episodes=12,
    )
    assert result["passed"] is True
    assert result["gate"]["accepted"] is True
    assert result["gates"]["positive_transfer"] is True
    assert result["gates"]["hierarchical_goal_composition"] is True
    assert result["restart"]["champion_retained"] is True
    assert result["restart"]["all_capsules_retained"] is True
    if result["promotion"]["decision"].get("promoted"):
        assert result["gate"]["accepted"] is True


def test_compositional_goal_graph_transfers_across_prerequisite_orders(
    tmp_path: Path,
) -> None:
    result = run_compositional_goal_graph_benchmark(
        state_path=tmp_path / "goal_graph.json",
        result_path=tmp_path / "goal_graph_result.json",
        development_episodes=8,
        sealed_episodes=12,
    )
    assert result["passed"] is True
    assert result["gate"]["accepted"] is True
    assert result["gates"]["multiple_prerequisite_orders_solved"] is True
    assert result["gates"]["sealed_composition_gain"] is True
    assert result["restart"]["champion_retained"] is True


def test_open_ontology_invention_transfers_and_rejects_unnecessary_concepts(
    tmp_path: Path,
) -> None:
    result = run_open_ontology_invention_benchmark(
        state_path=tmp_path / "ontology.json",
        result_path=tmp_path / "ontology_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["accepted"] is True
    assert result["gates"]["new_relational_predicate_invented"] is True
    assert result["gates"]["duplicates_merged"] is True
    assert result["gates"]["unnecessary_inventions_rejected"] is True
    assert result["restart"]["invented_concept_retained"] is True


def test_skill_contract_invention_uses_promoted_concept_and_transfers(
    tmp_path: Path,
) -> None:
    result = run_skill_contract_invention_benchmark(
        state_path=tmp_path / "skill_invention.json",
        result_path=tmp_path / "skill_invention_result.json",
        development_episodes=60,
        sealed_episodes=120,
    )
    assert result["passed"] is True
    assert result["gate"]["accepted"] is True
    assert result["gates"]["new_guarded_skill_invented"] is True
    assert result["gates"]["concept_skill_dependency_explicit"] is True
    assert result["restart"]["skill_contract_retained"] is True


def test_meta_abstraction_invention_is_hierarchical_and_conservative(
    tmp_path: Path,
) -> None:
    result = run_meta_abstraction_invention_benchmark(
        state_path=tmp_path / "meta_abstraction.json",
        result_path=tmp_path / "meta_abstraction_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_structure_recovery"] == 1.0
    assert result["gate"]["example_reduction"] == 0.80
    assert result["gate"]["nonlinear_controls_rejected"] is True
    assert result["restart"]["meta_concept_retained"] is True


def test_autonomous_concept_curriculum_targets_representation_failure(
    tmp_path: Path,
) -> None:
    result = run_autonomous_concept_curriculum_benchmark(
        state_path=tmp_path / "concept_curriculum.json",
        result_path=tmp_path / "concept_curriculum_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_structure_recovery"] == 1.0
    assert result["gate"]["probe_reduction"] > 0.0
    assert result["gate"]["negative_controls_rejected"] is True
    assert result["restart"]["concept_retained"] is True


def test_multigeneration_theory_revision_accumulates_without_forgetting(
    tmp_path: Path,
) -> None:
    result = run_multigeneration_theory_revision_benchmark(
        state_path=tmp_path / "theory_revision.json",
        result_path=tmp_path / "theory_revision_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["ambiguity_preserved"] is True
    assert result["gate"]["duplicate_aliases_merged"] == 1
    assert result["gate"]["sealed_structure_recovery"] == 1.0
    assert result["gate"]["backward_retention_worst_accuracy"] >= 0.99
    assert result["restart"]["revision_cycle_retained"] is True


def test_learned_experiment_policy_reduces_real_cost_with_safe_fallback(
    tmp_path: Path,
) -> None:
    result = run_learned_experiment_policy_benchmark(
        state_path=tmp_path / "experiment_policy.json",
        result_path=tmp_path / "experiment_policy_result.json",
        sealed_worlds=80,
    )
    assert result["passed"] is True
    assert result["gate"]["probe_reduction"] >= 0.08
    assert result["gate"]["cost_reduction"] >= 0.08
    assert result["gate"]["ood_accuracy"] == 1.0
    assert result["gate"]["ood_fallbacks"] > 0
    assert result["restart"]["policy_retained"] is True


def test_structural_analogy_lifts_arity_and_abstains_safely(
    tmp_path: Path,
) -> None:
    result = run_structural_analogy_benchmark(
        state_path=tmp_path / "structural_analogy.json",
        result_path=tmp_path / "structural_analogy_result.json",
        sealed_worlds=80,
    )
    assert result["passed"] is True
    assert result["gate"]["analogical_accuracy"] == 1.0
    assert result["gate"]["environmental_probe_reduction"] >= 0.15
    assert result["gate"]["unsafe_analogy_forced"] == 0
    assert result["gate"]["nonanalog_abstentions"] > 0
    assert result["restart"]["analogy_retained"] is True


def test_relational_program_induction_composes_executes_and_repairs(
    tmp_path: Path,
) -> None:
    result = run_relational_program_induction_benchmark(
        state_path=tmp_path / "relational_program.json",
        result_path=tmp_path / "relational_program_result.json",
        sealed_worlds=80,
    )
    assert result["passed"] is True
    assert result["gate"]["program_accuracy"] == 1.0
    assert result["gate"]["goal_success"] == 1.0
    assert result["gate"]["observation_reduction"] >= 0.15
    assert result["gate"]["repair_success"] == 1.0
    assert result["gate"]["unsafe_programs_forced"] == 0
    assert result["restart"]["program_retained"] is True


def test_cognitive_program_evolution_accumulates_three_safe_generations(
    tmp_path: Path,
) -> None:
    result = run_cognitive_program_evolution_benchmark(
        state_path=tmp_path / "program_evolution.json",
        result_path=tmp_path / "program_evolution_result.json",
        development_worlds_per_generation=6,
        sealed_worlds_per_generation=10,
    )
    assert result["passed"] is True
    assert result["gate"]["three_generations_promoted"] is True
    assert result["gate"]["program_accuracy"] == 1.0
    assert result["gate"]["goal_success"] == 1.0
    assert result["gate"]["observation_reduction"] > 0.0
    assert result["gate"]["cost_reduction"] > 0.0
    assert result["gate"]["grammar_growth"] == 3
    assert result["gate"]["unsafe_programs_forced"] == 0
    assert result["restart"]["generations_retained"] is True


def test_executable_knowledge_is_verified_revised_and_persistent(
    tmp_path: Path,
) -> None:
    result = run_executable_knowledge_grounding_benchmark(
        state_path=tmp_path / "executable_knowledge.json",
        result_path=tmp_path / "executable_knowledge_result.json",
        development_documents=8,
        sealed_documents=16,
    )
    assert result["passed"] is True
    assert result["gate"]["parse_accuracy"] == 1.0
    assert result["gate"]["execution_validation"] == 1.0
    assert result["gate"]["retrieval_accuracy"] == 1.0
    assert result["gate"]["goal_success"] == 1.0
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["gate"]["obsolete_rule_corrected"] is True
    assert result["gate"]["unsupported_rejection"] == 1.0
    assert result["restart"]["programs_retained"] is True


def test_tool_grounded_learning_transfers_and_abstains_safely(
    tmp_path: Path,
) -> None:
    result = run_tool_grounded_task_learning_benchmark(
        state_path=tmp_path / "tool_learning.json",
        result_path=tmp_path / "tool_learning_result.json",
        development_per_family=4,
        sealed_per_family=8,
    )
    assert result["passed"] is True
    assert result["gate"]["tool_families"] == 4
    assert result["gate"]["accuracy"] == 1.0
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["attempt_reduction"] >= 0.50
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["gate"]["unknown_unsafe_acceptances"] == 0
    assert result["restart"]["all_tool_skills_retained"] is True


def test_integrated_workspace_outperforms_isolated_components_and_resumes(
    tmp_path: Path,
) -> None:
    result = run_integrated_cognitive_workspace_benchmark(
        state_path=tmp_path / "workspace.json",
        result_path=tmp_path / "workspace_result.json",
        development_tasks=4,
        sealed_tasks=12,
    )
    assert result["passed"] is True
    assert result["gate"]["accuracy"] == 1.0
    assert result["gate"]["accuracy_gain"] > 0.0
    assert result["gate"]["weakest_conflict_accuracy"] == 1.0
    assert result["gate"]["cost_reduction"] > 0.0
    assert (
        result["gate"]["successful_resumptions"]
        == result["gate"]["interruptions"]
    )
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["restart"]["all_sessions_retained"] is True


def test_neural_consolidation_accelerates_proposals_without_authority(
    tmp_path: Path,
) -> None:
    result = run_neural_consolidation_benchmark(
        state_path=tmp_path / "neural_consolidation.json",
        results_dir=Path("/Users/kevinrobinson/dev/COMDEX/results"),
        weights_path=tmp_path / "proposal_weights.npz",
        result_path=tmp_path / "neural_consolidation_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["accuracy"] == 1.0
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["evaluation_reduction"] >= 0.15
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["disabled_symbolic_accuracy"] == 1.0
    assert result["gate"]["ood_unsafe_acceptances"] == 0
    assert result["restart"]["weights_checksum_matches"] is True


def test_continual_neural_improvement_is_cumulative_and_reversible(
    tmp_path: Path,
) -> None:
    result = run_continual_neural_improvement_benchmark(
        state_path=tmp_path / "continual_state.json",
        results_dir=Path("/Users/kevinrobinson/dev/COMDEX/results"),
        phase34_weights_path=Path(
            "/Users/kevinrobinson/dev/COMDEX/data/hexcore/"
            "neural_consolidation_weights.npz"
        ),
        artifact_dir=tmp_path / "phase35_artifacts",
        result_path=tmp_path / "continual_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["successive_generations"] == 3
    assert result["gate"]["all_generations_promoted"] is True
    assert result["gate"]["final_accuracy"] == 1.0
    assert result["gate"]["final_weakest_family_accuracy"] == 1.0
    assert result["gate"]["maximum_measured_forgetting"] <= 0.02
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["disabled_symbolic_accuracy"] == 1.0
    assert result["gate"]["component_replacement_accuracy"] == 1.0
    assert result["gate"]["revived_generation_accuracy"] == 1.0
    assert result["gate"]["independent_tracks_unchanged"] is True
    assert result["restart"]["all_generations_retained"] is True

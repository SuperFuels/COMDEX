from __future__ import annotations

import json
import re
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
from backend.modules.hexcore.open_schema_learning_benchmark import (
    run_open_schema_learning_benchmark,
)
from backend.modules.hexcore.adaptive_schema_theory_revision_benchmark import (
    run_adaptive_schema_theory_revision_benchmark,
)
from backend.modules.hexcore.compositional_theory_program_induction_benchmark import (
    run_compositional_theory_program_benchmark,
)
from backend.modules.hexcore.typed_dsl_program_synthesis_benchmark import (
    run_typed_dsl_program_synthesis_benchmark,
)
from backend.modules.hexcore.primitive_invention_and_compression_benchmark import (
    run_primitive_invention_benchmark,
)
from backend.modules.hexcore.algebraic_continuous_operator_learning_benchmark import (
    run_algebraic_continuous_operator_benchmark,
)
from backend.modules.hexcore.governed_photon_tool_invention_benchmark import (
    run_governed_photon_tool_invention_benchmark,
)
from backend.modules.hexcore.long_horizon_project_intelligence_benchmark import (
    run_long_horizon_project_benchmark,
)
from backend.modules.hexcore.open_ended_goal_decomposition_benchmark import (
    run_open_ended_goal_decomposition_benchmark,
)
from backend.modules.hexcore.multimodal_world_grounding_benchmark import (
    run_multimodal_world_grounding_benchmark,
)
from backend.modules.hexcore.large_continual_learning_arena_benchmark import (
    run_large_continual_learning_arena,
)
from backend.modules.hexcore.stronger_foundation_substrate_benchmark import (
    PARAPHRASES,
    run_stronger_foundation_substrate_benchmark,
)
from backend.modules.hexcore.public_external_intelligence_benchmark import (
    run_phase48_external_evaluation,
    run_phase49_open_document_intelligence,
    run_phase50_autonomous_projects,
)
from backend.modules.hexcore.general_tool_self_improvement_benchmark import (
    run_phase51_general_tool_invention,
    run_phase52_continual_self_improvement,
)
from backend.modules.hexcore.open_world_evaluation_ingestion import (
    _canonical_commitment,
    freeze_phase53_protocol,
    run_phase54_open_world_ingestion,
    score_blind_reveal,
)
from backend.modules.hexcore.recursive_photon_synthesis_benchmark import (
    run_phase55_recursive_photon_synthesis,
)
from backend.modules.hexcore.real_file_long_horizon_project_benchmark import (
    run_phase56_real_file_projects,
)
from backend.modules.hexcore.richer_real_file_world_model_benchmark import (
    run_phase57_richer_world_models,
)
from backend.modules.hexcore.open_multimodal_project_intelligence_benchmark import (
    run_phase58_open_multimodal_projects,
)
from backend.modules.hexcore.outcome_grounded_project_learning_benchmark import (
    run_phase59_outcome_grounded_project_learning,
)
from backend.modules.hexcore.open_project_repair_invention_benchmark import (
    run_phase60_open_project_repair_invention,
)
from backend.modules.hexcore.compound_project_repair_composition_benchmark import (
    run_phase61_compound_project_repair_composition,
)
from backend.modules.hexcore.learned_repair_contract_discovery_benchmark import (
    run_phase62_learned_repair_contract_discovery,
)
from backend.modules.hexcore.learned_repair_interference_benchmark import (
    run_phase63_learned_repair_interference,
)
from backend.modules.hexcore.raw_event_representation_learning_benchmark import (
    run_raw_event_representation_learning,
)
from backend.modules.hexcore.real_outcome_grounding_benchmark import (
    run_real_outcome_grounding,
)
from backend.modules.hexcore.autonomous_capability_curriculum_benchmark import (
    run_autonomous_capability_curriculum,
)
from backend.modules.hexcore.open_topology_natural_event_induction_benchmark import (
    run_open_topology_natural_event_induction,
)
from backend.modules.hexcore.human_judgment_evaluation_protocol import (
    prepare_human_judgment_protocol,
)
from backend.modules.hexcore.continuous_natural_world_learning_benchmark import (
    run_continuous_natural_world_learning,
)
from backend.modules.hexcore.outcome_driven_world_revision_benchmark import (
    run_outcome_driven_world_revision,
)
from backend.modules.hexcore.open_continuous_operator_invention_benchmark import (
    run_open_continuous_operator_invention,
)
from backend.modules.hexcore.compositional_multivariate_discovery_benchmark import (
    run_compositional_multivariate_discovery,
)
from backend.modules.hexcore.open_causal_scientific_learning_benchmark import (
    run_open_causal_scientific_learning,
)
from backend.modules.hexcore.real_repository_experimental_scientist_benchmark import (
    run_real_repository_experimental_scientist,
)
from backend.modules.hexcore.natural_historical_repository_repair_benchmark import (
    run_natural_historical_repository_repair,
)
from backend.modules.hexcore.open_outcome_project_scientist_benchmark import (
    run_open_outcome_project_scientist,
)
from backend.modules.hexcore.natural_repair_substrate_comparison_benchmark import (
    run_natural_repair_substrate_comparison,
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


def test_open_schema_learning_invents_transfers_queries_and_persists(
    tmp_path: Path,
) -> None:
    result = run_open_schema_learning_benchmark(
        state_path=tmp_path / "phase41_state.json",
        artifact_dir=tmp_path / "phase41_artifacts",
        result_path=tmp_path / "phase41_result.json",
        development_projects=8,
        sealed_projects=12,
    )
    assert result["passed"] is True
    assert result["gate"]["goal_accuracy"] >= 0.90
    assert result["gate"]["schema_recovery_accuracy"] >= 0.90
    assert result["gate"]["missing_knowledge_accuracy"] >= 0.90
    assert result["gate"]["query_recovery_accuracy"] >= 0.90
    assert result["gate"]["unnecessary_queries"] == 0
    assert result["gate"]["provenance_complete"] == 1.0
    assert result["gold_isolation"]["solver_receives_expected_schema"] is False
    assert result["restart"]["schemas_retained"] is True


def test_adaptive_schema_revision_criticises_experiments_and_persists(
    tmp_path: Path,
) -> None:
    result = run_adaptive_schema_theory_revision_benchmark(
        state_path=tmp_path / "phase42_state.json",
        result_path=tmp_path / "phase42_result.json",
        sealed_worlds=18,
    )
    assert result["passed"] is True
    assert result["gate"]["final_theory_accuracy"] >= 0.90
    assert result["gate"]["novel_schema_accuracy"] >= 0.90
    assert result["gate"]["change_recall"] >= 0.90
    assert result["gate"]["stable_false_revisions"] == 0
    assert result["gate"]["active_trial_reduction"] >= 0.10
    assert result["gate"]["complexity_violations"] == 0
    assert result["restart"]["champion_retained"] is True


def test_compositional_theory_programs_invent_abstain_and_persist(
    tmp_path: Path,
) -> None:
    result = run_compositional_theory_program_benchmark(
        state_path=tmp_path / "phase43_state.json",
        result_path=tmp_path / "phase43_result.json",
        sealed_worlds=12,
        external_worlds=4,
        ood_worlds=4,
    )
    assert result["passed"] is True
    assert result["gate"]["exact_program_accuracy"] >= 0.90
    assert result["gate"]["revision_kind_accuracy"] >= 0.95
    assert result["gate"]["external_family_accuracy"] >= 0.90
    assert result["gate"]["safe_ood_abstention"] >= 0.90
    assert result["gate"]["unsafe_forced_theories"] == 0
    assert result["gate"]["active_trial_reduction"] >= 0.10
    assert result["restart"]["champion_retained"] is True


def test_typed_dsl_synthesises_transfers_abstains_and_persists(
    tmp_path: Path,
) -> None:
    result = run_typed_dsl_program_synthesis_benchmark(
        state_path=tmp_path / "phase44_state.json",
        result_path=tmp_path / "phase44_result.json",
        development_worlds=9,
        sealed_worlds=9,
        external_worlds=3,
        ood_worlds=3,
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_exact_accuracy"] >= 0.90
    assert result["gate"]["external_interpreter_accuracy"] >= 0.90
    assert result["gate"]["safe_ood_abstention"] >= 0.90
    assert result["gate"]["transfer_trial_reduction"] >= 0.10
    assert result["gate"]["unsafe_forced_programs"] == 0
    assert result["restart"]["champion_retained"] is True


def test_primitive_invention_compresses_transfers_and_abstains(
    tmp_path: Path,
) -> None:
    result = run_primitive_invention_benchmark(
        state_path=tmp_path / "phase45_state.json",
        result_path=tmp_path / "phase45_result.json",
        development_worlds=12,
        transfer_worlds=8,
        external_worlds=4,
        novel_worlds=4,
        ood_worlds=4,
    )
    assert result["passed"] is True
    assert result["gate"]["promoted_primitives"] >= 4
    assert result["gate"]["transfer_exact_accuracy"] >= 0.95
    assert result["gate"]["novel_primitive_exact_accuracy"] >= 0.90
    assert result["gate"]["safe_ood_abstention"] >= 0.90
    assert result["gate"]["transfer_trial_reduction"] >= 0.15
    assert result["gate"]["unsafe_forced_primitives"] == 0
    assert result["restart"]["champion_retained"] is True


def test_algebraic_laws_and_continuous_operators_transfer_and_persist(
    tmp_path: Path,
) -> None:
    result = run_algebraic_continuous_operator_benchmark(
        state_path=tmp_path / "phase46_state.json",
        result_path=tmp_path / "phase46_result.json",
        sealed_worlds=12,
        external_worlds=4,
    )
    assert result["passed"] is True
    assert result["gate"]["algebraic_primitives_profiled"] == 4
    assert result["gate"]["support_recovery_accuracy"] >= 0.90
    assert result["gate"]["mean_validation_rmse"] <= 0.02
    assert result["gate"]["mean_recursive_rmse"] <= 0.08
    assert result["gate"]["active_policy_promoted"] is False
    assert result["restart"]["champion_retained"] is True


def test_governed_photon_tools_are_invented_sandboxed_and_retained(
    tmp_path: Path,
) -> None:
    result = run_governed_photon_tool_invention_benchmark(
        state_path=tmp_path / "photon_tool_invention.json",
        result_path=tmp_path / "photon_tool_invention_result.json",
        development_cases=8,
        sealed_cases=16,
        external_cases=8,
    )
    assert result["passed"] is True
    assert result["gate"]["tool_families_invented"] == 4
    assert result["gate"]["sealed_accuracy"] == 1.0
    assert result["gate"]["external_accuracy"] == 1.0
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["execution_cost_reduction"] >= 0.50
    assert result["gate"]["unsafe_candidates_rejected"] == 1.0
    assert result["restart"]["tools_retained"] is True


def test_long_horizon_projects_resume_revise_and_verify(
    tmp_path: Path,
) -> None:
    result = run_long_horizon_project_benchmark(
        state_path=tmp_path / "long_horizon_projects.json",
        result_path=tmp_path / "long_horizon_projects_result.json",
        development_projects=3,
        sealed_projects=12,
    )
    assert result["passed"] is True
    assert result["gate"]["project_accuracy"] == 1.0
    assert result["gate"]["accuracy_gain"] >= 0.20
    assert result["gate"]["weakest_domain_accuracy"] == 1.0
    assert result["gate"]["projects_resumed"] == 1.0
    assert result["gate"]["plan_revision_accuracy"] == 1.0
    assert result["gate"]["unresolved_questions_closed"] == 1.0
    assert result["restart"]["all_projects_retained"] is True


def test_broad_goals_create_verified_plans_or_request_clarification(
    tmp_path: Path,
) -> None:
    result = run_open_ended_goal_decomposition_benchmark(
        state_path=tmp_path / "open_goal_decomposition.json",
        result_path=tmp_path / "open_goal_decomposition_result.json",
        development_worlds=5,
        sealed_worlds=20,
        external_worlds=10,
    )
    assert result["passed"] is True
    assert result["gate"]["resolvable_accuracy"] == 1.0
    assert result["gate"]["weakest_domain_accuracy"] == 1.0
    assert result["gate"]["external_accuracy"] == 1.0
    assert result["gate"]["graph_exactness"] == 1.0
    assert result["gate"]["approval_boundary_accuracy"] == 1.0
    assert result["gate"]["clarification_accuracy"] == 1.0
    assert result["gate"]["unsafe_forced_plans"] == 0
    assert result["restart"]["all_plans_retained"] is True


def test_multimodal_grounding_uses_glyphchain_proofs_and_rejects_conflicts(
    tmp_path: Path,
) -> None:
    result = run_multimodal_world_grounding_benchmark(
        state_path=tmp_path / "multimodal_state.json",
        artifact_dir=tmp_path / "multimodal_artifacts",
        result_path=tmp_path / "multimodal_result.json",
        development_worlds=5,
        sealed_worlds=20,
        external_worlds=10,
    )
    assert result["passed"] is True
    assert result["gate"]["multimodal_accuracy"] == 1.0
    assert result["gate"]["accuracy_gain"] >= 0.25
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["external_accuracy"] == 1.0
    assert result["gate"]["glyphchain_commitments_verified"] == 1.0
    assert result["gate"]["tampered_commitments_accepted"] == 0
    assert result["gate"]["unsafe_false_acceptances"] == 0
    assert result["gate"]["live_chain_transactions_submitted"] == 0
    assert result["restart"]["commitments_retained"] is True


def test_large_continual_arena_improves_without_forgetting(
    tmp_path: Path,
) -> None:
    result = run_large_continual_learning_arena(
        state_path=tmp_path / "continual_arena.json",
        result_path=tmp_path / "continual_arena_result.json",
        development_per_operator=20,
        sealed_per_operator=10,
        external_per_operator=5,
    )
    assert result["passed"] is True
    assert result["gate"]["successive_generations"] == 3
    assert result["gate"]["all_generations_promoted"] is True
    assert result["gate"]["final_accuracy"] == 1.0
    assert result["gate"]["final_weakest_family_accuracy"] == 1.0
    assert result["gate"]["final_attempt_reduction"] >= 0.70
    assert result["gate"]["continual_memory_advantage"] >= 0.30
    assert result["gate"]["maximum_forgetting"] <= 0.02
    assert result["gate"]["ood_unsafe_acceptances"] == 0
    assert result["restart"]["all_generations_retained"] is True


def test_stronger_substrate_is_replaceable_and_never_authoritative(
    tmp_path: Path,
) -> None:
    labels = {
        phrase: operator
        for operator, phrases in PARAPHRASES.items()
        for phrase in phrases
    }

    def provider(instruction: str) -> Dict[str, Any]:
        label = next(
            (
                operator
                for phrase, operator in labels.items()
                if phrase in instruction
            ),
            "abstain",
        )
        return {"label": label, "latency_ms": 1.0, "cached": False}

    result = run_stronger_foundation_substrate_benchmark(
        state_path=tmp_path / "foundation_substrate.json",
        cache_path=tmp_path / "provider_cache.json",
        result_path=tmp_path / "foundation_substrate_result.json",
        sealed_per_operator=2,
        external_per_operator=1,
        provider=provider,
        model="deterministic_test_provider",
    )
    assert result["passed"] is True
    assert result["gate"]["substrate_proposal_accuracy"] == 1.0
    assert result["gate"]["proposal_accuracy_gain"] >= 0.20
    assert result["gate"]["governed_accuracy"] == 1.0
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["ood_abstention_accuracy"] == 1.0
    assert result["gate"]["provider_disabled_governed_accuracy"] == 1.0
    assert result["gate"]["backbone_frozen"] is True
    assert result["gate"]["hexcore_authority_independent"] is True


def test_public_external_document_and_project_chain_persists(
    tmp_path: Path,
) -> None:
    boolq_path = tmp_path / "boolq.jsonl"
    arc_path = tmp_path / "arc.jsonl"
    squad_path = tmp_path / "squad.jsonl"
    boolq_rows = [
        {
            "answer": True,
            "passage": f"PASSAGE_{index}",
            "question": f"QYES_{index}",
            "source_id": "boolq",
            "source_revision": "test",
            "source_split": "validation",
        }
        for index in range(4)
    ]
    arc_rows = [
        {
            "answer_key": "A",
            "choice_labels": ["A", "B", "C", "D"],
            "choices": ["right", "wrong1", "wrong2", "wrong3"],
            "question": f"ARCQ_{index}",
            "source_id": "arc",
            "source_revision": "test",
            "source_split": "validation",
        }
        for index in range(4)
    ]
    squad_rows = []
    for index in range(32):
        answerable = index < 24
        squad_rows.append(
            {
                "answer": f"token{index}" if answerable else "",
                "answerable": answerable,
                "context": (
                    f"The verified answer is token{index}."
                    if answerable
                    else "This passage deliberately omits the requested value."
                ),
                "question": (
                    f"QANSWERABLE_{index}"
                    if answerable
                    else f"QUNANSWERABLE_{index}"
                ),
                "source_id": "squad",
                "source_revision": "test",
                "source_split": "validation",
                "title": "fixture",
            }
        )
    for path, rows in (
        (boolq_path, boolq_rows),
        (arc_path, arc_rows),
        (squad_path, squad_rows),
    ):
        path.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )

    def provider(prompt: str) -> Dict[str, Any]:
        if "Return exactly YES or NO" in prompt:
            text = "YES"
        elif "Return only its letter" in prompt:
            text = "A"
        elif "SUPPORTED or UNSUPPORTED" in prompt:
            text = "UNSUPPORTED" if "QUNANSWERABLE" in prompt else "SUPPORTED"
        elif "QUNANSWERABLE" in prompt:
            text = "ANSWER: ABSTAIN"
        else:
            match = re.search(r"QANSWERABLE_(\d+)", prompt)
            text = f"ANSWER: token{match.group(1)}" if match else "ANSWER: ABSTAIN"
        return {"text": text, "latency_ms": 1.0, "cached": False}

    phase48 = run_phase48_external_evaluation(
        state_path=tmp_path / "phase48_state.json",
        cache_path=tmp_path / "cache.json",
        result_path=tmp_path / "phase48.json",
        boolq_path=boolq_path,
        arc_path=arc_path,
        squad_path=squad_path,
        per_family=4,
        provider=provider,
        model="fixture",
    )
    assert phase48["passed"] is True
    assert phase48["gate"]["mean_accuracy"] == 1.0
    assert phase48["gate"]["pretraining_contamination_excluded"] is False

    phase49 = run_phase49_open_document_intelligence(
        state_path=tmp_path / "phase49_state.json",
        cache_path=tmp_path / "cache.json",
        result_path=tmp_path / "phase49.json",
        squad_path=squad_path,
        cases=32,
        provider=provider,
        model="fixture",
    )
    assert phase49["passed"] is True
    assert phase49["gate"]["accepted_precision"] == 1.0
    assert phase49["gate"]["unsafe_committed_answers"] == 0

    phase50 = run_phase50_autonomous_projects(
        state_path=tmp_path / "phase50_state.json",
        phase49_result_path=tmp_path / "phase49.json",
        result_path=tmp_path / "phase50.json",
        projects=12,
    )
    assert phase50["passed"] is True
    assert phase50["gate"]["project_completion"] == 1.0
    assert phase50["gate"]["restart_recovery"] == 1.0
    assert phase50["restart"]["all_projects_retained"] is True


def test_general_tools_and_multitrack_self_improvement_are_governed(
    tmp_path: Path,
) -> None:
    phase51_path = tmp_path / "phase51.json"
    phase51 = run_phase51_general_tool_invention(
        state_path=tmp_path / "phase51_state.json",
        result_path=phase51_path,
        development_cases=8,
        sealed_cases=12,
        external_cases=8,
    )
    assert phase51["passed"] is True
    assert phase51["gate"]["tool_families_invented"] == 6
    assert phase51["gate"]["malicious_candidates_rejected"] == 1.0
    assert phase51["gate"]["experiment_policy_invented"] is True

    source_paths = {}
    for phase in (48, 49, 50):
        path = tmp_path / f"phase{phase}.json"
        path.write_text(
            json.dumps({"passed": True, "gate": {"accepted": True}}),
            encoding="utf-8",
        )
        source_paths[phase] = path
    phase52 = run_phase52_continual_self_improvement(
        state_path=tmp_path / "phase52_state.json",
        phase48_path=source_paths[48],
        phase49_path=source_paths[49],
        phase50_path=source_paths[50],
        phase51_path=phase51_path,
        result_path=tmp_path / "phase52.json",
    )
    assert phase52["passed"] is True
    assert phase52["gate"]["capability_families"] == 9
    assert phase52["gate"]["maximum_forgetting"] == 0.0
    assert phase52["gate"]["ood_safe_abstention"] is True
    assert phase52["gate"]["independent_reversible_tracks"] == 5
    assert phase52["gate"]["symbolic_component_replacement_accuracy"] == 1.0
    assert phase52["restart"]["relearning_tasks"] == 0


def test_blind_protocol_open_ingestion_and_recursive_photon_persist(
    tmp_path: Path,
) -> None:
    phase53 = freeze_phase53_protocol(
        state_path=tmp_path / "phase53_state.json",
        result_path=tmp_path / "phase53.json",
        code_commit="fixture-commit",
    )
    assert phase53["infrastructure_complete"] is True
    assert phase53["capability_promoted"] is False
    salt = "external-secret"
    envelopes = [
        {
            "task_id": "task-1",
            "family": "reading",
            "payload": {"question": "hidden"},
            "answer_commitment": _canonical_commitment("task-1", "yes", salt),
        }
    ]
    score = score_blind_reveal(
        {"task-1": "yes"},
        envelopes,
        [{"task_id": "task-1", "answer": "yes", "salt": salt}],
    )
    assert score["accuracy"] == 1.0
    assert score["invalid_reveals"] == 0

    sources = []
    suffixes = (".md", ".tex", ".json", ".csv", ".pdf")
    for index in range(10):
        path = tmp_path / f"source_{index}{suffixes[index % len(suffixes)]}"
        if path.suffix == ".json":
            content = json.dumps(
                {
                    "phase": index,
                    "result": f"verified result {index}",
                    "total_accuracy": 100,
                }
            )
        elif path.suffix == ".csv":
            content = (
                f"phase,result\n{index},verified result {index}\n"
                f"{index + 1},total accuracy 100 percent\n"
            )
        else:
            content = (
                f"Phase {index} result is recorded.\n"
                f"Total accuracy for phase {index} is 100 percent.\n"
            )
        path.write_text(content, encoding="utf-8")
        sources.append(path)
    phase54 = run_phase54_open_world_ingestion(
        state_path=tmp_path / "phase54_state.json",
        source_paths=sources,
        result_path=tmp_path / "phase54.json",
    )
    assert phase54["passed"] is True
    assert phase54["gate"]["formats"] == 5
    assert phase54["gate"]["evidence_recoverability"] == 1.0
    assert phase54["gate"]["reported_claims_mislabeled_as_verified"] == 0

    phase55 = run_phase55_recursive_photon_synthesis(
        state_path=tmp_path / "phase55_state.json",
        result_path=tmp_path / "phase55.json",
        worlds_per_arity=2,
    )
    assert phase55["passed"] is True
    assert phase55["gate"]["mean_external_accuracy"] == 1.0
    assert phase55["gate"]["out_of_grammar_abstention"] is True
    assert phase55["restart"]["relearning_tools"] == 0


def test_real_file_projects_detect_revise_resume_and_abstain(
    tmp_path: Path,
) -> None:
    result = run_phase56_real_file_projects(
        repo_root=Path("/Users/kevinrobinson/dev/COMDEX"),
        state_path=tmp_path / "phase56_state.json",
        workspace_root=tmp_path / "phase56_workspaces",
        result_path=tmp_path / "phase56_result.json",
        development_phases=(48,),
        sealed_phases=(53, 54, 55),
    )
    assert result["passed"] is True
    assert result["gate"]["project_outcome_accuracy"] == 1.0
    assert result["gate"]["weakest_family_accuracy"] == 1.0
    assert result["gate"]["source_change_detection"] == 1.0
    assert result["gate"]["restart_recovery"] == 1.0
    assert result["gate"]["conflict_safe_abstention"] is True
    assert result["gate"]["reexecution_reduction"] >= 0.20
    assert result["restart"]["relearning_projects"] == 0


def test_richer_world_model_predicts_revisions_and_criticises_novelty(
    tmp_path: Path,
) -> None:
    result = run_phase57_richer_world_models(
        repo_root=Path("/Users/kevinrobinson/dev/COMDEX"),
        state_path=tmp_path / "phase57_state.json",
        workspace_root=tmp_path / "phase57_workspaces",
        result_path=tmp_path / "phase57_result.json",
        development_phases=(48, 49, 50),
        sealed_phases=(53, 54, 55, 56),
    )
    assert result["passed"] is True
    assert result["gate"]["withheld_event_accuracy"] >= 0.90
    assert result["gate"]["weakest_family_accuracy"] >= 0.85
    assert result["gate"]["novel_event_criticism"] == 1.0
    assert result["gate"]["unsafe_novel_event_forcing"] == 0
    assert result["gate"]["competing_models_retained"] >= 2
    assert result["gate"]["cost_reduction_vs_cold"] >= 0.15
    assert result["restart"]["relearning_events"] == 0


def test_open_multimodal_projects_invent_schema_plan_and_verify(
    tmp_path: Path,
) -> None:
    result = run_phase58_open_multimodal_projects(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase58_state.json",
        workspace_root=tmp_path / "phase58_workspaces",
        result_path=tmp_path / "phase58_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["broad_goal_only"] is True
    assert result["gate"]["project_completion"] >= 0.90
    assert result["gate"]["weakest_family_accuracy"] >= 0.85
    assert result["gate"]["schema_invention"] == 1.0
    assert result["gate"]["goal_graph_construction"] == 1.0
    assert result["gate"]["unsafe_knowledge_commitments"] == 0
    assert result["gate"]["accuracy_gain_over_cold"] >= 0.20
    assert result["gate"]["information_action_reduction"] >= 0.10
    assert result["restart"]["relearning_projects"] == 0


def test_outcome_grounded_projects_learn_repair_and_transfer(
    tmp_path: Path,
) -> None:
    result = run_phase59_outcome_grounded_project_learning(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase59_state.json",
        workspace_root=tmp_path / "phase59_workspaces",
        result_path=tmp_path / "phase59_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["source_identity_overlap"] == 0
    assert result["gate"]["generations_completed"] == 2
    assert result["gate"]["sealed_challenger_accuracy"] >= 0.90
    assert result["gate"]["sealed_accuracy_gain"] >= 0.30
    assert result["gate"]["sealed_weakest_family_accuracy"] >= 0.85
    assert result["gate"]["sealed_diagnosis_accuracy"] >= 0.90
    assert result["gate"]["unsafe_final_commitments"] == 0
    assert result["gate"]["backward_retention"] >= 0.98
    assert result["gate"]["unknown_failure_abstention"] == 1.0
    assert result["restart"]["relearning_episodes"] == 0


def test_open_project_repair_invention_synthesises_and_transfers(
    tmp_path: Path,
) -> None:
    result = run_phase60_open_project_repair_invention(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase60_state.json",
        workspace_root=tmp_path / "phase60_workspaces",
        result_path=tmp_path / "phase60_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["repair_families_invented"] == 3
    assert result["gate"]["mean_sealed_accuracy"] >= 0.95
    assert result["gate"]["weakest_repair_accuracy"] >= 0.90
    assert result["gate"]["source_identity_overlap"] == 0
    assert result["gate"]["counterexamples_generated"] > 0
    assert result["gate"]["malicious_opcodes_rejected"] == 1.0
    assert result["gate"]["phase59_backward_retention"] >= 0.98
    assert result["gate"]["phase59_unsafe_commitments"] == 0
    assert result["gate"]["out_of_grammar_abstention"] is True
    assert result["restart"]["relearning_tools"] == 0


def test_compound_project_repairs_compose_and_retain_prior_skills(
    tmp_path: Path,
) -> None:
    result = run_phase61_compound_project_repair_composition(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase61_state.json",
        workspace_root=tmp_path / "phase61_workspaces",
        result_path=tmp_path / "phase61_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["phase60_prerequisite"] is True
    assert result["gate"]["generations_completed"] == 2
    assert result["gate"]["sealed_challenger_accuracy"] >= 0.95
    assert result["gate"]["sealed_accuracy_gain"] >= 0.50
    assert result["gate"]["sealed_weakest_family_accuracy"] >= 0.90
    assert result["gate"]["verified_execution_traces"] is True
    assert result["gate"]["backward_retention"] >= 0.98
    assert result["gate"]["phase59_backward_retention"] >= 0.98
    assert result["gate"]["out_of_contract_abstention"] is True
    assert result["gate"]["unsafe_side_effects"] == 0
    assert result["restart"]["relearning_episodes"] == 0


def test_repair_contracts_are_learned_by_active_counterfactuals(
    tmp_path: Path,
) -> None:
    result = run_phase62_learned_repair_contract_discovery(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase62_state.json",
        workspace_root=tmp_path / "phase62_workspaces",
        result_path=tmp_path / "phase62_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["phase61_prerequisite"] is True
    assert result["gate"]["contracts_inferred"] == 4
    assert result["gate"]["exact_contract_recovery"] >= 0.95
    assert result["gate"]["active_contract_sealed_accuracy"] >= 0.95
    assert result["gate"]["sealed_accuracy_gain"] >= 0.50
    assert result["gate"]["sealed_weakest_family_accuracy"] >= 0.90
    assert result["gate"]["experiment_reduction_vs_exhaustive"] >= 0.40
    assert result["gate"]["ambiguous_contract_abstention"] is True
    assert result["gate"]["unsafe_side_effects"] == 0
    assert result["restart"]["relearning_contracts"] == 0


def test_repair_interference_is_learned_and_reorders_composition(
    tmp_path: Path,
) -> None:
    result = run_phase63_learned_repair_interference(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "phase63_state.json",
        workspace_root=tmp_path / "phase63_workspaces",
        result_path=tmp_path / "phase63_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["phase62_prerequisite"] is True
    assert result["gate"]["generations_completed"] == 2
    assert result["gate"]["learned_ordering_edges"] == 3
    assert result["gate"]["exact_safe_plan"] is True
    assert result["gate"]["sealed_challenger_accuracy"] >= 0.95
    assert result["gate"]["sealed_accuracy_gain"] >= 0.50
    assert result["gate"]["sealed_weakest_family_accuracy"] >= 0.90
    assert result["gate"]["generation_one_retention"] == 1.0
    assert result["gate"]["ambiguous_interference_abstention"] is True
    assert result["gate"]["unsafe_side_effects"] == 0
    assert result["restart"]["relearning_experiments"] == 0


def test_raw_event_vocabulary_is_invented_and_transfers_under_renaming(
    tmp_path: Path,
) -> None:
    result = run_raw_event_representation_learning(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "raw_representation_state.json",
        workspace_root=tmp_path / "raw_representation_workspaces",
        result_path=tmp_path / "raw_representation_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["semantic_state_labels_supplied"] is False
    assert result["gate"]["semantic_relation_labels_supplied"] is False
    assert result["gate"]["raw_field_names_shared_between_domains"] is False
    assert result["gate"]["development_structural_invariance"] is True
    assert result["gate"]["sealed_mean_state_accuracy"] >= 0.95
    assert result["gate"]["sealed_weakest_state_accuracy"] >= 0.90
    assert result["gate"]["sealed_mean_transition_accuracy"] >= 0.95
    assert result["gate"]["sealed_weakest_transition_accuracy"] >= 0.90
    assert result["gate"]["observation_reduction_vs_exhaustive"] >= 0.80
    assert result["gate"]["non_analogous_abstention"] is True
    assert result["gate"]["photon_ir_traceable"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["relearning_events"] == 0


def test_real_outcomes_govern_acceptance_across_independent_authorities(
    tmp_path: Path,
) -> None:
    result = run_real_outcome_grounding(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "real_outcome_state.json",
        workspace_root=tmp_path / "real_outcome_workspaces",
        result_path=tmp_path / "real_outcome_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["source_disjoint"] is True
    assert result["gate"]["real_outcome_families"] == 4
    assert result["gate"]["challenger_accuracy"] >= 0.95
    assert result["gate"]["accuracy_gain"] >= 0.40
    assert result["gate"]["weakest_family_accuracy"] >= 0.90
    assert result["gate"]["independent_authorities_observed"] == 4
    assert result["gate"]["proposal_confidence_used_as_truth"] is False
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["relearning_outcomes"] == 0


def test_autonomous_curriculum_targets_weaknesses_in_large_arena(
    tmp_path: Path,
) -> None:
    result = run_autonomous_capability_curriculum(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "autonomous_curriculum_state.json",
        workspace_root=tmp_path / "autonomous_curriculum_workspaces",
        result_path=tmp_path / "autonomous_curriculum_result.json",
        arena_tasks=1000,
    )
    assert result["passed"] is True
    assert result["gate"]["generations_completed"] == 4
    assert result["gate"]["families_trained"] == 4
    assert result["gate"]["arena_tasks"] == 1000
    assert result["gate"]["source_disjoint"] is True
    assert result["gate"]["challenger_accuracy"] >= 0.95
    assert result["gate"]["weakest_family_accuracy"] >= 0.90
    assert result["gate"]["probe_reduction"] >= 0.50
    assert result["gate"]["backward_retention"] is True
    assert result["gate"]["self_scoring_used_for_promotion"] is False
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["relearning_tasks"] == 0


def test_open_topology_is_inferred_from_unfamiliar_natural_event_logs(
    tmp_path: Path,
) -> None:
    result = run_open_topology_natural_event_induction(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "open_topology_state.json",
        workspace_root=tmp_path / "open_topology_workspaces",
        result_path=tmp_path / "open_topology_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["semantic_fact_vocabulary_supplied"] is False
    assert result["gate"]["entity_count_supplied"] is False
    assert result["gate"]["dimension_count_supplied"] is False
    assert result["gate"]["latent_mode_count_supplied"] is False
    assert result["gate"]["variable_count_configurations"] >= 5
    assert result["gate"]["sealed_exact_structure_rate"] >= 0.95
    assert result["gate"]["sealed_weakest_relation_recall"] >= 0.95
    assert result["gate"]["sealed_latent_mode_accuracy"] >= 0.95
    assert result["gate"]["sealed_persistence_accuracy"] >= 0.95
    assert result["gate"]["stochastic_ood_abstention"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["relearning_lines"] == 0


def test_human_judgment_protocol_cannot_self_certify_capability(
    tmp_path: Path,
) -> None:
    result = prepare_human_judgment_protocol(
        output_dir=tmp_path / "human_protocol",
        result_path=tmp_path / "human_protocol_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["protocol_frozen"] is True
    assert result["gate"]["development_tasks"] == 6
    assert result["gate"]["independent_human_evaluation_complete"] is False
    assert result["gate"]["promotion_open"] is False
    assert result["capability_promotion"] is False


def test_continuous_natural_world_learning_predicts_and_criticizes(
    tmp_path: Path,
) -> None:
    result = run_continuous_natural_world_learning(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "continuous_world_state.json",
        result_path=tmp_path / "continuous_world_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["semantic_fact_vocabulary_supplied"] is False
    assert result["gate"]["dimension_count_supplied"] is False
    assert result["gate"]["continuous_values"] is True
    assert result["gate"]["coreference_records_resolved"] > 0
    assert result["gate"]["sealed_exact_structure_rate"] >= 0.90
    assert result["gate"]["sealed_weakest_relation_recall"] >= 0.90
    assert result["gate"]["sealed_mean_prediction_accuracy"] >= 0.90
    assert result["gate"]["sealed_weakest_prediction_accuracy"] >= 0.80
    assert result["gate"]["sealed_mean_coefficient_mae"] <= 0.06
    assert result["gate"]["nonlinear_ood_abstention"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["champion_retained"] is True
    assert result["restart"]["relearning_records"] == 0


def test_outcomes_drive_world_revision_and_continual_retention(
    tmp_path: Path,
) -> None:
    result = run_outcome_driven_world_revision(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "outcome_revision_state.json",
        result_path=tmp_path / "outcome_revision_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_diagnosis_accuracy"] >= 0.95
    assert result["gate"]["sealed_change_detection_accuracy"] >= 0.95
    assert result["gate"]["sealed_mean_change_point_error"] <= 1.0
    assert result["gate"]["sealed_challenger_accuracy"] >= 0.95
    assert result["gate"]["sealed_accuracy_gain"] >= 0.20
    assert result["gate"]["sealed_weakest_world_accuracy"] >= 0.90
    assert result["gate"]["alternating_ood_abstention"] is True
    assert result["gate"]["continual_arena_tasks"] >= 1000
    assert result["gate"]["all_generations_accepted"] is True
    assert result["gate"]["final_backward_retention"] >= 0.95
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["three_generations_retained"] is True
    assert result["restart"]["relearning_outcomes"] == 0


def test_open_operator_invention_transfers_and_abstains(
    tmp_path: Path,
) -> None:
    result = run_open_continuous_operator_invention(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "operator_invention_state.json",
        external_cache_dir=tmp_path / "external_cache",
        result_path=tmp_path / "operator_invention_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_operator_recovery"] >= 0.95
    assert result["gate"]["sealed_weakest_family_recovery"] >= 0.90
    assert result["gate"]["sealed_counterexample_success"] >= 0.90
    assert result["gate"]["unstructured_ood_abstention"] is True
    assert result["gate"]["software_transfer_accuracy"] == 1.0
    assert result["gate"]["sensor_predictive_transfer"] is True
    assert result["gate"]["sensor_test_r2"] > 0.0
    assert result["gate"]["external_sources_with_provenance"] >= 4
    assert result["gate"]["all_generations_accepted"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["operator_library_retained"] is True
    assert result["restart"]["external_provenance_retained"] is True
    assert result["restart"]["relearning_traces"] == 0


def test_compositional_multivariate_discovery_transfers_cost_effectively(
    tmp_path: Path,
) -> None:
    result = run_compositional_multivariate_discovery(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "compositional_multivariate_state.json",
        external_cache_dir=tmp_path / "external_cache",
        result_path=tmp_path / "compositional_multivariate_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_predictive_acceptance"] >= 0.95
    assert result["gate"]["sealed_weakest_family_acceptance"] >= 0.90
    assert result["gate"]["sealed_mean_test_r2"] >= 0.95
    assert result["gate"]["sealed_exact_motif_recovery"] >= 0.95
    assert result["gate"]["active_counterexample_success"] >= 0.90
    assert result["gate"]["mean_measurement_cost_saving"] >= 0.05
    assert result["gate"]["unstructured_ood_abstention"] is True
    assert result["gate"]["software_test_r2"] >= 0.95
    assert result["gate"]["sensor_test_r2"] >= 0.50
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["compositional_library_retained"] is True
    assert result["restart"]["external_provenance_retained"] is True
    assert result["restart"]["relearning_traces"] == 0


def test_open_causal_science_rejects_confounders_and_maintains_theories(
    tmp_path: Path,
) -> None:
    result = run_open_causal_scientific_learning(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "open_causal_science_state.json",
        result_path=tmp_path / "open_causal_science_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["sealed_world_acceptance"] >= 0.95
    assert result["gate"]["sealed_mean_motif_recall"] >= 0.95
    assert result["gate"]["sealed_mean_motif_precision"] >= 0.90
    assert result["gate"]["sealed_weakest_output_r2"] >= 0.85
    assert result["gate"]["relevant_variable_recovery"] >= 0.95
    assert result["gate"]["nuisance_variable_rejection"] >= 0.90
    assert result["gate"]["latent_count_accuracy"] >= 0.90
    assert result["gate"]["observational_control_confounder_rate"] >= 0.50
    assert result["gate"]["causal_learner_confounder_rate"] <= 0.05
    assert result["gate"]["failure_diagnosis_accuracy"] >= 0.95
    assert result["gate"]["mean_change_point_error"] <= 2.0
    assert result["gate"]["unexplained_family_abstention"] is True
    assert result["gate"]["external_software_change_detection"] is True
    assert result["gate"]["all_curricula_accepted"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["causal_theories_retained"] is True
    assert result["restart"]["revisions_retained"] is True
    assert result["restart"]["curricula_retained"] is True
    assert result["restart"]["relearning_events"] == 0


def test_repository_scientist_infers_interventions_and_invents_repairs(
    tmp_path: Path,
) -> None:
    result = run_real_repository_experimental_scientist(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "repository_science_state.json",
        result_path=tmp_path / "repository_science_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["real_repository_files"] >= 3
    assert result["gate"]["git_provenance_complete"] is True
    assert result["gate"]["sandbox_project_success"] == 1.0
    assert result["gate"]["hidden_verification_success"] == 1.0
    assert result["gate"]["inferred_intervention_accuracy"] == 1.0
    assert result["gate"]["compound_repair_invented"] is True
    assert result["gate"]["adaptive_mdl_depth"] >= 2
    assert result["gate"]["cross_domain_transfer_success"] is True
    assert result["gate"]["transfer_attempt_reduction"] > 0.0
    assert result["gate"]["mid_project_process_recovery"] is True
    assert result["gate"]["live_repository_unchanged"] is True
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["patch_library_retained"] is True
    assert result["restart"]["isomorphism_memory_retained"] is True
    assert result["restart"]["curriculum_retained"] is True
    assert result["restart"]["relearning_experiments"] == 0


def test_natural_historical_failures_are_repaired_blindly_and_transfer(
    tmp_path: Path,
) -> None:
    result = run_natural_historical_repository_repair(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "natural_historical_repair_state.json",
        result_path=tmp_path / "natural_historical_repair_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["authentic_historical_failures"] >= 3
    assert result["gate"]["source_families"] >= 3
    assert result["gate"]["natural_failure_repair_success"] >= 0.90
    assert result["gate"]["fault_localization_accuracy"] >= 0.90
    assert result["gate"]["self_invented_tests_rejected_wrong_patches"] is True
    assert result["gate"]["held_out_historical_verification"] >= 0.90
    assert result["gate"]["human_patch_blind_during_search"] is True
    assert result["gate"]["renamed_transfer_success"] is True
    assert result["gate"]["transfer_attempt_reduction"] > 0.0
    assert result["gate"]["live_repository_unchanged"] is True
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["restart"]["falsification_tests_retained"] is True
    assert result["restart"]["patches_retained"] is True
    assert result["restart"]["transfer_model_retained"] is True
    assert result["restart"]["relearning_failures"] == 0


def test_open_outcome_project_invents_failure_states_and_learns_delayed(
    tmp_path: Path,
) -> None:
    result = run_open_outcome_project_scientist(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "open_outcome_project_state.json",
        result_path=tmp_path / "open_outcome_project_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["autonomous_project_nodes"] >= 3
    assert result["gate"]["supplied_failure_names"] == 0
    assert result["gate"]["invented_failure_clusters"] >= 3
    assert result["gate"]["failure_case_separation"] == 1.0
    assert result["gate"]["delayed_outcome_streams"] >= 3
    assert result["gate"]["independent_delayed_authority"] is True
    assert result["gate"]["counterfactual_credit_accuracy"] >= 2 / 3
    assert result["gate"]["project_accuracy_gain"] > 0.0
    assert result["gate"]["separate_curriculum_evaluation_authority"] is True
    assert result["gate"]["mid_project_process_recovery"] is True
    assert result["gate"]["unsafe_knowledge_commitments"] == 0
    assert result["restart"]["ontology_retained"] is True
    assert result["restart"]["delayed_outcomes_retained"] is True
    assert result["restart"]["curriculum_retained"] is True
    assert result["restart"]["outcome_replay_required"] == 0


def test_natural_repair_substrates_remain_proposal_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate(*, model: str, prompt: str, timeout: int = 180):
        if "invalid syntax" in prompt:
            proposal = {
                "diagnosis": "Normalization was placed in the signature.",
                "repair_plan": (
                    "Move request normalization inside the function body "
                    "while retaining the docstring."
                ),
                "falsification_tests": [
                    "Compile the source.",
                    "Call with a request dictionary and retain documentation.",
                ],
                "confidence": 0.9,
            }
        elif "NameError" in prompt:
            proposal = {
                "diagnosis": "Stable identity includes runtime envelope data.",
                "repair_plan": (
                    "Filter timestamp and trace fields while retaining content."
                ),
                "falsification_tests": [
                    "Change timestamp and trace without changing the hash.",
                    "Change message body content and require a different hash.",
                ],
                "confidence": 0.9,
            }
        else:
            proposal = {
                "diagnosis": "Producer and consumer disagree on JSON depth.",
                "repair_plan": (
                    "Flatten caller fields to the top-level worker request."
                ),
                "falsification_tests": [
                    "Require text at the top level for the worker.",
                    "Require audio fields at the top level for STT.",
                ],
                "confidence": 0.9,
            }
        return {
            "available": True,
            "proposal": proposal,
            "latency_seconds": 0.001,
            "eval_count": 1,
            "prompt_eval_count": 1,
            "done_reason": "stop",
        }

    monkeypatch.setattr(
        "backend.modules.hexcore."
        "natural_repair_substrate_comparison_benchmark._ollama_generate",
        fake_generate,
    )
    result = run_natural_repair_substrate_comparison(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "natural_repair_substrate_state.json",
        result_path=tmp_path / "natural_repair_substrate_result.json",
        models=("mock-1b", "mock-2b", "mock-5b"),
    )
    assert result["passed"] is True
    assert result["gate"]["models_compared"] >= 3
    assert result["gate"]["proposal_only_boundary"] is True
    assert result["gate"]["best_verified_success"] == 1.0
    assert result["gate"]["best_proposal_understanding"] >= 2 / 3
    assert result["gate"]["best_falsification_test_quality"] >= 2 / 3
    assert result["gate"]["best_attempt_reduction"] >= 0.20
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["hexcore_verification_authority"] is True
    assert result["restart"]["substrate_route_retained"] is True
    assert result["restart"]["symbolic_fallback_retained"] is True
    assert result["restart"]["relearning_proposals"] == 0


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

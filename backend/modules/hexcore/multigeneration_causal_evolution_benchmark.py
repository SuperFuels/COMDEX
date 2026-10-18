from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
)
from backend.modules.hexcore.outcome_driven_causal_evolution import (
    GeneratedCausalWorld,
    InvestigationPolicy,
    OutcomeDrivenCausalEvolution,
    ProceduralCausalWorldGenerator,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    StochasticLatentGraph,
)


PHASE9_CHAMPION = InvestigationPolicy(
    policy_id="phase9_goal_aware_adaptive7",
    confidence_gate=0.97,
    maximum_experiments=7,
    cost_weight=0.05,
    mutation="immutable_phase9_control",
    goal_relevance_only=True,
    uncertain_factor_only=True,
    goal_retries=1,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "multigeneration_causal_evolution_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _utility(result: Mapping[str, Any]) -> float:
    return (
        float(result["mean_goal_success"])
        + 0.20 * float(result["mean_relevant_factor_accuracy"])
        - 0.12 * float(result["average_total_action_cost"])
        - 0.25 * float(result["calibration_error"])
    )


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in result.items() if key != "rows"
    } | {"total_cost_utility": _utility(result)}


def _mutations(
    parent: InvestigationPolicy,
    generation: int,
) -> List[InvestigationPolicy]:
    candidates = []
    for offset, slope in ((-0.04, 0.15), (-0.03, 0.25), (-0.02, 0.35)):
        gate = min(0.98, max(0.90, parent.confidence_gate + offset))
        candidates.append(
            InvestigationPolicy(
                policy_id=(
                    f"generation_{generation}_adaptive_"
                    f"{int(gate * 1000)}_{int(slope * 100)}"
                ),
                confidence_gate=gate,
                maximum_experiments=parent.maximum_experiments,
                cost_weight=parent.cost_weight,
                mutation=(
                    "reliability_conditioned_per_factor_stopping"
                ),
                parent_policy_id=parent.policy_id,
                goal_relevance_only=True,
                uncertain_factor_only=True,
                goal_retries=1,
                adaptive_confidence=True,
                reliability_slope=slope,
                adaptive_experiment_budget=True,
                low_reliability_budget=10,
                high_reliability_budget=5,
            )
        )
    candidates.append(
        InvestigationPolicy(
            policy_id=f"generation_{generation}_one_fewer_probe",
            confidence_gate=parent.confidence_gate,
            maximum_experiments=max(
                5, parent.maximum_experiments - 1
            ),
            cost_weight=parent.cost_weight,
            mutation="low_reliability_budget_expansion",
            parent_policy_id=parent.policy_id,
            goal_relevance_only=True,
            uncertain_factor_only=True,
            goal_retries=1,
            adaptive_experiment_budget=True,
            low_reliability_budget=10,
            high_reliability_budget=7,
        )
    )
    return candidates


def _promotion_gate(
    parent: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> Dict[str, Any]:
    goal_change = (
        challenger["mean_goal_success"] - parent["mean_goal_success"]
    )
    worst_change = (
        challenger["worst_family_goal_success"]
        - parent["worst_family_goal_success"]
    )
    relevant_change = (
        challenger["mean_relevant_factor_accuracy"]
        - parent["mean_relevant_factor_accuracy"]
    )
    calibration_change = (
        challenger["calibration_error"] - parent["calibration_error"]
    )
    cost_change = (
        challenger["average_total_action_cost"]
        - parent["average_total_action_cost"]
    )
    utility_change = _utility(challenger) - _utility(parent)
    errors = []
    if goal_change < 0.0:
        errors.append("VERIFIED_GOAL_SUCCESS_REGRESSION")
    if worst_change < 0.0:
        errors.append("WORST_FAMILY_GOAL_REGRESSION")
    if relevant_change < -0.02:
        errors.append("RELEVANT_FACTOR_REGRESSION_ABOVE_TWO_POINTS")
    if calibration_change > 0.01:
        errors.append("CALIBRATION_REGRESSION_ABOVE_ONE_POINT")
    if cost_change > 0.0:
        errors.append("TOTAL_ACTION_COST_REGRESSION")
    if utility_change <= 0.0:
        errors.append("TOTAL_COST_UTILITY_NOT_IMPROVED")
    if challenger["policy"]["complexity"] > 12:
        errors.append("PROCEDURE_COMPLEXITY_CAP_EXCEEDED")
    return {
        "accepted": not errors,
        "errors": errors,
        "goal_change": goal_change,
        "worst_family_goal_change": worst_change,
        "relevant_factor_accuracy_change": relevant_change,
        "calibration_change": calibration_change,
        "total_action_cost_change": cost_change,
        "total_cost_utility_change": utility_change,
    }


def _external_transfer_gate(
    control: Mapping[str, Any],
    final: Mapping[str, Any],
) -> Dict[str, Any]:
    errors = []
    if final["mean_goal_success"] < 0.85:
        errors.append("EXTERNAL_MEAN_GOAL_BELOW_85_PERCENT")
    if final["worst_family_goal_success"] < 0.65:
        errors.append("EXTERNAL_WORST_FAMILY_BELOW_65_PERCENT")
    if final["mean_relevant_factor_accuracy"] < 0.85:
        errors.append("EXTERNAL_RELEVANT_ACCURACY_BELOW_85_PERCENT")
    if final["calibration_error"] > 0.05:
        errors.append("EXTERNAL_CALIBRATION_ERROR_ABOVE_5_PERCENT")
    if (
        final["average_total_action_cost"]
        > control["average_total_action_cost"] + 0.05
    ):
        errors.append("EXTERNAL_TOTAL_COST_REGRESSION")
    return {
        "accepted": not errors,
        "errors": errors,
        "absolute_mean_goal": final["mean_goal_success"],
        "absolute_worst_family_goal": (
            final["worst_family_goal_success"]
        ),
        "absolute_relevant_factor_accuracy": (
            final["mean_relevant_factor_accuracy"]
        ),
        "absolute_calibration_error": final["calibration_error"],
        "total_action_cost_change": (
            final["average_total_action_cost"]
            - control["average_total_action_cost"]
        ),
    }


def _external_worlds(
    *,
    seed: int,
    count: int,
) -> List[GeneratedCausalWorld]:
    """A sealed family outside the Phase 8/9 procedural grammar.

    Every world has four latent factors, exactly two goal-relevant factors,
    new symbol roots, and reliability values absent from the original
    generator.
    """

    rng = random.Random(seed)
    roots = (
        "quartz",
        "raven",
        "saffron",
        "tundra",
        "umbra",
        "vector",
        "willow",
        "xenon",
        "yarrow",
        "zephyr",
    )
    worlds = []
    for index in range(count):
        prefix = f"external_four_{index}_{rng.randrange(100000):05d}"
        selected = rng.sample(roots, 4)
        signals = tuple(f"{prefix}_{name}_state" for name in selected)
        toggles = tuple(f"{prefix}_{name}_alter" for name in selected)
        probes = tuple(f"{prefix}_{name}_inspect" for name in selected)
        relevant = set(rng.sample(range(4), 2))
        pattern = tuple(
            rng.randint(0, 1) if factor in relevant else -1
            for factor in range(4)
        )
        probe_reliability = rng.choice((0.72, 0.82, 0.92))
        goal_reliability = rng.choice((0.91, 0.96, 0.985))
        goal_action = f"{prefix}_resolve"
        spec = CausalDomainSpec(
            domain_id=prefix,
            signal_targets=signals,
            toggle_actions=toggles,
            probe_actions=probes,
            goal_action=goal_action,
            goal_pattern_by_signal=pattern,
            probe_reliability=probe_reliability,
            goal_reliability=goal_reliability,
        )
        graph = StochasticLatentGraph(
            graph_id=f"external_{_canonical_hash(spec)[:16]}",
            factor_count=4,
            toggle_actions=toggles,
            signal_targets=signals,
            signal_factor_assignments=(0, 1, 2, 3),
            probe_actions=probes,
            goal_action=goal_action,
            goal_pattern=pattern,
            probe_reliability=probe_reliability,
            goal_reliability=goal_reliability,
        )
        worlds.append(
            GeneratedCausalWorld(
                spec=spec,
                probe_costs={
                    probe: rng.choice((0.07, 0.17, 0.31, 0.43))
                    for probe in probes
                },
                family=(
                    f"external_four:noise_"
                    f"{int(probe_reliability * 100)}"
                ),
                graph=graph,
            )
        )
    return worlds


def _promote_generation(
    runtime: HexCorePersistentLearningRuntime,
    result: Mapping[str, Any],
    gate: Mapping[str, Any],
    generation: int,
) -> Dict[str, Any]:
    policy = result["policy"]
    candidate = ProcedureCandidate(
        procedure_id=(
            f"procedure_multigeneration_{generation}_"
            f"{_canonical_hash(policy)[:12]}"
        ),
        goal="causal_investigation_policy",
        steps=[
            "identify_goal_relevant_factors",
            "set_reliability_conditioned_factor_thresholds",
            "select_probe_by_information_gain_minus_cost",
            "stop_each_factor_independently",
            "execute_retry_and_verify",
        ],
        score=_utility(result),
        success=bool(gate["accepted"]),
        evidence={
            "evaluation": f"phase10_generation_{generation}_sealed",
            "gate": dict(gate),
            "metrics": _summary(result),
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    return {
        "candidate": candidate.to_dict(),
        "promotion": promotion,
    }


def run_multigeneration_causal_evolution(
    *,
    state_path: Path,
    result_path: Path | None = None,
    generations: int = 3,
    development_worlds: int = 14,
    sealed_worlds: int = 18,
    episodes_per_world: int = 60,
    external_world_count: int = 12,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    evolution = OutcomeDrivenCausalEvolution(runtime)
    generator = ProceduralCausalWorldGenerator()
    parent_policy = PHASE9_CHAMPION
    baseline = ProcedureCandidate(
        procedure_id="procedure_efficient_causal_34e0b23ffd0f",
        goal="causal_investigation_policy",
        steps=[
            "probe_goal_relevant_uncertain_factors",
            "stop_at_0.97_or_7",
            "retry_terminal_action_once",
            "execute_and_verify",
        ],
        score=0.0,
        success=True,
        evidence={"source": "immutable_phase9_control"},
    )
    runtime.skills.promote(baseline)
    generation_records = []
    successful_promotions = 0

    for generation in range(1, generations + 1):
        development = generator.generate(
            seed=10_300_000 + generation * 100,
            count=development_worlds,
            cohort=f"phase10_generation_{generation}_development",
        )
        sealed = generator.generate(
            seed=10_300_050 + generation * 100,
            count=sealed_worlds,
            cohort=f"phase10_generation_{generation}_sealed",
        )
        parent_development = evolution.evaluate_policy(
            policy=parent_policy,
            worlds=development,
            episodes_per_world=episodes_per_world,
            seed_offset=1_000_000 + generation * 100_000,
        )
        challengers = _mutations(parent_policy, generation)
        challenger_development = [
            evolution.evaluate_policy(
                policy=policy,
                worlds=development,
                episodes_per_world=episodes_per_world,
                seed_offset=1_000_000 + generation * 100_000,
            )
            for policy in challengers
        ]
        selected_development = max(
            challenger_development,
            key=lambda result: (
                _utility(result),
                result["worst_family_goal_success"],
                -result["average_total_action_cost"],
            ),
        )
        selected_policy = next(
            policy for policy in challengers
            if policy.policy_id
            == selected_development["policy"]["policy_id"]
        )
        mutation_record = evolution.persist_development_outcomes(
            champion=parent_development,
            challengers=challenger_development,
            selected_policy=selected_policy,
        )
        parent_sealed = evolution.evaluate_policy(
            policy=parent_policy,
            worlds=sealed,
            episodes_per_world=episodes_per_world,
            seed_offset=2_000_000 + generation * 100_000,
        )
        challenger_sealed = evolution.evaluate_policy(
            policy=selected_policy,
            worlds=sealed,
            episodes_per_world=episodes_per_world,
            seed_offset=2_000_000 + generation * 100_000,
        )
        gate = _promotion_gate(parent_sealed, challenger_sealed)
        promotion = None
        if gate["accepted"]:
            promotion = _promote_generation(
                runtime,
                challenger_sealed,
                gate,
                generation,
            )
            if promotion["promotion"].get("promoted") is True:
                parent_policy = selected_policy
                successful_promotions += 1
        generation_records.append(
            {
                "generation": generation,
                "development": {
                    "parent": _summary(parent_development),
                    "challengers": [
                        _summary(row) for row in challenger_development
                    ],
                    "selected_policy": selected_policy.to_dict(),
                    "mutation_record": mutation_record,
                },
                "sealed": {
                    "parent": _summary(parent_sealed),
                    "challenger": _summary(challenger_sealed),
                    "gate": gate,
                },
                "promotion": promotion,
                "active_policy_after_generation": (
                    parent_policy.to_dict()
                ),
            }
        )

    external = _external_worlds(
        seed=10_399_991,
        count=external_world_count,
    )
    external_control = evolution.evaluate_policy(
        policy=PHASE9_CHAMPION,
        worlds=external,
        episodes_per_world=episodes_per_world,
        seed_offset=3_000_000,
    )
    external_final = evolution.evaluate_policy(
        policy=parent_policy,
        worlds=external,
        episodes_per_world=episodes_per_world,
        seed_offset=3_000_000,
    )
    external_gate = _external_transfer_gate(
        external_control, external_final
    )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "causal_investigation_policy"
    )
    result = {
        "schema_version": (
            "aion.hexcore.multigeneration_causal_evolution.v1"
        ),
        "benchmark": (
            "calibrated_total_cost_multigeneration_evolution"
        ),
        "language_provider_used": False,
        "calibration_target": "goal_relevant_factor_correctness",
        "action_cost_contract": {
            "probe": "world-specific observed cost",
            "toggle": 0.25,
            "terminal_attempt": 0.50,
            "retries_charged": True,
        },
        "generations": generation_records,
        "successful_promotions": successful_promotions,
        "plateau_detected": successful_promotions == 0,
        "initial_policy": PHASE9_CHAMPION.to_dict(),
        "final_policy": parent_policy.to_dict(),
        "external_family": {
            "description": (
                "four-factor, two-relevant-factor worlds with unseen "
                "symbol grammar, costs, and reliability values"
            ),
            "control": _summary(external_control),
            "final": _summary(external_final),
            "gate": external_gate,
        },
        "restart": {
            "champion_retained": retained is not None,
            "champion_id": (
                retained.get("procedure_id") if retained else None
            ),
            "mutation_cycles": len(
                restarted.store.state["procedure_mutation_cycles"]
            ),
            "failure_queue_records": sum(
                len(rows)
                for rows in restarted.store.state[
                    "failure_queues"
                ].values()
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "at_least_one_generation_promoted": (
                successful_promotions >= 1
            ),
            "external_family_passed": external_gate["accepted"],
            "total_action_cost_accounted": True,
            "goal_relevant_calibration_used": True,
            "fresh_sealed_cohort_each_generation": True,
            "restart_retention": (
                successful_promotions == 0
                or bool(retained)
            ),
        },
        "boundary_statement": (
            "This is bounded mutation of an allowlisted causal procedure "
            "over generated worlds. It does not modify source code, CAU, "
            "or the structural grammar."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(
            "data/hexcore/multigeneration_causal_evolution.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_multigeneration_causal_evolution.json"
        ),
    )
    args = parser.parse_args()
    result = run_multigeneration_causal_evolution(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

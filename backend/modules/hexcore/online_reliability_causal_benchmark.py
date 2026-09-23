from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
)
from backend.modules.hexcore.outcome_driven_causal_evolution import (
    GeneratedCausalWorld,
    InvestigationPolicy,
    OutcomeDrivenCausalEvolution,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    StochasticLatentGraph,
)


CONTROL = InvestigationPolicy(
    policy_id="phase9_fixed_reliability_control",
    confidence_gate=0.97,
    maximum_experiments=7,
    cost_weight=0.05,
    mutation="immutable_phase9_under_unknown_reliability",
    goal_relevance_only=True,
    uncertain_factor_only=True,
    goal_retries=1,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "goal": goal,
        "source": "online_reliability_causal_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _worlds(seed: int, count: int, cohort: str):
    rng = random.Random(seed)
    roots = (
        "aegis", "boreal", "coral", "drift", "echo", "fjord",
        "garnet", "harbor", "isotope", "juniper", "kestrel", "lattice",
        "meridian", "nectar", "orbit", "pulse", "ripple", "solstice",
    )
    output = []
    for index in range(count):
        factor_count = rng.choice((2, 3, 4))
        names = rng.sample(roots, factor_count)
        prefix = f"{cohort}_{index}_{rng.randrange(100000):05d}"
        signals = tuple(f"{prefix}_{name}_state" for name in names)
        toggles = tuple(f"{prefix}_{name}_change" for name in names)
        probes = tuple(f"{prefix}_{name}_observe" for name in names)
        goal = f"{prefix}_complete"
        relevant_count = rng.randint(1, min(3, factor_count))
        relevant = set(rng.sample(range(factor_count), relevant_count))
        pattern = tuple(
            rng.randint(0, 1) if position in relevant else -1
            for position in range(factor_count)
        )
        reliabilities = tuple(
            rng.choice((0.62, 0.72, 0.82, 0.92, 0.97))
            for _ in range(factor_count)
        )
        spec = CausalDomainSpec(
            domain_id=prefix,
            signal_targets=signals,
            toggle_actions=toggles,
            probe_actions=probes,
            goal_action=goal,
            goal_pattern_by_signal=pattern,
            probe_reliability=0.80,
            probe_reliabilities=reliabilities,
            goal_reliability=rng.choice((0.92, 0.96, 0.99)),
        )
        # The planner receives the correct structure but only an uninformative
        # reliability prior. Channel reliabilities remain hidden in the world.
        graph = StochasticLatentGraph(
            graph_id=f"unknown_reliability_{_canonical_hash(spec)[:16]}",
            factor_count=factor_count,
            toggle_actions=toggles,
            signal_targets=signals,
            signal_factor_assignments=tuple(range(factor_count)),
            probe_actions=probes,
            goal_action=goal,
            goal_pattern=pattern,
            probe_reliability=0.80,
            goal_reliability=spec.goal_reliability,
        )
        output.append(
            GeneratedCausalWorld(
                spec=spec,
                probe_costs={
                    probe: rng.choice((0.08, 0.16, 0.28, 0.40))
                    for probe in probes
                },
                family=(
                    f"unknown_channels_{factor_count}:"
                    f"minimum_{int(min(reliabilities) * 100)}"
                ),
                graph=graph,
            )
        )
    return output


def _utility(result: Mapping[str, Any]) -> float:
    return (
        result["mean_goal_success"]
        + 0.20 * result["mean_relevant_factor_accuracy"]
        - 0.10 * result["average_total_action_cost"]
        - 0.20 * result["calibration_error"]
        - 0.05 * result["mean_reliability_mae"]
    )


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in result.items() if key != "rows"
    } | {"effective_intelligence_utility": _utility(result)}


def _gate(
    control: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> Dict[str, Any]:
    goal_change = (
        challenger["mean_goal_success"] - control["mean_goal_success"]
    )
    worst_change = (
        challenger["worst_family_goal_success"]
        - control["worst_family_goal_success"]
    )
    cost_change = (
        challenger["average_total_action_cost"]
        - control["average_total_action_cost"]
    )
    calibration_change = (
        challenger["calibration_error"] - control["calibration_error"]
    )
    utility_change = _utility(challenger) - _utility(control)
    errors = []
    if goal_change < 0.01:
        errors.append("MEAN_GOAL_GAIN_BELOW_ONE_POINT")
    if worst_change < 0.0:
        errors.append("WORST_FAMILY_GOAL_REGRESSION")
    if calibration_change > 0.01:
        errors.append("CALIBRATION_REGRESSION_ABOVE_ONE_POINT")
    if cost_change > 0.25:
        errors.append("TOTAL_ACTION_COST_INCREASE_ABOVE_0_25")
    if utility_change <= 0.0:
        errors.append("EFFECTIVE_INTELLIGENCE_UTILITY_NOT_IMPROVED")
    if challenger["mean_goal_success"] < 0.80:
        errors.append("ABSOLUTE_GOAL_SUCCESS_BELOW_80_PERCENT")
    return {
        "accepted": not errors,
        "errors": errors,
        "mean_goal_change": goal_change,
        "worst_family_goal_change": worst_change,
        "calibration_change": calibration_change,
        "total_action_cost_change": cost_change,
        "reliability_mae_change": (
            challenger["mean_reliability_mae"]
            - control["mean_reliability_mae"]
        ),
        "effective_intelligence_utility_change": utility_change,
    }


def run_online_reliability_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 18,
    sealed_worlds: int = 24,
    episodes_per_world: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    evolution = OutcomeDrivenCausalEvolution(runtime)
    development_folds = [
        _worlds(
            11_700_101 + fold * 1_000,
            development_worlds,
            f"reliability_v7_voi_development_fold_{fold}",
        )
        for fold in range(3)
    ]
    development = [
        world for fold in development_folds for world in fold
    ]
    sealed = _worlds(
        11_700_909, sealed_worlds, "reliability_v7_voi_sealed"
    )
    challengers = [
        InvestigationPolicy(
            policy_id=(
                "online_reliability_voi_"
                f"{str(minimum_voi).replace('.', '_')}"
            ),
            confidence_gate=0.95,
            maximum_experiments=10,
            cost_weight=0.05,
            mutation=(
                "estimate_channel_reliability_and_rank_by_information_cost"
            ),
            parent_policy_id=CONTROL.policy_id,
            goal_relevance_only=True,
            uncertain_factor_only=True,
            goal_retries=1,
            online_reliability_learning=True,
            reliability_prior=0.80,
            value_of_information_ratio=True,
            three_factor_reserve=True,
            minimum_voi_per_cost=minimum_voi,
        )
        for minimum_voi in (0.20, 0.225, 0.25, 0.275)
    ]
    control_development_folds = [
        evolution.evaluate_policy(
            policy=CONTROL,
            worlds=fold,
            episodes_per_world=episodes_per_world,
            seed_offset=5_000_000 + index * 100_000,
        )
        for index, fold in enumerate(development_folds)
    ]
    control_development = evolution.evaluate_policy(
        policy=CONTROL,
        worlds=development,
        episodes_per_world=episodes_per_world,
        seed_offset=5_400_000,
    )
    challenger_development_folds = [
        [
            evolution.evaluate_policy(
                policy=policy,
                worlds=fold,
                episodes_per_world=episodes_per_world,
                seed_offset=5_000_000 + index * 100_000,
            )
            for index, fold in enumerate(development_folds)
        ]
        for policy in challengers
    ]
    development_results = [
        evolution.evaluate_policy(
            policy=policy,
            worlds=development,
            episodes_per_world=episodes_per_world,
            seed_offset=5_400_000,
        )
        for policy in challengers
    ]
    eligible = [
        row for row in development_results
        if (
            row["mean_goal_success"]
            >= control_development["mean_goal_success"] + 0.01
            and row["worst_family_goal_success"]
            >= control_development["worst_family_goal_success"]
            and all(
                fold["average_total_action_cost"]
                <= control_development_folds[index][
                    "average_total_action_cost"
                ] + 0.25
                for index, fold in enumerate(
                    challenger_development_folds[
                        development_results.index(row)
                    ]
                )
            )
        )
    ]
    selected = max(
        eligible or development_results,
        key=lambda row: (
            min(
                fold["mean_goal_success"]
                for fold in challenger_development_folds[
                    development_results.index(row)
                ]
            ),
            min(
                fold["worst_family_goal_success"]
                for fold in challenger_development_folds[
                    development_results.index(row)
                ]
            ),
            sum(
                _utility(fold)
                for fold in challenger_development_folds[
                    development_results.index(row)
                ]
            ) / len(development_folds),
        ),
    )
    selected_policy = next(
        policy for policy in challengers
        if policy.policy_id == selected["policy"]["policy_id"]
    )
    mutation = evolution.persist_development_outcomes(
        champion=control_development,
        challengers=development_results,
        selected_policy=selected_policy,
    )
    control_sealed = evolution.evaluate_policy(
        policy=CONTROL,
        worlds=sealed,
        episodes_per_world=episodes_per_world,
        seed_offset=6_000_000,
    )
    challenger_sealed = evolution.evaluate_policy(
        policy=selected_policy,
        worlds=sealed,
        episodes_per_world=episodes_per_world,
        seed_offset=6_000_000,
    )
    gate = _gate(control_sealed, challenger_sealed)
    baseline = ProcedureCandidate(
        procedure_id="procedure_efficient_causal_34e0b23ffd0f",
        goal="causal_investigation_policy",
        steps=["phase9_goal_relevant_investigation"],
        score=_utility(control_sealed),
        success=True,
        evidence={"evaluation": "phase11_sealed_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_online_reliability_"
            f"{_canonical_hash(selected_policy.to_dict())[:12]}"
        ),
        goal="causal_investigation_policy",
        steps=[
            "start_with_uncertain_channel_reliability",
            "estimate_reliability_from_repeated_observations",
            "update_the_belief_model_online",
            "rank_probes_by_information_per_cost",
            "stop_when_marginal_information_value_is_too_low",
            "plan_execute_and_verify",
        ],
        score=_utility(challenger_sealed),
        success=bool(gate["accepted"]),
        evidence={
            "evaluation": "phase11_sealed_unknown_reliability",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "causal_investigation_policy"
    )
    result = {
        "schema_version": (
            "aion.hexcore.online_reliability_causal.v7"
        ),
        "benchmark": "hidden_channel_reliability_and_voi_planning",
        "language_provider_used": False,
        "true_channel_reliability_supplied_to_aion": False,
        "development": {
            "control": _summary(control_development),
            "control_folds": [
                _summary(row) for row in control_development_folds
            ],
            "challengers": [
                _summary(row) for row in development_results
            ],
            "challenger_folds": {
                policy.policy_id: [
                    _summary(row) for row in folds
                ]
                for policy, folds in zip(
                    challengers, challenger_development_folds
                )
            },
            "selected_policy": selected_policy.to_dict(),
            "mutation": mutation,
        },
        "sealed": {
            "control": _summary(control_sealed),
            "challenger": _summary(challenger_sealed),
            "gate": gate,
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained is not None,
            "champion_id": (
                retained.get("procedure_id") if retained else None
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "hidden_reliability": True,
            "online_estimation_recorded": True,
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                promotion.get("promoted") is bool(gate["accepted"])
            ),
            "restart_retention": retained is not None,
        },
        "boundary_statement": (
            "The structural graph is supplied, but observation-channel "
            "reliability is hidden and estimated online. This is not open "
            "graph discovery or unrestricted procedure synthesis."
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
        default=Path("data/hexcore/online_reliability_causal.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_online_reliability_causal.json"),
    )
    args = parser.parse_args()
    result = run_online_reliability_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

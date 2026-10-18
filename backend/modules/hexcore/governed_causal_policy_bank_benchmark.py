from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.online_reliability_causal_benchmark import (
    CONTROL,
    _summary,
    _utility,
    _worlds,
)
from backend.modules.hexcore.outcome_driven_causal_evolution import (
    InvestigationPolicy,
    OutcomeDrivenCausalEvolution,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "goal": goal,
        "source": "governed_causal_policy_bank_authority",
        "S": 1.0,
        "H": 0.0,
    }


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
    if cost_change > 0.25:
        errors.append("TOTAL_ACTION_COST_INCREASE_ABOVE_0_25")
    if calibration_change > 0.01:
        errors.append("CALIBRATION_REGRESSION_ABOVE_ONE_POINT")
    if utility_change <= 0.0:
        errors.append("EFFECTIVE_INTELLIGENCE_UTILITY_NOT_IMPROVED")
    if challenger["mean_goal_success"] < 0.80:
        errors.append("ABSOLUTE_GOAL_SUCCESS_BELOW_80_PERCENT")
    if challenger["policy"]["complexity"] > 14:
        errors.append("POLICY_BANK_COMPLEXITY_CAP_EXCEEDED")
    return {
        "accepted": not errors,
        "errors": errors,
        "mean_goal_change": goal_change,
        "worst_family_goal_change": worst_change,
        "total_action_cost_change": cost_change,
        "calibration_change": calibration_change,
        "effective_intelligence_utility_change": utility_change,
    }


def run_governed_policy_bank_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 16,
    sealed_worlds: int = 28,
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
            13_100_101 + fold * 10_000,
            development_worlds,
            f"policy_bank_development_fold_{fold}",
        )
        for fold in range(3)
    ]
    sealed = _worlds(
        13_199_909,
        sealed_worlds,
        "policy_bank_source_disjoint_sealed",
    )
    candidates = [
        InvestigationPolicy(
            policy_id=(
                f"policy_bank_low_{int(low * 100)}_"
                f"high_{int(high * 100)}"
            ),
            confidence_gate=0.95,
            maximum_experiments=10,
            cost_weight=0.05,
            mutation=(
                "route_between_conservative_efficient_and_phase9"
            ),
            parent_policy_id=CONTROL.policy_id,
            goal_relevance_only=True,
            uncertain_factor_only=True,
            goal_retries=1,
            online_reliability_learning=True,
            reliability_prior=0.80,
            value_of_information_ratio=True,
            three_factor_reserve=True,
            policy_bank_enabled=True,
            router_low_reliability_threshold=low,
            router_high_reliability_threshold=high,
        )
        for low, high in (
            (0.72, 0.84),
            (0.76, 0.86),
            (0.80, 0.88),
        )
    ]
    control_folds = [
        evolution.evaluate_policy(
            policy=CONTROL,
            worlds=fold,
            episodes_per_world=episodes_per_world,
            seed_offset=13_500_000 + index * 100_000,
        )
        for index, fold in enumerate(development_folds)
    ]
    candidate_folds = [
        [
            evolution.evaluate_policy(
                policy=policy,
                worlds=fold,
                episodes_per_world=episodes_per_world,
                seed_offset=13_500_000 + index * 100_000,
            )
            for index, fold in enumerate(development_folds)
        ]
        for policy in candidates
    ]

    eligible_indexes = []
    for candidate_index, folds in enumerate(candidate_folds):
        if all(
            (
                row["mean_goal_success"]
                >= control_folds[index]["mean_goal_success"]
                and row["worst_family_goal_success"]
                >= control_folds[index]["worst_family_goal_success"]
                and row["average_total_action_cost"]
                <= control_folds[index]["average_total_action_cost"]
                + 0.25
            )
            for index, row in enumerate(folds)
        ):
            eligible_indexes.append(candidate_index)
    pool = eligible_indexes or list(range(len(candidates)))
    selected_index = max(
        pool,
        key=lambda index: (
            min(
                row["worst_family_goal_success"]
                for row in candidate_folds[index]
            ),
            min(
                row["mean_goal_success"]
                for row in candidate_folds[index]
            ),
            sum(_utility(row) for row in candidate_folds[index])
            / len(candidate_folds[index]),
        ),
    )
    selected_policy = candidates[selected_index]

    combined_development = [
        world for fold in development_folds for world in fold
    ]
    combined_control = evolution.evaluate_policy(
        policy=CONTROL,
        worlds=combined_development,
        episodes_per_world=episodes_per_world,
        seed_offset=13_900_000,
    )
    combined_candidates = [
        evolution.evaluate_policy(
            policy=policy,
            worlds=combined_development,
            episodes_per_world=episodes_per_world,
            seed_offset=13_900_000,
        )
        for policy in candidates
    ]
    mutation = evolution.persist_development_outcomes(
        champion=combined_control,
        challengers=combined_candidates,
        selected_policy=selected_policy,
    )

    control_sealed = evolution.evaluate_policy(
        policy=CONTROL,
        worlds=sealed,
        episodes_per_world=episodes_per_world,
        seed_offset=14_500_000,
    )
    challenger_sealed = evolution.evaluate_policy(
        policy=selected_policy,
        worlds=sealed,
        episodes_per_world=episodes_per_world,
        seed_offset=14_500_000,
    )
    gate = _gate(control_sealed, challenger_sealed)
    baseline = ProcedureCandidate(
        procedure_id="procedure_efficient_causal_34e0b23ffd0f",
        goal="causal_investigation_policy",
        steps=["phase9_goal_relevant_investigation"],
        score=_utility(control_sealed),
        success=True,
        evidence={"evaluation": "phase13_sealed_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_governed_policy_bank_"
            f"{_canonical_hash(selected_policy.to_dict())[:12]}"
        ),
        goal="causal_investigation_policy",
        steps=[
            "estimate_channel_reliability_online",
            "measure_goal_relevant_belief_uncertainty",
            "route_to_conservative_or_efficient_specialist",
            "fallback_to_phase9_on_router_uncertainty",
            "execute_verify_and_record_specialist_outcome",
        ],
        score=_utility(challenger_sealed),
        success=bool(gate["accepted"]),
        evidence={
            "evaluation": "phase13_source_disjoint_sealed",
            "gate": gate,
            "specialist_counts": challenger_sealed[
                "specialist_counts"
            ],
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
        "schema_version": "aion.hexcore.governed_policy_bank.v1",
        "benchmark": "online_reliability_specialist_policy_bank",
        "language_provider_used": False,
        "router_inputs": [
            "factor_count",
            "estimated_channel_reliability",
            "goal_relevant_belief_entropy",
            "relevant_observation_count",
            "remaining_experiment_budget",
        ],
        "development": {
            "control_folds": [_summary(row) for row in control_folds],
            "candidate_folds": {
                policy.policy_id: [
                    _summary(row) for row in folds
                ]
                for policy, folds in zip(candidates, candidate_folds)
            },
            "eligible_policy_ids": [
                candidates[index].policy_id
                for index in eligible_indexes
            ],
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
            "three_development_folds": True,
            "source_disjoint_sealed_family": True,
            "router_has_explicit_fallback": True,
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                bool(promotion.get("promoted"))
                == bool(gate["accepted"])
            ),
            "restart_retention": retained is not None,
        },
        "boundary_statement": (
            "The router selects among three allowlisted investigation "
            "procedures. It cannot alter specialists, source code, CAU, "
            "or the supplied causal graph grammar."
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
        default=Path("data/hexcore/governed_causal_policy_bank.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_governed_causal_policy_bank.json"),
    )
    args = parser.parse_args()
    result = run_governed_policy_bank_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

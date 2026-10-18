from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.outcome_driven_causal_evolution import (
    InvestigationPolicy,
    OutcomeDrivenCausalEvolution,
    ProceduralCausalWorldGenerator,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)


PHASE8_CHAMPION = InvestigationPolicy(
    policy_id="phase8_high_confidence_champion",
    confidence_gate=0.98,
    maximum_experiments=10,
    cost_weight=0.05,
    mutation="immutable_phase8_control",
)

EFFICIENCY_CHALLENGERS = [
    InvestigationPolicy(
        policy_id="goal_relevance_only",
        confidence_gate=0.98,
        maximum_experiments=10,
        cost_weight=0.05,
        mutation=(
            "stop_and_probe_only_goal_relevant_uncertain_factors"
        ),
        parent_policy_id=PHASE8_CHAMPION.policy_id,
        goal_relevance_only=True,
        uncertain_factor_only=True,
    ),
    InvestigationPolicy(
        policy_id="goal_aware_retry8",
        confidence_gate=0.98,
        maximum_experiments=8,
        cost_weight=0.05,
        mutation=(
            "goal_relevant_factor_stopping_plus_execution_retry"
        ),
        parent_policy_id=PHASE8_CHAMPION.policy_id,
        goal_relevance_only=True,
        uncertain_factor_only=True,
        goal_retries=1,
    ),
    InvestigationPolicy(
        policy_id="goal_aware_adaptive7",
        confidence_gate=0.97,
        maximum_experiments=7,
        cost_weight=0.05,
        mutation=(
            "goal_relevant_stopping_lower_threshold_and_retry"
        ),
        parent_policy_id=PHASE8_CHAMPION.policy_id,
        goal_relevance_only=True,
        uncertain_factor_only=True,
        goal_retries=1,
    ),
    InvestigationPolicy(
        policy_id="goal_aware_lean6",
        confidence_gate=0.95,
        maximum_experiments=6,
        cost_weight=0.08,
        mutation="lean_goal_relevant_efficiency_control",
        parent_policy_id=PHASE8_CHAMPION.policy_id,
        goal_relevance_only=True,
        uncertain_factor_only=True,
        goal_retries=1,
    ),
]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "causal_efficiency_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _efficiency_score(result: Mapping[str, Any]) -> float:
    return (
        float(result["mean_goal_success"])
        + 0.20 * float(result["mean_relevant_factor_accuracy"])
        - 0.03 * float(result["average_experiments"])
        - 0.20 * float(result["calibration_error"])
    )


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in result.items()
        if key != "rows"
    } | {"efficiency_score": _efficiency_score(result)}


def _promotion_gate(
    champion: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> Dict[str, Any]:
    goal_change = (
        challenger["mean_goal_success"]
        - champion["mean_goal_success"]
    )
    experiment_reduction = (
        champion["average_experiments"]
        - challenger["average_experiments"]
    )
    worst_goal_change = (
        challenger["worst_family_goal_success"]
        - champion["worst_family_goal_success"]
    )
    relevant_factor_change = (
        challenger["mean_relevant_factor_accuracy"]
        - champion["mean_relevant_factor_accuracy"]
    )
    calibration_change = (
        challenger["calibration_error"]
        - champion["calibration_error"]
    )
    errors = []
    if goal_change < 0.0:
        errors.append("MEAN_GOAL_SUCCESS_REGRESSION")
    if experiment_reduction < 1.0:
        errors.append("EXPERIMENT_REDUCTION_BELOW_ONE")
    if worst_goal_change < 0.0:
        errors.append("WORST_FAMILY_GOAL_REGRESSION")
    if relevant_factor_change < -0.02:
        errors.append("RELEVANT_FACTOR_REGRESSION_ABOVE_TWO_POINTS")
    if calibration_change > 0.03:
        errors.append("CALIBRATION_REGRESSION_ABOVE_THREE_POINTS")
    if challenger["policy"]["complexity"] > 10:
        errors.append("PROCEDURE_COMPLEXITY_CAP_EXCEEDED")
    if challenger["policy"]["maximum_experiments"] > 10:
        errors.append("EXPERIMENT_BUDGET_CAP_EXCEEDED")
    return {
        "accepted": not errors,
        "errors": errors,
        "mean_goal_change": goal_change,
        "average_experiment_reduction": experiment_reduction,
        "worst_family_goal_change": worst_goal_change,
        "relevant_factor_accuracy_change": relevant_factor_change,
        "calibration_change": calibration_change,
    }


def _promote(
    *,
    runtime: HexCorePersistentLearningRuntime,
    champion: Mapping[str, Any],
    challenger: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> Dict[str, Any]:
    goal = "causal_investigation_policy"
    baseline = ProcedureCandidate(
        procedure_id="procedure_phase8_high_confidence_control",
        goal=goal,
        steps=[
            "probe_all_factors_by_information_gain",
            "stop_at_0.98_or_10",
            "intervene_to_goal_pattern",
            "execute_and_verify",
        ],
        score=_efficiency_score(champion),
        success=True,
        evidence={
            "evaluation": "phase9_sealed_worlds",
            "mean_goal_success": champion["mean_goal_success"],
            "average_experiments": champion["average_experiments"],
        },
    )
    baseline_promotion = runtime.skills.promote(baseline)
    policy = challenger["policy"]
    evolved = ProcedureCandidate(
        procedure_id=(
            "procedure_efficient_causal_"
            f"{_canonical_hash(policy)[:12]}"
        ),
        goal=goal,
        steps=[
            "probe_goal_relevant_uncertain_factors",
            (
                f"stop_at_{policy['confidence_gate']}"
                f"_or_{policy['maximum_experiments']}"
            ),
            f"retry_goal_up_to_{policy['goal_retries']}",
            "intervene_to_goal_pattern",
            "execute_and_verify",
        ],
        score=_efficiency_score(challenger),
        success=bool(gate["accepted"]),
        evidence={
            "evaluation": "phase9_sealed_worlds",
            "gate": dict(gate),
            "mean_goal_success": challenger["mean_goal_success"],
            "average_experiments": challenger["average_experiments"],
            "failure_counts": challenger["failure_counts"],
        },
    )
    challenger_promotion = runtime.skills.promote(evolved)
    runtime.skills.record_outcome(
        procedure_id=evolved.procedure_id,
        success=evolved.success,
        score=evolved.score,
        evidence=evolved.evidence,
    )
    return {
        "baseline": baseline.to_dict(),
        "baseline_promotion": baseline_promotion,
        "challenger": evolved.to_dict(),
        "challenger_promotion": challenger_promotion,
    }


def run_causal_efficiency_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 12,
    sealed_worlds: int = 16,
    development_episodes: int = 40,
    sealed_episodes: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    evolution = OutcomeDrivenCausalEvolution(runtime)
    generator = ProceduralCausalWorldGenerator()
    development = generator.generate(
        seed=79_220_888,
        count=development_worlds,
        cohort="efficiency_development",
    )
    sealed = generator.generate(
        seed=79_220_999,
        count=sealed_worlds,
        cohort="efficiency_sealed",
    )
    champion_development = evolution.evaluate_policy(
        policy=PHASE8_CHAMPION,
        worlds=development,
        episodes_per_world=development_episodes,
        seed_offset=700_000,
    )
    challenger_development = [
        evolution.evaluate_policy(
            policy=policy,
            worlds=development,
            episodes_per_world=development_episodes,
            seed_offset=700_000,
        )
        for policy in EFFICIENCY_CHALLENGERS
    ]
    selected_development = max(
        challenger_development,
        key=lambda row: (
            _efficiency_score(row),
            row["worst_family_goal_success"],
            -row["average_experiments"],
        ),
    )
    selected_policy = next(
        policy for policy in EFFICIENCY_CHALLENGERS
        if policy.policy_id
        == selected_development["policy"]["policy_id"]
    )
    mutation_record = evolution.persist_development_outcomes(
        champion=champion_development,
        challengers=challenger_development,
        selected_policy=selected_policy,
    )

    champion_sealed = evolution.evaluate_policy(
        policy=PHASE8_CHAMPION,
        worlds=sealed,
        episodes_per_world=sealed_episodes,
        seed_offset=800_000,
    )
    challenger_sealed = evolution.evaluate_policy(
        policy=selected_policy,
        worlds=sealed,
        episodes_per_world=sealed_episodes,
        seed_offset=800_000,
    )
    gate = _promotion_gate(champion_sealed, challenger_sealed)
    promotion = _promote(
        runtime=runtime,
        champion=champion_sealed,
        challenger=challenger_sealed,
        gate=gate,
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
            "aion.hexcore.causal_efficiency_evolution.v1"
        ),
        "benchmark": (
            "goal_relevant_factor_stopping_and_execution_retry"
        ),
        "language_provider_used": False,
        "development": {
            "champion": _summary(champion_development),
            "challengers": [
                _summary(row) for row in challenger_development
            ],
            "selected_policy": selected_policy.to_dict(),
            "mutation_record": mutation_record,
        },
        "sealed_evaluation": {
            "champion": _summary(champion_sealed),
            "challenger": _summary(challenger_sealed),
            "gate": gate,
        },
        "promotion": promotion,
        "restart": {
            "champion_retained": retained is not None,
            "champion_id": (
                retained.get("procedure_id") if retained else None
            ),
            "failure_queue_records": sum(
                len(rows)
                for rows in restarted.store.state[
                    "failure_queues"
                ].values()
            ),
            "mutation_cycles": len(
                restarted.store.state[
                    "procedure_mutation_cycles"
                ]
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "mean_goal_preserved_or_improved": (
                gate["mean_goal_change"] >= 0.0
            ),
            "at_least_one_experiment_removed": (
                gate["average_experiment_reduction"] >= 1.0
            ),
            "worst_family_goal_not_regressed": (
                gate["worst_family_goal_change"] >= 0.0
            ),
            "relevant_factor_accuracy_protected": (
                gate["relevant_factor_accuracy_change"] >= -0.02
            ),
            "calibration_protected": (
                gate["calibration_change"] <= 0.03
            ),
            "complexity_bounded": (
                selected_policy.complexity <= 10
                and selected_policy.maximum_experiments <= 10
            ),
            "challenger_promoted": (
                promotion["challenger_promotion"].get(
                    "promoted"
                )
                is True
            ),
            "restart_retention": bool(
                retained
                and retained.get("procedure_id")
                == promotion["challenger"]["procedure_id"]
            ),
        },
        "boundary_statement": (
            "This is one governed efficiency mutation cycle over bounded "
            "generated worlds. It does not demonstrate unbounded recursive "
            "self-improvement or autonomous source-code modification."
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
            "data/hexcore/causal_efficiency_evolution.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_causal_efficiency_evolution.json"
        ),
    )
    args = parser.parse_args()
    result = run_causal_efficiency_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


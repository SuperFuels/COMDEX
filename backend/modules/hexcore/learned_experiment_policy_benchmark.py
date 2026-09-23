from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Hypothesis = Tuple[str, int]
Point = Tuple[int, int]
POINTS = tuple((left, right) for left in range(11) for right in range(11))
THRESHOLDS: Dict[str, Tuple[int, ...]] = {
    "difference_ge": tuple(range(-8, 9)),
    "sum_ge": tuple(range(2, 19)),
    "min_ge": tuple(range(1, 10)),
    "max_ge": tuple(range(1, 10)),
    "abs_difference_le": tuple(range(0, 10)),
}
HYPOTHESES = tuple(
    (operator, threshold)
    for operator, thresholds in THRESHOLDS.items()
    for threshold in thresholds
)


@dataclass(frozen=True)
class PolicyWorld:
    world_id: str
    fields: Tuple[str, str]
    hypothesis: Hypothesis

    def observe(self, point: Point) -> bool:
        return _predict(self.hypothesis, point)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "learned_experiment_policy_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _value(operator: str, point: Point) -> int:
    left, right = point
    if operator == "difference_ge":
        return left - right
    if operator == "sum_ge":
        return left + right
    if operator == "min_ge":
        return min(left, right)
    if operator == "max_ge":
        return max(left, right)
    if operator == "abs_difference_le":
        return abs(left - right)
    raise ValueError(operator)


def _predict(hypothesis: Hypothesis, point: Point) -> bool:
    operator, threshold = hypothesis
    value = _value(operator, point)
    if operator == "abs_difference_le":
        return value <= threshold
    return value >= threshold


def _probe_cost(point: Point) -> float:
    left, right = point
    return 1.0 + 0.025 * (left + right) + 0.05 * int(left != right)


def _entropy(probabilities: Iterable[float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _normalise(weights: Mapping[Hypothesis, float]) -> Dict[Hypothesis, float]:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("posterior has zero mass")
    return {
        hypothesis: weight / total
        for hypothesis, weight in weights.items()
    }


def _development_history() -> List[Hypothesis]:
    history: List[Hypothesis] = []
    for threshold in range(3, 8):
        history.extend([("min_ge", threshold)] * 12)
    for threshold in range(4, 9):
        history.extend([("max_ge", threshold)] * 10)
    for threshold in range(1, 4):
        history.extend([("abs_difference_le", threshold)] * 9)
    for threshold in range(2, 6):
        history.extend([("difference_ge", threshold)] * 2)
    for threshold in range(8, 15):
        history.extend([("sum_ge", threshold)] * 2)
    return history


def _learn_prior(
    history: Sequence[Hypothesis],
    *,
    smoothing: float = 0.25,
) -> Dict[Hypothesis, float]:
    counts = {hypothesis: smoothing for hypothesis in HYPOTHESES}
    for hypothesis in history:
        counts[hypothesis] += 1.0
    return _normalise(counts)


def _uniform_prior() -> Dict[Hypothesis, float]:
    return {
        hypothesis: 1.0 / len(HYPOTHESES)
        for hypothesis in HYPOTHESES
    }


def _select_probe(
    *,
    posterior: Mapping[Hypothesis, float],
    unused: Sequence[Point],
) -> Point:
    prior_entropy = _entropy(posterior.values())

    def utility(point: Point) -> Tuple[float, float, Point]:
        positive = sum(
            probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, point)
        )
        negative = 1.0 - positive
        expected_entropy = 0.0
        for outcome_probability, outcome in (
            (positive, True),
            (negative, False),
        ):
            if outcome_probability <= 0.0:
                continue
            conditional = [
                probability / outcome_probability
                for hypothesis, probability in posterior.items()
                if _predict(hypothesis, point) == outcome
            ]
            expected_entropy += outcome_probability * _entropy(conditional)
        information_gain = prior_entropy - expected_entropy
        return (
            information_gain / _probe_cost(point),
            information_gain,
            point,
        )

    return max(unused, key=utility)


def _run_policy(
    *,
    world: PolicyWorld,
    prior: Mapping[Hypothesis, float],
    surprise_fallback: bool,
    surprise_threshold: float = 0.08,
    max_probes: int = 30,
) -> Dict[str, Any]:
    posterior = dict(prior)
    unused = list(POINTS)
    trace = []
    fallback_count = 0
    total_cost = 0.0
    while len(posterior) > 1 and len(trace) < max_probes:
        point = _select_probe(posterior=posterior, unused=unused)
        unused.remove(point)
        positive_probability = sum(
            probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, point)
        )
        outcome = world.observe(point)
        outcome_probability = (
            positive_probability if outcome else 1.0 - positive_probability
        )
        survivors = {
            hypothesis: probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, point) == outcome
        }
        fallback_triggered = bool(
            surprise_fallback
            and outcome_probability < surprise_threshold
            and len(survivors) > 1
        )
        if fallback_triggered:
            fallback_count += 1
            posterior = {
                hypothesis: 1.0 / len(survivors)
                for hypothesis in survivors
            }
        else:
            posterior = _normalise(survivors)
        cost = _probe_cost(point)
        total_cost += cost
        trace.append(
            {
                "point": list(point),
                "outcome": int(outcome),
                "predicted_outcome_probability": outcome_probability,
                "fallback_triggered": fallback_triggered,
                "remaining_hypotheses": len(posterior),
                "cost": cost,
            }
        )
    selected = max(posterior, key=posterior.get)
    return {
        "selected": list(selected),
        "correct": selected == world.hypothesis,
        "probes": len(trace),
        "total_cost": total_cost,
        "fallback_count": fallback_count,
        "final_confidence": posterior[selected],
        "trace": trace,
    }


def _make_worlds(
    *,
    prefix: str,
    hypotheses: Sequence[Hypothesis],
) -> List[PolicyWorld]:
    names = (
        ("aperture", "buffer"),
        ("canopy", "ballast"),
        ("charge", "leak"),
        ("signal", "noise"),
        ("supply", "load"),
        ("growth", "decay"),
        ("pressure", "drag"),
        ("reserve", "demand"),
    )
    return [
        PolicyWorld(
            world_id=f"{prefix}_{index:03d}",
            fields=names[index % len(names)],
            hypothesis=hypothesis,
        )
        for index, hypothesis in enumerate(hypotheses)
    ]


def _sample_in_distribution(
    *,
    history: Sequence[Hypothesis],
    count: int,
    seed: int,
) -> List[Hypothesis]:
    rng = random.Random(seed)
    return [rng.choice(history) for _ in range(count)]


def _development_ood_hypotheses() -> List[Hypothesis]:
    rare = (
        ("difference_ge", -8),
        ("difference_ge", 8),
        ("sum_ge", 2),
        ("sum_ge", 18),
        ("min_ge", 1),
        ("min_ge", 9),
        ("max_ge", 1),
        ("max_ge", 9),
        ("abs_difference_le", 8),
        ("abs_difference_le", 9),
    )
    return list(rare) * 6


def _sealed_ood_hypotheses() -> List[Hypothesis]:
    # Exact hypotheses are disjoint from fallback calibration.
    rare = (
        ("difference_ge", -7),
        ("difference_ge", -6),
        ("difference_ge", 6),
        ("difference_ge", 7),
        ("sum_ge", 3),
        ("sum_ge", 17),
        ("min_ge", 2),
        ("min_ge", 8),
        ("max_ge", 2),
        ("max_ge", 3),
        ("abs_difference_le", 7),
    )
    return list(rare) * 6


def _evaluate(
    *,
    worlds: Sequence[PolicyWorld],
    learned_prior: Mapping[Hypothesis, float],
    surprise_threshold: float = 0.08,
) -> Dict[str, Any]:
    rows = []
    for world in worlds:
        learned = _run_policy(
            world=world,
            prior=learned_prior,
            surprise_fallback=True,
            surprise_threshold=surprise_threshold,
        )
        cold = _run_policy(
            world=world,
            prior=_uniform_prior(),
            surprise_fallback=False,
        )
        rows.append(
            {
                "world_id": world.world_id,
                "fields": list(world.fields),
                "true_hypothesis": list(world.hypothesis),
                "learned": learned,
                "cold": cold,
            }
        )
    learned_probes = sum(row["learned"]["probes"] for row in rows) / len(rows)
    cold_probes = sum(row["cold"]["probes"] for row in rows) / len(rows)
    learned_cost = sum(
        row["learned"]["total_cost"] for row in rows
    ) / len(rows)
    cold_cost = sum(row["cold"]["total_cost"] for row in rows) / len(rows)
    return {
        "worlds": len(rows),
        "learned_accuracy": sum(
            int(row["learned"]["correct"]) for row in rows
        ) / len(rows),
        "cold_accuracy": sum(
            int(row["cold"]["correct"]) for row in rows
        ) / len(rows),
        "learned_mean_probes": learned_probes,
        "cold_mean_probes": cold_probes,
        "probe_reduction": 1.0 - learned_probes / cold_probes,
        "learned_mean_cost": learned_cost,
        "cold_mean_cost": cold_cost,
        "cost_reduction": 1.0 - learned_cost / cold_cost,
        "learned_worst_probes": max(row["learned"]["probes"] for row in rows),
        "cold_worst_probes": max(row["cold"]["probes"] for row in rows),
        "fallbacks": sum(
            row["learned"]["fallback_count"] for row in rows
        ),
        "rows": rows,
    }


def run_learned_experiment_policy_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_worlds: int = 160,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    runtime.store.state["theory_revisions"].append(
        {
            "cycle_id": "phase26_multigeneration_revision",
            "status": "promoted_dependency",
            "source_procedure_id": (
                "procedure_multigeneration_theory_ea3ae1b2a2df"
            ),
        }
    )
    runtime.store.commit(reason="load_phase26_theory_revision")

    history = _development_history()
    learned_prior = _learn_prior(history, smoothing=6.0)
    development_checksum = _canonical_hash(history)
    fallback_calibration = _evaluate(
        worlds=_make_worlds(
            prefix="development_ood",
            hypotheses=_development_ood_hypotheses(),
        ),
        learned_prior=learned_prior,
        surprise_threshold=0.38,
    )
    in_distribution = _evaluate(
        worlds=_make_worlds(
            prefix="sealed_motif",
            hypotheses=_sample_in_distribution(
                history=history,
                count=sealed_worlds,
                seed=41_027,
            ),
        ),
        learned_prior=learned_prior,
        surprise_threshold=0.38,
    )
    ood = _evaluate(
        worlds=_make_worlds(
            prefix="sealed_ood",
            hypotheses=_sealed_ood_hypotheses(),
        ),
        learned_prior=learned_prior,
        surprise_threshold=0.38,
    )

    errors = []
    if in_distribution["learned_accuracy"] < 1.0:
        errors.append("IN_DISTRIBUTION_IDENTIFICATION_NOT_EXACT")
    if in_distribution["probe_reduction"] < 0.08:
        errors.append("REAL_INTERVENTION_REDUCTION_BELOW_8_PERCENT")
    if in_distribution["cost_reduction"] < 0.08:
        errors.append("ACTION_COST_REDUCTION_BELOW_8_PERCENT")
    if ood["learned_accuracy"] < ood["cold_accuracy"]:
        errors.append("OOD_ACCURACY_REGRESSION")
    if (
        ood["learned_mean_probes"]
        > ood["cold_mean_probes"] + 1.0
    ):
        errors.append("OOD_PROBE_REGRESSION_ABOVE_ONE")
    if ood["fallbacks"] <= 0:
        errors.append("SURPRISE_FALLBACK_NEVER_EXERCISED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "sealed_worlds": sealed_worlds,
        "in_distribution_accuracy": in_distribution["learned_accuracy"],
        "cold_accuracy": in_distribution["cold_accuracy"],
        "learned_mean_probes": in_distribution["learned_mean_probes"],
        "cold_mean_probes": in_distribution["cold_mean_probes"],
        "probe_reduction": in_distribution["probe_reduction"],
        "learned_mean_cost": in_distribution["learned_mean_cost"],
        "cold_mean_cost": in_distribution["cold_mean_cost"],
        "cost_reduction": in_distribution["cost_reduction"],
        "ood_accuracy": ood["learned_accuracy"],
        "ood_cold_accuracy": ood["cold_accuracy"],
        "ood_mean_probes": ood["learned_mean_probes"],
        "ood_cold_mean_probes": ood["cold_mean_probes"],
        "ood_fallbacks": ood["fallbacks"],
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_multigeneration_theory_ea3ae1b2a2df",
        goal="learned_experiment_policy",
        steps=["uniform_prior_information_gain"],
        score=-in_distribution["cold_mean_cost"],
        success=True,
        evidence={"evaluation": "phase27_uniform_active_control"},
    )
    runtime.skills.promote(baseline)
    policy = {
        "schema_version": "aion.hexcore.experiment_policy.v1",
        "name": "motif_prior_information_gain",
        "hypothesis_space_size": len(HYPOTHESES),
        "development_examples": len(history),
        "development_checksum": development_checksum,
        "smoothing": 6.0,
        "objective": "expected_information_gain_per_action_cost",
        "surprise_fallback_probability": 0.38,
        "prior": {
            f"{operator}:{threshold}": probability
            for (operator, threshold), probability in learned_prior.items()
        },
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    policy_id = (
        "experiment_policy_motif_"
        + _canonical_hash(policy)[:12]
    )
    policy["policy_id"] = policy_id
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_learned_experiments_"
            + _canonical_hash(policy)[:12]
        ),
        goal="learned_experiment_policy",
        steps=[
            "learn_prior_over_recurring_causal_motifs",
            "select_probe_by_expected_information_gain_per_cost",
            "update_exact_posterior_from_observed_outcome",
            "fall_back_to_uniform_reasoning_on_prior_surprise",
            "verify_real_intervention_reduction",
            "protect_out_of_distribution_accuracy",
            "retain_policy_with_provenance",
        ],
        score=-in_distribution["learned_mean_cost"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase27_learned_experiment_policy_sealed",
            "policy_id": policy_id,
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    if gate["accepted"]:
        runtime.store.state["experiment_policies"][policy_id] = policy
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "experiment_policy",
                "invention_id": policy_id,
                "procedure_id": candidate.procedure_id,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"experiment_policy:{policy_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "policy_retained": (
            policy_id in restarted.store.state["experiment_policies"]
        ),
        "champion_retained": (
            restarted.store.state.get("champions", {}).get(
                "learned_experiment_policy"
            )
            == candidate.procedure_id
        ),
        "phase26_dependency_retained": any(
            row.get("cycle_id") == "phase26_multigeneration_revision"
            for row in restarted.store.state["theory_revisions"]
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            value is True
            for key, value in restart.items()
            if key != "relearning_worlds"
        )
    )
    result = {
        "schema_version": "aion.hexcore.learned_experiment_policy.v1",
        "benchmark": "meta_learned_cost_aware_experiment_selection",
        "passed": passed,
        "development": {
            "examples": len(history),
            "checksum": development_checksum,
            "fallback_calibration": {
                "worlds": fallback_calibration["worlds"],
                "learned_accuracy": fallback_calibration[
                    "learned_accuracy"
                ],
                "learned_mean_probes": fallback_calibration[
                    "learned_mean_probes"
                ],
                "cold_mean_probes": fallback_calibration[
                    "cold_mean_probes"
                ],
                "fallbacks": fallback_calibration["fallbacks"],
            },
        },
        "in_distribution": in_distribution,
        "out_of_distribution": ood,
        "gate": gate,
        "policy": policy,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION learned a prior over a bounded recurring task distribution "
            "and used it to order experiments. It did not learn unrestricted "
            "scientific experimentation or guarantee savings under arbitrary "
            "distribution shift."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore learned experiment-policy benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=160)
    args = parser.parse_args()
    result = run_learned_experiment_policy_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

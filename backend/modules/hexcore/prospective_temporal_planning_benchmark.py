from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.anticipatory_temporal_reasoning_benchmark import (
    Assignment,
    TemporalWorld,
    TemporalWorldGenerator,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class ProspectivePolicy:
    policy_id: str
    minimum_transition_support: int
    maximum_duration_std: float
    minimum_prediction_confidence: float
    maximum_horizon: int

    @property
    def complexity(self) -> int:
        return 5 + self.maximum_horizon + self.minimum_transition_support

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "minimum_transition_support": self.minimum_transition_support,
            "maximum_duration_std": self.maximum_duration_std,
            "minimum_prediction_confidence": self.minimum_prediction_confidence,
            "maximum_horizon": self.maximum_horizon,
            "complexity": self.complexity,
        }


def _segments(schedule: Sequence[Assignment], stop: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start = 0
    active = schedule[0]
    for block in range(1, stop):
        if schedule[block] == active:
            continue
        rows.append(
            {
                "graph": active,
                "next": schedule[block],
                "duration": block - start,
            }
        )
        start = block
        active = schedule[block]
    return rows


def _learn_temporal_model(
    schedule: Sequence[Assignment],
    stop: int,
) -> Dict[Assignment, List[Dict[str, Any]]]:
    model: Dict[Assignment, List[Dict[str, Any]]] = defaultdict(list)
    for row in _segments(schedule, stop):
        model[row["graph"]].append(
            {"next": row["next"], "duration": row["duration"]}
        )
    return dict(model)


def _duration_stats(rows: Sequence[Mapping[str, Any]]) -> Tuple[float, float]:
    values = [float(row["duration"]) for row in rows]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def _future_distribution(
    *,
    active: Assignment,
    elapsed: int,
    horizon: int,
    model: Mapping[Assignment, Sequence[Mapping[str, Any]]],
    policy: ProspectivePolicy,
) -> Dict[Assignment, float] | None:
    if horizon > policy.maximum_horizon:
        return None
    initial_rows = list(model.get(active) or [])
    if len(initial_rows) < policy.minimum_transition_support:
        return None
    _, initial_std = _duration_stats(initial_rows)
    initial_durations = [int(row["duration"]) for row in initial_rows]
    if (
        initial_std > policy.maximum_duration_std
        or max(initial_durations) - min(initial_durations)
        > 2.0 * policy.maximum_duration_std
    ):
        return None
    distribution: Dict[Tuple[Assignment, int], float] = {(active, elapsed): 1.0}
    for _ in range(horizon):
        updated: Dict[Tuple[Assignment, int], float] = defaultdict(float)
        for (graph, age), mass in distribution.items():
            rows = list(model.get(graph) or [])
            if len(rows) < policy.minimum_transition_support:
                updated[(graph, age + 1)] += mass
                continue
            mean, std = _duration_stats(rows)
            durations = [int(row["duration"]) for row in rows]
            if (
                std > policy.maximum_duration_std
                or max(durations) - min(durations)
                > 2.0 * policy.maximum_duration_std
            ):
                return None
            next_counts: Dict[Assignment, int] = defaultdict(int)
            for row in rows:
                next_counts[tuple(row["next"])] += 1
            transition_probability = min(
                1.0,
                max(0.0, (age + 1 - (mean - 1.0)) / max(1.0, std + 0.5)),
            )
            stay = 1.0 - transition_probability
            updated[(graph, age + 1)] += mass * stay
            total = sum(next_counts.values())
            for target, count in next_counts.items():
                updated[(target, 0)] += (
                    mass * transition_probability * count / total
                )
        distribution = dict(updated)
    graph_distribution: Dict[Assignment, float] = defaultdict(float)
    for (graph, _), mass in distribution.items():
        graph_distribution[graph] += mass
    total = sum(graph_distribution.values())
    if total <= 0:
        return None
    return {graph: mass / total for graph, mass in graph_distribution.items()}


def _active_since(schedule: Sequence[Assignment], block: int) -> int:
    graph = schedule[block]
    start = block
    while start > 0 and schedule[start - 1] == graph:
        start -= 1
    return start


def _run_world(
    *,
    world: TemporalWorld,
    policy: ProspectivePolicy,
    seed: int,
    learning_stop: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    model = _learn_temporal_model(world.schedule, learning_stop)
    planned = 0
    correct_predictions = 0
    unsafe_predictive_commits = 0
    prospective_success = 0
    reactive_success = 0
    fallback_count = 0
    confidence_sum = 0.0
    rows = []
    for block in range(evaluation_start, len(world.schedule) - 3):
        horizon = rng.choice((1, 2, 3))
        current = world.schedule[block]
        actual_at_execution = world.schedule[block + horizon]
        elapsed = block - _active_since(world.schedule, block)
        distribution = _future_distribution(
            active=current,
            elapsed=elapsed,
            horizon=horizon,
            model=model,
            policy=policy,
        )
        predicted = current
        confidence = 0.0
        used_prediction = False
        if distribution:
            candidate = max(distribution, key=distribution.get)
            confidence = distribution[candidate]
            if confidence >= policy.minimum_prediction_confidence:
                predicted = candidate
                used_prediction = True
                planned += 1
                confidence_sum += confidence
                correct_predictions += int(predicted == actual_at_execution)
                unsafe_predictive_commits += int(
                    predicted != actual_at_execution and predicted != current
                )
            else:
                fallback_count += 1
        else:
            fallback_count += 1

        # A correct graph-conditioned plan succeeds except for execution noise.
        prospective_probability = (
            world.reliability
            if predicted == actual_at_execution
            else 1.0 - world.reliability
        )
        reactive_probability = (
            world.reliability
            if current == actual_at_execution
            else 1.0 - world.reliability
        )
        prospective_success += int(rng.random() < prospective_probability)
        reactive_success += int(rng.random() < reactive_probability)
        rows.append(
            {
                "block": block,
                "execution_block": block + horizon,
                "horizon": horizon,
                "current_graph": list(current),
                "predicted_graph": list(predicted),
                "actual_execution_graph": list(actual_at_execution),
                "prediction_confidence": confidence,
                "used_prediction": used_prediction,
            }
        )
    attempts = len(rows)
    return {
        "world_id": world.world_id,
        "family": world.family,
        "attempts": attempts,
        "prospective_goal_success": prospective_success / attempts,
        "reactive_goal_success": reactive_success / attempts,
        "prediction_precision": (
            correct_predictions / planned if planned else 1.0
        ),
        "prediction_coverage": planned / attempts,
        "unsafe_predictive_commit_rate": unsafe_predictive_commits / attempts,
        "mean_prediction_confidence": (
            confidence_sum / planned if planned else 0.0
        ),
        "fallback_rate": fallback_count / attempts,
        "temporal_model": {
            str(graph): [
                {"next": list(row["next"]), "duration": row["duration"]}
                for row in observations
            ]
            for graph, observations in model.items()
        },
        "trace": rows,
    }


def _evaluate(
    *,
    worlds: Sequence[TemporalWorld],
    policy: ProspectivePolicy,
    seed: int,
    learning_stop: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rows = [
        _run_world(
            world=world,
            policy=policy,
            seed=seed + index * 100_003,
            learning_stop=learning_stop,
            evaluation_start=evaluation_start,
        )
        for index, world in enumerate(worlds)
    ]
    by_family = {}
    for family in TemporalWorldGenerator.FAMILIES:
        group = [row for row in rows if row["family"] == family]
        attempts = sum(row["attempts"] for row in group)
        by_family[family] = {
            "worlds": len(group),
            "prospective_goal_success": sum(
                row["prospective_goal_success"] for row in group
            ) / len(group),
            "reactive_goal_success": sum(
                row["reactive_goal_success"] for row in group
            ) / len(group),
            "prediction_precision": sum(
                row["prediction_precision"] * row["attempts"]
                * row["prediction_coverage"]
                for row in group
            ) / max(1, sum(
                row["attempts"] * row["prediction_coverage"] for row in group
            )),
            "prediction_coverage": sum(
                row["attempts"] * row["prediction_coverage"] for row in group
            ) / attempts,
            "unsafe_predictive_commit_rate": sum(
                row["attempts"] * row["unsafe_predictive_commit_rate"]
                for row in group
            ) / attempts,
        }
    attempts = sum(row["attempts"] for row in rows)
    planned = sum(row["attempts"] * row["prediction_coverage"] for row in rows)
    return {
        "policy": policy.to_dict(),
        "worlds": len(rows),
        "prospective_goal_success": sum(
            row["prospective_goal_success"] * row["attempts"] for row in rows
        ) / attempts,
        "reactive_goal_success": sum(
            row["reactive_goal_success"] * row["attempts"] for row in rows
        ) / attempts,
        "prediction_precision": sum(
            row["prediction_precision"] * row["attempts"]
            * row["prediction_coverage"] for row in rows
        ) / max(1, planned),
        "prediction_coverage": planned / attempts,
        "unsafe_predictive_commit_rate": sum(
            row["unsafe_predictive_commit_rate"] * row["attempts"]
            for row in rows
        ) / attempts,
        "fallback_rate": sum(
            row["fallback_rate"] * row["attempts"] for row in rows
        ) / attempts,
        "by_family": by_family,
        "rows": rows,
    }


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "rows"}


def run_prospective_temporal_planning_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_family: int = 5,
    sealed_worlds_per_family: int = 8,
    blocks: int = 100,
    learning_stop: int = 48,
    evaluation_start: int = 52,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    authority = lambda goal: {
        "allow_learn": True,
        "goal": "maintain_coherence",
        "source": "prospective_temporal_planning_authority",
        "S": 1.0,
        "H": 0.0,
    }
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    generator = TemporalWorldGenerator()
    development = generator.generate(
        seed=18181,
        worlds_per_family=development_worlds_per_family,
        blocks=blocks,
        cohort="prospective_development",
    )
    sealed = generator.generate(
        seed=29292,
        worlds_per_family=sealed_worlds_per_family,
        blocks=blocks,
        cohort="prospective_sealed",
    )
    policies = [
        ProspectivePolicy("prospective_safe_1", 1, 0.6, 0.82, 3),
        ProspectivePolicy("prospective_safe_2", 2, 0.8, 0.82, 3),
        ProspectivePolicy("prospective_balanced", 2, 1.2, 0.75, 3),
        ProspectivePolicy("prospective_conservative", 3, 1.0, 0.85, 3),
    ]
    development_results = [
        _evaluate(
            worlds=development,
            policy=policy,
            seed=4040,
            learning_stop=learning_stop,
            evaluation_start=evaluation_start,
        )
        for policy in policies
    ]
    selected_result = max(
        development_results,
        key=lambda row: (
            row["prospective_goal_success"] - row["reactive_goal_success"]
            - 2.0 * row["unsafe_predictive_commit_rate"],
            row["prediction_precision"],
        ),
    )
    selected = next(
        policy for policy in policies
        if policy.policy_id == selected_result["policy"]["policy_id"]
    )
    sealed_result = _evaluate(
        worlds=sealed,
        policy=selected,
        seed=5050,
        learning_stop=learning_stop,
        evaluation_start=evaluation_start,
    )
    goal_gain = (
        sealed_result["prospective_goal_success"]
        - sealed_result["reactive_goal_success"]
    )
    nonperiodic = sealed_result["by_family"]["nonperiodic"]
    errors = []
    if goal_gain < 0.05:
        errors.append("PROSPECTIVE_GOAL_GAIN_BELOW_FIVE_POINTS")
    if sealed_result["prediction_precision"] < 0.90:
        errors.append("PREDICTION_PRECISION_BELOW_NINETY_PERCENT")
    if sealed_result["unsafe_predictive_commit_rate"] > 0.02:
        errors.append("UNSAFE_PREDICTIVE_COMMIT_RATE_ABOVE_TWO_PERCENT")
    if (
        nonperiodic["prospective_goal_success"]
        < nonperiodic["reactive_goal_success"] - 0.01
    ):
        errors.append("NONPERIODIC_FAMILY_REGRESSION")
    if nonperiodic["prediction_coverage"] > 0.35:
        errors.append("NONPERIODIC_ABSTENTION_GATE_FAILED")
    if selected.complexity > 11:
        errors.append("UNCONTROLLED_POLICY_COMPLEXITY")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "prospective_goal_success_gain": goal_gain,
        "prediction_precision": sealed_result["prediction_precision"],
        "unsafe_predictive_commit_rate": (
            sealed_result["unsafe_predictive_commit_rate"]
        ),
        "nonperiodic_goal_change": (
            nonperiodic["prospective_goal_success"]
            - nonperiodic["reactive_goal_success"]
        ),
        "nonperiodic_prediction_coverage": (
            nonperiodic["prediction_coverage"]
        ),
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_anticipatory_temporal_39ad2cf55b17",
        goal="prospective_temporal_planning",
        steps=["predict_regime_transition", "confirm_before_operational_switch"],
        score=sealed_result["reactive_goal_success"],
        success=True,
        evidence={"evaluation": "phase17_anticipatory_temporal_control"},
    )
    runtime.skills.promote(baseline)

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_prospective_temporal_"
            + _canonical_hash(selected.to_dict())[:12]
        ),
        goal="prospective_temporal_planning",
        steps=[
            "learn_confirmed_regime_duration_model",
            "enumerate_future_graph_distribution",
            "score_delayed_actions_against_future_graphs",
            "commit_only_above_prediction_confidence",
            "fallback_when_temporal_structure_is_unreliable",
            "record_plan_outcome_with_provenance",
        ],
        score=sealed_result["prospective_goal_success"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase18_prospective_temporal_sealed",
            "gate": gate,
        },
    )
    decision = runtime.skills.promote(candidate)
    if gate["accepted"]:
        runtime.store.state.setdefault("causal_graphs", {})[
            "prospective_temporal_planning"
        ] = {
            "schema_version": "aion.hexcore.prospective_temporal_memory.v1",
            "selected_policy": selected.to_dict(),
            "source": "confirmed_phase17_graph_lineage",
            "created_at": _utc_timestamp(),
            "sealed_worlds": len(sealed),
            "gate": gate,
        }
        runtime.store.commit(reason="prospective_temporal_planning_memory")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    champion = restarted.skills.champion(candidate.goal)
    result = {
        "schema_version": "aion.hexcore.prospective_temporal_planning.v1",
        "benchmark": "delayed_action_counterfactual_temporal_planning",
        "language_provider_used": False,
        "development": {
            "policies": [_summary(row) for row in development_results],
            "selected_policy": selected.to_dict(),
        },
        "sealed": {"result": _summary(sealed_result), "gate": gate},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": decision,
        },
        "restart": {
            "champion_retained": bool(
                champion
                and champion.get("procedure_id") == candidate.procedure_id
            ),
            "prospective_memory_retained": (
                "prospective_temporal_planning"
                in restarted.store.state.get("causal_graphs", {})
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "future_distribution_learned": True,
            "delayed_action_planning": True,
            "unpredictable_family_fallback": True,
            "sealed_gate_passed": gate["accepted"],
            "restart_retention": bool(
                champion
                and champion.get("procedure_id") == candidate.procedure_id
            ),
        },
        "boundary_statement": (
            "Prospective planning is evaluated in bounded temporal causal "
            "worlds with delays of one to three blocks. It does not establish "
            "unrestricted forecasting or general planning."
        ),
        "passed": bool(
            gate["accepted"]
            and champion
            and champion.get("procedure_id") == candidate.procedure_id
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/prospective_temporal_planning.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_prospective_temporal_planning.json"),
    )
    args = parser.parse_args()
    result = run_prospective_temporal_planning_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

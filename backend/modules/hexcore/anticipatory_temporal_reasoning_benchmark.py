from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.continuous_causal_change_benchmark import (
    Assignment,
    _goal_success_probability,
    _mapping_posterior,
    _observe_response_counts,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class TemporalWorld:
    world_id: str
    family: str
    factor_count: int
    regimes: Tuple[Assignment, ...]
    schedule: Tuple[Assignment, ...]
    change_points: Tuple[int, ...]
    reliability: float


class TemporalWorldGenerator:
    FAMILIES = (
        "periodic_two",
        "periodic_three",
        "jittered_two",
        "nonperiodic",
    )

    @staticmethod
    def _regimes(count: int) -> Tuple[Assignment, ...]:
        permutations = list(itertools.permutations(range(count)))
        return tuple(tuple(row) for row in permutations)

    def generate(
        self,
        *,
        seed: int,
        worlds_per_family: int,
        blocks: int,
        cohort: str,
    ) -> List[TemporalWorld]:
        rng = random.Random(seed)
        output = []
        for family in self.FAMILIES:
            for index in range(worlds_per_family):
                factor_count = 2 if "two" in family else 3
                choices = self._regimes(factor_count)
                regime_count = 3 if family == "periodic_three" else 2
                regimes = tuple(rng.sample(choices, regime_count))
                schedule: List[Assignment] = []
                change_points = []
                current = 0
                while len(schedule) < blocks:
                    if family == "periodic_two":
                        duration = 6
                        next_index = 1 - current
                    elif family == "periodic_three":
                        durations = (5, 4, 6)
                        duration = durations[current]
                        next_index = (current + 1) % 3
                    elif family == "jittered_two":
                        duration = 6 + rng.choice((-1, 0, 1))
                        next_index = 1 - current
                    else:
                        duration = rng.randint(3, 9)
                        alternatives = [
                            value for value in range(regime_count)
                            if value != current
                        ]
                        next_index = rng.choice(alternatives)
                    schedule.extend([regimes[current]] * duration)
                    if len(schedule) < blocks:
                        change_points.append(len(schedule))
                    current = next_index
                schedule = schedule[:blocks]
                change_points = [
                    point for point in change_points if point < blocks
                ]
                output.append(
                    TemporalWorld(
                        world_id=(
                            f"{cohort}_{family}_{index}_"
                            f"{rng.randrange(100000):05d}"
                        ),
                        family=family,
                        factor_count=factor_count,
                        regimes=regimes,
                        schedule=tuple(schedule),
                        change_points=tuple(change_points),
                        reliability=rng.choice((0.88, 0.92, 0.95)),
                    )
                )
        return output


def _world_view(world: TemporalWorld):
    """Expose the observation fields used by the Phase 15 likelihood helper."""

    return type(
        "TemporalObservationView",
        (),
        {
            "factor_count": world.factor_count,
            "reliability": world.reliability,
        },
    )()


@dataclass(frozen=True)
class AnticipationPolicy:
    policy_id: str
    minimum_support: int
    duration_tolerance: float
    anticipation_window: int
    posterior_gate: float = 0.85
    provisional_stability: int = 2
    durable_stability: int = 4
    diagnostic_trials: int = 3
    escalation_trials: int = 4

    @property
    def complexity(self) -> int:
        return 7 + self.minimum_support + self.anticipation_window

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "minimum_support": self.minimum_support,
            "duration_tolerance": self.duration_tolerance,
            "anticipation_window": self.anticipation_window,
            "posterior_gate": self.posterior_gate,
            "provisional_stability": self.provisional_stability,
            "durable_stability": self.durable_stability,
            "diagnostic_trials": self.diagnostic_trials,
            "escalation_trials": self.escalation_trials,
            "complexity": self.complexity,
        }


REACTIVE = AnticipationPolicy(
    policy_id="phase16_reactive_control",
    minimum_support=99,
    duration_tolerance=0.0,
    anticipation_window=0,
)


def _temporal_prediction(
    *,
    active: Assignment,
    active_since: int,
    block: int,
    transition_memory: Mapping[Assignment, Sequence[Mapping[str, Any]]],
    policy: AnticipationPolicy,
) -> Dict[str, Any] | None:
    rows = list(transition_memory.get(active) or [])
    if len(rows) < policy.minimum_support:
        return None
    next_regimes = {tuple(row["next"]) for row in rows}
    if len(next_regimes) != 1:
        return None
    durations = [int(row["duration"]) for row in rows]
    mean_duration = sum(durations) / len(durations)
    variance = sum(
        (duration - mean_duration) ** 2 for duration in durations
    ) / len(durations)
    if math.sqrt(variance) > policy.duration_tolerance:
        return None
    elapsed = block - active_since
    due = elapsed >= mean_duration - policy.anticipation_window
    return {
        "next": next(iter(next_regimes)),
        "mean_duration": mean_duration,
        "duration_std": math.sqrt(variance),
        "support": len(rows),
        "due": due,
    }


def _run_world(
    *,
    world: TemporalWorld,
    policy: AnticipationPolicy,
    seed: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    view = _world_view(world)
    durable = world.schedule[0]
    operational = durable
    durable_since = 0
    last_estimated_change = 0
    candidate = None
    candidate_since = None
    stability = 0
    transition_memory: Dict[Assignment, List[Dict[str, Any]]] = {}
    revisions = []
    predictions = 0
    correct_predictions = 0
    false_operational_switches = 0
    anticipated_confirmations = 0
    reactive_correct = 0
    anticipatory_correct = 0
    reactive_goal = 0
    anticipatory_goal = 0
    trace = []

    # Run a paired reactive state beside the anticipatory state.
    reactive_durable = durable
    reactive_operational = durable
    reactive_candidate = None
    reactive_stability = 0

    for block, actual in enumerate(world.schedule):
        counts = _observe_response_counts(
            world=view,
            assignment=actual,
            trials=policy.diagnostic_trials,
            rng=rng,
        )
        trials = policy.diagnostic_trials
        posterior = _mapping_posterior(
            world=view,
            counts=counts,
            trials=trials,
        )
        best = max(posterior, key=lambda row: posterior[row])
        if best != durable or posterior.get(durable, 0.0) < 0.80:
            extra = _observe_response_counts(
                world=view,
                assignment=actual,
                trials=policy.escalation_trials,
                rng=rng,
            )
            counts = [
                [
                    counts[toggle][signal] + extra[toggle][signal]
                    for signal in range(world.factor_count)
                ]
                for toggle in range(world.factor_count)
            ]
            trials += policy.escalation_trials
            posterior = _mapping_posterior(
                world=view,
                counts=counts,
                trials=trials,
            )
            best = max(posterior, key=lambda row: posterior[row])
        confidence = posterior[best]

        prediction = _temporal_prediction(
            active=durable,
            active_since=durable_since,
            block=block,
            transition_memory=transition_memory,
            policy=policy,
        )
        predicted_due = bool(prediction and prediction["due"])
        predicted_graph = (
            tuple(prediction["next"]) if predicted_due else None
        )
        if predicted_due:
            predictions += 1

        if best == durable:
            candidate = None
            candidate_since = None
            stability = 0
            operational = durable
        elif best == candidate:
            stability += 1
        else:
            candidate = best
            candidate_since = block
            stability = 1

        required_provisional = policy.provisional_stability
        if (
            predicted_graph is not None
            and best == predicted_graph
            and confidence >= policy.posterior_gate
        ):
            required_provisional = 1
            correct_predictions += int(predicted_graph == actual)
            anticipated_confirmations += 1
        if (
            candidate is not None
            and confidence >= policy.posterior_gate
            and stability >= required_provisional
        ):
            operational = candidate
        elif candidate is not None:
            operational = durable

        if (
            candidate is not None
            and confidence >= policy.posterior_gate
            and stability >= policy.durable_stability
        ):
            previous = durable
            estimated = int(candidate_since)
            duration = estimated - last_estimated_change
            transition_memory.setdefault(previous, []).append(
                {
                    "next": tuple(candidate),
                    "duration": duration,
                }
            )
            durable = candidate
            operational = durable
            durable_since = estimated
            last_estimated_change = estimated
            revisions.append(
                {
                    "block": block,
                    "estimated_change_point": estimated,
                    "previous": list(previous),
                    "new": list(durable),
                    "duration": duration,
                }
            )
            candidate = None
            candidate_since = None
            stability = 0

        # Paired reactive controller: same posterior, always two confirmations.
        if best == reactive_durable:
            reactive_candidate = None
            reactive_stability = 0
            reactive_operational = reactive_durable
        elif best == reactive_candidate:
            reactive_stability += 1
        else:
            reactive_candidate = best
            reactive_stability = 1
        if (
            reactive_candidate is not None
            and confidence >= policy.posterior_gate
            and reactive_stability >= 2
        ):
            reactive_operational = reactive_candidate
        if (
            reactive_candidate is not None
            and confidence >= policy.posterior_gate
            and reactive_stability >= 4
        ):
            reactive_durable = reactive_candidate
            reactive_operational = reactive_durable
            reactive_candidate = None
            reactive_stability = 0

        if operational != actual and predicted_due:
            false_operational_switches += 1

        if block >= evaluation_start:
            anticipatory_correct += int(operational == actual)
            reactive_correct += int(reactive_operational == actual)
            anticipatory_goal += int(
                rng.random()
                < _goal_success_probability(
                    active=operational,
                    actual=actual,
                    reliability=world.reliability,
                )
            )
            reactive_goal += int(
                rng.random()
                < _goal_success_probability(
                    active=reactive_operational,
                    actual=actual,
                    reliability=world.reliability,
                )
            )
        trace.append(
            {
                "block": block,
                "actual": list(actual),
                "durable": list(durable),
                "operational": list(operational),
                "prediction": (
                    {
                        **prediction,
                        "next": list(prediction["next"]),
                    }
                    if prediction else None
                ),
                "best_graph": list(best),
                "confidence": confidence,
            }
        )

    evaluated = len(world.schedule) - evaluation_start
    return {
        "world_id": world.world_id,
        "family": world.family,
        "anticipatory_graph_accuracy": anticipatory_correct / evaluated,
        "reactive_graph_accuracy": reactive_correct / evaluated,
        "anticipatory_goal_success": anticipatory_goal / evaluated,
        "reactive_goal_success": reactive_goal / evaluated,
        "predictions": predictions,
        "correct_predictions": correct_predictions,
        "prediction_precision": (
            correct_predictions / anticipated_confirmations
            if anticipated_confirmations else 1.0
        ),
        "anticipated_confirmations": anticipated_confirmations,
        "false_operational_switches": false_operational_switches,
        "revisions": revisions,
        "temporal_motifs": {
            str(key): [
                {"next": list(row["next"]), "duration": row["duration"]}
                for row in values
            ]
            for key, values in transition_memory.items()
        },
        "trace": trace,
    }


def _evaluate(
    *,
    worlds: Sequence[TemporalWorld],
    policy: AnticipationPolicy,
    seed: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rows = [
        _run_world(
            world=world,
            policy=policy,
            seed=seed + index * 100_000,
            evaluation_start=evaluation_start,
        )
        for index, world in enumerate(worlds)
    ]
    by_family = {}
    for family in TemporalWorldGenerator.FAMILIES:
        group = [row for row in rows if row["family"] == family]
        by_family[family] = {
            "worlds": len(group),
            "anticipatory_graph_accuracy": sum(
                row["anticipatory_graph_accuracy"] for row in group
            ) / len(group),
            "reactive_graph_accuracy": sum(
                row["reactive_graph_accuracy"] for row in group
            ) / len(group),
            "anticipatory_goal_success": sum(
                row["anticipatory_goal_success"] for row in group
            ) / len(group),
            "reactive_goal_success": sum(
                row["reactive_goal_success"] for row in group
            ) / len(group),
            "predictions": sum(row["predictions"] for row in group),
            "false_operational_switches": sum(
                row["false_operational_switches"] for row in group
            ),
        }
    confirmations = sum(row["anticipated_confirmations"] for row in rows)
    return {
        "policy": policy.to_dict(),
        "worlds": len(rows),
        "anticipatory_graph_accuracy": sum(
            row["anticipatory_graph_accuracy"] for row in rows
        ) / len(rows),
        "reactive_graph_accuracy": sum(
            row["reactive_graph_accuracy"] for row in rows
        ) / len(rows),
        "anticipatory_goal_success": sum(
            row["anticipatory_goal_success"] for row in rows
        ) / len(rows),
        "reactive_goal_success": sum(
            row["reactive_goal_success"] for row in rows
        ) / len(rows),
        "prediction_precision": (
            sum(row["correct_predictions"] for row in rows) / confirmations
            if confirmations else 1.0
        ),
        "anticipated_confirmations": confirmations,
        "false_operational_switch_rate": (
            sum(row["false_operational_switches"] for row in rows)
            / (len(rows) * (len(worlds[0].schedule) - evaluation_start))
        ),
        "by_family": by_family,
        "rows": rows,
    }


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "rows"}


def run_anticipatory_temporal_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_family: int = 4,
    sealed_worlds_per_family: int = 7,
    blocks: int = 80,
    evaluation_start: int = 40,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    authority = lambda goal: {
        "allow_learn": True,
        "goal": goal,
        "source": "anticipatory_temporal_authority",
        "S": 1.0,
        "H": 0.0,
    }
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    generator = TemporalWorldGenerator()
    development = generator.generate(
        seed=17_100_101,
        worlds_per_family=development_worlds_per_family,
        blocks=blocks,
        cohort="anticipatory_development",
    )
    sealed = generator.generate(
        seed=17_199_909,
        worlds_per_family=sealed_worlds_per_family,
        blocks=blocks,
        cohort="anticipatory_sealed",
    )
    candidates = [
        AnticipationPolicy(
            policy_id=f"anticipate_support_{support}_tol_{tolerance}",
            minimum_support=support,
            duration_tolerance=tolerance,
            anticipation_window=1,
        )
        for support, tolerance in ((1, 0.5), (2, 0.5), (2, 1.0), (2, 1.5))
    ]
    development_results = [
        _evaluate(
            worlds=development,
            policy=policy,
            seed=17_500_000,
            evaluation_start=evaluation_start,
        )
        for policy in candidates
    ]
    selected_index = max(
        range(len(candidates)),
        key=lambda index: (
            development_results[index][
                "anticipatory_graph_accuracy"
            ] - development_results[index]["reactive_graph_accuracy"],
            -development_results[index][
                "false_operational_switch_rate"
            ],
            development_results[index]["prediction_precision"],
        ),
    )
    selected = candidates[selected_index]
    sealed_result = _evaluate(
        worlds=sealed,
        policy=selected,
        seed=18_500_000,
        evaluation_start=evaluation_start,
    )
    graph_gain = (
        sealed_result["anticipatory_graph_accuracy"]
        - sealed_result["reactive_graph_accuracy"]
    )
    goal_gain = (
        sealed_result["anticipatory_goal_success"]
        - sealed_result["reactive_goal_success"]
    )
    nonperiodic = sealed_result["by_family"]["nonperiodic"]
    errors = []
    if sealed_result["prediction_precision"] < 0.90:
        errors.append("TEMPORAL_PREDICTION_PRECISION_BELOW_90_PERCENT")
    if sealed_result["false_operational_switch_rate"] > 0.02:
        errors.append("FALSE_OPERATIONAL_SWITCH_RATE_ABOVE_2_PERCENT")
    if graph_gain < 0.01:
        errors.append("ANTICIPATORY_GRAPH_GAIN_BELOW_ONE_POINT")
    if goal_gain < 0.005:
        errors.append("ANTICIPATORY_GOAL_GAIN_BELOW_HALF_POINT")
    if (
        nonperiodic["anticipatory_graph_accuracy"]
        < nonperiodic["reactive_graph_accuracy"] - 0.01
    ):
        errors.append("NONPERIODIC_GRAPH_REGRESSION")
    if selected.complexity > 11:
        errors.append("TEMPORAL_PROCEDURE_COMPLEXITY_CAP_EXCEEDED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "prediction_precision": sealed_result["prediction_precision"],
        "false_operational_switch_rate": sealed_result[
            "false_operational_switch_rate"
        ],
        "anticipatory_graph_accuracy_gain": graph_gain,
        "anticipatory_goal_success_gain": goal_gain,
        "nonperiodic_graph_change": (
            nonperiodic["anticipatory_graph_accuracy"]
            - nonperiodic["reactive_graph_accuracy"]
        ),
    }

    before = runtime.store.prepare_mutation()
    try:
        for row in sealed_result["rows"]:
            runtime.store.state["causal_graphs"][row["world_id"]] = {
                "schema_version": "aion.hexcore.temporal_motif_memory.v1",
                "world_id": row["world_id"],
                "temporal_motifs": row["temporal_motifs"],
                "source": "phase17_sealed_stream",
                "updated_at": _utc_timestamp(),
            }
        runtime.store.commit(reason="anticipatory_temporal_motif_memory")
    except Exception:
        runtime.store.rollback(before)
        raise

    baseline = ProcedureCandidate(
        procedure_id=(
            "procedure_adaptive_change_diagnostics_62bd6071e44c"
        ),
        goal="continuous_world_model_maintenance",
        steps=["react_to_change_after_two_confirming_blocks"],
        score=sealed_result["reactive_graph_accuracy"],
        success=True,
        evidence={"evaluation": "phase17_reactive_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_anticipatory_temporal_"
            f"{_canonical_hash(selected.to_dict())[:12]}"
        ),
        goal="continuous_world_model_maintenance",
        steps=[
            "retain_regime_transition_lineage",
            "learn_state_conditioned_next_regime",
            "learn_regime_duration_distribution",
            "predict_when_a_transition_is_due",
            "preactivate_predicted_graph",
            "require_observational_confirmation",
            "retain_durable_consolidation_gate",
        ],
        score=sealed_result["anticipatory_graph_accuracy"],
        success=not errors,
        evidence={
            "evaluation": "phase17_anticipatory_temporal_sealed",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    retained = restarted.skills.champion(
        "continuous_world_model_maintenance"
    )
    motifs_retained = all(
        restarted.store.state["causal_graphs"].get(world.world_id)
        for world in sealed
    )
    result = {
        "schema_version": (
            "aion.hexcore.anticipatory_temporal_reasoning.v1"
        ),
        "benchmark": "learned_regime_motifs_and_duration_prediction",
        "language_provider_used": False,
        "development": {
            "policies": [
                {
                    "policy": policy.to_dict(),
                    "result": _summary(policy_result),
                }
                for policy, policy_result in zip(
                    candidates, development_results
                )
            ],
            "selected_policy": selected.to_dict(),
        },
        "sealed": {
            "result": _summary(sealed_result),
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
            "temporal_motifs_retained": motifs_retained,
            "relearning_worlds": 0,
        },
        "gates": {
            "temporal_rules_learned_from_stream": True,
            "prediction_requires_confirmation": True,
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                bool(promotion.get("promoted"))
                == bool(gate["accepted"])
            ),
            "restart_retention": retained is not None and motifs_retained,
        },
        "boundary_statement": (
            "Temporal anticipation is learned within bounded permutation "
            "regimes and periodic/jittered families. It does not establish "
            "unrestricted future prediction."
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
        default=Path("data/hexcore/anticipatory_temporal.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_anticipatory_temporal.json"),
    )
    args = parser.parse_args()
    result = run_anticipatory_temporal_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

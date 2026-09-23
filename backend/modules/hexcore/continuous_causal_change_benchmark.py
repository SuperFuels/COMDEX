from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Assignment = Tuple[int, ...]


def _normalize(values: Mapping[Assignment, float]) -> Dict[Assignment, float]:
    maximum = max(values.values())
    weights = {
        key: math.exp(value - maximum) for key, value in values.items()
    }
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


@dataclass(frozen=True)
class ContinuousWorld:
    world_id: str
    family: str
    factor_count: int
    baseline: Assignment
    alternative: Assignment
    schedule: Tuple[Assignment, ...]
    structural_change_points: Tuple[int, ...]
    reliability: float
    goal_pattern: Tuple[int, ...]


class ContinuousWorldGenerator:
    FAMILIES = (
        "permanent_change",
        "recurring_change",
        "temporary_disturbance",
        "stochastic_flicker",
    )

    @staticmethod
    def _alternative(count: int, rng: random.Random) -> Assignment:
        identity = tuple(range(count))
        return tuple(
            rng.choice(
                [
                    row for row in itertools.permutations(range(count))
                    if row != identity
                ]
            )
        )

    def generate(
        self,
        *,
        seed: int,
        worlds_per_family: int,
        blocks: int,
        cohort: str,
    ) -> List[ContinuousWorld]:
        rng = random.Random(seed)
        output = []
        for family in self.FAMILIES:
            for index in range(worlds_per_family):
                factor_count = rng.choice((2, 3))
                baseline = tuple(range(factor_count))
                alternative = self._alternative(factor_count, rng)
                schedule = [baseline for _ in range(blocks)]
                change_points: List[int] = []
                if family == "permanent_change":
                    change = rng.randint(6, 10)
                    schedule[change:] = [alternative] * (blocks - change)
                    change_points = [change]
                elif family == "recurring_change":
                    first = rng.randint(5, 7)
                    second = rng.randint(13, 16)
                    schedule[first:second] = [alternative] * (
                        second - first
                    )
                    change_points = [first, second]
                elif family == "temporary_disturbance":
                    first = rng.randint(7, 12)
                    duration = rng.choice((1, 2))
                    schedule[first:first + duration] = [alternative] * duration
                else:
                    candidates = list(range(4, blocks - 2))
                    rng.shuffle(candidates)
                    for block in sorted(candidates[:3]):
                        schedule[block] = alternative
                output.append(
                    ContinuousWorld(
                        world_id=(
                            f"{cohort}_{family}_{index}_"
                            f"{rng.randrange(100000):05d}"
                        ),
                        family=family,
                        factor_count=factor_count,
                        baseline=baseline,
                        alternative=alternative,
                        schedule=tuple(schedule),
                        structural_change_points=tuple(change_points),
                        reliability=rng.choice((0.86, 0.90, 0.94)),
                        goal_pattern=tuple(
                            rng.randint(0, 1)
                            for _ in range(factor_count)
                        ),
                    )
                )
        return output


def _majority_accuracy(reliability: float) -> float:
    return (
        reliability ** 3
        + 3.0 * reliability ** 2 * (1.0 - reliability)
    )


def _observe_response_counts(
    *,
    world: ContinuousWorld,
    assignment: Assignment,
    trials: int,
    rng: random.Random,
) -> List[List[int]]:
    majority_accuracy = _majority_accuracy(world.reliability)
    true_change_probability = (
        majority_accuracy ** 2
        + (1.0 - majority_accuracy) ** 2
    )
    false_change_probability = (
        2.0 * majority_accuracy * (1.0 - majority_accuracy)
    )
    counts = [
        [0 for _ in range(world.factor_count)]
        for _ in range(world.factor_count)
    ]
    for toggle in range(world.factor_count):
        for signal in range(world.factor_count):
            probability = (
                true_change_probability
                if assignment[signal] == toggle
                else false_change_probability
            )
            counts[toggle][signal] = sum(
                rng.random() < probability for _ in range(trials)
            )
    return counts


def _mapping_posterior(
    *,
    world: ContinuousWorld,
    counts: Sequence[Sequence[int]],
    trials: int,
) -> Dict[Assignment, float]:
    majority_accuracy = _majority_accuracy(world.reliability)
    true_probability = (
        majority_accuracy ** 2
        + (1.0 - majority_accuracy) ** 2
    )
    false_probability = 2.0 * majority_accuracy * (
        1.0 - majority_accuracy
    )
    log_scores = {}
    for assignment in itertools.permutations(range(world.factor_count)):
        score = 0.0
        for toggle in range(world.factor_count):
            for signal in range(world.factor_count):
                probability = (
                    true_probability
                    if assignment[signal] == toggle
                    else false_probability
                )
                changed = counts[toggle][signal]
                score += (
                    changed * math.log(max(probability, 1e-9))
                    + (trials - changed)
                    * math.log(max(1.0 - probability, 1e-9))
                )
        log_scores[tuple(assignment)] = score
    return _normalize(log_scores)


def _goal_success_probability(
    *,
    active: Assignment,
    actual: Assignment,
    reliability: float,
) -> float:
    if active == actual:
        return min(0.99, 0.91 + 0.08 * reliability)
    mismatches = sum(
        int(active[index] != actual[index])
        for index in range(len(active))
    )
    return max(0.15, 0.62 - 0.17 * mismatches)


@dataclass(frozen=True)
class ChangePolicy:
    policy_id: str
    posterior_gate: float
    stability_blocks: int
    diagnostic_trials: int
    maximum_revisions: int = 4
    provisional_stability_blocks: int = 2
    escalation_trials: int = 0

    @property
    def complexity(self) -> int:
        return 5 + self.stability_blocks + int(self.diagnostic_trials > 5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "posterior_gate": self.posterior_gate,
            "stability_blocks": self.stability_blocks,
            "diagnostic_trials": self.diagnostic_trials,
            "maximum_revisions": self.maximum_revisions,
            "provisional_stability_blocks": (
                self.provisional_stability_blocks
            ),
            "escalation_trials": self.escalation_trials,
            "complexity": self.complexity,
        }


class ContinuousCausalMaintainer:
    def __init__(
        self,
        runtime: HexCorePersistentLearningRuntime,
    ) -> None:
        self.runtime = runtime

    def run_world(
        self,
        *,
        world: ContinuousWorld,
        policy: ChangePolicy,
        seed: int,
        persist: bool,
    ) -> Dict[str, Any]:
        rng = random.Random(seed)
        active = world.baseline
        operational = active
        candidate: Assignment | None = None
        candidate_since: int | None = None
        candidate_stability = 0
        revisions = []
        trace = []
        goal_successes = 0
        static_goal_successes = 0
        correct_active_blocks = 0
        hypothesis_history = []
        diagnostic_actions = 0

        for block, actual in enumerate(world.schedule):
            counts = _observe_response_counts(
                world=world,
                assignment=actual,
                trials=policy.diagnostic_trials,
                rng=rng,
            )
            trials_used = policy.diagnostic_trials
            posterior = _mapping_posterior(
                world=world,
                counts=counts,
                trials=policy.diagnostic_trials,
            )
            preliminary_best = max(
                posterior, key=lambda assignment: posterior[assignment]
            )
            active_probability = posterior.get(active, 0.0)
            if (
                policy.escalation_trials > 0
                and (
                    preliminary_best != active
                    or active_probability < 0.80
                )
            ):
                extra = _observe_response_counts(
                    world=world,
                    assignment=actual,
                    trials=policy.escalation_trials,
                    rng=rng,
                )
                counts = [
                    [
                        counts[toggle][signal]
                        + extra[toggle][signal]
                        for signal in range(world.factor_count)
                    ]
                    for toggle in range(world.factor_count)
                ]
                trials_used += policy.escalation_trials
                posterior = _mapping_posterior(
                    world=world,
                    counts=counts,
                    trials=trials_used,
                )
            diagnostic_actions += (
                world.factor_count
                * world.factor_count
                * trials_used
                * 6
            )
            ranked = sorted(
                posterior.items(),
                key=lambda row: row[1],
                reverse=True,
            )
            best, confidence = ranked[0]
            hypothesis_history.append(
                {
                    "block": block,
                    "hypotheses": [
                        {
                            "assignment": list(assignment),
                            "probability": probability,
                        }
                        for assignment, probability in ranked
                    ],
                }
            )

            if best == active:
                candidate = None
                candidate_since = None
                candidate_stability = 0
                operational = active
            elif best == candidate:
                candidate_stability += 1
            else:
                candidate = best
                candidate_since = block
                candidate_stability = 1

            provisional = False
            if (
                candidate is not None
                and confidence >= policy.posterior_gate
                and candidate_stability
                >= policy.provisional_stability_blocks
            ):
                operational = candidate
                provisional = True
            else:
                operational = active

            promoted = False
            if (
                candidate is not None
                and confidence >= policy.posterior_gate
                and candidate_stability >= policy.stability_blocks
                and len(revisions) < policy.maximum_revisions
            ):
                previous = active
                active = candidate
                operational = active
                revisions.append(
                    {
                        "revision": len(revisions) + 1,
                        "detected_at": block,
                        "estimated_change_point": candidate_since,
                        "previous_assignment": list(previous),
                        "new_assignment": list(active),
                        "posterior_confidence": confidence,
                    }
                )
                candidate = None
                candidate_since = None
                candidate_stability = 0
                promoted = True

            correct_active_blocks += int(operational == actual)
            adaptive_probability = _goal_success_probability(
                active=operational,
                actual=actual,
                reliability=world.reliability,
            )
            static_probability = _goal_success_probability(
                active=world.baseline,
                actual=actual,
                reliability=world.reliability,
            )
            goal_successes += int(rng.random() < adaptive_probability)
            static_goal_successes += int(rng.random() < static_probability)
            trace.append(
                {
                    "block": block,
                    "actual_assignment": list(actual),
                    "durable_assignment": list(active),
                    "operational_assignment": list(operational),
                    "best_hypothesis": list(best),
                    "posterior_confidence": confidence,
                    "candidate_stability": candidate_stability,
                    "revision_promoted": promoted,
                    "provisional_graph_used": provisional,
                    "diagnostic_trials_used": trials_used,
                }
            )

        expected_changes = list(world.structural_change_points)
        detected_points = [
            row["estimated_change_point"] for row in revisions
        ]
        matched_errors = []
        unused = list(detected_points)
        for expected in expected_changes:
            if not unused:
                continue
            closest = min(unused, key=lambda value: abs(value - expected))
            if abs(closest - expected) <= policy.stability_blocks:
                matched_errors.append(abs(closest - expected))
                unused.remove(closest)
        detected_change_recall = (
            len(matched_errors) / len(expected_changes)
            if expected_changes
            else 1.0
        )
        false_revisions = (
            len(revisions) - len(matched_errors)
            if expected_changes
            else len(revisions)
        )
        result = {
            "world_id": world.world_id,
            "family": world.family,
            "blocks": len(world.schedule),
            "expected_change_points": expected_changes,
            "revisions": revisions,
            "detected_change_recall": detected_change_recall,
            "false_revisions": false_revisions,
            "change_point_mae": (
                sum(matched_errors) / len(matched_errors)
                if matched_errors else None
            ),
            "active_graph_accuracy": (
                correct_active_blocks / len(world.schedule)
            ),
            "adaptive_goal_success": (
                goal_successes / len(world.schedule)
            ),
            "static_goal_success": (
                static_goal_successes / len(world.schedule)
            ),
            "diagnostic_actions": diagnostic_actions,
            "hypothesis_history": hypothesis_history,
            "trace": trace,
        }
        if persist:
            before = self.runtime.store.prepare_mutation()
            try:
                self.runtime.store.state["change_events"].append(
                    {
                        "schema_version": (
                            "aion.hexcore.continuous_change_session.v1"
                        ),
                        "session_id": (
                            f"continuous_{uuid.uuid4().hex[:16]}"
                        ),
                        "world_id": world.world_id,
                        "family": world.family,
                        "revisions": revisions,
                        "active_assignment": list(active),
                        "hypothesis_history_hash": _canonical_hash(
                            hypothesis_history
                        ),
                        "timestamp": _utc_timestamp(),
                    }
                )
                self.runtime.store.state["causal_graphs"][
                    world.world_id
                ] = {
                    "schema_version": (
                        "aion.hexcore.continuous_causal_graph.v1"
                    ),
                    "world_id": world.world_id,
                    "active_assignment": list(active),
                    "baseline_assignment": list(world.baseline),
                    "revision_history": revisions,
                    "status": "active",
                    "updated_at": _utc_timestamp(),
                }
                self.runtime.store.commit(
                    reason=f"continuous_change:{world.world_id}"
                )
            except Exception:
                self.runtime.store.rollback(before)
                raise
        return result


def _evaluate(
    *,
    runtime: HexCorePersistentLearningRuntime,
    worlds: Sequence[ContinuousWorld],
    policy: ChangePolicy,
    seed: int,
    persist: bool,
) -> Dict[str, Any]:
    maintainer = ContinuousCausalMaintainer(runtime)
    rows = [
        maintainer.run_world(
            world=world,
            policy=policy,
            seed=seed + index * 100_000,
            persist=persist,
        )
        for index, world in enumerate(worlds)
    ]
    by_family = {}
    for family in ContinuousWorldGenerator.FAMILIES:
        group = [row for row in rows if row["family"] == family]
        by_family[family] = {
            "worlds": len(group),
            "change_recall": sum(
                row["detected_change_recall"] for row in group
            ) / len(group),
            "false_revisions": sum(
                row["false_revisions"] for row in group
            ),
            "active_graph_accuracy": sum(
                row["active_graph_accuracy"] for row in group
            ) / len(group),
            "adaptive_goal_success": sum(
                row["adaptive_goal_success"] for row in group
            ) / len(group),
            "static_goal_success": sum(
                row["static_goal_success"] for row in group
            ) / len(group),
        }
    change_rows = [
        row for row in rows
        if row["family"] in ("permanent_change", "recurring_change")
    ]
    disturbance_rows = [
        row for row in rows
        if row["family"] in (
            "temporary_disturbance",
            "stochastic_flicker",
        )
    ]
    errors = [
        row["change_point_mae"] for row in change_rows
        if row["change_point_mae"] is not None
    ]
    return {
        "policy": policy.to_dict(),
        "worlds": len(rows),
        "change_recall": sum(
            row["detected_change_recall"] for row in change_rows
        ) / len(change_rows),
        "false_revision_rate": sum(
            row["false_revisions"] for row in disturbance_rows
        ) / len(disturbance_rows),
        "change_point_mae": sum(errors) / len(errors) if errors else None,
        "active_graph_accuracy": sum(
            row["active_graph_accuracy"] for row in rows
        ) / len(rows),
        "adaptive_goal_success": sum(
            row["adaptive_goal_success"] for row in rows
        ) / len(rows),
        "static_goal_success": sum(
            row["static_goal_success"] for row in rows
        ) / len(rows),
        "average_revisions": sum(
            len(row["revisions"]) for row in rows
        ) / len(rows),
        "average_diagnostic_actions": sum(
            row["diagnostic_actions"] for row in rows
        ) / len(rows),
        "by_family": by_family,
        "rows": rows,
    }


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "rows"}


def _score(result: Mapping[str, Any]) -> float:
    return (
        result["change_recall"]
        + result["active_graph_accuracy"]
        + result["adaptive_goal_success"]
        - 0.25 * result["false_revision_rate"]
        - 0.05 * float(result["change_point_mae"] or 0.0)
    )


def run_continuous_change_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_family: int = 5,
    sealed_worlds_per_family: int = 8,
    blocks: int = 24,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    authority = lambda goal: {
        "allow_learn": True,
        "goal": goal,
        "source": "continuous_change_authority",
        "S": 1.0,
        "H": 0.0,
    }
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    generator = ContinuousWorldGenerator()
    development = generator.generate(
        seed=15_300_101,
        worlds_per_family=development_worlds_per_family,
        blocks=blocks,
        cohort="continuous_v3_development",
    )
    sealed = generator.generate(
        seed=15_399_909,
        worlds_per_family=sealed_worlds_per_family,
        blocks=blocks,
        cohort="continuous_v3_sealed",
    )
    policies = [
        ChangePolicy(
            policy_id=f"change_gate_{int(gate * 100)}_stable_{stable}",
            posterior_gate=gate,
            stability_blocks=stable,
            diagnostic_trials=5,
        )
        for gate, stable in (
            (0.85, 4),
            (0.90, 4),
            (0.95, 4),
            (0.90, 5),
        )
    ]
    development_results = [
        _evaluate(
            runtime=runtime,
            worlds=development,
            policy=policy,
            seed=15_500_000,
            persist=False,
        )
        for policy in policies
    ]
    selected_index = max(
        range(len(policies)),
        key=lambda index: (
            _score(development_results[index]),
            -development_results[index]["false_revision_rate"],
            -float(development_results[index]["change_point_mae"] or 99),
        ),
    )
    selected = policies[selected_index]
    sealed_result = _evaluate(
        runtime=runtime,
        worlds=sealed,
        policy=selected,
        seed=16_500_000,
        persist=True,
    )
    goal_gain = (
        sealed_result["adaptive_goal_success"]
        - sealed_result["static_goal_success"]
    )
    errors = []
    if sealed_result["change_recall"] < 0.90:
        errors.append("STRUCTURAL_CHANGE_RECALL_BELOW_90_PERCENT")
    if sealed_result["false_revision_rate"] > 0.10:
        errors.append("FALSE_REVISION_RATE_ABOVE_10_PERCENT")
    if (
        sealed_result["change_point_mae"] is None
        or float(sealed_result["change_point_mae"]) > 1.5
    ):
        errors.append("CHANGE_POINT_MAE_ABOVE_1_5_BLOCKS")
    if sealed_result["active_graph_accuracy"] < 0.90:
        errors.append("ACTIVE_GRAPH_ACCURACY_BELOW_90_PERCENT")
    if goal_gain < 0.10:
        errors.append("ADAPTIVE_GOAL_GAIN_BELOW_10_POINTS")
    if sealed_result["adaptive_goal_success"] < 0.85:
        errors.append("ADAPTIVE_GOAL_SUCCESS_BELOW_85_PERCENT")
    if selected.complexity > 10:
        errors.append("CHANGE_PROCEDURE_COMPLEXITY_CAP_EXCEEDED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "change_recall": sealed_result["change_recall"],
        "false_revision_rate": sealed_result["false_revision_rate"],
        "change_point_mae": sealed_result["change_point_mae"],
        "active_graph_accuracy": sealed_result[
            "active_graph_accuracy"
        ],
        "adaptive_goal_gain": goal_gain,
        "adaptive_goal_success": sealed_result[
            "adaptive_goal_success"
        ],
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_continuous_world_maintenance_"
            f"{_canonical_hash(selected.to_dict())[:12]}"
        ),
        goal="continuous_world_model_maintenance",
        steps=[
            "stream_intervention_response_observations",
            "maintain_competing_graph_posteriors",
            "accumulate_change_candidate_stability",
            "infer_change_point",
            "promote_or_reject_graph_revision",
            "preserve_graph_lineage_and_outcomes",
        ],
        score=_score(sealed_result),
        success=not errors,
        evidence={
            "evaluation": "phase15_continuous_source_disjoint_sealed",
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
    retained_graphs = [
        restarted.store.state["causal_graphs"].get(world.world_id)
        for world in sealed
    ]
    result = {
        "schema_version": (
            "aion.hexcore.continuous_world_model_maintenance.v3"
        ),
        "benchmark": (
            "unsegmented_recurring_and_stochastic_structural_change"
        ),
        "language_provider_used": False,
        "early_late_boundaries_supplied": False,
        "development": {
            "policies": [
                {
                    "policy": policy.to_dict(),
                    "result": _summary(policy_result),
                }
                for policy, policy_result in zip(
                    policies, development_results
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
            "graph_lineages_retained": all(
                graph is not None for graph in retained_graphs
            ),
            "environment_change_sessions": len(
                restarted.store.state["change_events"]
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "unsegmented_stream": True,
            "competing_hypotheses_retained": True,
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                bool(promotion.get("promoted"))
                == bool(gate["accepted"])
            ),
            "restart_retention": (
                retained is not None
                and all(graph is not None for graph in retained_graphs)
            ),
        },
        "boundary_statement": (
            "The stream uses bounded graph permutations and four supplied "
            "change families. This does not establish unrestricted "
            "non-stationary world-model discovery."
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
        default=Path("data/hexcore/continuous_causal_change.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_continuous_causal_change.json"),
    )
    args = parser.parse_args()
    result = run_continuous_change_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

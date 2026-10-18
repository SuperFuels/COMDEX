from __future__ import annotations

import argparse
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.outcome_driven_causal_evolution import (
    InvestigationPolicy,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    GovernedStochasticMultiLatentLearner,
    StochasticLatentGraph,
)


@dataclass(frozen=True)
class DiagnosticWorld:
    world_id: str
    mode: str
    factor_count: int
    supplied_assignment: Tuple[int, ...]
    early_assignment: Tuple[int, ...]
    late_assignment: Tuple[int, ...]
    early_reliabilities: Tuple[float, ...]
    late_reliabilities: Tuple[float, ...]
    toggle_actions: Tuple[str, ...]
    probe_actions: Tuple[str, ...]
    signal_targets: Tuple[str, ...]
    goal_action: str
    goal_pattern: Tuple[int, ...]


class DiagnosticCausalEnvironment:
    def __init__(
        self,
        *,
        world: DiagnosticWorld,
        seed: int,
        epoch: str,
        initial_factors: Tuple[int, ...] | None = None,
    ) -> None:
        self.world = world
        self.random = random.Random(seed)
        self.epoch = epoch
        self.factors = (
            tuple(initial_factors)
            if initial_factors is not None
            else tuple(
                self.random.randint(0, 1)
                for _ in range(world.factor_count)
            )
        )
        self.visible = {
            **{signal: 0 for signal in world.signal_targets},
            "opened": 0,
        }

    @property
    def assignment(self) -> Tuple[int, ...]:
        return (
            self.world.early_assignment
            if self.epoch == "early"
            else self.world.late_assignment
        )

    @property
    def reliabilities(self) -> Tuple[float, ...]:
        return (
            self.world.early_reliabilities
            if self.epoch == "early"
            else self.world.late_reliabilities
        )

    def step(self, action: str) -> Dict[str, Any]:
        before = dict(self.visible)
        factors = list(self.factors)
        if action in self.world.toggle_actions:
            factor = self.world.toggle_actions.index(action)
            factors[factor] ^= 1
        elif action in self.world.probe_actions:
            signal = self.world.probe_actions.index(action)
            factor = self.assignment[signal]
            correct = (
                self.random.random() < self.reliabilities[signal]
            )
            value = factors[factor] if correct else 1 - factors[factor]
            self.visible[self.world.signal_targets[signal]] = value
        elif action == self.world.goal_action:
            should_open = all(
                required == -1 or factors[index] == required
                for index, required in enumerate(
                    self.world.goal_pattern
                )
            )
            follows = self.random.random() < 0.97
            self.visible["opened"] = int(
                should_open if follows else not should_open
            )
        self.factors = tuple(factors)
        return {
            "state": before,
            "next_state": dict(self.visible),
            "evidence": {
                "world_id": self.world.world_id,
                "epoch": self.epoch,
                "action": action,
                "hidden_factors_visible": False,
            },
        }

    def audit_hidden_factors(self) -> Tuple[int, ...]:
        return tuple(self.factors)


def _non_identity_permutation(
    count: int,
    rng: random.Random,
) -> Tuple[int, ...]:
    identity = tuple(range(count))
    choices = [
        row for row in itertools.permutations(range(count))
        if row != identity
    ]
    return tuple(rng.choice(choices))


def _worlds(seed: int, count: int, cohort: str) -> List[DiagnosticWorld]:
    rng = random.Random(seed)
    modes = ("sensor_error", "graph_error", "world_change")
    output = []
    for index in range(count):
        mode = modes[index % len(modes)]
        factor_count = rng.choice((2, 3))
        identity = tuple(range(factor_count))
        changed = _non_identity_permutation(factor_count, rng)
        if mode == "sensor_error":
            early = late = identity
            noisy = rng.randrange(factor_count)
            reliabilities = tuple(
                0.62 if signal == noisy else 0.92
                for signal in range(factor_count)
            )
            early_reliabilities = late_reliabilities = reliabilities
        elif mode == "graph_error":
            early = late = changed
            early_reliabilities = late_reliabilities = tuple(
                0.94 for _ in range(factor_count)
            )
        else:
            early = identity
            late = changed
            early_reliabilities = late_reliabilities = tuple(
                0.94 for _ in range(factor_count)
            )
        prefix = f"{cohort}_{index}_{rng.randrange(100000):05d}"
        output.append(
            DiagnosticWorld(
                world_id=prefix,
                mode=mode,
                factor_count=factor_count,
                supplied_assignment=identity,
                early_assignment=early,
                late_assignment=late,
                early_reliabilities=early_reliabilities,
                late_reliabilities=late_reliabilities,
                toggle_actions=tuple(
                    f"{prefix}_intervene_{factor}"
                    for factor in range(factor_count)
                ),
                probe_actions=tuple(
                    f"{prefix}_observe_{signal}"
                    for signal in range(factor_count)
                ),
                signal_targets=tuple(
                    f"{prefix}_signal_{signal}"
                    for signal in range(factor_count)
                ),
                goal_action=f"{prefix}_commit",
                goal_pattern=tuple(
                    rng.randint(0, 1)
                    for _ in range(factor_count)
                ),
            )
        )
    return output


def _majority_probe(
    environment: DiagnosticCausalEnvironment,
    action: str,
    signal: str,
    repeats: int,
) -> Tuple[int, float]:
    values = []
    for _ in range(repeats):
        observation = environment.step(action)
        values.append(int(observation["next_state"][signal]))
    ones = sum(values)
    majority = int(ones >= len(values) / 2)
    disagreement = min(ones, len(values) - ones) / len(values)
    return majority, disagreement


def _epoch_signature(
    *,
    world: DiagnosticWorld,
    epoch: str,
    seed: int,
    trials: int,
    repeats: int,
) -> Dict[str, Any]:
    response = [
        [0.0 for _ in range(world.factor_count)]
        for _ in range(world.factor_count)
    ]
    disagreement = [0.0 for _ in range(world.factor_count)]
    for trial in range(trials):
        initial = tuple(
            random.Random(seed + trial * 101 + factor).randint(0, 1)
            for factor in range(world.factor_count)
        )
        for toggle in range(world.factor_count):
            environment = DiagnosticCausalEnvironment(
                world=world,
                seed=seed + trial * 10_000 + toggle,
                epoch=epoch,
                initial_factors=initial,
            )
            before = []
            after = []
            for signal in range(world.factor_count):
                value, noise = _majority_probe(
                    environment,
                    world.probe_actions[signal],
                    world.signal_targets[signal],
                    repeats,
                )
                before.append(value)
                disagreement[signal] += noise
            environment.step(world.toggle_actions[toggle])
            for signal in range(world.factor_count):
                value, noise = _majority_probe(
                    environment,
                    world.probe_actions[signal],
                    world.signal_targets[signal],
                    repeats,
                )
                after.append(value)
                disagreement[signal] += noise
            for signal in range(world.factor_count):
                response[toggle][signal] += int(
                    before[signal] != after[signal]
                )
    normalized = [
        [value / trials for value in row] for row in response
    ]
    assignment = tuple(
        max(
            range(world.factor_count),
            key=lambda toggle: normalized[toggle][signal],
        )
        for signal in range(world.factor_count)
    )
    margins = []
    for signal in range(world.factor_count):
        values = sorted(
            (
                normalized[toggle][signal]
                for toggle in range(world.factor_count)
            ),
            reverse=True,
        )
        margins.append(values[0] - values[1])
    return {
        "assignment": assignment,
        "response_matrix": normalized,
        "minimum_mapping_margin": min(margins),
        "mean_repeat_disagreement": (
            sum(disagreement)
            / (world.factor_count * trials * 2)
        ),
    }


def _diagnose(
    *,
    world: DiagnosticWorld,
    early: Mapping[str, Any],
    late: Mapping[str, Any],
    disagreement_gate: float,
    mapping_margin_gate: float,
) -> Dict[str, Any]:
    supplied = world.supplied_assignment
    early_assignment = tuple(early["assignment"])
    late_assignment = tuple(late["assignment"])
    mapping_confident = (
        early["minimum_mapping_margin"] >= mapping_margin_gate
        and late["minimum_mapping_margin"] >= mapping_margin_gate
    )
    maximum_disagreement = max(
        early["mean_repeat_disagreement"],
        late["mean_repeat_disagreement"],
    )
    stable_structural_mismatch = (
        mapping_confident
        and early_assignment == late_assignment
        and early_assignment != supplied
    )
    temporal_structural_mismatch = (
        mapping_confident
        and early_assignment == supplied
        and late_assignment != early_assignment
    )
    if (
        maximum_disagreement >= disagreement_gate
        and not stable_structural_mismatch
        and not temporal_structural_mismatch
    ):
        diagnosis = "sensor_error"
        specialist = "conservative_evidence"
    elif (
        mapping_confident
        and early_assignment == supplied
        and late_assignment != early_assignment
    ):
        diagnosis = "world_change"
        specialist = "change_detection_and_rediscovery"
    elif (
        mapping_confident
        and early_assignment != supplied
        and late_assignment == early_assignment
    ):
        diagnosis = "graph_error"
        specialist = "graph_construction_and_revision"
    else:
        diagnosis = "abstain"
        specialist = "phase9_fallback"
    return {
        "diagnosis": diagnosis,
        "specialist": specialist,
        "early_assignment": early_assignment,
        "late_assignment": late_assignment,
        "mapping_confident": mapping_confident,
        "maximum_repeat_disagreement": maximum_disagreement,
    }


def _planning_graph(
    world: DiagnosticWorld,
    assignment: Sequence[int],
) -> StochasticLatentGraph:
    return StochasticLatentGraph(
        graph_id=(
            f"diagnosed_graph_{_canonical_hash([world.world_id, assignment])[:16]}"
        ),
        factor_count=world.factor_count,
        toggle_actions=world.toggle_actions,
        signal_targets=world.signal_targets,
        signal_factor_assignments=tuple(int(value) for value in assignment),
        probe_actions=world.probe_actions,
        goal_action=world.goal_action,
        goal_pattern=world.goal_pattern,
        probe_reliability=0.80,
        goal_reliability=0.97,
    )


POLICY_BANK = InvestigationPolicy(
    policy_id="phase13_governed_policy_bank",
    confidence_gate=0.95,
    maximum_experiments=10,
    cost_weight=0.05,
    mutation="promoted_phase13_policy_bank",
    goal_relevance_only=True,
    uncertain_factor_only=True,
    goal_retries=1,
    online_reliability_learning=True,
    reliability_prior=0.80,
    value_of_information_ratio=True,
    three_factor_reserve=True,
    policy_bank_enabled=True,
    router_low_reliability_threshold=0.72,
    router_high_reliability_threshold=0.84,
)


def _audit_planning(
    *,
    runtime: HexCorePersistentLearningRuntime,
    world: DiagnosticWorld,
    assignment: Sequence[int],
    episodes: int,
    seed: int,
    specialist: str = "phase13_policy_bank",
) -> float:
    learner = GovernedStochasticMultiLatentLearner(runtime.store)
    graph = _planning_graph(world, assignment)
    successes = 0
    for episode in range(episodes):
        environment = DiagnosticCausalEnvironment(
            world=world,
            seed=seed + episode,
            epoch="late",
        )
        sensor_specialist = specialist == "conservative_evidence"

        def routed_runner(action: str) -> Mapping[str, Any]:
            if (
                not sensor_specialist
                or action not in world.probe_actions
            ):
                return environment.step(action)
            signal_index = world.probe_actions.index(action)
            signal = world.signal_targets[signal_index]
            observations = [
                environment.step(action) for _ in range(3)
            ]
            values = [
                int(row["next_state"][signal])
                for row in observations
            ]
            final = dict(observations[-1])
            next_state = dict(final["next_state"])
            next_state[signal] = int(sum(values) >= 2)
            final["next_state"] = next_state
            final["evidence"] = {
                **dict(final.get("evidence") or {}),
                "majority_observation": True,
                "physical_readings": 3,
            }
            return final

        result = learner.investigate_and_plan(
            graph=graph,
            runner=routed_runner,
            initial_visible=environment.visible,
            action_costs={
                action: (
                    0.45 if sensor_specialist else 0.15
                )
                for action in world.probe_actions
            },
            confidence_gate=(
                0.97 if sensor_specialist
                else POLICY_BANK.confidence_gate
            ),
            maximum_experiments=(
                6 if sensor_specialist
                else POLICY_BANK.maximum_experiments
            ),
            cost_weight=POLICY_BANK.cost_weight,
            goal_relevance_only=True,
            uncertain_factor_only=True,
            goal_retries=1,
            online_reliability_learning=True,
            reliability_prior=0.80,
            value_of_information_ratio=True,
            three_factor_reserve=True,
            minimum_voi_per_cost=(
                0.10 if sensor_specialist else 0.0
            ),
            policy_bank_enabled=not sensor_specialist,
            router_low_reliability_threshold=0.72,
            router_high_reliability_threshold=0.84,
        )
        actual = environment.audit_hidden_factors()
        goal_correct = all(
            actual[index] == required
            for index, required in enumerate(world.goal_pattern)
        )
        successes += int(result["goal_success"] and goal_correct)
    return successes / episodes


def _evaluate(
    *,
    runtime: HexCorePersistentLearningRuntime,
    worlds: Sequence[DiagnosticWorld],
    disagreement_gate: float,
    mapping_margin_gate: float,
    trials: int,
    planning_episodes: int,
    seed: int,
) -> Dict[str, Any]:
    rows = []
    for index, world in enumerate(worlds):
        early = _epoch_signature(
            world=world,
            epoch="early",
            seed=seed + index * 100_000,
            trials=trials,
            repeats=3,
        )
        late = _epoch_signature(
            world=world,
            epoch="late",
            seed=seed + index * 100_000 + 50_000,
            trials=trials,
            repeats=3,
        )
        diagnosis = _diagnose(
            world=world,
            early=early,
            late=late,
            disagreement_gate=disagreement_gate,
            mapping_margin_gate=mapping_margin_gate,
        )
        repaired_assignment = (
            tuple(diagnosis["late_assignment"])
            if diagnosis["diagnosis"] in ("graph_error", "world_change")
            else world.supplied_assignment
        )
        repaired = repaired_assignment == world.late_assignment
        control_goal = _audit_planning(
            runtime=runtime,
            world=world,
            assignment=world.supplied_assignment,
            episodes=planning_episodes,
            seed=seed + index * 100_000 + 70_000,
            specialist="phase13_policy_bank",
        )
        repaired_goal = _audit_planning(
            runtime=runtime,
            world=world,
            assignment=repaired_assignment,
            episodes=planning_episodes,
            seed=seed + index * 100_000 + 70_000,
            specialist=diagnosis["specialist"],
        )
        rows.append(
            {
                "world_id": world.world_id,
                "true_mode": world.mode,
                **diagnosis,
                "diagnosis_correct": diagnosis["diagnosis"] == world.mode,
                "graph_repaired": repaired,
                "control_goal_success": control_goal,
                "repaired_goal_success": repaired_goal,
            }
        )
    by_mode = {}
    for mode in ("sensor_error", "graph_error", "world_change"):
        group = [row for row in rows if row["true_mode"] == mode]
        by_mode[mode] = {
            "worlds": len(group),
            "diagnosis_accuracy": sum(
                row["diagnosis_correct"] for row in group
            ) / len(group),
            "graph_repair_accuracy": sum(
                row["graph_repaired"] for row in group
            ) / len(group),
            "control_goal_success": sum(
                row["control_goal_success"] for row in group
            ) / len(group),
            "repaired_goal_success": sum(
                row["repaired_goal_success"] for row in group
            ) / len(group),
        }
    return {
        "worlds": len(rows),
        "diagnosis_accuracy": sum(
            row["diagnosis_correct"] for row in rows
        ) / len(rows),
        "graph_repair_accuracy": sum(
            row["graph_repaired"] for row in rows
        ) / len(rows),
        "control_goal_success": sum(
            row["control_goal_success"] for row in rows
        ) / len(rows),
        "repaired_goal_success": sum(
            row["repaired_goal_success"] for row in rows
        ) / len(rows),
        "worst_mode_diagnosis_accuracy": min(
            row["diagnosis_accuracy"] for row in by_mode.values()
        ),
        "worst_mode_repaired_goal_success": min(
            row["repaired_goal_success"] for row in by_mode.values()
        ),
        "by_mode": by_mode,
        "rows": rows,
    }


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "rows"}


def run_causal_failure_diagnosis_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 18,
    sealed_worlds: int = 30,
    diagnostic_trials: int = 12,
    planning_episodes: int = 30,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=lambda goal: {
            "allow_learn": True,
            "goal": goal,
            "source": "causal_failure_diagnosis_authority",
            "S": 1.0,
            "H": 0.0,
        },
    )
    development = _worlds(
        14_300_101, development_worlds, "diagnosis_v3_development"
    )
    sealed = _worlds(
        14_399_909, sealed_worlds, "diagnosis_v3_sealed"
    )
    candidates = [
        {
            "disagreement_gate": disagreement,
            "mapping_margin_gate": margin,
        }
        for disagreement, margin in (
            (0.05, 0.25),
            (0.08, 0.30),
            (0.12, 0.35),
        )
    ]
    development_results = [
        _evaluate(
            runtime=runtime,
            worlds=development,
            trials=diagnostic_trials,
            planning_episodes=planning_episodes,
            seed=14_500_000,
            **candidate,
        )
        for candidate in candidates
    ]
    selected_index = max(
        range(len(candidates)),
        key=lambda index: (
            development_results[index]["worst_mode_diagnosis_accuracy"],
            development_results[index]["diagnosis_accuracy"],
            development_results[index]["repaired_goal_success"],
        ),
    )
    selected = candidates[selected_index]
    sealed_result = _evaluate(
        runtime=runtime,
        worlds=sealed,
        trials=diagnostic_trials,
        planning_episodes=planning_episodes,
        seed=15_500_000,
        **selected,
    )
    goal_gain = (
        sealed_result["repaired_goal_success"]
        - sealed_result["control_goal_success"]
    )
    errors = []
    if sealed_result["diagnosis_accuracy"] < 0.85:
        errors.append("DIAGNOSIS_ACCURACY_BELOW_85_PERCENT")
    if sealed_result["worst_mode_diagnosis_accuracy"] < 0.75:
        errors.append("WORST_MODE_DIAGNOSIS_BELOW_75_PERCENT")
    if sealed_result["graph_repair_accuracy"] < 0.85:
        errors.append("GRAPH_REPAIR_ACCURACY_BELOW_85_PERCENT")
    if goal_gain < 0.05:
        errors.append("REPAIRED_GOAL_GAIN_BELOW_5_POINTS")
    if sealed_result["worst_mode_repaired_goal_success"] < 0.75:
        errors.append("WORST_MODE_REPAIRED_GOAL_BELOW_75_PERCENT")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "diagnosis_accuracy": sealed_result["diagnosis_accuracy"],
        "worst_mode_diagnosis_accuracy": (
            sealed_result["worst_mode_diagnosis_accuracy"]
        ),
        "graph_repair_accuracy": sealed_result[
            "graph_repair_accuracy"
        ],
        "repaired_goal_gain": goal_gain,
        "worst_mode_repaired_goal_success": (
            sealed_result["worst_mode_repaired_goal_success"]
        ),
    }
    before = runtime.store.prepare_mutation()
    try:
        for row in sealed_result["rows"]:
            queue = (
                row["diagnosis"]
                if row["diagnosis"] != "abstain"
                else "diagnostic_abstention"
            )
            runtime.store.state["failure_queues"].setdefault(
                queue, []
            ).append(
                {
                    "schema_version": (
                        "aion.hexcore.causal_failure_diagnosis.v1"
                    ),
                    "world_id": row["world_id"],
                    "true_mode": row["true_mode"],
                    "diagnosis": row["diagnosis"],
                    "correct": row["diagnosis_correct"],
                    "timestamp": _utc_timestamp(),
                }
            )
        runtime.store.commit(reason="causal_failure_diagnosis_sealed")
    except Exception:
        runtime.store.rollback(before)
        raise
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_causal_failure_diagnosis_"
            f"{_canonical_hash(selected)[:12]}"
        ),
        goal="causal_failure_diagnosis",
        steps=[
            "measure_repeat_instability",
            "infer_early_intervention_response_graph",
            "infer_late_intervention_response_graph",
            "classify_sensor_graph_or_world_change",
            "route_to_bounded_repair_specialist",
            "validate_repair_by_verified_goal_outcome",
        ],
        score=(
            sealed_result["diagnosis_accuracy"]
            + sealed_result["repaired_goal_success"]
        ),
        success=not errors,
        evidence={
            "evaluation": "phase14_source_disjoint_sealed",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=lambda goal: {
            "allow_learn": True,
            "goal": goal,
            "source": "causal_failure_diagnosis_authority",
            "S": 1.0,
            "H": 0.0,
        },
    )
    retained = restarted.skills.champion("causal_failure_diagnosis")
    result = {
        "schema_version": "aion.hexcore.causal_failure_diagnosis.v3",
        "benchmark": "sensor_graph_and_world_change_diagnosis",
        "language_provider_used": False,
        "development": {
            "candidates": [
                {
                    "configuration": candidate_config,
                    "result": _summary(candidate_result),
                }
                for candidate_config, candidate_result in zip(
                    candidates, development_results
                )
            ],
            "selected_configuration": selected,
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
            "failure_queue_records": sum(
                len(rows)
                for rows in restarted.store.state[
                    "failure_queues"
                ].values()
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                bool(promotion.get("promoted"))
                == bool(gate["accepted"])
            ),
            "separate_failure_queues": all(
                key in restarted.store.state["failure_queues"]
                for key in (
                    "sensor_error",
                    "graph_error",
                    "world_change",
                )
            ),
            "restart_retention": retained is not None,
        },
        "boundary_statement": (
            "The diagnostic grammar contains three supplied failure classes "
            "and bounded graph permutations. This is not unrestricted fault "
            "discovery or autonomous source-code repair."
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
        default=Path("data/hexcore/causal_failure_diagnosis.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_causal_failure_diagnosis.json"),
    )
    args = parser.parse_args()
    result = run_causal_failure_diagnosis_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

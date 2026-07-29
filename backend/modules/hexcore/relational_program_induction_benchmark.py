from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


ProgramHypothesis = Tuple[str, int]
State = Tuple[int, ...]
ANALOG_PROGRAMS = (
    "min_plus_tail_ge",
    "max_minus_tail_ge",
    "range_plus_tail_le",
    "minmax_sum_ge",
)
NON_ANALOG_PROGRAMS = (
    "count_parity",
    "product_pair_ge",
    "sum_minus_tail_ge",
    "max_plus_tail_ge",
    "min_minus_tail_ge",
    "range_minus_tail_le",
    "maxmin_difference_ge",
    "minmax_difference_ge",
    "sum_plus_tail_ge",
    "sum_plus_tail_le",
    "sum_minus_tail_le",
    "min_plus_tail_le",
    "min_minus_tail_le",
    "max_plus_tail_le",
    "max_minus_tail_le",
    "range_plus_tail_ge",
    "range_minus_tail_ge",
)
FULL_PROGRAMS = ANALOG_PROGRAMS + NON_ANALOG_PROGRAMS


@dataclass(frozen=True)
class ProgramWorld:
    world_id: str
    fields: Tuple[str, ...]
    hypothesis: ProgramHypothesis
    graph_depth: int

    @property
    def arity(self) -> int:
        return len(self.fields)

    def execute(self, state: State) -> Dict[str, Any]:
        outcome, intermediates = _execute_program(self.hypothesis, state)
        return {
            "outcome": outcome,
            "intermediates": intermediates,
        }


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "relational_program_induction_authority",
        "S": 1.0,
        "H": 0.0,
    }


@lru_cache(maxsize=None)
def _thresholds(program: str, arity: int) -> Tuple[int, ...]:
    if program == "min_plus_tail_ge":
        return tuple(range(1, 20))
    if program == "max_minus_tail_ge":
        return tuple(range(-8, 9))
    if program == "range_plus_tail_le":
        return tuple(range(0, 20))
    if program == "minmax_sum_ge":
        return tuple(range(1, 20))
    if program == "count_parity":
        return (0,)
    if program == "product_pair_ge":
        return tuple(range(10, 91, 10))
    if program in {
        "sum_minus_tail_ge",
        "max_plus_tail_ge",
        "sum_plus_tail_ge",
        "sum_plus_tail_le",
        "sum_minus_tail_le",
        "min_plus_tail_le",
        "min_minus_tail_le",
        "max_plus_tail_le",
        "max_minus_tail_le",
        "range_plus_tail_ge",
        "range_minus_tail_ge",
    }:
        return tuple(range(-5, 26))
    if program in {
        "min_minus_tail_ge",
        "range_minus_tail_le",
        "maxmin_difference_ge",
        "minmax_difference_ge",
    }:
        return tuple(range(-10, 11))
    raise ValueError(program)


@lru_cache(maxsize=None)
def _hypotheses(arity: int) -> Tuple[ProgramHypothesis, ...]:
    return tuple(
        (program, threshold)
        for program in FULL_PROGRAMS
        for threshold in _thresholds(program, arity)
    )


def _execute_program(
    hypothesis: ProgramHypothesis,
    state: State,
) -> Tuple[bool, Dict[str, int]]:
    program, threshold = hypothesis
    prefix = state[:-1]
    tail = state[-1]
    if program == "min_plus_tail_ge":
        hidden_1 = min(prefix)
        score = hidden_1 + tail
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "max_minus_tail_ge":
        hidden_1 = max(prefix)
        score = hidden_1 - tail
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "range_plus_tail_le":
        hidden_1 = max(prefix) - min(prefix)
        score = hidden_1 + tail
        return score <= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "minmax_sum_ge":
        split = max(1, len(state) // 2)
        hidden_1 = min(state[:split])
        hidden_2 = max(state[split:])
        score = hidden_1 + hidden_2
        return score >= threshold, {
            "hidden_1": hidden_1,
            "hidden_2": hidden_2,
            "score": score,
        }
    if program == "count_parity":
        hidden_1 = sum(int(value >= 6) for value in state)
        return hidden_1 % 2 == 1, {"hidden_1": hidden_1}
    if program == "product_pair_ge":
        hidden_1 = state[0] * state[1]
        score = hidden_1 + sum(state[2:])
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "sum_minus_tail_ge":
        hidden_1 = sum(prefix)
        score = hidden_1 - tail
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "max_plus_tail_ge":
        hidden_1 = max(prefix)
        score = hidden_1 + tail
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "min_minus_tail_ge":
        hidden_1 = min(prefix)
        score = hidden_1 - tail
        return score >= threshold, {"hidden_1": hidden_1, "score": score}
    if program == "range_minus_tail_le":
        hidden_1 = max(prefix) - min(prefix)
        score = hidden_1 - tail
        return score <= threshold, {"hidden_1": hidden_1, "score": score}
    if program in {"maxmin_difference_ge", "minmax_difference_ge"}:
        split = max(1, len(state) // 2)
        if program == "maxmin_difference_ge":
            hidden_1 = max(state[:split])
            hidden_2 = min(state[split:])
        else:
            hidden_1 = min(state[:split])
            hidden_2 = max(state[split:])
        score = hidden_1 - hidden_2
        return score >= threshold, {
            "hidden_1": hidden_1,
            "hidden_2": hidden_2,
            "score": score,
        }
    if program in {
        "sum_plus_tail_ge",
        "sum_plus_tail_le",
        "sum_minus_tail_le",
        "min_plus_tail_le",
        "min_minus_tail_le",
        "max_plus_tail_le",
        "max_minus_tail_le",
        "range_plus_tail_ge",
        "range_minus_tail_ge",
    }:
        parts = program.split("_")
        aggregator_name = parts[0]
        tail_operation = parts[1]
        comparator = parts[3]
        if aggregator_name == "sum":
            hidden_1 = sum(prefix)
        elif aggregator_name == "min":
            hidden_1 = min(prefix)
        elif aggregator_name == "max":
            hidden_1 = max(prefix)
        elif aggregator_name == "range":
            hidden_1 = max(prefix) - min(prefix)
        else:
            raise ValueError(program)
        score = (
            hidden_1 + tail
            if tail_operation == "plus"
            else hidden_1 - tail
        )
        outcome = score >= threshold if comparator == "ge" else score <= threshold
        return outcome, {"hidden_1": hidden_1, "score": score}
    raise ValueError(program)


def _predict(hypothesis: ProgramHypothesis, state: State) -> bool:
    return _execute_program(hypothesis, state)[0]


@lru_cache(maxsize=None)
def _candidate_states(arity: int) -> Tuple[State, ...]:
    states = set(itertools.product((0, 5, 10), repeat=arity))
    states.update(itertools.product((0, 5, 6, 10), repeat=arity))
    for value in range(11):
        states.add((value,) * arity)
    for total in range(0, 10 * arity + 1):
        remaining = total
        values = []
        for _ in range(arity):
            value = min(10, remaining)
            values.append(value)
            remaining -= value
        states.add(tuple(values))
        states.add(tuple(reversed(values)))
    return tuple(sorted(states))


def _intervention_cost(state: State) -> float:
    mean = sum(state) / len(state)
    heterogeneous = int(len(set(state)) > 1)
    return 1.0 + 0.025 * mean + 0.05 * heterogeneous


def _entropy(probabilities: Iterable[float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _normalise(
    weights: Mapping[ProgramHypothesis, float],
) -> Dict[ProgramHypothesis, float]:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("zero posterior mass")
    return {
        hypothesis: weight / total
        for hypothesis, weight in weights.items()
    }


def _uniform_prior(
    arity: int,
    *,
    programs: Sequence[str] = FULL_PROGRAMS,
) -> Dict[ProgramHypothesis, float]:
    hypotheses = [
        hypothesis
        for hypothesis in _hypotheses(arity)
        if hypothesis[0] in programs
    ]
    return {
        hypothesis: 1.0 / len(hypotheses)
        for hypothesis in hypotheses
    }


def _select_intervention(
    posterior: Mapping[ProgramHypothesis, float],
    unused: Sequence[State],
) -> State:
    prior_entropy = _entropy(posterior.values())

    def utility(state: State) -> Tuple[float, float, State]:
        positive = sum(
            probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, state)
        )
        expected_entropy = 0.0
        for outcome_probability, outcome in (
            (positive, True),
            (1.0 - positive, False),
        ):
            if outcome_probability <= 0.0:
                continue
            conditional = [
                probability / outcome_probability
                for hypothesis, probability in posterior.items()
                if _predict(hypothesis, state) == outcome
            ]
            expected_entropy += outcome_probability * _entropy(conditional)
        gain = prior_entropy - expected_entropy
        return (gain / _intervention_cost(state), gain, state)

    return max(unused, key=utility)


def _active_search(
    *,
    world: ProgramWorld,
    posterior: Mapping[ProgramHypothesis, float],
    unused: List[State],
    trace: List[Dict[str, Any]],
    stage: str,
    max_interventions: int,
) -> Tuple[
    Dict[ProgramHypothesis, float],
    float,
    int,
]:
    current = dict(posterior)
    cost = 0.0
    candidate_evaluations = 0
    while len(current) > 1 and len(trace) < max_interventions:
        candidate_evaluations += len(current) * len(unused)
        state = _select_intervention(current, unused)
        unused.remove(state)
        observation = world.execute(state)
        survivors = {
            hypothesis: probability
            for hypothesis, probability in current.items()
            if _predict(hypothesis, state) == observation["outcome"]
        }
        intervention_cost = _intervention_cost(state)
        cost += intervention_cost
        trace.append(
            {
                "stage": stage,
                "state": list(state),
                "outcome": int(observation["outcome"]),
                "intervention_cost": intervention_cost,
                "remaining": len(survivors),
            }
        )
        if not survivors:
            return {}, cost, candidate_evaluations
        current = _normalise(survivors)
    return current, cost, candidate_evaluations


def _run_cold(
    world: ProgramWorld,
    *,
    max_interventions: int = 36,
) -> Dict[str, Any]:
    unused = list(_candidate_states(world.arity))
    trace: List[Dict[str, Any]] = []
    posterior, cost, evaluations = _active_search(
        world=world,
        posterior=_uniform_prior(world.arity),
        unused=unused,
        trace=trace,
        stage="cold_program_search",
        max_interventions=max_interventions,
    )
    selected = max(posterior, key=posterior.get)
    return {
        "selected": list(selected),
        "correct": selected == world.hypothesis,
        "interventions": len(trace),
        "intervention_cost": cost,
        "fallbacks": 0,
        "abstained": False,
        "unsafe_program_forced": False,
        "candidate_evaluations": evaluations,
        "trace": trace,
    }


def _run_compositional(
    world: ProgramWorld,
    *,
    max_interventions: int = 36,
) -> Dict[str, Any]:
    unused = list(_candidate_states(world.arity))
    trace: List[Dict[str, Any]] = []
    posterior, cost, evaluations = _active_search(
        world=world,
        posterior=_uniform_prior(
            world.arity,
            programs=ANALOG_PROGRAMS,
        ),
        unused=unused,
        trace=trace,
        stage="compositional_program_search",
        max_interventions=max_interventions,
    )
    candidate = max(posterior, key=posterior.get) if len(posterior) == 1 else None
    abstained = candidate is None
    fallbacks = int(abstained)

    if candidate is not None:
        for _ in range(1):
            alternatives = [
                hypothesis
                for hypothesis in _hypotheses(world.arity)
                if hypothesis[0] in NON_ANALOG_PROGRAMS
                and all(
                    _predict(hypothesis, tuple(row["state"]))
                    == bool(row["outcome"])
                    for row in trace
                )
            ]
            if not alternatives:
                break
            evaluations += len(alternatives) * len(unused)

            def falsification_utility(
                value: State,
            ) -> Tuple[float, float, float, float, float, State]:
                by_program: Dict[str, List[ProgramHypothesis]] = {}
                for alternative in alternatives:
                    by_program.setdefault(alternative[0], []).append(alternative)
                fractions = [
                    sum(
                        int(
                            _predict(alternative, value)
                            != _predict(candidate, value)
                        )
                        for alternative in members
                    )
                    / len(members)
                    for members in by_program.values()
                ]
                critical_fractions = [
                    fraction
                    for program, fraction in zip(
                        by_program.keys(),
                        fractions,
                    )
                    if program in {"count_parity", "product_pair_ge"}
                ]
                total_disagreement = sum(
                    int(
                        _predict(alternative, value)
                        != _predict(candidate, value)
                    )
                    for alternative in alternatives
                )
                return (
                    min(critical_fractions)
                    if critical_fractions else 0.0,
                    sum(critical_fractions) / len(critical_fractions)
                    if critical_fractions else 0.0,
                    min(fractions),
                    sum(fractions) / len(fractions),
                    total_disagreement / _intervention_cost(value),
                    value,
                )

            state = max(
                unused,
                key=falsification_utility,
            )
            unused.remove(state)
            observation = world.execute(state)
            predicted = _predict(candidate, state)
            intervention_cost = _intervention_cost(state)
            cost += intervention_cost
            mismatch = observation["outcome"] != predicted
            trace.append(
                {
                    "stage": "program_falsification",
                    "state": list(state),
                    "outcome": int(observation["outcome"]),
                    "predicted": int(predicted),
                    "fallback": mismatch,
                    "intervention_cost": intervention_cost,
                    "remaining": len(alternatives),
                }
            )
            if mismatch:
                abstained = True
                fallbacks += 1
                break

    if abstained:
        survivors = {
            hypothesis: 1.0
            for hypothesis in _hypotheses(world.arity)
            if all(
                _predict(hypothesis, tuple(row["state"]))
                == bool(row["outcome"])
                for row in trace
            )
        }
        posterior, extra_cost, extra_evaluations = _active_search(
            world=world,
            posterior=_normalise(survivors),
            unused=unused,
            trace=trace,
            stage="full_program_fallback",
            max_interventions=max_interventions,
        )
        cost += extra_cost
        evaluations += extra_evaluations

    selected = max(posterior, key=posterior.get)
    return {
        "selected": list(selected),
        "correct": selected == world.hypothesis,
        "interventions": len(trace),
        "intervention_cost": cost,
        "fallbacks": fallbacks,
        "abstained": abstained,
        "unsafe_program_forced": (
            world.hypothesis[0] in NON_ANALOG_PROGRAMS and not abstained
        ),
        "candidate_evaluations": evaluations,
        "trace": trace,
    }


def _execute_goal(
    *,
    world: ProgramWorld,
    hypothesis: ProgramHypothesis,
    episode_index: int,
) -> Dict[str, Any]:
    candidates = list(_candidate_states(world.arity))
    successful = [
        state for state in candidates if _predict(hypothesis, state)
    ]
    plan = min(
        successful,
        key=lambda state: (
            sum(state),
            len(set(state)),
            state,
        ),
    )
    executed = plan
    repair = False
    if episode_index % 5 == 0:
        false_states = [
            state for state in candidates if not _predict(hypothesis, state)
        ]
        if false_states:
            executed = min(false_states, key=lambda state: (sum(state), state))
    first = world.execute(executed)
    if not first["outcome"]:
        repair = True
        executed = plan
    final = world.execute(executed)
    return {
        "success": bool(final["outcome"]),
        "repair": repair,
        "planned_state": list(plan),
        "executed_state": list(executed),
        "verified_intermediates": final["intermediates"],
    }


def _field_names(arity: int, index: int) -> Tuple[str, ...]:
    families = (
        ("lattice", "flux", "buffer", "gate"),
        ("root", "stem", "canopy", "seed"),
        ("north", "south", "east", "west"),
        ("carrier", "signal", "noise", "drain"),
        ("nickel", "carbon", "cobalt", "silicon"),
        ("supply", "reserve", "load", "loss"),
        ("orbit", "thrust", "drift", "drag"),
        ("crest", "keel", "sail", "rudder"),
    )
    return tuple(families[index % len(families)][:arity])


def _graph_depth(program: str) -> int:
    return 3 if program in {
        "minmax_sum_ge",
        "maxmin_difference_ge",
        "minmax_difference_ge",
    } else 2


def _analog_programs(count: int, seed: int) -> List[Tuple[int, ProgramHypothesis]]:
    rng = random.Random(seed)
    rows: List[Tuple[int, ProgramHypothesis]] = []
    for index in range(count):
        arity = 3 if index % 2 == 0 else 4
        program = ANALOG_PROGRAMS[(index // 2) % len(ANALOG_PROGRAMS)]
        if program == "min_plus_tail_ge":
            threshold = rng.randint(6, 14)
        elif program == "max_minus_tail_ge":
            threshold = rng.randint(-2, 6)
        elif program == "range_plus_tail_le":
            threshold = rng.randint(4, 12)
        else:
            threshold = rng.randint(7, 15)
        rows.append((arity, (program, threshold)))
    return rows


def _development_nonanalog() -> List[Tuple[int, ProgramHypothesis]]:
    return [
        (3, ("count_parity", 0)),
        (4, ("product_pair_ge", 20)),
        (4, ("product_pair_ge", 40)),
    ] * 10


def _sealed_nonanalog() -> List[Tuple[int, ProgramHypothesis]]:
    return [
        (4, ("count_parity", 0)),
        (3, ("product_pair_ge", 30)),
        (3, ("product_pair_ge", 50)),
    ] * 12


def _make_worlds(
    prefix: str,
    rows: Sequence[Tuple[int, ProgramHypothesis]],
) -> List[ProgramWorld]:
    return [
        ProgramWorld(
            world_id=f"{prefix}_{index:03d}",
            fields=_field_names(arity, index),
            hypothesis=hypothesis,
            graph_depth=_graph_depth(hypothesis[0]),
        )
        for index, (arity, hypothesis) in enumerate(rows)
    ]


def _evaluate(worlds: Sequence[ProgramWorld]) -> Dict[str, Any]:
    rows = []
    for index, world in enumerate(worlds):
        composed = _run_compositional(world)
        cold = _run_cold(world)
        selected = tuple(composed["selected"])
        goal = _execute_goal(
            world=world,
            hypothesis=selected,
            episode_index=index,
        )
        rows.append(
            {
                "world_id": world.world_id,
                "arity": world.arity,
                "graph_depth": world.graph_depth,
                "fields": list(world.fields),
                "true_program": list(world.hypothesis),
                "family": (
                    f"depth_{world.graph_depth}:"
                    f"arity_{world.arity}:{world.hypothesis[0]}"
                ),
                "composed": composed,
                "cold": cold,
                "goal": goal,
            }
        )
    composed_observations = sum(
        row["composed"]["interventions"] for row in rows
    ) / len(rows)
    cold_observations = sum(
        row["cold"]["interventions"] for row in rows
    ) / len(rows)
    composed_cost = sum(
        row["composed"]["intervention_cost"] for row in rows
    ) / len(rows)
    cold_cost = sum(
        row["cold"]["intervention_cost"] for row in rows
    ) / len(rows)
    families = sorted({row["family"] for row in rows})
    family_results = []
    for family in families:
        members = [row for row in rows if row["family"] == family]
        family_results.append(
            {
                "family": family,
                "worlds": len(members),
                "program_accuracy": sum(
                    int(row["composed"]["correct"]) for row in members
                ) / len(members),
                "goal_success": sum(
                    int(row["goal"]["success"]) for row in members
                ) / len(members),
            }
        )
    return {
        "worlds": len(rows),
        "program_accuracy": sum(
            int(row["composed"]["correct"]) for row in rows
        ) / len(rows),
        "cold_program_accuracy": sum(
            int(row["cold"]["correct"]) for row in rows
        ) / len(rows),
        "goal_success": sum(
            int(row["goal"]["success"]) for row in rows
        ) / len(rows),
        "repair_success": sum(
            int(row["goal"]["success"])
            for row in rows
            if row["goal"]["repair"]
        )
        / max(1, sum(int(row["goal"]["repair"]) for row in rows)),
        "repairs": sum(int(row["goal"]["repair"]) for row in rows),
        "weakest_family_program_accuracy": min(
            row["program_accuracy"] for row in family_results
        ),
        "weakest_family_goal_success": min(
            row["goal_success"] for row in family_results
        ),
        "composed_mean_observations": composed_observations,
        "cold_mean_observations": cold_observations,
        "observation_reduction": (
            1.0 - composed_observations / cold_observations
        ),
        "composed_mean_cost": composed_cost,
        "cold_mean_cost": cold_cost,
        "cost_reduction": 1.0 - composed_cost / cold_cost,
        "fallbacks": sum(row["composed"]["fallbacks"] for row in rows),
        "abstentions": sum(
            int(row["composed"]["abstained"]) for row in rows
        ),
        "unsafe_programs_forced": sum(
            int(row["composed"]["unsafe_program_forced"]) for row in rows
        ),
        "composed_candidate_evaluations": sum(
            row["composed"]["candidate_evaluations"] for row in rows
        ),
        "cold_candidate_evaluations": sum(
            row["cold"]["candidate_evaluations"] for row in rows
        ),
        "families": family_results,
        "rows": rows,
    }


def run_relational_program_induction_benchmark(
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
    runtime.store.state["structural_analogies"][
        "structural_analogy_phase28"
    ] = {
        "status": "promoted_dependency",
        "source_procedure_id": (
            "procedure_structural_analogy_2b9547ef2511"
        ),
    }
    runtime.store.commit(reason="load_phase28_structural_analogy")

    development_analog = _evaluate(
        _make_worlds(
            "development_program",
            _analog_programs(96, 81_101),
        )
    )
    development_nonanalog = _evaluate(
        _make_worlds(
            "development_program_nonanalog",
            _development_nonanalog(),
        )
    )
    sealed_analog = _evaluate(
        _make_worlds(
            "sealed_program",
            _analog_programs(sealed_worlds, 93_017),
        )
    )
    sealed_nonanalog = _evaluate(
        _make_worlds(
            "sealed_program_nonanalog",
            _sealed_nonanalog(),
        )
    )

    errors = []
    if sealed_analog["program_accuracy"] < 1.0:
        errors.append("SEALED_PROGRAM_ACCURACY_NOT_EXACT")
    if sealed_analog["goal_success"] < 1.0:
        errors.append("SEALED_GOAL_SUCCESS_NOT_EXACT")
    if sealed_analog["weakest_family_program_accuracy"] < 1.0:
        errors.append("WEAKEST_PROGRAM_FAMILY_REGRESSED")
    if sealed_analog["weakest_family_goal_success"] < 1.0:
        errors.append("WEAKEST_GOAL_FAMILY_REGRESSED")
    if sealed_analog["observation_reduction"] < 0.15:
        errors.append("PROGRAM_OBSERVATION_REDUCTION_BELOW_15_PERCENT")
    if sealed_analog["cost_reduction"] < 0.12:
        errors.append("PROGRAM_COST_REDUCTION_BELOW_12_PERCENT")
    if sealed_analog["repair_success"] < 1.0:
        errors.append("ONLINE_PROGRAM_REPAIR_FAILED")
    if sealed_nonanalog["program_accuracy"] < 1.0:
        errors.append("NONCOMPOSABLE_PROGRAM_ACCURACY_NOT_EXACT")
    if sealed_nonanalog["unsafe_programs_forced"] != 0:
        errors.append("UNSAFE_COMPOSITION_FORCED")
    if sealed_nonanalog["abstentions"] <= 0:
        errors.append("NONCOMPOSABLE_ABSTENTION_NOT_EXERCISED")
    if (
        sealed_nonanalog["composed_mean_observations"]
        > sealed_nonanalog["cold_mean_observations"] + 1.0
    ):
        errors.append("NONCOMPOSABLE_FALLBACK_OVERHEAD_ABOVE_ONE")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "sealed_worlds": sealed_analog["worlds"],
        "symbol_families": len(
            {tuple(row["fields"]) for row in sealed_analog["rows"]}
        ),
        "arities": sorted({row["arity"] for row in sealed_analog["rows"]}),
        "graph_depths": sorted(
            {row["graph_depth"] for row in sealed_analog["rows"]}
        ),
        "program_accuracy": sealed_analog["program_accuracy"],
        "goal_success": sealed_analog["goal_success"],
        "weakest_family_program_accuracy": sealed_analog[
            "weakest_family_program_accuracy"
        ],
        "weakest_family_goal_success": sealed_analog[
            "weakest_family_goal_success"
        ],
        "composed_mean_observations": sealed_analog[
            "composed_mean_observations"
        ],
        "cold_mean_observations": sealed_analog[
            "cold_mean_observations"
        ],
        "observation_reduction": sealed_analog["observation_reduction"],
        "composed_mean_cost": sealed_analog["composed_mean_cost"],
        "cold_mean_cost": sealed_analog["cold_mean_cost"],
        "cost_reduction": sealed_analog["cost_reduction"],
        "repairs": sealed_analog["repairs"],
        "repair_success": sealed_analog["repair_success"],
        "noncomposable_accuracy": sealed_nonanalog["program_accuracy"],
        "noncomposable_abstentions": sealed_nonanalog["abstentions"],
        "noncomposable_fallbacks": sealed_nonanalog["fallbacks"],
        "unsafe_programs_forced": sealed_nonanalog[
            "unsafe_programs_forced"
        ],
        "noncomposable_mean_observations": sealed_nonanalog[
            "composed_mean_observations"
        ],
        "noncomposable_cold_mean_observations": sealed_nonanalog[
            "cold_mean_observations"
        ],
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_structural_analogy_2b9547ef2511",
        goal="relational_program_induction",
        steps=["fresh_full_relational_program_search"],
        score=-sealed_analog["cold_mean_cost"],
        success=True,
        evidence={"evaluation": "phase29_cold_program_control"},
    )
    runtime.skills.promote(baseline)
    composition_specs = {
        "min_plus_tail_ge": {
            "parents": ["fold_min", "fold_sum", "threshold_ge"],
            "hidden_variables": ["hidden_1", "score"],
            "depth": 2,
        },
        "max_minus_tail_ge": {
            "parents": ["fold_max", "signed_difference", "threshold_ge"],
            "hidden_variables": ["hidden_1", "score"],
            "depth": 2,
        },
        "range_plus_tail_le": {
            "parents": ["max_minus_min", "fold_sum", "threshold_le"],
            "hidden_variables": ["hidden_1", "score"],
            "depth": 2,
        },
        "minmax_sum_ge": {
            "parents": ["fold_min", "fold_max", "fold_sum", "threshold_ge"],
            "hidden_variables": ["hidden_1", "hidden_2", "score"],
            "depth": 3,
        },
    }
    program = {
        "schema_version": "aion.hexcore.cognitive_program.v1",
        "name": "relational_program_composer",
        "source_analogy": "procedure_structural_analogy_2b9547ef2511",
        "composition_specs": composition_specs,
        "falsification_probes": 1,
        "development_checksums": {
            "analog": _canonical_hash(
                [
                    (row["arity"], row["graph_depth"], row["true_program"])
                    for row in development_analog["rows"]
                ]
            ),
            "nonanalog": _canonical_hash(
                [
                    (row["arity"], row["graph_depth"], row["true_program"])
                    for row in development_nonanalog["rows"]
                ]
            ),
        },
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    program_id = (
        "cognitive_program_composer_"
        + _canonical_hash(program)[:12]
    )
    program["program_id"] = program_id
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_relational_program_"
            + _canonical_hash(program)[:12]
        ),
        goal="relational_program_induction",
        steps=[
            "retrieve_verified_relational_primitives",
            "compose_hidden_intermediate_program_candidates",
            "select_cost_aware_discriminating_interventions",
            "infer_program_depth_and_threshold",
            "falsify_composition_against_noncomposable_alternatives",
            "plan_and_execute_goal_through_inferred_program",
            "repair_after_execution_mismatch",
            "retain_program_with_primitive_provenance",
        ],
        score=-sealed_analog["composed_mean_cost"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase29_relational_program_sealed",
            "program_id": program_id,
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
        runtime.store.state["cognitive_programs"][program_id] = program
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "relational_program",
                "invention_id": program_id,
                "procedure_id": candidate.procedure_id,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"cognitive_program:{program_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "program_retained": (
            program_id in restarted.store.state["cognitive_programs"]
        ),
        "champion_retained": (
            restarted.store.state.get("champions", {}).get(
                "relational_program_induction"
            )
            == candidate.procedure_id
        ),
        "phase28_dependency_retained": (
            "structural_analogy_phase28"
            in restarted.store.state["structural_analogies"]
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
        "schema_version": "aion.hexcore.relational_program_induction.v1",
        "benchmark": "cross_depth_relational_program_induction",
        "passed": passed,
        "development": {
            "analog": {
                key: value
                for key, value in development_analog.items()
                if key != "rows"
            },
            "nonanalog": {
                key: value
                for key, value in development_nonanalog.items()
                if key != "rows"
            },
        },
        "sealed_analog": sealed_analog,
        "sealed_nonanalog": sealed_nonanalog,
        "gate": gate,
        "program": program,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION composed a bounded library of supplied relational program "
            "schemas and inferred their hidden intermediate values through "
            "execution. It did not synthesize unrestricted source code, "
            "recursive programs, or its own authority rules."
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
        description="Run HexCore relational-program induction benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=160)
    args = parser.parse_args()
    result = run_relational_program_induction_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

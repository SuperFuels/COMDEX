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


Hypothesis = Tuple[str, int]
State = Tuple[int, ...]
ANALOG_OPERATORS = ("min_ge", "max_ge", "sum_ge", "range_le")
NON_ANALOG_OPERATORS = ("count_high_ge", "parity_high")
FULL_OPERATORS = ANALOG_OPERATORS + NON_ANALOG_OPERATORS


@dataclass(frozen=True)
class StructuralWorld:
    world_id: str
    fields: Tuple[str, ...]
    hypothesis: Hypothesis

    @property
    def arity(self) -> int:
        return len(self.fields)

    def observe(self, state: State) -> bool:
        return _predict(self.hypothesis, state)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "structural_analogy_authority",
        "S": 1.0,
        "H": 0.0,
    }


@lru_cache(maxsize=None)
def _thresholds(operator: str, arity: int) -> Tuple[int, ...]:
    if operator in {"min_ge", "max_ge"}:
        return tuple(range(1, 10))
    if operator == "sum_ge":
        return tuple(range(1, 10 * arity))
    if operator == "range_le":
        return tuple(range(0, 10))
    if operator == "count_high_ge":
        return tuple(range(1, arity + 1))
    if operator == "parity_high":
        return (0,)
    raise ValueError(operator)


@lru_cache(maxsize=None)
def _hypotheses(arity: int) -> Tuple[Hypothesis, ...]:
    return tuple(
        (operator, threshold)
        for operator in FULL_OPERATORS
        for threshold in _thresholds(operator, arity)
    )


def _predict(hypothesis: Hypothesis, state: State) -> bool:
    operator, threshold = hypothesis
    if operator == "min_ge":
        return min(state) >= threshold
    if operator == "max_ge":
        return max(state) >= threshold
    if operator == "sum_ge":
        return sum(state) >= threshold
    if operator == "range_le":
        return max(state) - min(state) <= threshold
    if operator == "count_high_ge":
        return sum(int(value >= 6) for value in state) >= threshold
    if operator == "parity_high":
        return sum(int(value >= 6) for value in state) % 2 == 1
    raise ValueError(operator)


@lru_cache(maxsize=None)
def _candidate_states(arity: int) -> Tuple[State, ...]:
    states = set()
    for value in range(11):
        states.add((value,) * arity)
    for values in itertools.product((0, 10), repeat=arity):
        states.add(tuple(values))
    # Boundary-crossing states distinguish count/parity rules from min/max
    # analogies. They are interventions, not evaluation labels.
    for values in itertools.product((0, 5, 6, 10), repeat=arity):
        states.add(tuple(values))
    for total in range(0, 10 * arity + 1):
        remaining = total
        values = []
        for _ in range(arity):
            value = min(10, remaining)
            values.append(value)
            remaining -= value
        states.add(tuple(values))
        states.add(tuple(reversed(values)))
    graduated = tuple(
        round(index * 10 / max(1, arity - 1))
        for index in range(arity)
    )
    for permutation in set(itertools.permutations(graduated)):
        states.add(tuple(permutation))
    return tuple(sorted(states))


def _probe_cost(state: State) -> float:
    mean = sum(state) / len(state)
    heterogeneous = int(len(set(state)) > 1)
    return 1.0 + 0.025 * mean + 0.05 * heterogeneous


def _entropy(probabilities: Iterable[float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _normalise(weights: Mapping[Hypothesis, float]) -> Dict[Hypothesis, float]:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("zero posterior mass")
    return {
        hypothesis: weight / total
        for hypothesis, weight in weights.items()
    }


def _lift_specs() -> Dict[str, Dict[str, Any]]:
    return {
        "min_ge": {
            "parent": "concept_joint_minimum_81473a7af3f3",
            "binary_operator": "min_ge",
            "lift": "fold_min",
            "fingerprint": [
                "commutative",
                "associative",
                "idempotent",
                "monotone",
                "low_absorbing",
            ],
        },
        "max_ge": {
            "parent": "concept_max_ge_phase26",
            "binary_operator": "max_ge",
            "lift": "fold_max",
            "fingerprint": [
                "commutative",
                "associative",
                "idempotent",
                "monotone",
                "high_absorbing",
            ],
        },
        "sum_ge": {
            "parent": "concept_signed_linear_relation_8b22663b2ca3",
            "binary_operator": "sum_ge",
            "lift": "fold_sum",
            "fingerprint": [
                "commutative",
                "associative",
                "non_idempotent",
                "monotone",
            ],
        },
        "range_le": {
            "parent": "concept_abs_difference_le_phase26",
            "binary_operator": "abs_difference_le",
            "lift": "max_minus_min",
            "fingerprint": [
                "permutation_invariant",
                "translation_invariant",
                "zero_on_equal_inputs",
            ],
        },
    }


def _analogy_prior(
    *,
    arity: int,
    smoothing: float,
) -> Dict[Hypothesis, float]:
    # Counts are inherited only from solved two-variable Phase 27 motifs.
    lower_arity_counts = {
        "min_ge": 60.0,
        "max_ge": 50.0,
        "range_le": 27.0,
        "sum_ge": 14.0,
        "count_high_ge": 0.0,
        "parity_high": 0.0,
    }
    weights: Dict[Hypothesis, float] = {}
    for hypothesis in _hypotheses(arity):
        operator, _ = hypothesis
        operator_count = lower_arity_counts[operator]
        weights[hypothesis] = (
            operator_count / len(_thresholds(operator, arity))
            + smoothing
        )
    return _normalise(weights)


def _uniform_prior(arity: int) -> Dict[Hypothesis, float]:
    hypotheses = _hypotheses(arity)
    return {
        hypothesis: 1.0 / len(hypotheses)
        for hypothesis in hypotheses
    }


def _select_probe(
    posterior: Mapping[Hypothesis, float],
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
        return (gain / _probe_cost(state), gain, state)

    return max(unused, key=utility)


def _run_policy(
    *,
    world: StructuralWorld,
    prior: Mapping[Hypothesis, float],
    surprise_threshold: float,
    allow_fallback: bool,
    max_probes: int = 30,
) -> Dict[str, Any]:
    posterior = dict(prior)
    unused = list(_candidate_states(world.arity))
    trace = []
    total_cost = 0.0
    fallbacks = 0
    analogy_abstained = False
    candidate_evaluations = 0
    while len(posterior) > 1 and len(trace) < max_probes:
        candidate_evaluations += len(posterior) * len(unused)
        state = _select_probe(posterior, unused)
        unused.remove(state)
        positive = sum(
            probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, state)
        )
        outcome = world.observe(state)
        outcome_probability = positive if outcome else 1.0 - positive
        survivors = {
            hypothesis: probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, state) == outcome
        }
        fallback = bool(
            allow_fallback
            and outcome_probability < surprise_threshold
            and len(survivors) > 1
        )
        if fallback:
            fallbacks += 1
            analogy_abstained = True
            posterior = {
                hypothesis: 1.0 / len(survivors)
                for hypothesis in survivors
            }
        else:
            posterior = _normalise(survivors)
        cost = _probe_cost(state)
        total_cost += cost
        trace.append(
            {
                "state": list(state),
                "outcome": int(outcome),
                "outcome_probability": outcome_probability,
                "fallback": fallback,
                "remaining": len(posterior),
                "cost": cost,
            }
        )
    selected = max(posterior, key=posterior.get)
    selected_is_analogy = selected[0] in ANALOG_OPERATORS
    return {
        "selected": list(selected),
        "correct": selected == world.hypothesis,
        "probes": len(trace),
        "total_cost": total_cost,
        "fallbacks": fallbacks,
        "analogy_abstained": analogy_abstained,
        "unsafe_analogy_forced": (
            world.hypothesis[0] in NON_ANALOG_OPERATORS
            and selected_is_analogy
        ),
        "candidate_evaluations": candidate_evaluations,
        "trace": trace,
    }


def _run_analogical_policy(
    *,
    world: StructuralWorld,
    smoothing: float,
    validation_probes: int = 1,
    max_probes: int = 30,
) -> Dict[str, Any]:
    full_prior = _analogy_prior(arity=world.arity, smoothing=smoothing)
    posterior = _normalise(
        {
            hypothesis: probability
            for hypothesis, probability in full_prior.items()
            if hypothesis[0] in ANALOG_OPERATORS
        }
    )
    unused = list(_candidate_states(world.arity))
    trace: List[Dict[str, Any]] = []
    total_cost = 0.0
    candidate_evaluations = 0

    while len(posterior) > 1 and len(trace) < max_probes:
        candidate_evaluations += len(posterior) * len(unused)
        state = _select_probe(posterior, unused)
        unused.remove(state)
        outcome = world.observe(state)
        survivors = {
            hypothesis: probability
            for hypothesis, probability in posterior.items()
            if _predict(hypothesis, state) == outcome
        }
        cost = _probe_cost(state)
        total_cost += cost
        trace.append(
            {
                "stage": "analogy_search",
                "state": list(state),
                "outcome": int(outcome),
                "fallback": False,
                "remaining": len(survivors),
                "cost": cost,
            }
        )
        if not survivors:
            posterior = {}
            break
        posterior = _normalise(survivors)

    analog_candidate = (
        max(posterior, key=posterior.get) if len(posterior) == 1 else None
    )
    analogy_abstained = analog_candidate is None
    fallbacks = int(analogy_abstained)

    if analog_candidate is not None:
        for _ in range(validation_probes):
            alternatives = [
                hypothesis
                for hypothesis in _hypotheses(world.arity)
                if hypothesis[0] in NON_ANALOG_OPERATORS
                and all(
                    _predict(hypothesis, tuple(row["state"]))
                    == bool(row["outcome"])
                    for row in trace
                )
            ]
            if not alternatives:
                break
            candidate_evaluations += len(alternatives) * len(unused)
            state = max(
                unused,
                key=lambda point: (
                    sum(
                        int(
                            _predict(hypothesis, point)
                            != _predict(analog_candidate, point)
                        )
                        for hypothesis in alternatives
                    )
                    / _probe_cost(point),
                    point,
                ),
            )
            unused.remove(state)
            outcome = world.observe(state)
            predicted = _predict(analog_candidate, state)
            cost = _probe_cost(state)
            total_cost += cost
            trace.append(
                {
                    "stage": "analogy_falsification",
                    "state": list(state),
                    "outcome": int(outcome),
                    "predicted": int(predicted),
                    "fallback": outcome != predicted,
                    "remaining": len(alternatives),
                    "cost": cost,
                }
            )
            if outcome != predicted:
                analogy_abstained = True
                fallbacks += 1
                break

    if analogy_abstained:
        survivors = {
            hypothesis: 1.0
            for hypothesis in _hypotheses(world.arity)
            if all(
                _predict(hypothesis, tuple(row["state"]))
                == bool(row["outcome"])
                for row in trace
            )
        }
        posterior = _normalise(survivors)
        while len(posterior) > 1 and len(trace) < max_probes:
            candidate_evaluations += len(posterior) * len(unused)
            state = _select_probe(posterior, unused)
            unused.remove(state)
            outcome = world.observe(state)
            survivors = {
                hypothesis: probability
                for hypothesis, probability in posterior.items()
                if _predict(hypothesis, state) == outcome
            }
            posterior = _normalise(survivors)
            cost = _probe_cost(state)
            total_cost += cost
            trace.append(
                {
                    "stage": "cold_fallback",
                    "state": list(state),
                    "outcome": int(outcome),
                    "fallback": True,
                    "remaining": len(posterior),
                    "cost": cost,
                }
            )

    selected = max(posterior, key=posterior.get)
    return {
        "selected": list(selected),
        "correct": selected == world.hypothesis,
        "probes": len(trace),
        "total_cost": total_cost,
        "fallbacks": fallbacks,
        "analogy_abstained": analogy_abstained,
        "unsafe_analogy_forced": (
            world.hypothesis[0] in NON_ANALOG_OPERATORS
            and not analogy_abstained
        ),
        "candidate_evaluations": candidate_evaluations,
        "trace": trace,
    }


def _field_names(arity: int, index: int) -> Tuple[str, ...]:
    families = (
        ("petal", "stem", "root", "seed"),
        ("north", "south", "east", "west"),
        ("signal", "carrier", "buffer", "drain"),
        ("nickel", "cobalt", "carbon", "silicon"),
        ("orbit", "drift", "thrust", "drag"),
        ("supply", "load", "reserve", "loss"),
        ("crest", "keel", "sail", "rudder"),
        ("alpha", "beta", "gamma", "delta"),
    )
    return tuple(families[index % len(families)][:arity])


def _analog_hypotheses(count: int, seed: int) -> List[Tuple[int, Hypothesis]]:
    rng = random.Random(seed)
    rows: List[Tuple[int, Hypothesis]] = []
    operators = list(ANALOG_OPERATORS)
    for index in range(count):
        arity = 3 if index % 2 == 0 else 4
        operator = operators[(index // 2) % len(operators)]
        if operator == "min_ge":
            threshold = rng.randint(3, 7)
        elif operator == "max_ge":
            threshold = rng.randint(4, 8)
        elif operator == "sum_ge":
            threshold = rng.randint(4 * arity, 6 * arity)
        else:
            threshold = rng.randint(1, 3)
        rows.append((arity, (operator, threshold)))
    return rows


def _development_nonanalog() -> List[Tuple[int, Hypothesis]]:
    return [
        (4, ("count_high_ge", 2)),
        (3, ("parity_high", 0)),
    ] * 12


def _sealed_nonanalog() -> List[Tuple[int, Hypothesis]]:
    # Exact arity/operator/threshold structures are disjoint from calibration.
    return [
        (3, ("count_high_ge", 2)),
        (4, ("count_high_ge", 3)),
        (4, ("parity_high", 0)),
    ] * 12


def _make_worlds(
    prefix: str,
    rows: Sequence[Tuple[int, Hypothesis]],
) -> List[StructuralWorld]:
    return [
        StructuralWorld(
            world_id=f"{prefix}_{index:03d}",
            fields=_field_names(arity, index),
            hypothesis=hypothesis,
        )
        for index, (arity, hypothesis) in enumerate(rows)
    ]


def _evaluate(
    *,
    worlds: Sequence[StructuralWorld],
    smoothing: float,
) -> Dict[str, Any]:
    rows = []
    for world in worlds:
        analogical = _run_analogical_policy(
            world=world,
            smoothing=smoothing,
        )
        cold = _run_policy(
            world=world,
            prior=_uniform_prior(world.arity),
            surprise_threshold=0.0,
            allow_fallback=False,
        )
        rows.append(
            {
                "world_id": world.world_id,
                "arity": world.arity,
                "fields": list(world.fields),
                "true_hypothesis": list(world.hypothesis),
                "family": f"arity_{world.arity}:{world.hypothesis[0]}",
                "analogical": analogical,
                "cold": cold,
            }
        )
    analog_probes = sum(
        row["analogical"]["probes"] for row in rows
    ) / len(rows)
    cold_probes = sum(row["cold"]["probes"] for row in rows) / len(rows)
    analog_cost = sum(
        row["analogical"]["total_cost"] for row in rows
    ) / len(rows)
    cold_cost = sum(
        row["cold"]["total_cost"] for row in rows
    ) / len(rows)
    families = sorted({row["family"] for row in rows})
    family_results = []
    for family in families:
        members = [row for row in rows if row["family"] == family]
        family_results.append(
            {
                "family": family,
                "worlds": len(members),
                "accuracy": sum(
                    int(row["analogical"]["correct"]) for row in members
                ) / len(members),
                "mean_probes": sum(
                    row["analogical"]["probes"] for row in members
                ) / len(members),
            }
        )
    return {
        "worlds": len(rows),
        "accuracy": sum(
            int(row["analogical"]["correct"]) for row in rows
        ) / len(rows),
        "cold_accuracy": sum(
            int(row["cold"]["correct"]) for row in rows
        ) / len(rows),
        "weakest_family_accuracy": min(
            row["accuracy"] for row in family_results
        ),
        "analogical_mean_probes": analog_probes,
        "cold_mean_probes": cold_probes,
        "probe_reduction": 1.0 - analog_probes / cold_probes,
        "analogical_mean_cost": analog_cost,
        "cold_mean_cost": cold_cost,
        "cost_reduction": 1.0 - analog_cost / cold_cost,
        "fallbacks": sum(
            row["analogical"]["fallbacks"] for row in rows
        ),
        "abstentions": sum(
            int(row["analogical"]["analogy_abstained"]) for row in rows
        ),
        "unsafe_analogy_forced": sum(
            int(row["analogical"]["unsafe_analogy_forced"]) for row in rows
        ),
        "analogical_candidate_evaluations": sum(
            row["analogical"]["candidate_evaluations"] for row in rows
        ),
        "cold_candidate_evaluations": sum(
            row["cold"]["candidate_evaluations"] for row in rows
        ),
        "families": family_results,
        "rows": rows,
    }


def run_structural_analogy_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_worlds: int = 160,
    smoothing: float = 0.25,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    runtime.store.state["experiment_policies"][
        "experiment_policy_motif_phase27"
    ] = {
        "status": "promoted_dependency",
        "source_procedure_id": (
            "procedure_learned_experiments_64399d6d90a7"
        ),
    }
    runtime.store.commit(reason="load_phase27_experiment_policy")

    lift_specs = _lift_specs()
    development_analog = _evaluate(
        worlds=_make_worlds(
            "development_analog",
            _analog_hypotheses(96, 51_001),
        ),
        smoothing=smoothing,
    )
    development_nonanalog = _evaluate(
        worlds=_make_worlds(
            "development_nonanalog",
            _development_nonanalog(),
        ),
        smoothing=smoothing,
    )
    sealed_analog = _evaluate(
        worlds=_make_worlds(
            "sealed_analog",
            _analog_hypotheses(sealed_worlds, 72_019),
        ),
        smoothing=smoothing,
    )
    sealed_nonanalog = _evaluate(
        worlds=_make_worlds(
            "sealed_nonanalog",
            _sealed_nonanalog(),
        ),
        smoothing=smoothing,
    )

    errors = []
    if sealed_analog["accuracy"] < 1.0:
        errors.append("ANALOGICAL_STRUCTURAL_ACCURACY_NOT_EXACT")
    if sealed_analog["weakest_family_accuracy"] < 1.0:
        errors.append("WEAKEST_ANALOGICAL_FAMILY_REGRESSED")
    if sealed_analog["probe_reduction"] < 0.15:
        errors.append("ENVIRONMENTAL_PROBE_REDUCTION_BELOW_15_PERCENT")
    if sealed_analog["cost_reduction"] < 0.12:
        errors.append("ANALOGICAL_ACTION_COST_REDUCTION_BELOW_12_PERCENT")
    if sealed_nonanalog["accuracy"] < 1.0:
        errors.append("NON_ANALOGOUS_ACCURACY_NOT_EXACT")
    if sealed_nonanalog["unsafe_analogy_forced"] != 0:
        errors.append("UNSAFE_ANALOGY_FORCED")
    if sealed_nonanalog["abstentions"] <= 0:
        errors.append("NON_ANALOGOUS_ABSTENTION_NOT_EXERCISED")
    if (
        sealed_nonanalog["analogical_mean_probes"]
        > sealed_nonanalog["cold_mean_probes"] + 1.0
    ):
        errors.append("NON_ANALOGOUS_PROBE_OVERHEAD_ABOVE_ONE")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "sealed_analog_worlds": sealed_analog["worlds"],
        "symbol_families": len(
            {tuple(row["fields"]) for row in sealed_analog["rows"]}
        ),
        "arities": sorted(
            {row["arity"] for row in sealed_analog["rows"]}
        ),
        "analogical_accuracy": sealed_analog["accuracy"],
        "weakest_family_accuracy": sealed_analog[
            "weakest_family_accuracy"
        ],
        "analogical_mean_probes": sealed_analog[
            "analogical_mean_probes"
        ],
        "cold_mean_probes": sealed_analog["cold_mean_probes"],
        "environmental_probe_reduction": sealed_analog[
            "probe_reduction"
        ],
        "analogical_mean_cost": sealed_analog["analogical_mean_cost"],
        "cold_mean_cost": sealed_analog["cold_mean_cost"],
        "cost_reduction": sealed_analog["cost_reduction"],
        "nonanalog_accuracy": sealed_nonanalog["accuracy"],
        "nonanalog_abstentions": sealed_nonanalog["abstentions"],
        "nonanalog_fallbacks": sealed_nonanalog["fallbacks"],
        "unsafe_analogy_forced": sealed_nonanalog[
            "unsafe_analogy_forced"
        ],
        "nonanalog_mean_probes": sealed_nonanalog[
            "analogical_mean_probes"
        ],
        "nonanalog_cold_mean_probes": sealed_nonanalog[
            "cold_mean_probes"
        ],
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_learned_experiments_64399d6d90a7",
        goal="structural_analogy",
        steps=["fresh_higher_arity_adaptive_search"],
        score=-sealed_analog["cold_mean_cost"],
        success=True,
        evidence={"evaluation": "phase28_cold_structure_control"},
    )
    runtime.skills.promote(baseline)
    analogy = {
        "schema_version": "aion.hexcore.structural_analogy.v1",
        "name": "permutation_invariant_arity_lift",
        "source_policy": "procedure_learned_experiments_64399d6d90a7",
        "lift_specs": lift_specs,
        "supported_arities": [3, 4],
        "smoothing": smoothing,
        "falsification_probes": 1,
        "development_checksums": {
            "analog": _canonical_hash(
                [
                    (row["arity"], row["true_hypothesis"])
                    for row in development_analog["rows"]
                ]
            ),
            "nonanalog": _canonical_hash(
                [
                    (row["arity"], row["true_hypothesis"])
                    for row in development_nonanalog["rows"]
                ]
            ),
        },
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    analogy_id = (
        "structural_analogy_arity_lift_"
        + _canonical_hash(analogy)[:12]
    )
    analogy["analogy_id"] = analogy_id
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_structural_analogy_"
            + _canonical_hash(analogy)[:12]
        ),
        goal="structural_analogy",
        steps=[
            "extract_algebraic_fingerprint_from_retained_binary_concept",
            "construct_permutation_invariant_higher_arity_lifts",
            "transfer_cost_aware_experiment_prior",
            "identify_structure_from_observed_interventions",
            "abstain_and_fallback_on_analogy_surprise",
            "verify_environmental_intervention_reduction",
            "retain_abstract_concrete_provenance_links",
        ],
        score=-sealed_analog["analogical_mean_cost"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase28_structural_analogy_sealed",
            "analogy_id": analogy_id,
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
        runtime.store.state["structural_analogies"][analogy_id] = analogy
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "structural_analogy",
                "invention_id": analogy_id,
                "procedure_id": candidate.procedure_id,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"structural_analogy:{analogy_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "analogy_retained": (
            analogy_id in restarted.store.state["structural_analogies"]
        ),
        "champion_retained": (
            restarted.store.state.get("champions", {}).get(
                "structural_analogy"
            )
            == candidate.procedure_id
        ),
        "phase27_dependency_retained": (
            "experiment_policy_motif_phase27"
            in restarted.store.state["experiment_policies"]
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
        "schema_version": "aion.hexcore.structural_analogy_benchmark.v1",
        "benchmark": "cross_arity_structural_analogy",
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
        "analogy": analogy,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION lifted a bounded library of permutation-invariant binary "
            "relations into engineered three- and four-variable candidate "
            "families. It did not perform unrestricted structural analogy, "
            "arbitrary program synthesis, or open-ended mathematics."
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
        description="Run HexCore cross-arity structural analogy benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=160)
    parser.add_argument("--smoothing", type=float, default=0.25)
    args = parser.parse_args()
    result = run_structural_analogy_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
        smoothing=args.smoothing,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

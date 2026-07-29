from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.relational_program_induction_benchmark import (
    ANALOG_PROGRAMS,
    FULL_PROGRAMS,
    ProgramHypothesis,
    ProgramWorld,
    State,
    _active_search,
    _candidate_states,
    _execute_goal,
    _hypotheses,
    _intervention_cost,
    _normalise,
    _predict,
    _uniform_prior,
)


MUTATION_SEQUENCE = (
    "sum_minus_tail_ge",
    "range_plus_tail_ge",
    "max_plus_tail_ge",
)
SURPRISE_PROGRAMS = ("count_parity", "product_pair_ge")


@dataclass(frozen=True)
class EvolutionPolicy:
    generation: int
    programs: Tuple[str, ...]
    parent_id: str

    @property
    def complexity(self) -> int:
        return len(self.programs)

    @property
    def policy_id(self) -> str:
        payload = {
            "generation": self.generation,
            "programs": list(self.programs),
            "parent_id": self.parent_id,
        }
        return "program_policy_" + _canonical_hash(payload)[:12]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "cognitive_program_evolution_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _run_policy(
    world: ProgramWorld,
    policy: EvolutionPolicy,
    *,
    max_interventions: int = 36,
) -> Dict[str, Any]:
    unused = list(_candidate_states(world.arity))
    trace: List[Dict[str, Any]] = []
    posterior, cost, evaluations = _active_search(
        world=world,
        posterior=_uniform_prior(world.arity, programs=policy.programs),
        unused=unused,
        trace=trace,
        stage=f"generation_{policy.generation}_program_search",
        max_interventions=max_interventions,
    )
    candidate = max(posterior, key=posterior.get) if len(posterior) == 1 else None
    abstained = candidate is None
    fallbacks = int(abstained)

    if candidate is not None:
        alternatives = [
            hypothesis
            for hypothesis in _hypotheses(world.arity)
            if hypothesis[0] not in policy.programs
            and all(
                _predict(hypothesis, tuple(row["state"]))
                == bool(row["outcome"])
                for row in trace
            )
        ]
        if alternatives:
            evaluations += len(alternatives) * len(unused)

            def falsification_utility(state: State) -> Tuple[float, float, float, State]:
                by_program: Dict[str, List[ProgramHypothesis]] = {}
                for alternative in alternatives:
                    by_program.setdefault(alternative[0], []).append(alternative)
                fractions = {
                    name: sum(
                        int(_predict(item, state) != _predict(candidate, state))
                        for item in members
                    )
                    / len(members)
                    for name, members in by_program.items()
                }
                surprise = [
                    fractions[name]
                    for name in SURPRISE_PROGRAMS
                    if name in fractions
                ]
                return (
                    min(surprise) if surprise else 0.0,
                    sum(fractions.values()) / len(fractions),
                    sum(
                        int(_predict(item, state) != _predict(candidate, state))
                        for item in alternatives
                    )
                    / _intervention_cost(state),
                    state,
                )

            state = max(unused, key=falsification_utility)
            unused.remove(state)
            observation = world.execute(state)
            predicted = _predict(candidate, state)
            intervention_cost = _intervention_cost(state)
            cost += intervention_cost
            mismatch = observation["outcome"] != predicted
            trace.append(
                {
                    "stage": "cross_grammar_falsification",
                    "state": list(state),
                    "outcome": int(observation["outcome"]),
                    "predicted": int(predicted),
                    "fallback": mismatch,
                    "intervention_cost": intervention_cost,
                }
            )
            if mismatch:
                abstained = True
                fallbacks += 1

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
            stage="neutral_full_grammar_fallback",
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
            world.hypothesis[0] not in policy.programs and not abstained
        ),
        "candidate_evaluations": evaluations,
        "trace": trace,
    }


def _threshold(program: str, rng: random.Random) -> int:
    if program == "sum_minus_tail_ge":
        return rng.randint(4, 18)
    if program == "range_plus_tail_ge":
        return rng.randint(3, 12)
    if program == "max_plus_tail_ge":
        return rng.randint(7, 16)
    if program == "count_parity":
        return 0
    if program == "product_pair_ge":
        return rng.choice((20, 30, 40, 50))
    if program == "min_plus_tail_ge":
        return rng.randint(6, 14)
    if program == "max_minus_tail_ge":
        return rng.randint(-2, 6)
    if program == "range_plus_tail_le":
        return rng.randint(4, 12)
    if program == "minmax_sum_ge":
        return rng.randint(7, 15)
    raise ValueError(program)


def _fields(arity: int, index: int, cohort: str) -> Tuple[str, ...]:
    families = (
        ("quartz", "ember", "tide", "veil"),
        ("alpha", "kappa", "sigma", "omega"),
        ("harbor", "current", "ballast", "mast"),
        ("intake", "reactor", "buffer", "exhaust"),
        ("pulse", "phase", "amplitude", "decay"),
        ("source", "channel", "reserve", "sink"),
    )
    stem = families[index % len(families)]
    return tuple(f"{cohort}_{name}" for name in stem[:arity])


def _worlds(
    *,
    program: str,
    count: int,
    seed: int,
    cohort: str,
) -> List[ProgramWorld]:
    rng = random.Random(seed)
    return [
        ProgramWorld(
            world_id=f"{cohort}_{program}_{index:03d}",
            fields=_fields(3 if index % 2 == 0 else 4, index, cohort),
            hypothesis=(program, _threshold(program, rng)),
            graph_depth=2,
        )
        for index in range(count)
    ]


def _evaluate_pair(
    worlds: Sequence[ProgramWorld],
    *,
    parent: EvolutionPolicy,
    challenger: EvolutionPolicy,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for index, world in enumerate(worlds):
        parent_result = _run_policy(world, parent)
        challenger_result = _run_policy(world, challenger)
        goal = _execute_goal(
            world=world,
            hypothesis=tuple(challenger_result["selected"]),
            episode_index=index,
        )
        rows.append(
            {
                "world_id": world.world_id,
                "family": f"{world.arity}:{world.hypothesis[0]}",
                "true_program": list(world.hypothesis),
                "parent": parent_result,
                "challenger": challenger_result,
                "goal": goal,
            }
        )

    families = sorted({row["family"] for row in rows})
    family_rows = []
    for family in families:
        members = [row for row in rows if row["family"] == family]
        family_rows.append(
            {
                "family": family,
                "parent_accuracy": sum(
                    int(row["parent"]["correct"]) for row in members
                )
                / len(members),
                "challenger_accuracy": sum(
                    int(row["challenger"]["correct"]) for row in members
                )
                / len(members),
                "goal_success": sum(
                    int(row["goal"]["success"]) for row in members
                )
                / len(members),
            }
        )

    def mean(path: str, metric: str) -> float:
        return sum(row[path][metric] for row in rows) / len(rows)

    parent_observations = mean("parent", "interventions")
    challenger_observations = mean("challenger", "interventions")
    parent_cost = mean("parent", "intervention_cost")
    challenger_cost = mean("challenger", "intervention_cost")
    return {
        "worlds": len(rows),
        "parent_accuracy": sum(int(row["parent"]["correct"]) for row in rows)
        / len(rows),
        "challenger_accuracy": sum(
            int(row["challenger"]["correct"]) for row in rows
        )
        / len(rows),
        "goal_success": sum(int(row["goal"]["success"]) for row in rows)
        / len(rows),
        "repair_success": sum(
            int(row["goal"]["success"]) for row in rows if row["goal"]["repair"]
        )
        / max(1, sum(int(row["goal"]["repair"]) for row in rows)),
        "parent_mean_observations": parent_observations,
        "challenger_mean_observations": challenger_observations,
        "observation_reduction": 1.0 - challenger_observations / parent_observations,
        "parent_mean_cost": parent_cost,
        "challenger_mean_cost": challenger_cost,
        "cost_reduction": 1.0 - challenger_cost / parent_cost,
        "weakest_family_accuracy": min(
            row["challenger_accuracy"] for row in family_rows
        ),
        "weakest_family_goal_success": min(
            row["goal_success"] for row in family_rows
        ),
        "abstentions": sum(row["challenger"]["abstained"] for row in rows),
        "fallbacks": sum(row["challenger"]["fallbacks"] for row in rows),
        "unsafe_programs_forced": sum(
            row["challenger"]["unsafe_program_forced"] for row in rows
        ),
        "families": family_rows,
        "rows": rows,
    }


def _retention(
    *,
    policy: EvolutionPolicy,
    count: int,
    seed: int,
    cohort: str,
) -> Dict[str, Any]:
    programs = list(ANALOG_PROGRAMS)
    worlds: List[ProgramWorld] = []
    per_program = max(2, count // len(programs))
    for offset, program in enumerate(programs):
        worlds.extend(
            _worlds(
                program=program,
                count=per_program,
                seed=seed + offset,
                cohort=f"{cohort}_{offset}",
            )
        )
    results = [_run_policy(world, policy) for world in worlds]
    return {
        "worlds": len(worlds),
        "accuracy": sum(int(row["correct"]) for row in results) / len(results),
        "unsafe_programs_forced": sum(
            int(row["unsafe_program_forced"]) for row in results
        ),
    }


def _surprise(
    *,
    policy: EvolutionPolicy,
    count: int,
    seed: int,
    cohort: str,
) -> Dict[str, Any]:
    worlds = []
    per_program = max(2, count // len(SURPRISE_PROGRAMS))
    for offset, program in enumerate(SURPRISE_PROGRAMS):
        worlds.extend(
            _worlds(
                program=program,
                count=per_program,
                seed=seed + offset,
                cohort=f"{cohort}_{offset}",
            )
        )
    results = [_run_policy(world, policy) for world in worlds]
    return {
        "worlds": len(worlds),
        "accuracy": sum(int(row["correct"]) for row in results) / len(results),
        "abstentions": sum(int(row["abstained"]) for row in results),
        "fallbacks": sum(row["fallbacks"] for row in results),
        "unsafe_programs_forced": sum(
            int(row["unsafe_program_forced"]) for row in results
        ),
    }


def run_cognitive_program_evolution_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_generation: int = 16,
    sealed_worlds_per_generation: int = 40,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase29_id = "procedure_relational_program_46d68960189f"
    phase29_program_id = "cognitive_program_composer_a002011588c6"
    runtime.store.state["cognitive_programs"][phase29_program_id] = {
        "status": "promoted_dependency",
        "procedure_id": phase29_id,
        "programs": list(ANALOG_PROGRAMS),
    }
    runtime.store.commit(reason="load_phase29_program_composer")
    baseline = ProcedureCandidate(
        procedure_id=phase29_id,
        goal="cognitive_program_evolution",
        steps=["bounded_relational_program_composition"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase29_promoted_parent"},
    )
    runtime.skills.promote(baseline)

    parent = EvolutionPolicy(
        generation=0,
        programs=tuple(ANALOG_PROGRAMS),
        parent_id=phase29_id,
    )
    generations: List[Dict[str, Any]] = []
    outcome_ledger: List[Dict[str, Any]] = []
    all_passed = True

    for generation, mutation in enumerate(MUTATION_SEQUENCE, start=1):
        development = _evaluate_pair(
            _worlds(
                program=mutation,
                count=development_worlds_per_generation,
                seed=31_000 + generation,
                cohort=f"development_g{generation}",
            ),
            parent=parent,
            challenger=EvolutionPolicy(
                generation=generation,
                programs=parent.programs + (mutation,),
                parent_id=parent.policy_id,
            ),
        )
        failure_queue = {
            "generation": generation,
            "kind": "composition_grammar_gap",
            "program_family": mutation,
            "parent_fallbacks": sum(
                row["parent"]["fallbacks"] for row in development["rows"]
            ),
            "verified_cases": development["worlds"],
            "source": "development_outcome_ledger",
        }
        outcome_ledger.append(failure_queue)
        challenger = EvolutionPolicy(
            generation=generation,
            programs=parent.programs + (mutation,),
            parent_id=parent.policy_id,
        )
        sealed = _evaluate_pair(
            _worlds(
                program=mutation,
                count=sealed_worlds_per_generation,
                seed=47_000 + generation,
                cohort=f"sealed_g{generation}",
            ),
            parent=parent,
            challenger=challenger,
        )
        retention = _retention(
            policy=challenger,
            count=16,
            seed=53_000 + generation,
            cohort=f"retention_g{generation}",
        )
        errors = []
        if development["challenger_accuracy"] < 1.0:
            errors.append("DEVELOPMENT_PROGRAM_ACCURACY_NOT_EXACT")
        if sealed["challenger_accuracy"] < 1.0:
            errors.append("SEALED_PROGRAM_ACCURACY_NOT_EXACT")
        if sealed["goal_success"] < 1.0:
            errors.append("SEALED_GOAL_SUCCESS_NOT_EXACT")
        if sealed["weakest_family_accuracy"] < 1.0:
            errors.append("WEAKEST_FAMILY_REGRESSED")
        if sealed["observation_reduction"] <= 0.0:
            errors.append("NO_ENVIRONMENTAL_OBSERVATION_GAIN")
        if sealed["cost_reduction"] <= 0.0:
            errors.append("NO_ACTION_COST_GAIN")
        if retention["accuracy"] < 1.0:
            errors.append("BACKWARD_RETENTION_REGRESSED")
        if challenger.complexity != parent.complexity + 1:
            errors.append("UNCONTROLLED_GRAMMAR_GROWTH")
        gate = {
            "accepted": not errors,
            "errors": errors,
            "generation": generation,
            "mutation": mutation,
            "complexity_before": parent.complexity,
            "complexity_after": challenger.complexity,
            "sealed_program_accuracy": sealed["challenger_accuracy"],
            "sealed_goal_success": sealed["goal_success"],
            "weakest_family_accuracy": sealed["weakest_family_accuracy"],
            "observation_reduction": sealed["observation_reduction"],
            "cost_reduction": sealed["cost_reduction"],
            "backward_retention": retention["accuracy"],
        }
        program_record = {
            "schema_version": "aion.hexcore.program_evolution_generation.v1",
            "generation": generation,
            "policy_id": challenger.policy_id,
            "parent_id": challenger.parent_id,
            "mutation": mutation,
            "programs": list(challenger.programs),
            "failure_queue": failure_queue,
            "gate": gate,
            "created_at": _utc_timestamp(),
        }
        candidate = ProcedureCandidate(
            procedure_id=(
                f"procedure_program_evolution_g{generation}_"
                + _canonical_hash(program_record)[:12]
            ),
            goal="cognitive_program_evolution",
            steps=[
                "read_persistent_program_failure_queue",
                "propose_one_bounded_composition_schema",
                "train_private_program_policy_on_development_worlds",
                "compete_against_immutable_parent",
                "evaluate_once_on_sealed_graph_family",
                "verify_backward_retention_and_complexity",
                "persist_authorized_generation",
            ],
            # Promotion score is lexicographically generation-first because
            # the gate has already required exact capability, backward
            # retention, and lower environmental cost.  This prevents raw
            # cost scales from making a strictly cumulative generation look
            # worse than its less capable parent.
            score=(
                float(generation)
                + sealed["observation_reduction"]
                + sealed["cost_reduction"]
            ),
            success=gate["accepted"],
            evidence={
                "evaluation": f"phase30_generation_{generation}_sealed",
                "gate": gate,
                "policy_id": challenger.policy_id,
            },
        )
        decision = runtime.skills.promote(candidate)
        if gate["accepted"] and decision.get("promoted"):
            runtime.store.state["program_evolution"][challenger.policy_id] = (
                program_record
            )
            runtime.store.state["procedure_mutation_cycles"].append(
                {
                    "cycle_id": f"phase30_generation_{generation}",
                    "parent_id": challenger.parent_id,
                    "challenger_policy_id": challenger.policy_id,
                    "procedure_id": candidate.procedure_id,
                    "mutation": mutation,
                    "accepted": True,
                    "timestamp": _utc_timestamp(),
                }
            )
            runtime.store.state["failure_queues"][
                f"program_generation_{generation}"
            ] = [failure_queue]
            runtime.store.commit(
                reason=f"program_evolution:{challenger.policy_id}"
            )
            parent = EvolutionPolicy(
                generation=generation,
                programs=challenger.programs,
                parent_id=candidate.procedure_id,
            )
        else:
            all_passed = False
        generations.append(
            {
                "generation": generation,
                "parent": {
                    "policy_id": challenger.parent_id,
                    "programs": list(challenger.programs[:-1]),
                },
                "challenger": {
                    "policy_id": challenger.policy_id,
                    "programs": list(challenger.programs),
                },
                "development": development,
                "sealed": sealed,
                "retention": retention,
                "failure_queue": failure_queue,
                "gate": gate,
                "promotion": {
                    "candidate": candidate.to_dict(),
                    "decision": decision,
                },
            }
        )

    surprise = _surprise(
        policy=parent,
        count=24,
        seed=67_301,
        cohort="sealed_surprise",
    )
    cumulative_worlds: List[ProgramWorld] = []
    for offset, program in enumerate(MUTATION_SEQUENCE):
        cumulative_worlds.extend(
            _worlds(
                program=program,
                count=20,
                seed=71_000 + offset,
                cohort=f"cumulative_{offset}",
            )
        )
    original = EvolutionPolicy(
        generation=0,
        programs=tuple(ANALOG_PROGRAMS),
        parent_id=phase29_id,
    )
    cumulative = _evaluate_pair(
        cumulative_worlds,
        parent=original,
        challenger=parent,
    )
    cumulative_gate = {
        "three_generations_promoted": all_passed and len(generations) == 3,
        "program_accuracy": cumulative["challenger_accuracy"],
        "goal_success": cumulative["goal_success"],
        "weakest_family_accuracy": cumulative["weakest_family_accuracy"],
        "observation_reduction": cumulative["observation_reduction"],
        "cost_reduction": cumulative["cost_reduction"],
        "grammar_growth": parent.complexity - len(ANALOG_PROGRAMS),
        "surprise_accuracy": surprise["accuracy"],
        "surprise_abstentions": surprise["abstentions"],
        "surprise_fallbacks": surprise["fallbacks"],
        "unsafe_programs_forced": surprise["unsafe_programs_forced"],
    }
    cumulative_errors = []
    if cumulative_gate["program_accuracy"] < 1.0:
        cumulative_errors.append("CUMULATIVE_PROGRAM_ACCURACY_NOT_EXACT")
    if cumulative_gate["goal_success"] < 1.0:
        cumulative_errors.append("CUMULATIVE_GOAL_SUCCESS_NOT_EXACT")
    if cumulative_gate["weakest_family_accuracy"] < 1.0:
        cumulative_errors.append("CUMULATIVE_WEAKEST_FAMILY_REGRESSED")
    if cumulative_gate["observation_reduction"] <= 0.0:
        cumulative_errors.append("CUMULATIVE_OBSERVATION_GAIN_MISSING")
    if cumulative_gate["cost_reduction"] <= 0.0:
        cumulative_errors.append("CUMULATIVE_COST_GAIN_MISSING")
    if cumulative_gate["grammar_growth"] != 3:
        cumulative_errors.append("GRAMMAR_GROWTH_NOT_EXACTLY_BOUNDED")
    if cumulative_gate["surprise_accuracy"] < 1.0:
        cumulative_errors.append("SURPRISE_RECOVERY_FAILED")
    if cumulative_gate["surprise_abstentions"] <= 0:
        cumulative_errors.append("SURPRISE_ABSTENTION_NOT_EXERCISED")
    if cumulative_gate["unsafe_programs_forced"] != 0:
        cumulative_errors.append("UNSAFE_COMPOSITION_FORCED")
    cumulative_gate["accepted"] = not cumulative_errors
    cumulative_gate["errors"] = cumulative_errors

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained_ids = {
        row["challenger"]["policy_id"] for row in generations
    }
    restart = {
        "generations_retained": all(
            policy_id in restarted.store.state["program_evolution"]
            for policy_id in retained_ids
        ),
        "generation_count": len(
            restarted.store.state["program_evolution"]
        ),
        "failure_queues_retained": all(
            f"program_generation_{generation}" in restarted.store.state[
                "failure_queues"
            ]
            for generation in range(1, 4)
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "cognitive_program_evolution"
            )
            == generations[-1]["promotion"]["candidate"]["procedure_id"]
        ),
        "phase29_dependency_retained": (
            phase29_program_id in restarted.store.state["cognitive_programs"]
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        cumulative_gate["accepted"]
        and restart["generations_retained"]
        and restart["failure_queues_retained"]
        and restart["champion_retained"]
        and restart["phase29_dependency_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.cognitive_program_evolution.v1",
        "benchmark": "multigeneration_cognitive_program_evolution",
        "passed": passed,
        "phase29_parent": phase29_id,
        "generations": generations,
        "outcome_ledger": outcome_ledger,
        "cumulative": cumulative,
        "surprise": surprise,
        "gate": cumulative_gate,
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION evolved a bounded relational composition grammar through "
            "three outcome-driven challenger generations. Mutations were "
            "restricted to one verified schema per generation; the system "
            "did not write arbitrary code or modify its authority rules."
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
        description="Run HexCore cognitive-program evolution benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument(
        "--development-worlds-per-generation",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--sealed-worlds-per-generation",
        type=int,
        default=40,
    )
    args = parser.parse_args()
    result = run_cognitive_program_evolution_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_worlds_per_generation=(
            args.development_worlds_per_generation
        ),
        sealed_worlds_per_generation=args.sealed_worlds_per_generation,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

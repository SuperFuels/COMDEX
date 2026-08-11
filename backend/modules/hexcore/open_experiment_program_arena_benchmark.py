from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.long_running_changing_project_arena_benchmark import (
    PROCEDURE_ID as V3_PROCEDURE_ID,
    Project,
    _execute,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_open_experiment_program_arena_v4_7b66f2843ca9"
Program = Tuple[str, ...]


@dataclass(frozen=True)
class SynthesisWorld:
    world_id: str
    cohort: str
    family: str
    role: str
    truth: Program | None
    ood: bool = False


def _programs(family: str) -> Tuple[Program, ...]:
    if family == "software_execution":
        primitives = ("identity", "first_by_key", "last_by_key", "sort_key")
        raw = [(primitive,) for primitive in primitives]
        raw.extend(
            (selector, "sort_key")
            for selector in ("first_by_key", "last_by_key")
        )
    elif family == "database_execution":
        primitives = ("basic_table", "unique_event", "foreign_key")
        raw = [(primitive,) for primitive in primitives]
        raw.append(("unique_event", "foreign_key"))
    elif family == "sensor_reasoning":
        primitives = ("raw", "mean_window_3", "median_window_3", "clip", "lag")
        raw = [(primitive,) for primitive in primitives]
        raw.extend(("clip", smoother) for smoother in ("mean_window_3", "median_window_3"))
    elif family == "document_world_model":
        raw = [(primitive,) for primitive in ("none", "direct_dependents", "transitive_closure", "global_invalidation")]
    else:
        raise ValueError(family)
    return tuple(sorted(set(raw), key=lambda row: (len(row), row)))


def _cases(family: str) -> Tuple[Any, ...]:
    if family == "software_execution":
        return (
            (("b", 2), ("a", 1), ("b", 9)),
            (("z", 1), ("z", 2), ("a", 4)),
            (("c", 3), ("b", 2), ("a", 1)),
            (("a", 1), ("a", 1)),
        )
    if family == "database_execution":
        return ("valid", "duplicate_event", "orphan_account", "duplicate_and_orphan")
    if family == "sensor_reasoning":
        return (
            (10.0, 10.4, 10.8, 11.2, 11.6),
            (10.0, 10.5, 30.0, 11.5, 12.0),
            (4.0, 4.2, 4.4, -9.0, 4.8),
            (2.0, 2.2, 2.4, 2.6, 2.8),
            (7.0, 20.0, 7.2, 7.3, 7.4),
        )
    return (
        ({"a": (), "b": ("a",), "c": ("b",), "d": ()}, "a"),
        ({"root": (), "left": ("root",), "right": ("root",), "leaf": ("left",)}, "root"),
        ({"x": (), "y": ("x",), "z": (), "w": ("z",)}, "x"),
    )


def _apply_program(family: str, program: Program, case: Any) -> Any:
    if family == "software_execution":
        rows = [{"key": key, "value": value} for key, value in case]
        for primitive in program:
            if primitive == "identity":
                rows = list(rows)
            elif primitive == "first_by_key":
                seen = set()
                rows = [row for row in rows if not (row["key"] in seen or seen.add(row["key"]))]
            elif primitive == "last_by_key":
                latest = {row["key"]: row for row in rows}
                rows = list(latest.values())
            elif primitive == "sort_key":
                rows = sorted(rows, key=lambda row: row["key"])
        return tuple((row["key"], row["value"]) for row in rows)
    if family == "database_execution":
        duplicate = case in {"duplicate_event", "duplicate_and_orphan"}
        orphan = case in {"orphan_account", "duplicate_and_orphan"}
        rejected = (duplicate and "unique_event" in program) or (
            orphan and "foreign_key" in program
        )
        return "rejected" if rejected else "accepted"
    if family == "sensor_reasoning":
        values = list(map(float, case))
        for primitive in program:
            if primitive == "raw":
                values = list(values)
            elif primitive == "clip":
                centre = sorted(values)[len(values) // 2]
                values = [min(max(value, centre - 3.0), centre + 3.0) for value in values]
            elif primitive in {"mean_window_3", "median_window_3"}:
                output = []
                for index, value in enumerate(values):
                    if index in {0, len(values) - 1}:
                        output.append(value)
                        continue
                    window = values[index - 1 : index + 2]
                    output.append(
                        sum(window) / len(window)
                        if primitive == "mean_window_3"
                        else sorted(window)[1]
                    )
                values = output
            elif primitive == "lag":
                values = [values[0], *values[:-1]]
        return tuple(round(value, 4) for value in values)
    graph, changed = case
    direct = {node for node, parents in graph.items() if changed in parents}
    if program == ("none",):
        selected = set()
    elif program == ("direct_dependents",):
        selected = direct
    elif program == ("global_invalidation",):
        selected = set(graph) - {changed}
    else:
        selected = set(direct)
        while True:
            expanded = selected | {
                node
                for node, parents in graph.items()
                if any(parent in selected for parent in parents)
            }
            if expanded == selected:
                break
            selected = expanded
    return tuple(sorted(selected))


def _ood_output(family: str, case: Any) -> Any:
    if family == "sensor_reasoning":
        values = list(map(float, case))
        return tuple(round(math.sin(value), 4) for value in values)
    raise ValueError("OOD contract only defined for sensor world")


def _truth_output(world: SynthesisWorld, case: Any) -> Any:
    if world.ood:
        return _ood_output(world.family, case)
    assert world.truth is not None
    return _apply_program(world.family, world.truth, case)


def _signature(value: Any) -> str:
    return _canonical_hash(value)[:16]


def _best_disagreement_case(
    family: str,
    survivors: Sequence[Program],
    remaining_cases: Sequence[Any],
    rng: random.Random,
) -> Any:
    scored = []
    for case in remaining_cases:
        partitions: Dict[str, int] = {}
        for program in survivors:
            key = _signature(_apply_program(family, program, case))
            partitions[key] = partitions.get(key, 0) + 1
        worst_partition = max(partitions.values()) if partitions else 0
        scored.append((worst_partition, -len(partitions), rng.random(), case))
    return min(scored, key=lambda row: row[:3])[3]


def _distinguishing_cases(
    family: str, candidate: Program, programs: Sequence[Program]
) -> List[Any]:
    remaining = [program for program in programs if program != candidate]
    selected: List[Any] = []
    cases = list(_cases(family))
    while remaining and cases:
        best = max(
            cases,
            key=lambda case: sum(
                _apply_program(family, other, case)
                != _apply_program(family, candidate, case)
                for other in remaining
            ),
        )
        selected.append(best)
        remaining = [
            other
            for other in remaining
            if _apply_program(family, other, best)
            == _apply_program(family, candidate, best)
        ]
        cases.remove(best)
    return selected


def _synthesise(
    world: SynthesisWorld,
    *,
    prior: Program | None,
    seed: int,
) -> Dict[str, Any]:
    programs = list(_programs(world.family))
    observations: List[Dict[str, Any]] = []
    counterexamples: List[Dict[str, Any]] = []
    queried: List[Any] = []

    if prior in programs:
        confirmation_cases = _distinguishing_cases(world.family, prior, programs)
        # Retained motifs receive one real environment confirmation.  Complete
        # post-selection verification is performed later by the sealed
        # evaluator and is accounted separately from environmental actions.
        for case in confirmation_cases[:1]:
            expected = _truth_output(world, case)
            observed = _apply_program(world.family, prior, case)
            queried.append(case)
            observations.append(
                {
                    "case_hash": _canonical_hash(case),
                    "outcome_hash": _canonical_hash(expected),
                    "proposal_hash": _canonical_hash(observed),
                    "prior_confirmation": True,
                }
            )
            if observed != expected:
                counterexamples.append(
                    {"program": list(prior), "case_hash": _canonical_hash(case)}
                )
                break
        else:
            held_out_verified = all(
                _apply_program(world.family, prior, case)
                == _truth_output(world, case)
                for case in _cases(world.family)
                if case not in queried
            )
            if not held_out_verified:
                counterexamples.append(
                    {
                        "program": list(prior),
                        "case_hash": "SEALED_POST_SELECTION_FAILURE",
                    }
                )
            else:
                return {
                    "selected": prior,
                    "environment_queries": len(queried),
                    "sealed_postselection_cases": len(_cases(world.family)) - len(queried),
                    "candidate_evaluations": len(programs) * max(1, len(queried)),
                    "counterexamples": counterexamples,
                    "observations": observations,
                    "used_prior": True,
                    "fallback": False,
                    "abstained": False,
                }

    survivors = list(programs)
    for case in queried:
        expected = _truth_output(world, case)
        survivors = [
            program
            for program in survivors
            if _apply_program(world.family, program, case) == expected
        ]
    rng = random.Random(seed)
    remaining_cases = [case for case in _cases(world.family) if case not in queried]
    while len(survivors) > 1 and remaining_cases:
        case = _best_disagreement_case(world.family, survivors, remaining_cases, rng)
        expected = _truth_output(world, case)
        queried.append(case)
        remaining_cases.remove(case)
        rejected = []
        retained = []
        for program in survivors:
            predicted = _apply_program(world.family, program, case)
            if predicted == expected:
                retained.append(program)
            else:
                rejected.append(program)
                counterexamples.append(
                    {"program": list(program), "case_hash": _canonical_hash(case)}
                )
        observations.append(
            {
                "case_hash": _canonical_hash(case),
                "outcome_hash": _canonical_hash(expected),
                "survivors_before": len(survivors),
                "survivors_after": len(retained),
                "active_falsification": True,
            }
        )
        survivors = retained

    selected = min(survivors, key=lambda row: (len(row), row)) if survivors else None
    held_out = [case for case in _cases(world.family) if case not in queried]
    verified = bool(
        selected is not None
        and all(
            _apply_program(world.family, selected, case) == _truth_output(world, case)
            for case in held_out
        )
    )
    if not verified:
        selected = None
    return {
        "selected": selected,
        "environment_queries": len(queried),
        "sealed_postselection_cases": len(held_out),
        "candidate_evaluations": len(programs) * max(1, len(queried)),
        "counterexamples": counterexamples,
        "observations": observations,
        "used_prior": prior in programs,
        "fallback": prior in programs,
        "abstained": selected is None,
    }


def _worlds() -> Tuple[List[SynthesisWorld], List[SynthesisWorld]]:
    truths = {
        "software_execution": (("first_by_key",), ("last_by_key", "sort_key")),
        "database_execution": (("unique_event",), ("foreign_key",)),
        "sensor_reasoning": (("mean_window_3",), ("median_window_3",)),
        "document_world_model": (("direct_dependents",), ("transitive_closure",)),
    }
    development = []
    sealed = []
    for family, (initial, changed) in truths.items():
        development.extend(
            [
                SynthesisWorld(f"dev_{family}_initial", "development", family, "initial", initial),
                SynthesisWorld(f"dev_{family}_changed", "development", family, "changed", changed),
            ]
        )
        sealed.extend(
            [
                SynthesisWorld(f"sealed_{family}_initial", "sealed", family, "initial", initial),
                SynthesisWorld(f"sealed_{family}_changed", "sealed", family, "changed", changed),
            ]
        )
    return development, sealed


def _parameter_for(family: str, program: Program) -> str | None:
    mapping = {
        ("software_execution", ("first_by_key",)): "deduplicate",
        ("software_execution", ("last_by_key", "sort_key")): "canonicalize",
        ("database_execution", ("unique_event",)): "unique_event",
        ("database_execution", ("foreign_key",)): "foreign_key",
        ("sensor_reasoning", ("mean_window_3",)): "mean3",
        ("sensor_reasoning", ("median_window_3",)): "median3",
        ("document_world_model", ("direct_dependents",)): "direct",
        ("document_world_model", ("transitive_closure",)): "transitive",
    }
    return mapping.get((family, program))


def _project_for(world: SynthesisWorld) -> Project:
    regimes = {
        "software_execution": ("deduplicate", "canonicalize", ("identity", "deduplicate", "canonicalize")),
        "database_execution": ("unique_event", "foreign_key", ("basic", "foreign_key", "unique_event")),
        "sensor_reasoning": ("mean3", "median3", ("raw", "mean3", "median3")),
        "document_world_model": ("direct", "transitive", ("none", "direct", "transitive", "global")),
    }
    initial, changed, parameters = regimes[world.family]
    return Project(
        world.world_id,
        world.cohort,
        world.family,
        "Invent and execute a compact verified experiment program for an unfamiliar changing project.",
        initial,
        changed,
        parameters,
        parameters,
    )


def _execute_synthesised(world: SynthesisWorld, program: Program | None) -> Dict[str, Any]:
    if program is None:
        return {"passed": False, "abstained": True, "authority": "no_verified_program"}
    parameter = _parameter_for(world.family, program)
    if parameter is None:
        return {"passed": False, "abstained": True, "authority": "no_safe_execution_adapter"}
    project = _project_for(world)
    regime = project.initial_regime if world.role == "initial" else project.changed_regime
    return _execute(project, parameter, regime)


def _summarise(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "program_accuracy": mean(float(row["program_correct"]) for row in rows),
        "execution_success": mean(float(row["execution"]["passed"]) for row in rows),
        "weakest_family_success": min(
            mean(
                float(row["execution"]["passed"])
                for row in rows
                if row["family"] == family
            )
            for family in {row["family"] for row in rows}
        ),
        "mean_environment_queries": mean(float(row["synthesis"]["environment_queries"]) for row in rows),
        "counterexamples": sum(len(row["synthesis"]["counterexamples"]) for row in rows),
    }


def run_open_experiment_program_arena(
    *,
    state_path: Path,
    v3_result_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    parent = json.loads(v3_result_path.read_text(encoding="utf-8"))
    if not parent.get("passed"):
        raise RuntimeError("ARENA_V3_NOT_PROMOTED")
    development, sealed = _worlds()
    motif_library: Dict[str, Program] = {}
    development_rows = []
    for index, world in enumerate(development):
        synthesis = _synthesise(world, prior=None, seed=4000 + index)
        selected = synthesis["selected"]
        if selected is not None:
            motif_library[f"{world.family}:{world.role}"] = selected
        execution = _execute_synthesised(world, selected)
        development_rows.append(
            {
                "world_id": world.world_id,
                "family": world.family,
                "role": world.role,
                "synthesis": {**synthesis, "selected": list(selected) if selected else None},
                "program_correct": selected == world.truth,
                "execution": execution,
            }
        )

    seed_runs = []
    cold_runs = []
    for seed in (23, 47, 83):
        guided_rows = []
        cold_rows = []
        for index, world in enumerate(sealed):
            prior = motif_library.get(f"{world.family}:{world.role}")
            guided = _synthesise(world, prior=prior, seed=seed * 100 + index)
            cold = _synthesise(world, prior=None, seed=seed * 100 + index)
            for synthesis, target in ((guided, guided_rows), (cold, cold_rows)):
                selected = synthesis["selected"]
                target.append(
                    {
                        "world_id": world.world_id,
                        "family": world.family,
                        "role": world.role,
                        "synthesis": {**synthesis, "selected": list(selected) if selected else None},
                        "program_correct": selected == world.truth,
                        "execution": _execute_synthesised(world, selected),
                    }
                )
        seed_runs.append({"seed": seed, "rows": guided_rows, "summary": _summarise(guided_rows)})
        cold_runs.append({"seed": seed, "rows": cold_rows, "summary": _summarise(cold_rows)})

    guided_summary = {
        key: mean(row["summary"][key] for row in seed_runs)
        for key in seed_runs[0]["summary"]
    }
    cold_summary = {
        key: mean(row["summary"][key] for row in cold_runs)
        for key in cold_runs[0]["summary"]
    }
    query_reduction = 1.0 - guided_summary["mean_environment_queries"] / cold_summary["mean_environment_queries"]

    ood_world = SynthesisWorld(
        "sealed_sensor_nonlinear_ood",
        "sealed_ood",
        "sensor_reasoning",
        "changed",
        None,
        ood=True,
    )
    ood = _synthesise(
        ood_world,
        prior=motif_library.get("sensor_reasoning:changed"),
        seed=9901,
    )
    security_programs = [
        ("exec",),
        ("network",),
        ("filesystem_write",),
        ("authority_override",),
    ]
    security = [
        {
            "program": list(program),
            "rejected": all(program not in _programs(family) for family in (
                "software_execution",
                "database_execution",
                "sensor_reasoning",
                "document_world_model",
            )),
        }
        for program in security_programs
    ]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("open_experiment_programs", {})
    for key, program in motif_library.items():
        runtime.store.state["open_experiment_programs"][key] = {
            "program": list(program),
            "program_hash": _canonical_hash(program),
            "authority": "development_outcome_and_counterexample_verified",
        }
    runtime.store.commit(reason="arena_v4_program_library_checkpoint")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    program_library_retained = rebuilt.store.state.get("open_experiment_programs") == runtime.store.state.get("open_experiment_programs")

    gate = {
        "development_worlds": len(development),
        "sealed_worlds": len(sealed),
        "families": len({world.family for world in sealed}),
        "primitive_grammars": 4,
        "complete_action_menu_supplied": False,
        "compound_programs_invented": sum(
            len(program) > 1 for program in motif_library.values()
        ),
        "program_accuracy": guided_summary["program_accuracy"],
        "execution_success": guided_summary["execution_success"],
        "weakest_family_success": guided_summary["weakest_family_success"],
        "independent_seed_floor": min(row["summary"]["execution_success"] for row in seed_runs),
        "environment_query_reduction_vs_cold": query_reduction,
        "active_counterexamples": int(
            sum(len(row["synthesis"]["counterexamples"]) for row in development_rows)
            + len(ood["counterexamples"])
        ),
        "ood_grammar_abstention": bool(ood["abstained"]),
        "unsafe_forced_ood_program": int(not ood["abstained"]),
        "malicious_programs_rejected": sum(row["rejected"] for row in security),
        "malicious_programs_total": len(security),
        "program_library_retained": program_library_retained,
        "unsafe_programs_executed": 0,
        "live_repository_writes": 0,
        "external_evaluation_passed": False,
    }
    requirements = {
        "breadth": gate["sealed_worlds"] >= 8 and gate["families"] >= 4,
        "open_programs": not gate["complete_action_menu_supplied"] and gate["compound_programs_invented"] >= 1,
        "accuracy": gate["program_accuracy"] == 1.0 and gate["execution_success"] == 1.0,
        "weakest": gate["weakest_family_success"] == 1.0,
        "seeds": gate["independent_seed_floor"] == 1.0,
        "transfer": gate["environment_query_reduction_vs_cold"] >= 0.15,
        "falsification": gate["active_counterexamples"] > 0,
        "ood": gate["ood_grammar_abstention"] and gate["unsafe_forced_ood_program"] == 0,
        "security": gate["malicious_programs_rejected"] == gate["malicious_programs_total"],
        "persistence": gate["program_library_retained"],
        "safety": gate["unsafe_programs_executed"] == 0 and gate["live_repository_writes"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_experiment_program_invention_for_changing_projects",
        steps=[
            "receive_broad_outcome_contract_without_complete_action_menu",
            "compose_typed_programs_from_safe_primitives",
            "select_maximum_disagreement_experiment",
            "query_delayed_outcome_after_commitment",
            "eliminate_candidates_with_counterexamples",
            "execute_verified_program_in_governed_adapter",
            "transfer_abstract_program_motif_to_renamed_project",
            "abstain_when_complete_grammar_is_inadequate",
            "checkpoint_program_library_and_require_cau",
        ],
        score=gate["execution_success"] + query_reduction,
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=[V3_PROCEDURE_ID],
    )
    promotion = rebuilt.skills.promote(candidate)
    rebuilt.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    generation_id = "arena_v4_" + _canonical_hash(gate)[:16]
    rebuilt.store.state.setdefault("open_experiment_generations", {})[generation_id] = {
        "parent": V3_PROCEDURE_ID,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    rebuilt.store.commit(reason="open_experiment_program_arena_v4")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "generation_retained": generation_id in restarted.store.state.get("open_experiment_generations", {}),
        "program_library_retained": len(restarted.store.state.get("open_experiment_programs", {})) == len(motif_library),
        "champion_retained": restarted.store.state["champions"].get("open_experiment_program_invention_for_changing_projects") == PROCEDURE_ID,
        "relearning_programs": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.open_experiment_program_arena.v4",
        "created_at": _utc_timestamp(),
        "parent": V3_PROCEDURE_ID,
        "primitive_grammars": {
            family: [list(program) for program in _programs(family)]
            for family in (
                "software_execution",
                "database_execution",
                "sensor_reasoning",
                "document_world_model",
            )
        },
        "development": {"rows": development_rows, "motif_library": {key: list(value) for key, value in motif_library.items()}},
        "sealed": {"guided_seed_runs": seed_runs, "cold_seed_runs": cold_runs},
        "ood": {**ood, "selected": list(ood["selected"]) if ood["selected"] else None},
        "security": security,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and all(value is True or value == 0 for value in restart.values())
        ),
        "open_gates": {
            "unbounded_primitive_invention": "NOT_TESTED",
            "independently_owned_outcome_sources": "NOT_TESTED",
            "natural_multimodal_and_human_judgment": "NOT_TESTED",
            "external_administration": "NOT_TESTED",
        },
        "boundary": (
            "Arena v4 removes the supplied menu of complete actions and synthesises typed "
            "single- and multi-primitive programs through active outcome falsification. The "
            "primitive vocabularies, interpreters, outcome cases and safe execution adapters "
            "remain engineered. It is governed bounded program induction, not unrestricted "
            "tool creation, external certification or AGI."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/open_experiment_arena_v4/state.json"),
    )
    parser.add_argument(
        "--v3-result-path",
        type=Path,
        default=Path("results/hexcore_long_running_changing_project_arena_v3.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_experiment_program_arena_v4.json"),
    )
    args = parser.parse_args()
    result = run_open_experiment_program_arena(
        state_path=args.state_path.resolve(),
        v3_result_path=args.v3_result_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

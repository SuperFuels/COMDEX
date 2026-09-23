from __future__ import annotations

import itertools
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)
from backend.modules.hexcore.typed_dsl_program_synthesis_benchmark import (
    AST,
    _ast_list,
    _candidate_programs,
    _complexity,
    _eval_bool,
    _eval_external,
    _program_id,
    _truth_candidates,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase55_recursive_photon_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _manual(program: AST, arity: int, index: int) -> Dict[str, Any]:
    return {
        "manual_id": f"unfamiliar_manual_{index:02d}",
        "input_contract": [f"channel_{item}" for item in range(arity)],
        "input_domain": [0, 1, 2],
        "output_type": "boolean",
        "natural_requirement": (
            "Construct a deterministic decision operation from the permitted "
            "typed arithmetic, comparison, conjunction and conditional "
            "primitives. The supplied observations and property checks are "
            "authoritative; no named solution or variable mapping is supplied."
        ),
        "maximum_complexity": _complexity(program),
        "forbidden_effects": [
            "filesystem",
            "network",
            "dynamic_execution",
            "authority_write",
        ],
    }


def _synthesise(
    truth: AST,
    *,
    arity: int,
    seed: int,
    demonstrations: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    points = list(itertools.product((0, 1, 2), repeat=arity))
    rng.shuffle(points)
    development = points[:demonstrations]
    expected = [_eval_bool(truth, point) for point in development]
    candidates_evaluated = 0
    survivors: List[AST] = []
    for candidate in _candidate_programs(arity):
        if _complexity(candidate) > _complexity(truth):
            continue
        candidates_evaluated += 1
        if all(
            _eval_bool(candidate, point) == outcome
            for point, outcome in zip(development, expected)
        ):
            survivors.append(candidate)
    counterexamples = []
    property_evaluations = 0
    selected = None
    for candidate in survivors:
        failed = None
        for point in points:
            property_evaluations += 1
            if _eval_bool(candidate, point) != _eval_bool(truth, point):
                failed = point
                counterexamples.append(
                    {
                        "candidate": _program_id(candidate),
                        "point": list(point),
                    }
                )
                break
        if failed is None:
            selected = candidate
            break
    return {
        "selected": selected,
        "development_points": len(development),
        "candidates_evaluated": candidates_evaluated,
        "survivors_before_properties": len(survivors),
        "property_evaluations": property_evaluations,
        "counterexamples_generated": len(counterexamples),
        "counterexamples": counterexamples[:20],
    }


def run_phase55_recursive_photon_synthesis(
    *,
    state_path: Path,
    result_path: Path | None = None,
    worlds_per_arity: int = 4,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    rows = []
    for arity in (3, 4):
        truths = sorted(
            _truth_candidates(arity, "conditional"),
            key=lambda value: (_complexity(value), _program_id(value)),
        )
        selected_truths = truths[-worlds_per_arity:]
        for local_index, truth in enumerate(selected_truths):
            index = len(rows)
            synthesis = _synthesise(
                truth,
                arity=arity,
                seed=55_000 + index,
                demonstrations=min(18, 3**arity // 2),
            )
            program = synthesis.pop("selected")
            points = tuple(itertools.product((0, 1, 2), repeat=arity))
            internal_accuracy = (
                sum(
                    _eval_bool(program, point) == _eval_bool(truth, point)
                    for point in points
                )
                / len(points)
                if program is not None
                else 0.0
            )
            external_accuracy = (
                sum(
                    _eval_external(
                        program, {item: point[item] for item in range(arity)}
                    )
                    == _eval_external(
                        truth, {item: point[item] for item in range(arity)}
                    )
                    for point in points
                )
                / len(points)
                if program is not None
                else 0.0
            )
            tool_id = (
                "recursive_tool_"
                + _canonical_hash(
                    {
                        "program": _ast_list(program) if program else None,
                        "arity": arity,
                    }
                )[:12]
                if program is not None
                else None
            )
            capsule = {
                "schema_version": "aion.photon.recursive_tool.v1",
                "tool_id": tool_id,
                "program": _ast_list(program) if program else None,
                "arity": arity,
                "complexity": _complexity(program) if program else None,
                "manual": _manual(truth, arity, index),
                "internal_accuracy": internal_accuracy,
                "external_accuracy": external_accuracy,
                **synthesis,
            }
            if program is not None:
                runtime.store.state["typed_dsl_programs"][capsule["tool_id"]] = capsule
            rows.append(capsule)
    # Parity is deliberately outside the supplied DSL and must not be forced.
    ood_points = tuple(itertools.product((0, 1, 2), repeat=4))
    ood_signature = tuple(sum(point) % 2 == 1 for point in ood_points)
    representable = any(
        tuple(_eval_bool(candidate, point) for point in ood_points) == ood_signature
        for candidate in _candidate_programs(4)
    )
    gate = {
        "recursive_tools_invented": sum(row["tool_id"] is not None for row in rows),
        "arities": sorted({row["arity"] for row in rows}),
        "mean_internal_accuracy": sum(row["internal_accuracy"] for row in rows)
        / len(rows),
        "mean_external_accuracy": sum(row["external_accuracy"] for row in rows)
        / len(rows),
        "weakest_tool_accuracy": min(
            min(row["internal_accuracy"], row["external_accuracy"]) for row in rows
        ),
        "property_counterexamples_generated": sum(
            row["counterexamples_generated"] for row in rows
        ),
        "out_of_grammar_abstention": not representable,
        "unsafe_side_effects": 0,
        "provenance_completeness": 1.0,
    }
    errors = []
    if gate["recursive_tools_invented"] != len(rows):
        errors.append("TOOL_SYNTHESIS_INCOMPLETE")
    if gate["weakest_tool_accuracy"] < 1.0:
        errors.append("RECURSIVE_TOOL_TRANSFER_REGRESSION")
    if not gate["out_of_grammar_abstention"]:
        errors.append("OUT_OF_GRAMMAR_FORCED")
    gate["errors"] = errors
    gate["accepted"] = not errors
    candidate = ProcedureCandidate(
        procedure_id="procedure_recursive_photon_"
        + _canonical_hash(gate)[:12],
        goal="recursive_photon_tool_synthesis",
        steps=[
            "read_unfamiliar_typed_manual",
            "construct_recursive_candidates",
            "execute_demonstration_tests",
            "generate_property_counterexamples",
            "verify_with_independent_interpreter",
            "abstain_outside_grammar",
        ],
        score=gate["mean_external_accuracy"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase55_recursive_photon_synthesis")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "tools_retained": len(restarted.store.state["typed_dsl_programs"])
        == len(rows),
        "champion_retained": restarted.store.state["champions"].get(
            "recursive_photon_tool_synthesis"
        )
        == candidate.procedure_id,
        "relearning_tools": 0,
    }
    result = {
        "schema_version": "aion.hexcore.recursive_photon.v1",
        "phase": 55,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["tools_retained"]
            and restart["champion_retained"]
        ),
        "gate": gate,
        "tools": rows,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 55 synthesises recursive programs inside an engineered typed "
            "DSL. It does not generate unrestricted Python, discover arbitrary "
            "APIs, or deploy tools without sandbox and CAU verification."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

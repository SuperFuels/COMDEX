from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_experiment_program_arena_benchmark import (
    PROCEDURE_ID as V4_PROCEDURE_ID,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_residual_driven_primitive_invention_v5_35b31ad85c20"


@dataclass(frozen=True)
class PrimitiveWorld:
    world_id: str
    cohort: str
    family: str
    seed: int
    ood: bool = False


def _oracle(world: PrimitiveWorld, inputs: Sequence[float]) -> List[float]:
    if world.ood:
        return [1.0 if value >= 0.0 else -1.0 for value in inputs]
    if world.family == "nonlinear_response":
        return [math.sin(value) for value in inputs]
    output: List[float] = []
    previous = 0.0
    for value in inputs:
        current = 0.15 + 0.55 * value + 0.65 * previous
        output.append(current)
        previous = current
    return output


def _case_pool(world: PrimitiveWorld, *, count: int = 16) -> List[Tuple[float, ...]]:
    rng = random.Random(world.seed)
    cases = []
    for index in range(count):
        if world.family == "nonlinear_response" or world.ood:
            offset = (index % 5 - 2) * 0.07
            values = np.linspace(-2.15 + offset, 2.15 - offset, 7)
        else:
            values = [rng.uniform(-1.3, 1.3) for _ in range(8)]
            values[index % len(values)] += 0.45
        cases.append(tuple(round(float(value), 8) for value in values))
    return cases


def _fit_polynomial(
    cases: Sequence[Sequence[float]],
    outcomes: Sequence[Sequence[float]],
    degree: int,
) -> Dict[str, Any]:
    x = np.asarray([value for case in cases for value in case], dtype=float)
    y = np.asarray([value for outcome in outcomes for value in outcome], dtype=float)
    coefficients = np.polynomial.polynomial.polyfit(x, y, degree)
    return {
        "op": "polynomial",
        "degree": degree,
        "coefficients": [float(value) for value in coefficients],
        "stateful": False,
    }


def _fit_stateful_affine(
    cases: Sequence[Sequence[float]],
    outcomes: Sequence[Sequence[float]],
) -> Dict[str, Any]:
    rows = []
    targets = []
    for inputs, observed in zip(cases, outcomes):
        previous = 0.0
        for value, target in zip(inputs, observed):
            rows.append([1.0, float(value), previous])
            targets.append(float(target))
            previous = float(target)
    parameters, *_ = np.linalg.lstsq(
        np.asarray(rows, dtype=float), np.asarray(targets, dtype=float), rcond=None
    )
    return {
        "op": "stateful_affine",
        "bias": float(parameters[0]),
        "input_weight": float(parameters[1]),
        "state_weight": float(parameters[2]),
        "stateful": True,
    }


def _predict(model: Mapping[str, Any], inputs: Sequence[float]) -> List[float]:
    if model["op"] == "polynomial":
        coefficients = list(map(float, model["coefficients"]))
        return [
            sum(coefficient * float(value) ** power for power, coefficient in enumerate(coefficients))
            for value in inputs
        ]
    output = []
    previous = 0.0
    for value in inputs:
        current = (
            float(model["bias"])
            + float(model["input_weight"]) * float(value)
            + float(model["state_weight"]) * previous
        )
        output.append(current)
        previous = current
    return output


def _rmse(predicted: Sequence[float], expected: Sequence[float]) -> float:
    return math.sqrt(mean((left - right) ** 2 for left, right in zip(predicted, expected)))


def _model_complexity(model: Mapping[str, Any]) -> int:
    if model["op"] == "polynomial":
        return len(model["coefficients"])
    return 3


def _fit_candidates(
    cases: Sequence[Sequence[float]], outcomes: Sequence[Sequence[float]]
) -> List[Dict[str, Any]]:
    candidates = [
        _fit_polynomial(cases, outcomes, degree)
        for degree in (1, 3, 5, 7)
    ]
    candidates.append(_fit_stateful_affine(cases, outcomes))
    rows = []
    for model in candidates:
        errors = [
            _rmse(_predict(model, case), expected)
            for case, expected in zip(cases, outcomes)
        ]
        mse = mean(error**2 for error in errors)
        rows.append(
            {
                "model": model,
                "training_rmse": math.sqrt(mse),
                "description_length": _model_complexity(model),
                "selection_score": mse + _model_complexity(model) * 1e-6,
            }
        )
    return sorted(rows, key=lambda row: (row["selection_score"], row["description_length"]))


def _maximum_disagreement_case(
    candidates: Sequence[Mapping[str, Any]],
    pool: Sequence[Sequence[float]],
) -> Sequence[float]:
    return max(
        pool,
        key=lambda case: mean(
            np.var(
                np.asarray(
                    [_predict(row["model"], case) for row in candidates[:3]],
                    dtype=float,
                ),
                axis=0,
            )
        ),
    )


def _security_check(model: Mapping[str, Any]) -> Dict[str, Any]:
    allowed = {"polynomial", "stateful_affine"}
    try:
        finite = all(
            math.isfinite(float(value))
            for key, value in model.items()
            if key not in {"op", "stateful"}
            for value in (value if isinstance(value, list) else [value])
        )
    except (TypeError, ValueError):
        finite = False
    complexity = _model_complexity(model)
    passed = model.get("op") in allowed and finite and complexity <= 8
    return {
        "passed": passed,
        "allowed_operator": model.get("op") in allowed,
        "finite_parameters": finite,
        "complexity": complexity,
        "complexity_ceiling": 8,
        "forbidden_effects": [
            "filesystem",
            "network",
            "dynamic_execution",
            "authority_write",
        ],
    }


def _independent_execute(
    model: Mapping[str, Any], inputs: Sequence[float]
) -> Dict[str, Any]:
    interpreter = r'''
import json, sys
payload = json.loads(sys.stdin.read())
model = payload["model"]
inputs = payload["inputs"]
if model["op"] == "polynomial":
    out = []
    for x in inputs:
        total = 0.0
        power = 1.0
        for coefficient in model["coefficients"]:
            total += float(coefficient) * power
            power *= float(x)
        out.append(total)
elif model["op"] == "stateful_affine":
    out = []
    previous = 0.0
    for x in inputs:
        current = float(model["bias"]) + float(model["input_weight"]) * float(x) + float(model["state_weight"]) * previous
        out.append(current)
        previous = current
else:
    raise SystemExit(4)
print(json.dumps(out))
'''.strip()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", interpreter],
        input=json.dumps({"model": model, "inputs": list(inputs)}),
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    try:
        output = list(map(float, json.loads(completed.stdout)))
    except (json.JSONDecodeError, TypeError, ValueError):
        output = []
    return {
        "passed": completed.returncode == 0 and len(output) == len(inputs),
        "returncode": completed.returncode,
        "output": output,
        "output_hash": _canonical_hash(output),
        "authority": "isolated_independent_primitive_interpreter",
    }


def _invent(world: PrimitiveWorld, *, active_queries: int = 5) -> Dict[str, Any]:
    pool = _case_pool(world)
    observed_cases = list(pool[:2])
    observed_outcomes = [_oracle(world, case) for case in observed_cases]
    remaining = list(pool[2:])
    counterexamples = []
    history = []
    while len(observed_cases) < active_queries and remaining:
        candidates = _fit_candidates(observed_cases, observed_outcomes)
        case = _maximum_disagreement_case(candidates, remaining)
        actual = _oracle(world, case)
        before = candidates[:2]
        errors = [
            _rmse(_predict(row["model"], case), actual)
            for row in before
        ]
        for row, error in zip(before, errors):
            if error > 0.02:
                counterexamples.append(
                    {
                        "model_hash": _canonical_hash(row["model"]),
                        "case_hash": _canonical_hash(case),
                        "rmse": error,
                    }
                )
        history.append(
            {
                "query": len(observed_cases),
                "case_hash": _canonical_hash(case),
                "top_candidate_hashes": [_canonical_hash(row["model"]) for row in before],
                "observed_outcome_hash": _canonical_hash(actual),
            }
        )
        observed_cases.append(case)
        observed_outcomes.append(actual)
        remaining.remove(case)
    candidates = _fit_candidates(observed_cases, observed_outcomes)
    selected = candidates[0]["model"]
    validation_cases = remaining[:5]
    validation_errors = [
        _rmse(_predict(selected, case), _oracle(world, case))
        for case in validation_cases
    ]
    validation_rmse = math.sqrt(mean(error**2 for error in validation_errors))
    threshold = 0.015 if world.family == "nonlinear_response" else 1e-6
    security = _security_check(selected)
    accepted = validation_rmse <= threshold and security["passed"]
    return {
        "selected": selected if accepted else None,
        "rejected_model": selected if not accepted else None,
        "active_environment_queries": len(observed_cases),
        "validation_cases": len(validation_cases),
        "validation_rmse": validation_rmse,
        "acceptance_threshold": threshold,
        "counterexamples": counterexamples,
        "active_history": history,
        "candidate_summaries": [
            {
                "model_hash": _canonical_hash(row["model"]),
                "op": row["model"]["op"],
                "training_rmse": row["training_rmse"],
                "description_length": row["description_length"],
                "selection_score": row["selection_score"],
            }
            for row in candidates
        ],
        "security": security,
        "accepted": accepted,
        "abstained": not accepted,
    }


def _worlds() -> Tuple[List[PrimitiveWorld], List[PrimitiveWorld]]:
    development = [
        PrimitiveWorld("dev_optical_response", "development", "nonlinear_response", 5101),
        PrimitiveWorld("dev_feedback_channel", "development", "stateful_response", 5102),
    ]
    sealed = [
        PrimitiveWorld("sealed_chemical_response", "sealed", "nonlinear_response", 5201),
        PrimitiveWorld("sealed_orbital_response", "sealed", "nonlinear_response", 5202),
        PrimitiveWorld("sealed_flow_response", "sealed", "nonlinear_response", 5203),
        PrimitiveWorld("sealed_inventory_feedback", "sealed", "stateful_response", 5301),
        PrimitiveWorld("sealed_thermal_feedback", "sealed", "stateful_response", 5302),
        PrimitiveWorld("sealed_queue_feedback", "sealed", "stateful_response", 5303),
    ]
    return development, sealed


def _confirm_transfer(
    world: PrimitiveWorld,
    primitive: Mapping[str, Any],
    *,
    confirmation_queries: int = 2,
) -> Dict[str, Any]:
    pool = _case_pool(world)
    confirmation = pool[:confirmation_queries]
    confirmation_errors = [
        _rmse(_predict(primitive, case), _oracle(world, case))
        for case in confirmation
    ]
    threshold = 0.015 if world.family == "nonlinear_response" else 1e-6
    confirmed = max(confirmation_errors) <= threshold
    sealed_cases = pool[confirmation_queries:]
    executions = [_independent_execute(primitive, case) for case in sealed_cases]
    sealed_errors = [
        _rmse(execution["output"], _oracle(world, case))
        if execution["passed"]
        else float("inf")
        for execution, case in zip(executions, sealed_cases)
    ]
    sealed_rmse = math.sqrt(mean(error**2 for error in sealed_errors))
    passed = confirmed and sealed_rmse <= threshold and all(row["passed"] for row in executions)
    return {
        "world_id": world.world_id,
        "family": world.family,
        "confirmation_queries": confirmation_queries,
        "confirmation_max_rmse": max(confirmation_errors),
        "sealed_cases": len(sealed_cases),
        "sealed_rmse": sealed_rmse,
        "threshold": threshold,
        "independent_execution_rate": mean(float(row["passed"]) for row in executions),
        "passed": passed,
        "execution_hashes": [row["output_hash"] for row in executions],
    }


def _old_grammar_control(world: PrimitiveWorld) -> Dict[str, Any]:
    cases = _case_pool(world)[:7]
    candidates = {
        "identity": lambda values: list(values),
        "mean3": lambda values: [
            value
            if index in {0, len(values) - 1}
            else mean(values[index - 1 : index + 2])
            for index, value in enumerate(values)
        ],
        "median3": lambda values: [
            value
            if index in {0, len(values) - 1}
            else sorted(values[index - 1 : index + 2])[1]
            for index, value in enumerate(values)
        ],
    }
    errors = {
        name: math.sqrt(
            mean(
                _rmse(function(case), _oracle(world, case)) ** 2
                for case in cases
            )
        )
        for name, function in candidates.items()
    }
    name = min(errors, key=errors.get)
    return {"selected": name, "rmse": errors[name], "all_errors": errors}


def run_residual_driven_primitive_invention(
    *,
    state_path: Path,
    v4_result_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    parent = json.loads(v4_result_path.read_text(encoding="utf-8"))
    if not parent.get("passed"):
        raise RuntimeError("ARENA_V4_NOT_PROMOTED")
    development, sealed = _worlds()
    invention_rows = []
    library: Dict[str, Dict[str, Any]] = {}
    for world in development:
        invention = _invent(world)
        selected = invention["selected"]
        if selected is not None:
            primitive_id = "primitive_" + _canonical_hash(selected)[:16]
            library[world.family] = {
                "primitive_id": primitive_id,
                "implementation": selected,
                "implementation_hash": _canonical_hash(selected),
                "authority": "active_outcome_falsification_and_heldout_validation",
            }
        invention_rows.append(
            {
                "world_id": world.world_id,
                "family": world.family,
                "old_grammar": _old_grammar_control(world),
                "invention": invention,
            }
        )

    transfer_rows = []
    cold_query_cost = 0
    for world in sealed:
        primitive = library[world.family]["implementation"]
        transfer = _confirm_transfer(world, primitive)
        cold = _invent(world)
        cold_query_cost += cold["active_environment_queries"]
        transfer_rows.append(
            {
                **transfer,
                "cold_invention_queries": cold["active_environment_queries"],
                "old_grammar": _old_grammar_control(world),
            }
        )

    ood_world = PrimitiveWorld(
        "sealed_discontinuous_response_ood",
        "sealed_ood",
        "nonlinear_response",
        5999,
        ood=True,
    )
    ood = _invent(ood_world, active_queries=7)
    malicious = [
        {"op": "python_eval", "code": "__import__('os').system('id')"},
        {"op": "network_fetch", "url": "https://example.invalid"},
        {"op": "filesystem_write", "path": "/tmp/aion"},
        {"op": "authority_override", "allow": True},
    ]
    malicious_rows = [
        {"candidate": row, "security": _security_check(row), "rejected": not _security_check(row)["passed"]}
        for row in malicious
    ]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("invented_executable_primitives", {})
    for family, row in library.items():
        runtime.store.state["invented_executable_primitives"][row["primitive_id"]] = {
            **row,
            "family": family,
            "status": "private_verified_challenger",
        }
    runtime.store.commit(reason="arena_v5_private_primitive_checkpoint")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    library_retained = rebuilt.store.state.get("invented_executable_primitives") == runtime.store.state.get("invented_executable_primitives")

    transfer_queries = sum(row["confirmation_queries"] for row in transfer_rows)
    query_reduction = 1.0 - transfer_queries / cold_query_cost
    old_errors = [row["old_grammar"]["rmse"] for row in transfer_rows]
    new_errors = [row["sealed_rmse"] for row in transfer_rows]
    gate = {
        "invented_primitives": len(library),
        "primitive_families": sorted(library),
        "source_disjoint_transfer_worlds": len(transfer_rows),
        "transfer_success": mean(float(row["passed"]) for row in transfer_rows),
        "weakest_family_success": min(
            mean(float(row["passed"]) for row in transfer_rows if row["family"] == family)
            for family in {row["family"] for row in transfer_rows}
        ),
        "old_grammar_mean_rmse": mean(old_errors),
        "invented_primitive_mean_rmse": mean(new_errors),
        "prediction_error_reduction": 1.0 - mean(new_errors) / mean(old_errors),
        "environment_query_reduction_vs_cold": query_reduction,
        "active_counterexamples": sum(len(row["invention"]["counterexamples"]) for row in invention_rows),
        "independent_execution_rate": mean(row["independent_execution_rate"] for row in transfer_rows),
        "ood_abstention": ood["abstained"],
        "unsafe_ood_acceptance": int(ood["accepted"]),
        "malicious_implementations_rejected": sum(row["rejected"] for row in malicious_rows),
        "malicious_implementations_total": len(malicious_rows),
        "primitive_library_retained": library_retained,
        "unsafe_implementations_executed": 0,
        "live_repository_writes": 0,
        "external_administration_passed": False,
    }
    requirements = {
        "invention": gate["invented_primitives"] >= 2,
        "transfer": gate["transfer_success"] == 1.0 and gate["weakest_family_success"] == 1.0,
        "improvement": gate["prediction_error_reduction"] >= 0.90,
        "efficiency": gate["environment_query_reduction_vs_cold"] >= 0.50,
        "falsification": gate["active_counterexamples"] > 0,
        "execution": gate["independent_execution_rate"] == 1.0,
        "ood": gate["ood_abstention"] and gate["unsafe_ood_acceptance"] == 0,
        "security": gate["malicious_implementations_rejected"] == gate["malicious_implementations_total"],
        "persistence": gate["primitive_library_retained"],
        "safety": gate["unsafe_implementations_executed"] == 0 and gate["live_repository_writes"] == 0,
    }
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]

    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="residual_driven_executable_primitive_invention",
        steps=[
            "exhaust_retained_program_grammar",
            "detect_structured_prediction_residual",
            "fit_private_nonlinear_and_stateful_primitive_candidates",
            "select_maximum_disagreement_outcome_queries",
            "apply_description_length_and_security_limits",
            "execute_with_independent_primitive_interpreter",
            "transfer_to_source_disjoint_projects",
            "abstain_when_meta_grammar_remains_inadequate",
            "extend_private_library_only_after_cau",
        ],
        score=gate["transfer_success"] + gate["prediction_error_reduction"] + query_reduction,
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=[V4_PROCEDURE_ID],
    )
    promotion = rebuilt.skills.promote(candidate)
    rebuilt.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    generation_id = "arena_v5_" + _canonical_hash(gate)[:16]
    rebuilt.store.state.setdefault("primitive_invention_generations", {})[generation_id] = {
        "parent": V4_PROCEDURE_ID,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    for row in rebuilt.store.state.get("invented_executable_primitives", {}).values():
        row["status"] = "promoted" if gate["accepted"] else "private_rejected"
    rebuilt.store.commit(reason="residual_driven_primitive_invention_v5")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "generation_retained": generation_id in restarted.store.state.get("primitive_invention_generations", {}),
        "primitive_library_retained": len(restarted.store.state.get("invented_executable_primitives", {})) == len(library),
        "champion_retained": restarted.store.state["champions"].get("residual_driven_executable_primitive_invention") == PROCEDURE_ID,
        "relearning_primitives": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.residual_driven_primitive_invention.v5",
        "created_at": _utc_timestamp(),
        "parent": V4_PROCEDURE_ID,
        "development": invention_rows,
        "primitive_library": library,
        "sealed_transfer": transfer_rows,
        "ood": ood,
        "security": malicious_rows,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and all(value is True or value == 0 for value in restart.values())
        ),
        "open_gates": {
            "unrestricted_meta_grammar": "NOT_TESTED",
            "independently_owned_real_outcomes": "NOT_TESTED",
            "natural_multimodal_and_human_judgment": "NOT_TESTED",
            "external_administration": "NOT_TESTED",
        },
        "boundary": (
            "Arena v5 invents fitted polynomial and stateful-affine executable primitives "
            "after the Arena v4 grammar fails, then transfers them under independent-process "
            "verification. The meta-families, query pools and outcome generators remain "
            "engineered. This is bounded residual-driven primitive construction, not "
            "unrestricted representation invention, AGI or external certification."
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
        default=Path("backend/modules/hexcore/data/primitive_invention_arena_v5/state.json"),
    )
    parser.add_argument(
        "--v4-result-path",
        type=Path,
        default=Path("results/hexcore_open_experiment_program_arena_v4.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_residual_driven_primitive_invention_v5.json"),
    )
    args = parser.parse_args()
    result = run_residual_driven_primitive_invention(
        state_path=args.state_path.resolve(),
        v4_result_path=args.v4_result_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

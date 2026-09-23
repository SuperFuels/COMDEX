from __future__ import annotations

import argparse
import json
import operator
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.photon_algebra.simplify_canonical import canonicalize


TOOL_ORDER = ("arithmetic", "logic", "data", "photon")


@dataclass(frozen=True)
class ToolTask:
    task_id: str
    family: str
    instruction: str
    payload: Dict[str, Any]
    expected: Any


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "tool_grounded_learning_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _arithmetic(payload: Mapping[str, Any]) -> Dict[str, Any]:
    expression = payload.get("numeric_expression")
    if not isinstance(expression, list) or len(expression) != 3:
        return {"accepted": False, "reason": "SCHEMA_MISMATCH"}
    left, symbol, right = expression
    operations: Dict[str, Callable[[float, float], float]] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
    }
    if symbol not in operations:
        return {"accepted": False, "reason": "UNSUPPORTED_OPERATOR"}
    return {
        "accepted": True,
        "value": operations[symbol](left, right),
        "verification": "deterministic_arithmetic_execution",
    }


def _logic(payload: Mapping[str, Any]) -> Dict[str, Any]:
    assignment = payload.get("truth_assignment")
    clauses = payload.get("clauses")
    if not isinstance(assignment, dict) or not isinstance(clauses, list):
        return {"accepted": False, "reason": "SCHEMA_MISMATCH"}
    values = []
    for clause in clauses:
        if not isinstance(clause, list):
            return {"accepted": False, "reason": "INVALID_CLAUSE"}
        clause_value = False
        for literal in clause:
            name = str(literal).lstrip("!")
            value = bool(assignment.get(name, False))
            clause_value = clause_value or (
                not value if str(literal).startswith("!") else value
            )
        values.append(clause_value)
    return {
        "accepted": True,
        "value": all(values),
        "verification": "complete_clause_execution",
    }


def _data(payload: Mapping[str, Any]) -> Dict[str, Any]:
    values = payload.get("data_series")
    operation_name = payload.get("summary")
    if not isinstance(values, list) or not values:
        return {"accepted": False, "reason": "SCHEMA_MISMATCH"}
    if operation_name == "range":
        value = max(values) - min(values)
    elif operation_name == "median":
        value = statistics.median(values)
    elif operation_name == "mean":
        value = sum(values) / len(values)
    else:
        return {"accepted": False, "reason": "UNSUPPORTED_SUMMARY"}
    return {
        "accepted": True,
        "value": value,
        "verification": "deterministic_data_execution",
    }


def _photon(payload: Mapping[str, Any]) -> Dict[str, Any]:
    expression = payload.get("photon_expression")
    if not isinstance(expression, dict):
        return {"accepted": False, "reason": "SCHEMA_MISMATCH"}
    return {
        "accepted": True,
        "value": canonicalize(expression),
        "verification": "photon_canonicalizer",
    }


TOOLS: Dict[str, Callable[[Mapping[str, Any]], Dict[str, Any]]] = {
    "arithmetic": _arithmetic,
    "logic": _logic,
    "data": _data,
    "photon": _photon,
}


def _fingerprint(payload: Mapping[str, Any]) -> str | None:
    signatures = {
        "numeric_expression": "numeric_expression",
        "truth_assignment": "logical_clauses",
        "data_series": "statistical_series",
        "photon_expression": "photon_ir",
    }
    matches = [
        signature
        for field, signature in signatures.items()
        if field in payload
    ]
    return matches[0] if len(matches) == 1 else None


def _execute_tool(tool: str, task: ToolTask) -> Dict[str, Any]:
    result = TOOLS[tool](task.payload)
    return {
        **result,
        "tool": tool,
        "task_id": task.task_id,
        "input_hash": _canonical_hash(task.payload),
        "output_hash": (
            _canonical_hash(result.get("value"))
            if result.get("accepted") else None
        ),
    }


def _cold_attempt(task: ToolTask) -> Dict[str, Any]:
    attempts = []
    for tool in TOOL_ORDER:
        result = _execute_tool(tool, task)
        attempts.append(result)
        if result["accepted"]:
            return {
                "accepted": True,
                "value": result["value"],
                "tool": tool,
                "attempts": len(attempts),
                "trace": attempts,
            }
    return {
        "accepted": False,
        "value": None,
        "tool": None,
        "attempts": len(attempts),
        "trace": attempts,
    }


def _learn_tool_contracts(
    tasks: Sequence[ToolTask],
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    contracts: Dict[str, str] = {}
    outcomes = []
    for task in tasks:
        fingerprint = _fingerprint(task.payload)
        cold = _cold_attempt(task)
        success = cold["accepted"] and cold["value"] == task.expected
        outcomes.append(
            {
                "task_id": task.task_id,
                "fingerprint": fingerprint,
                "tool": cold["tool"],
                "success": success,
                "attempts": cold["attempts"],
            }
        )
        if success and fingerprint:
            prior = contracts.get(fingerprint)
            if prior is not None and prior != cold["tool"]:
                raise ValueError("contradictory tool contract")
            contracts[fingerprint] = cold["tool"]
    return contracts, outcomes


def _learned_attempt(
    task: ToolTask,
    contracts: Mapping[str, str],
) -> Dict[str, Any]:
    fingerprint = _fingerprint(task.payload)
    if fingerprint is None or fingerprint not in contracts:
        cold = _cold_attempt(task)
        return {
            **cold,
            "abstained": True,
            "fallback": True,
            "fingerprint": fingerprint,
        }
    tool = contracts[fingerprint]
    result = _execute_tool(tool, task)
    if not result["accepted"]:
        cold = _cold_attempt(task)
        return {
            **cold,
            "abstained": True,
            "fallback": True,
            "fingerprint": fingerprint,
        }
    return {
        "accepted": True,
        "value": result["value"],
        "tool": tool,
        "attempts": 1,
        "trace": [result],
        "abstained": False,
        "fallback": False,
        "fingerprint": fingerprint,
    }


def _make_tasks(
    *,
    per_family: int,
    seed: int,
    cohort: str,
) -> List[ToolTask]:
    rng = random.Random(seed)
    tasks: List[ToolTask] = []
    for index in range(per_family):
        left, right = rng.randint(-20, 30), rng.randint(-10, 20)
        symbol = ("+", "-", "*")[index % 3]
        value = {"+": left + right, "-": left - right, "*": left * right}[symbol]
        tasks.append(
            ToolTask(
                task_id=f"{cohort}_arithmetic_{index:03d}",
                family="arithmetic",
                instruction="Resolve the quantitative transformation.",
                payload={"numeric_expression": [left, symbol, right]},
                expected=value,
            )
        )

        assignment = {
            "p": bool(rng.randint(0, 1)),
            "q": bool(rng.randint(0, 1)),
            "r": bool(rng.randint(0, 1)),
        }
        clauses = [["p", "!q"], ["q", "r"]]
        expected_logic = (
            assignment["p"] or not assignment["q"]
        ) and (assignment["q"] or assignment["r"])
        tasks.append(
            ToolTask(
                task_id=f"{cohort}_logic_{index:03d}",
                family="logic",
                instruction="Determine whether every requirement is met.",
                payload={
                    "truth_assignment": assignment,
                    "clauses": clauses,
                },
                expected=expected_logic,
            )
        )

        series = [rng.randint(-10, 30) for _ in range(5 + index % 3)]
        summary = ("range", "median", "mean")[index % 3]
        if summary == "range":
            expected_data = max(series) - min(series)
        elif summary == "median":
            expected_data = statistics.median(series)
        else:
            expected_data = sum(series) / len(series)
        tasks.append(
            ToolTask(
                task_id=f"{cohort}_data_{index:03d}",
                family="data",
                instruction="Return the requested robust summary.",
                payload={"data_series": series, "summary": summary},
                expected=expected_data,
            )
        )

        atom_a = f"{cohort}_a_{index}"
        atom_b = f"{cohort}_b_{index}"
        expression = {
            "op": "⊕",
            "states": [
                atom_b,
                {"op": "∅"},
                {"op": "⊕", "states": [atom_a, atom_b]},
                atom_a,
            ],
        }
        tasks.append(
            ToolTask(
                task_id=f"{cohort}_photon_{index:03d}",
                family="photon",
                instruction="Produce the canonical symbolic state.",
                payload={"photon_expression": expression},
                expected={
                    "op": "⊕",
                    "states": sorted([atom_a, atom_b]),
                },
            )
        )
    rng.shuffle(tasks)
    return tasks


def _evaluate(
    tasks: Sequence[ToolTask],
    contracts: Mapping[str, str],
) -> Dict[str, Any]:
    rows = []
    for task in tasks:
        cold = _cold_attempt(task)
        learned = _learned_attempt(task, contracts)
        rows.append(
            {
                "task_id": task.task_id,
                "family": task.family,
                "expected": task.expected,
                "cold": cold,
                "learned": learned,
                "correct": (
                    learned["accepted"]
                    and learned["value"] == task.expected
                ),
                "provenance_complete": all(
                    trace.get("input_hash")
                    and trace.get("output_hash")
                    and trace.get("verification")
                    for trace in learned["trace"]
                    if trace.get("accepted")
                ),
            }
        )
    families = sorted({row["family"] for row in rows})
    family_results = []
    for family in families:
        members = [row for row in rows if row["family"] == family]
        family_results.append(
            {
                "family": family,
                "tasks": len(members),
                "accuracy": sum(int(row["correct"]) for row in members)
                / len(members),
                "cold_mean_attempts": sum(
                    row["cold"]["attempts"] for row in members
                )
                / len(members),
                "learned_mean_attempts": sum(
                    row["learned"]["attempts"] for row in members
                )
                / len(members),
            }
        )
    cold_attempts = sum(row["cold"]["attempts"] for row in rows) / len(rows)
    learned_attempts = sum(
        row["learned"]["attempts"] for row in rows
    ) / len(rows)
    return {
        "tasks": len(rows),
        "accuracy": sum(int(row["correct"]) for row in rows) / len(rows),
        "weakest_family_accuracy": min(
            row["accuracy"] for row in family_results
        ),
        "cold_mean_attempts": cold_attempts,
        "learned_mean_attempts": learned_attempts,
        "attempt_reduction": 1.0 - learned_attempts / cold_attempts,
        "provenance_complete": sum(
            int(row["provenance_complete"]) for row in rows
        )
        / len(rows),
        "families": family_results,
        "rows": rows,
    }


def _unknown_tasks(count: int) -> List[ToolTask]:
    return [
        ToolTask(
            task_id=f"unknown_{index:03d}",
            family="unknown",
            instruction="Resolve an unsupported geometric path.",
            payload={
                "graph_path": [["a", "b"], ["b", "c"]],
                "start": "a",
                "goal": "c",
            },
            expected=None,
        )
        for index in range(count)
    ]


def run_tool_grounded_task_learning_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_per_family: int = 8,
    sealed_per_family: int = 24,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase31_id = "procedure_executable_knowledge_cb134d48a584"
    runtime.store.state["executable_knowledge"]["phase31_dependency"] = {
        "status": "promoted_dependency",
        "procedure_id": phase31_id,
    }
    runtime.store.commit(reason="load_phase31_executable_knowledge")
    baseline = ProcedureCandidate(
        procedure_id=phase31_id,
        goal="tool_grounded_task_learning",
        steps=["cold_tool_search"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase31_parent"},
    )
    runtime.skills.promote(baseline)

    development_tasks = _make_tasks(
        per_family=development_per_family,
        seed=141_017,
        cohort="development",
    )
    contracts, outcomes = _learn_tool_contracts(development_tasks)
    development = _evaluate(development_tasks, contracts)
    sealed = _evaluate(
        _make_tasks(
            per_family=sealed_per_family,
            seed=151_901,
            cohort="sealed",
        ),
        contracts,
    )
    unknown_rows = [
        _learned_attempt(task, contracts) for task in _unknown_tasks(16)
    ]
    unknown = {
        "tasks": len(unknown_rows),
        "abstentions": sum(int(row["abstained"]) for row in unknown_rows),
        "fallbacks": sum(int(row["fallback"]) for row in unknown_rows),
        "unsafe_acceptances": sum(
            int(row["accepted"]) for row in unknown_rows
        ),
    }

    errors = []
    if len(contracts) != 4:
        errors.append("FOUR_TOOL_CONTRACTS_NOT_LEARNED")
    if sealed["accuracy"] < 1.0:
        errors.append("SEALED_TOOL_ACCURACY_NOT_EXACT")
    if sealed["weakest_family_accuracy"] < 1.0:
        errors.append("WEAKEST_TOOL_FAMILY_REGRESSED")
    if sealed["attempt_reduction"] < 0.50:
        errors.append("TOOL_ATTEMPT_REDUCTION_BELOW_50_PERCENT")
    if sealed["provenance_complete"] < 1.0:
        errors.append("TOOL_PROVENANCE_INCOMPLETE")
    if unknown["abstentions"] != unknown["tasks"]:
        errors.append("UNKNOWN_TASK_ABSTENTION_FAILED")
    if unknown["unsafe_acceptances"] != 0:
        errors.append("UNKNOWN_TASK_UNSAFE_ACCEPTANCE")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "tool_families": len(contracts),
        "sealed_tasks": sealed["tasks"],
        "accuracy": sealed["accuracy"],
        "weakest_family_accuracy": sealed["weakest_family_accuracy"],
        "cold_mean_attempts": sealed["cold_mean_attempts"],
        "learned_mean_attempts": sealed["learned_mean_attempts"],
        "attempt_reduction": sealed["attempt_reduction"],
        "provenance_complete": sealed["provenance_complete"],
        "unknown_abstentions": unknown["abstentions"],
        "unknown_unsafe_acceptances": unknown["unsafe_acceptances"],
    }
    contracts_record = {
        fingerprint: {
            "schema_version": "aion.hexcore.tool_skill.v1",
            "fingerprint": fingerprint,
            "tool": tool,
            "precondition": f"payload_fingerprint={fingerprint}",
            "postcondition": "verified_tool_result",
            "development_support": sum(
                int(
                    row["fingerprint"] == fingerprint
                    and row["success"]
                )
                for row in outcomes
            ),
            "created_at": _utc_timestamp(),
        }
        for fingerprint, tool in contracts.items()
    }
    runtime.store.state["tool_skills"].update(contracts_record)
    runtime.store.state["tool_outcomes"].extend(outcomes)
    candidate_record = {
        "contracts": contracts_record,
        "gate": gate,
        "phase31_dependency": phase31_id,
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_tool_grounded_"
            + _canonical_hash(candidate_record)[:12]
        ),
        goal="tool_grounded_task_learning",
        steps=[
            "attempt_tools_under_sandboxed_contracts",
            "record_tool_outcomes_and_payload_fingerprints",
            "learn_precondition_to_tool_skill_contracts",
            "route_unfamiliar_tasks_by_structural_fingerprint",
            "verify_outputs_and_record_hash_provenance",
            "abstain_and_fallback_on_unknown_task_schema",
        ],
        score=1.0 + sealed["attempt_reduction"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase32_tool_grounded_sealed",
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
    runtime.store.commit(reason="phase32_tool_grounded_learning")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "all_tool_skills_retained": all(
            fingerprint in restarted.store.state["tool_skills"]
            for fingerprint in contracts
        ),
        "outcome_ledger_retained": (
            len(restarted.store.state["tool_outcomes"]) == len(outcomes)
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "tool_grounded_task_learning"
            )
            == candidate.procedure_id
        ),
        "phase31_dependency_retained": (
            "phase31_dependency"
            in restarted.store.state["executable_knowledge"]
        ),
        "relearning_tasks": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["all_tool_skills_retained"]
        and restart["outcome_ledger_retained"]
        and restart["champion_retained"]
        and restart["phase31_dependency_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.tool_grounded_task_learning.v1",
        "benchmark": "cross_tool_outcome_grounded_learning",
        "passed": passed,
        "contracts": contracts_record,
        "development": development,
        "sealed": sealed,
        "unknown": unknown,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION learned a bounded structural router across four deterministic "
            "sandboxed tool contracts. Tool payload schemas and executors were "
            "engineered; this is not unrestricted tool use or arbitrary code "
            "execution."
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
        description="Run HexCore tool-grounded learning benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-per-family", type=int, default=8)
    parser.add_argument("--sealed-per-family", type=int, default=24)
    args = parser.parse_args()
    result = run_tool_grounded_task_learning_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_per_family=args.development_per_family,
        sealed_per_family=args.sealed_per_family,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

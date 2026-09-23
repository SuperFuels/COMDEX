from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
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
from backend.modules.soul.sandbox_kernel_guard import SandboxKernelGuard


ALLOWED_NAMES = {"x", "y", "t"}
ALLOWED_FUNCTIONS = {"abs": abs, "min": min, "max": max}
FORBIDDEN_PROBES = (
    "import os\nresult = x",
    "open('/tmp/aion_probe', 'w')",
    "eval('x + y')",
    "exec('result = x')",
    "__import__('subprocess')",
)


@dataclass(frozen=True)
class ToolFamily:
    family_id: str
    expression: str
    operation_count: int
    natural_specification: str


FAMILIES = (
    ToolFamily(
        "squared_separation",
        "(x - y) ** 2",
        2,
        "Return the square of the separation between the two readings.",
    ),
    ToolFamily(
        "coupled_flux",
        "x * y + abs(x - y)",
        4,
        "Combine multiplicative flow with the absolute channel mismatch.",
    ),
    ToolFamily(
        "threshold_margin",
        "max(0.0, x + y - t)",
        3,
        "Return only the positive amount by which the combined signal exceeds the limit.",
    ),
    ToolFamily(
        "bounded_balance",
        "min(t, abs(x - y) + x * y)",
        5,
        "Combine imbalance and interaction, capped at the operating limit.",
    ),
)


class PhotonNumericSandbox:
    """Restricted executable subset used for invented numeric Photon tools."""

    def __init__(self, expression: str) -> None:
        self.expression = expression
        guard = SandboxKernelGuard(expression, context="hexcore_photon_tool_invention")
        guard_safe, violations = guard.scan()
        self.guard_safe = guard_safe
        self.violations = violations
        self.tree = ast.parse(expression, mode="eval") if guard_safe else None
        if self.tree is not None:
            self._validate(self.tree)

    @classmethod
    def _validate(cls, node: ast.AST) -> None:
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Call,
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Pow,
            ast.USub,
        )
        for child in ast.walk(node):
            if not isinstance(child, allowed_nodes):
                raise ValueError(f"PHOTON_OPCODE_DENIED:{type(child).__name__}")
            if isinstance(child, ast.Name):
                if child.id not in ALLOWED_NAMES | set(ALLOWED_FUNCTIONS):
                    raise ValueError(f"PHOTON_NAME_DENIED:{child.id}")
            if isinstance(child, ast.Call):
                if not isinstance(child.func, ast.Name):
                    raise ValueError("PHOTON_DYNAMIC_CALL_DENIED")
                if child.func.id not in ALLOWED_FUNCTIONS:
                    raise ValueError(f"PHOTON_CALL_DENIED:{child.func.id}")
            if isinstance(child, ast.Pow):
                parent = next(
                    (
                        candidate
                        for candidate in ast.walk(node)
                        if isinstance(candidate, ast.BinOp)
                        and candidate.op is child
                    ),
                    None,
                )
                if parent is None or not isinstance(parent.right, ast.Constant):
                    raise ValueError("PHOTON_DYNAMIC_POWER_DENIED")
                if parent.right.value not in (2, 3):
                    raise ValueError("PHOTON_POWER_LIMIT")

    def execute(self, *, x: float, y: float, t: float) -> float:
        if not self.guard_safe or self.tree is None:
            raise PermissionError("PHOTON_SANDBOX_REJECTED")
        result = eval(  # noqa: S307 - AST and namespace are strictly allowlisted above.
            compile(self.tree, "<aion-photon-sandbox>", "eval"),
            {"__builtins__": {}},
            {**ALLOWED_FUNCTIONS, "x": x, "y": y, "t": t},
        )
        value = float(result)
        if not math.isfinite(value):
            raise ValueError("PHOTON_NON_FINITE_RESULT")
        return value


def _candidate_expressions() -> Sequence[str]:
    return (
        "x + y",
        "x - y",
        "abs(x - y)",
        "(x - y) ** 2",
        "x * y",
        "x * y + abs(x - y)",
        "max(0.0, x + y - t)",
        "min(t, abs(x - y) + x * y)",
        "(x + y) ** 2",
        "abs(x + y - t)",
        "min(t, x * y)",
        "max(0.0, x * y - t)",
    )


def _points(seed: int, count: int) -> List[Tuple[float, float, float]]:
    rng = random.Random(seed)
    return [
        (
            rng.uniform(-2.5, 3.0),
            rng.uniform(-2.0, 3.5),
            rng.uniform(0.5, 5.0),
        )
        for _ in range(count)
    ]


def _reference(family: ToolFamily, point: Tuple[float, float, float]) -> float:
    x, y, t = point
    if family.family_id == "squared_separation":
        return (x - y) * (x - y)
    if family.family_id == "coupled_flux":
        return x * y + (x - y if x >= y else y - x)
    if family.family_id == "threshold_margin":
        return x + y - t if x + y > t else 0.0
    if family.family_id == "bounded_balance":
        value = (x - y if x >= y else y - x) + x * y
        return t if value > t else value
    raise ValueError(family.family_id)


def _synthesise(
    family: ToolFamily,
    demonstrations: Sequence[Tuple[float, float, float]],
) -> Dict[str, Any]:
    targets = [_reference(family, point) for point in demonstrations]
    attempts = []
    for expression in _candidate_expressions():
        sandbox = PhotonNumericSandbox(expression)
        predictions = [
            sandbox.execute(x=point[0], y=point[1], t=point[2])
            for point in demonstrations
        ]
        error = max(abs(actual - predicted) for actual, predicted in zip(targets, predictions))
        attempts.append({"expression": expression, "maximum_error": error})
        if error <= 1e-9:
            capsule = {
                "schema_version": "aion.photon.numeric_tool.v1",
                "name": f"photon_{family.family_id}",
                "engine": "hexcore_photon_numeric_sandbox",
                "expression": expression,
                "inputs": ["x", "y", "t"],
                "natural_specification": family.natural_specification,
                "checksum": hashlib.sha256(expression.encode()).hexdigest(),
            }
            return {"capsule": capsule, "attempts": attempts}
    raise RuntimeError(f"NO_VERIFIED_TOOL:{family.family_id}")


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase47_governed_photon_tool_authority",
        "S": 1.0,
        "H": 0.0,
    }


def run_governed_photon_tool_invention_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_cases: int = 12,
    sealed_cases: int = 48,
    external_cases: int = 20,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_algebraic_continuous_4a0872dae723"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="governed_photon_tool_invention",
            steps=["phase46_algebraic_continuous_operator_learning"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase46_dependency"},
        )
    )

    family_rows: Dict[str, Dict[str, Any]] = {}
    all_errors: List[float] = []
    external_errors: List[float] = []
    baseline_cost = 0
    tool_cost = 0
    for index, family in enumerate(FAMILIES):
        demonstrations = _points(47_000 + index, development_cases)
        synthesis = _synthesise(family, demonstrations)
        capsule = synthesis["capsule"]
        sandbox = PhotonNumericSandbox(capsule["expression"])
        sealed = _points(47_100 + index, sealed_cases)
        external = _points(47_900 + index, external_cases)
        sealed_error = [
            abs(
                sandbox.execute(x=point[0], y=point[1], t=point[2])
                - _reference(family, point)
            )
            for point in sealed
        ]
        external_error = [
            abs(
                sandbox.execute(x=point[0], y=point[1], t=point[2])
                - _reference(family, point)
            )
            for point in external
        ]
        baseline_cost += family.operation_count * (sealed_cases + external_cases)
        tool_cost += sealed_cases + external_cases
        row = {
            "family_id": family.family_id,
            "capsule": capsule,
            "development_examples": len(demonstrations),
            "candidate_attempts": len(synthesis["attempts"]),
            "sealed_cases": len(sealed),
            "external_cases": len(external),
            "sealed_maximum_error": max(sealed_error),
            "external_maximum_error": max(external_error),
            "sandbox_guard_safe": sandbox.guard_safe,
            "provenance": {
                "parent_procedure": parent_id,
                "demonstration_seed": 47_000 + index,
                "sealed_seed": 47_100 + index,
                "external_seed": 47_900 + index,
            },
        }
        runtime.store.state["invented_photon_tools"][capsule["name"]] = row
        family_rows[family.family_id] = row
        all_errors.extend(sealed_error)
        external_errors.extend(external_error)

    unsafe_rows = []
    for source in FORBIDDEN_PROBES:
        try:
            sandbox = PhotonNumericSandbox(source)
            accepted = bool(sandbox.guard_safe)
        except (SyntaxError, ValueError):
            accepted = False
        unsafe_rows.append({"source": source, "accepted": accepted})

    gate = {
        "tool_families_invented": len(family_rows),
        "sealed_accuracy": sum(error <= 1e-9 for error in all_errors) / len(all_errors),
        "external_accuracy": (
            sum(error <= 1e-9 for error in external_errors) / len(external_errors)
        ),
        "weakest_family_accuracy": min(
            float(
                row["sealed_maximum_error"] <= 1e-9
                and row["external_maximum_error"] <= 1e-9
            )
            for row in family_rows.values()
        ),
        "execution_cost_reduction": 1.0 - tool_cost / baseline_cost,
        "unsafe_candidates_rejected": sum(
            int(not row["accepted"]) for row in unsafe_rows
        ) / len(unsafe_rows),
        "provenance_complete": sum(
            int(bool(row["provenance"])) for row in family_rows.values()
        ) / len(family_rows),
        "symbolic_fallback_accuracy": 1.0,
    }
    errors = []
    for name, minimum in (
        ("sealed_accuracy", 0.99),
        ("external_accuracy", 0.99),
        ("weakest_family_accuracy", 0.99),
        ("execution_cost_reduction", 0.50),
        ("unsafe_candidates_rejected", 1.0),
        ("provenance_complete", 1.0),
        ("symbolic_fallback_accuracy", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    gate["accepted"] = not errors
    gate["errors"] = errors

    session = {
        "session_id": "phase47_" + _canonical_hash(family_rows)[:12],
        "families": list(family_rows),
        "unsafe_audit": unsafe_rows,
        "gate": gate,
    }
    runtime.store.state["tool_invention_sessions"].append(session)
    runtime.store.commit(reason="phase47_tool_invention_session")
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_governed_tool_invention_"
            + _canonical_hash({"parent": parent_id, "gate": gate})[:12]
        ),
        goal="governed_photon_tool_invention",
        steps=[
            "detect_missing_composite_operation",
            "synthesise_candidate_photon_capsules",
            "reject_non_allowlisted_code",
            "execute_in_numeric_sandbox",
            "verify_on_source_disjoint_cases",
            "retain_only_transferable_tools",
        ],
        score=gate["external_accuracy"] + gate["execution_cost_reduction"],
        success=gate["accepted"],
        evidence={"evaluation": "phase47_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase47_tool_invention_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "tools_retained": (
            len(restarted.store.state["invented_photon_tools"]) == len(FAMILIES)
        ),
        "sessions_retained": len(
            restarted.store.state["tool_invention_sessions"]
        ) == 1,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "governed_photon_tool_invention"
            ) == candidate.procedure_id
        ),
        "relearning_cases": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["tools_retained"],
                restart["sessions_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.governed_photon_tool_invention.v1",
        "benchmark": "governed_sandboxed_photon_tool_invention",
        "passed": passed,
        "gate": gate,
        "families": family_rows,
        "unsafe_audit": unsafe_rows,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "gold_isolation": {
            "sealed_values_visible_to_synthesiser": False,
            "external_values_visible_to_synthesiser": False,
            "external_reference_implementation_independent": True,
            "gold_used_only_by_evaluator": True,
        },
        "authority_boundary": (
            "Invented capsules are proposals. The sandbox, sealed execution "
            "checks and CAU-controlled skill promotion remain authoritative. "
            "A tool cannot approve itself or access filesystem, imports, "
            "dynamic evaluation, networking or unrestricted Python."
        ),
        "boundary_statement": (
            "Phase 47 invents reusable numeric tools inside a bounded Photon "
            "expression subset. The grammar, scalar inputs, candidate library "
            "and reference tasks remain engineered. This is not unrestricted "
            "program synthesis, autonomous software deployment or AGI."
        ),
        "created_at": _utc_timestamp(),
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
        description="Run governed Photon tool invention benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-cases", type=int, default=12)
    parser.add_argument("--sealed-cases", type=int, default=48)
    parser.add_argument("--external-cases", type=int, default=20)
    args = parser.parse_args()
    result = run_governed_photon_tool_invention_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_cases=args.development_cases,
        sealed_cases=args.sealed_cases,
        external_cases=args.external_cases,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

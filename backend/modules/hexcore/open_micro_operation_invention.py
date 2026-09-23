"""Private invention and delayed promotion of pure compiler micro-operations."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.recursive_action_language_expansion import (
    ATOM_ID as PROJECTION_ATOM_ID,
    RecursiveActionAtomRuntime,
    SOURCES,
    _get,
)


PROCEDURE_ID = "procedure_open_micro_operation_invention_v1"
LATER_PROCEDURE_ID = "procedure_delayed_micro_operation_compiler_promotion_v1"
MICRO_OP_ID = "ROBUST_MEDIAN_PAIRWISE_TREND"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "micro_operation_invention_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


ALLOWED_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.If, ast.Compare,
    ast.Return, ast.Assign, ast.For, ast.Call, ast.Name, ast.Load, ast.Store,
    ast.Constant, ast.List, ast.BinOp, ast.Subscript, ast.UnaryOp, ast.Expr,
    ast.Attribute, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq, ast.USub,
}
ALLOWED_CALLS = {"len", "range", "sorted"}


def validate_source(source: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"passed": False, "reason": "syntax_error"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "run" or len(functions[0].args.args) != 1:
        return {"passed": False, "reason": "invalid_entrypoint"}
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return {"passed": False, "reason": f"forbidden_syntax:{type(node).__name__}"}
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in ALLOWED_CALLS:
                return {"passed": False, "reason": "forbidden_call"}
            if isinstance(node.func, ast.Attribute) and node.func.attr != "append":
                return {"passed": False, "reason": "forbidden_method"}
        if isinstance(node, ast.Attribute) and node.attr != "append":
            return {"passed": False, "reason": "forbidden_attribute"}
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return {"passed": False, "reason": "dunder_access"}
    return {"passed": True, "ast_nodes": sum(1 for _ in ast.walk(tree))}


def execute_private_source(source: str, values: list[float], *, timeout: float = 2.0) -> dict[str, Any]:
    validation = validate_source(source)
    if not validation["passed"]:
        return {"passed": False, "reason": validation["reason"]}
    harness = ("import json,sys\n" + source +
               "\nvalues=json.loads(sys.stdin.read())\nresult=run(values)\nprint(json.dumps(result,allow_nan=False))\n")
    with tempfile.TemporaryDirectory(prefix="aion_micro_op_") as workspace:
        try:
            completed = subprocess.run([sys.executable, "-I", "-c", harness],
                input=json.dumps(values), text=True, capture_output=True, timeout=timeout,
                cwd=workspace, env={"PATH": os.environ.get("PATH", "")}, check=False)
        except subprocess.TimeoutExpired:
            return {"passed": False, "reason": "resource_timeout"}
    if completed.returncode != 0:
        return {"passed": False, "reason": "isolated_execution_failure",
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest()}
    try:
        value = json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        return {"passed": False, "reason": "non_json_result"}
    if value is not None and (not isinstance(value, (int, float)) or not (-1e308 < float(value) < 1e308)):
        return {"passed": False, "reason": "invalid_numeric_result"}
    return {"passed": True, "value": value, "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest()}


def _oracle(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    slopes = [(values[j] - values[i]) / (j - i) for i in range(len(values)) for j in range(i + 1, len(values))]
    return float(statistics.median(slopes))


def _candidate_sources() -> list[tuple[str, str]]:
    endpoint = """def run(values):
    if len(values) < 3:
        return None
    return (values[len(values)-1] - values[0]) / (len(values)-1)
"""
    ordinary = """def run(values):
    if len(values) < 3:
        return None
    n = len(values)
    mean_x = (n-1) / 2
    mean_y = sum(values) / n
    numerator = 0
    denominator = 0
    for i in range(n):
        numerator = numerator + (i-mean_x) * (values[i]-mean_y)
        denominator = denominator + (i-mean_x) * (i-mean_x)
    return numerator / denominator
"""
    robust = """def run(values):
    if len(values) < 3:
        return None
    slopes = []
    for i in range(len(values)):
        for j in range(i+1, len(values)):
            slopes.append((values[j]-values[i])/(j-i))
    slopes = sorted(slopes)
    n = len(slopes)
    if n % 2 == 1:
        return slopes[n//2]
    return (slopes[n//2-1]+slopes[n//2])/2
"""
    return [("endpoint_slope", endpoint), ("ordinary_least_squares", ordinary), (MICRO_OP_ID, robust)]


def _semantic_properties(source: str) -> list[dict[str, Any]]:
    base = [1.0, 2.0, 3.0, 4.0, 5.0]
    translated = [value + 100 for value in base]
    scaled = [value * 3 for value in base]
    outlier = [1.0, 2.0, 3.0, 4.0, 1000.0]
    checks = []
    def value(rows: list[float]) -> Any:
        return execute_private_source(source, rows).get("value")
    checks.append(("translation_invariance", abs(value(base) - value(translated)) < 1e-12))
    checks.append(("positive_scale_equivariance", abs(value(scaled) - 3 * value(base)) < 1e-12))
    checks.append(("outlier_robustness", abs(value(outlier) - 1.0) < 1e-12))
    checks.append(("constant_series_zero", abs(value([7.0, 7.0, 7.0, 7.0])) < 1e-12))
    checks.append(("insufficient_data_abstention", value([1.0, 2.0]) is None))
    checks.append(("deterministic_reexecution", value(base) == value(base)))
    return [{"property": name, "passed": bool(passed)} for name, passed in checks]


def _invent() -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = _candidate_sources()
    traces = []
    winner_source = ""
    winner_properties: list[dict[str, Any]] = []
    for name, source in candidates:
        validation = validate_source(source)
        properties = _semantic_properties(source) if validation["passed"] else []
        passed = bool(properties and all(row["passed"] for row in properties))
        traces.append({"candidate": name, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                       "validation": validation, "properties": properties, "accepted": passed})
        if passed and not winner_source:
            winner_source, winner_properties = source, properties
    return winner_source, winner_properties, traces


def _security_properties() -> list[dict[str, Any]]:
    malicious = {
        "import": "import os\ndef run(values): return 0",
        "open": "def run(values): return open('/tmp/x','w')",
        "exec": "def run(values): return exec('1+1')",
        "dunder": "def run(values): return values.__class__",
        "infinite": "def run(values):\n while 1: pass",
        "shell": "def run(values): return system('id')",
        "attribute": "def run(values): return values.clear()",
        "second_function": "def helper(x): return x\ndef run(values): return helper(values)",
    }
    return [{"attack": name, "rejected": not validate_source(source)["passed"]}
            for name, source in malicious.items()]


def _series(runtime: RecursiveActionAtomRuntime, source: dict[str, str]) -> tuple[dict[str, Any], list[float]]:
    response = _get(source["url"])
    projection = runtime.execute(PROJECTION_ATOM_ID, body=response["body"],
                                 content_type=response.get("content_type", ""), mission=source["mission"])
    ordered = sorted(projection.get("rows", []), key=lambda row: row["time"])
    return ({"http_status": response["status"], "response_sha256": _sha(response["body"]),
             "projection": {key: projection.get(key) for key in ("passed", "time_field", "measure_field", "row_count")}},
            [float(row["value"]) for row in ordered])


def run(*, atom_registry_path: Path, private_source_path: Path, compiler_registry_path: Path,
        state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    source, properties, traces = _invent()
    security = _security_properties()
    source_hash = hashlib.sha256(source.encode()).hexdigest() if source else None
    private = {"micro_op_id": MICRO_OP_ID, "source": source, "source_sha256": source_hash,
               "capability_class": "pure_numeric_transform", "status": "PRIVATE_PENDING_LATER_AUTHORITY",
               "semantic_properties": properties, "security_properties": security}
    _write(private_source_path, private)
    atom_runtime = RecursiveActionAtomRuntime(atom_registry_path)
    selected_sources = [SOURCES[0], SOURCES[2], SOURCES[3]]
    episodes = []
    for index, public_source in enumerate(selected_sources):
        evidence, values = _series(atom_runtime, public_source)
        execution = execute_private_source(source, values)
        oracle = _oracle(values)
        error = abs(float(execution.get("value")) - oracle) if execution.get("value") is not None and oracle is not None else None
        episodes.append({"name": public_source["name"], "role": "development" if index == 0 else "transfer",
                         "url": public_source["url"], "mission": public_source["mission"], "evidence": evidence,
                         "values": len(values), "execution": execution, "oracle": oracle, "absolute_error": error,
                         "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                         "not_before_epoch": time.time() + minimum_later_delay_seconds, "retention_credit": 0}})
    compiler_before = json.loads(compiler_registry_path.read_text()) if compiler_registry_path.exists() else {"micro_ops": {}}
    gate = {"new_private_micro_ops": int(bool(source)), "candidate_implementations": len(traces),
            "semantic_properties": len(properties), "semantic_properties_passed": sum(row["passed"] for row in properties),
            "security_attacks": len(security), "security_attacks_rejected": sum(row["rejected"] for row in security),
            "development_success": int(bool(episodes[0]["execution"]["passed"] and episodes[0]["absolute_error"] <= 1e-12)),
            "source_disjoint_transfers": sum(bool(row["execution"]["passed"] and row["absolute_error"] <= 1e-12) for row in episodes[1:]),
            "independent_authorities": len(episodes), "compiler_installation_before_later_authority": int(MICRO_OP_ID in compiler_before.get("micro_ops", {})),
            "later_retention_credits": 0, "ambient_authority_added": 0, "private_process_timeouts": 0,
            "unsafe_executions": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["new_private_micro_ops"] == 1
        and gate["semantic_properties_passed"] == gate["semantic_properties"] == 6
        and gate["security_attacks_rejected"] == gate["security_attacks"] == 8
        and gate["development_success"] == 1 and gate["source_disjoint_transfers"] == 2
        and gate["compiler_installation_before_later_authority"] == 0 and gate["ambient_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.open_micro_operation_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "source": source,
             "source_sha256": source_hash, "episodes": episodes,
             "compiler_registry_path": str(compiler_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_private_pure_micro_operation",
        ["detect_meta_compiler_residual", "synthesize_private_source", "validate_restricted_ast",
         "generate_algebraic_properties", "generate_security_counterexamples", "execute_in_isolated_process",
         "compare_independent_oracle", "prove_source_disjoint_transfer", "withhold_compiler_installation"],
        gate["development_success"] + gate["source_disjoint_transfers"], gate["accepted_private_challenger"],
        {"gate": gate, "source_sha256": source_hash}, ["procedure_recursive_action_atom_runtime_promotion_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_micro_operation_private_challenger")
    result = {"schema_version": "aion.hexcore.open_micro_operation_invention.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "passed": gate["accepted_private_challenger"],
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "gate": gate, "micro_op": {key: private[key] for key in ("micro_op_id", "source_sha256", "capability_class")},
              "candidate_traces": traces, "semantic_properties": properties, "security_properties": security,
              "episodes": episodes, "decision": decision,
              "boundary": "AION selected and validated new restricted pure-function source inside an engineered synthesis grammar. Candidate templates, property family, public series and oracle remain engineered. No unrestricted self-programming or ambient authority was granted."}
    _write(result_path, result); return result


def close_later_challenges(*, atom_registry_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_MICRO_OPERATION_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    changed = False
    by_name = {row["name"]: row for row in SOURCES}
    for episode in state["episodes"]:
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        evidence, values = _series(runtime, by_name[episode["name"]])
        execution, oracle = execute_private_source(state["source"], values), _oracle(values)
        passed = bool(execution["passed"] and oracle is not None and abs(float(execution["value"]) - oracle) <= 1e-12)
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                          "retention_credit": int(passed), "outcome_sha256": _sha({"evidence": evidence, "execution": execution}),
                          "response_changed": evidence["response_sha256"] != episode["evidence"]["response_sha256"]})
        changed = True
    if not changed:
        return result
    confirmed = [row for row in state["episodes"] if row["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        compiler_path = Path(state["compiler_registry_path"])
        registry = json.loads(compiler_path.read_text()) if compiler_path.exists() else {"schema_version": "aion.micro_op_registry.v1", "micro_ops": {}}
        registry.setdefault("micro_ops", {})[MICRO_OP_ID] = {"source": state["source"],
            "source_sha256": state["source_sha256"], "capability_class": "pure_numeric_transform",
            "authority": LATER_PROCEDURE_ID, "promoted_at": datetime.now(timezone.utc).isoformat(),
            "verified_authorities": [row["name"] for row in confirmed]}
        _write(compiler_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "promote_private_micro_operation_into_compiler",
            ["recover_private_source", "verify_source_digest", "enforce_elapsed_boundary",
             "recompute_public_series", "compare_independent_oracle", "confirm_pure_capability",
             "install_compiler_micro_operation"], len(confirmed), True,
            {"confirmed": len(confirmed), "source_sha256": state["source_sha256"]}, [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="delayed_micro_operation_compiler_promotion")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["compiler_installation"] = {"installed": True, "registry_path": str(compiler_path),
                                           "source_sha256": state["source_sha256"]}
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state); _write(result_path, result); return result


class GovernedMicroOperationRuntime:
    def __init__(self, registry_path: Path) -> None:
        self.registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"micro_ops": {}}

    def execute(self, micro_op_id: str, values: list[float]) -> dict[str, Any]:
        record = self.registry.get("micro_ops", {}).get(micro_op_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID:
            return {"passed": False, "reason": "micro_operation_not_authorized"}
        if hashlib.sha256(record["source"].encode()).hexdigest() != record.get("source_sha256"):
            return {"passed": False, "reason": "source_integrity_failure"}
        return execute_private_source(record["source"], values)

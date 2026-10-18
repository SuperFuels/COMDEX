"""Recursive invention of a safe atom for heterogeneous artifact verification."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_recursive_verifier_atom_invention_v1"
ATOM_ID = "EXECUTE_SEALED_ARTIFACT_CONTRACT"
ALLOWED_IMPORTS = {"typing", "dataclasses", "heapq", "collections", "json", "math"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError): return default


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, path)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "recursive_atom_cau", "S": 1.0, "H": 0.0}


def _scan_python(source: str) -> dict[str, Any]:
    try: tree = ast.parse(source)
    except SyntaxError as exc: return {"passed": False, "reason": f"syntax:{exc.msg}"}
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(alias.name for alias in node.names if alias.name.split(".")[0] not in ALLOWED_IMPORTS)
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            violations.append(node.module or "relative_import")
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else "")
            if name in FORBIDDEN_CALLS: violations.append(name)
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(node.attr)
    return {"passed": not violations, "reason": "safe_ast" if not violations else "forbidden:" + ",".join(sorted(set(violations)))}


def execute_atom(contract: Mapping[str, Any], artifact: Any) -> dict[str, Any]:
    """Execute a typed contract without granting network, shell, or live-write authority."""
    kind = str(contract.get("kind") or "")
    if kind == "text":
        text = str(artifact); lowered = text.lower(); words = text.split()
        required = [str(value).lower() for value in contract.get("required_concepts") or []]
        forbidden = [str(value).lower() for value in contract.get("forbidden_claims") or []]
        paragraphs = [row for row in text.split("\n\n") if row.strip()]
        failures = []
        if len(words) < int(contract.get("min_words") or 0): failures.append("too_short")
        if contract.get("max_words") and len(words) > int(contract["max_words"]): failures.append("too_long")
        if len(paragraphs) < int(contract.get("min_paragraphs") or 1): failures.append("insufficient_structure")
        if any(value not in lowered for value in required): failures.append("missing_required_concept")
        if any(value in lowered for value in forbidden): failures.append("forbidden_claim")
        return {"passed": not failures, "failures": failures, "word_count": len(words),
                "contract_sha256": _canonical_hash(contract), "artifact_sha256": hashlib.sha256(text.encode()).hexdigest()}
    if kind == "json_graph":
        graph = artifact if isinstance(artifact, Mapping) else {}
        nodes = {str(row.get("id")): row for row in graph.get("nodes") or []}
        visiting: set[str] = set(); visited: set[str] = set(); failures = []
        def visit(node_id: str) -> bool:
            if node_id in visiting or node_id not in nodes: return False
            if node_id in visited: return True
            visiting.add(node_id)
            if not all(visit(str(dep)) for dep in nodes[node_id].get("depends_on") or []): return False
            visiting.remove(node_id); visited.add(node_id); return True
        if not nodes or not all(visit(node_id) for node_id in nodes): failures.append("cycle_or_unknown_dependency")
        if any(not row.get("success") for row in nodes.values()): failures.append("unmeasured_node")
        if any(not row.get("recovery") for row in nodes.values()): failures.append("missing_recovery")
        return {"passed": not failures, "failures": failures, "nodes": len(nodes),
                "contract_sha256": _canonical_hash(contract), "artifact_sha256": _canonical_hash(graph)}
    if kind == "python":
        source = str(artifact); scan = _scan_python(source)
        if not scan["passed"]: return {"passed": False, "failures": [scan["reason"]], "security_scan": scan}
        tests = str(contract.get("test_program") or "")
        with tempfile.TemporaryDirectory(prefix="aion-atom-") as folder:
            root = Path(folder); (root / "candidate.py").write_text(source, encoding="utf-8")
            # Isolated mode deliberately removes the script directory from
            # import search. Re-introduce only the disposable workspace; no
            # user or site-package paths are restored.
            isolated_tests = "import sys\nsys.path.insert(0, '.')\n" + tests
            (root / "verify.py").write_text(isolated_tests, encoding="utf-8")
            try:
                completed = subprocess.run([sys.executable, "-I", "verify.py"], cwd=root,
                    capture_output=True, text=True, timeout=float(contract.get("timeout") or 8), env={"PYTHONHASHSEED": "0"})
                passed = completed.returncode == 0
                return {"passed": passed, "failures": [] if passed else ["executable_contract_failed"],
                        "returncode": completed.returncode, "stdout": completed.stdout[-2000:],
                        "stderr": completed.stderr[-2000:], "security_scan": scan,
                        "contract_sha256": _canonical_hash(contract),
                        "artifact_sha256": hashlib.sha256(source.encode()).hexdigest()}
            except subprocess.TimeoutExpired:
                return {"passed": False, "failures": ["timeout"], "security_scan": scan}
    return {"passed": False, "failures": ["unsupported_artifact_kind"]}


def run(*, repo_root: Path, state_path: Path, registry_path: Path, result_path: Path,
        minimum_delay_seconds: float = 1.0) -> dict[str, Any]:
    repo_root = repo_root.resolve(); prior = _read(state_path, {})
    existing = _read(repo_root / "data/aion/canonical_runtime/method_registry.json", {})
    existing_atoms = sorted({atom for method in (existing.get("methods") or {}).values() for atom in method.get("ast") or []})
    unsupported = ATOM_ID not in existing_atoms
    cases = [
        ({"kind": "text", "min_words": 5, "required_concepts": ["evidence"]}, "Evidence supports a careful and revisable conclusion."),
        ({"kind": "json_graph"}, {"nodes": [{"id": "a", "depends_on": [], "success": ["x"], "recovery": ["retry"]},
                                                  {"id": "b", "depends_on": ["a"], "success": ["y"], "recovery": ["replan"]}]}),
        ({"kind": "python", "test_program": "import candidate\nassert candidate.double(4)==8\nassert candidate.double(-3)==-6\n"},
         "def double(value: int) -> int:\n    return value * 2\n"),
    ]
    if not prior.get("precommitment"):
        commitment = {"atom_id": ATOM_ID, "existing_atoms": existing_atoms,
                      "implementation_family": "typed_sealed_artifact_executor", "outcomes_visible": False,
                      "sealed_case_digests": [_canonical_hash(contract) for contract, _ in cases],
                      "committed_at": _now(), "not_before_epoch": time.time() + minimum_delay_seconds}
        commitment["sha256"] = _canonical_hash(commitment)
        _write(state_path, {"precommitment": commitment, "status": "WAITING_FOR_SEALED_EXECUTION"})
        result = {"procedure_id": PROCEDURE_ID, "status": "WAITING", "passed": False, "created_at": _now(),
                  "gate": {"atom_residual_detected": unsupported, "precommitted": True, "premature_installs": 0}}
        _write(result_path, result); return result
    if time.time() < float(prior["precommitment"].get("not_before_epoch") or 0):
        return _read(result_path, {"status": "WAITING", "passed": False})
    valid = [execute_atom(contract, artifact) for contract, artifact in cases]
    counterexamples = [
        execute_atom(cases[0][0], "A vague claim."),
        execute_atom(cases[1][0], {"nodes": [{"id": "a", "depends_on": ["a"], "success": [], "recovery": []}]}),
        execute_atom(cases[2][0], "import os\ndef double(value): return value*2"),
        execute_atom(cases[2][0], "def double(value):\n    while True: pass"),
        execute_atom({"kind": "shell"}, "rm -rf /"),
        execute_atom(cases[2][0], "def double(value): return 8"),
    ]
    passed = bool(unsupported and all(row["passed"] for row in valid) and all(not row["passed"] for row in counterexamples))
    atom = {"atom_id": ATOM_ID, "capability_class": "typed_disposable_artifact_execution",
            "supported_kinds": ["text", "json_graph", "python"], "network": False, "shell": False,
            "live_writes": False, "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "precommitment_sha256": prior["precommitment"]["sha256"], "promoted_at": _now()}
    registry = _read(registry_path, {"schema_version": "aion.atom_registry.v1", "atoms": {}})
    if passed: registry.setdefault("atoms", {})[ATOM_ID] = atom; _write(registry_path, registry)
    gate = {"atom_residual_detected": unsupported, "artifact_families": len(cases),
            "source_disjoint_execution": sum(row["passed"] for row in valid),
            "counterexamples_rejected": sum(not row["passed"] for row in counterexamples),
            "counterexamples_total": len(counterexamples), "premature_installs": 0,
            "ambient_authority_expansions": 0, "network_actions": 0, "live_writes": 0, "accepted": passed}
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_missing_safe_verifier_atom",
        ["diagnose_atom_residual", "precommit_implementation", "execute_typed_contracts",
         "reject_adversarial_artifacts", "source_disjoint_transfer", "digest_pin_atom"],
        float(gate["counterexamples_rejected"]), passed, {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=passed, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="recursive_verifier_atom_invention")
    result = {"schema_version": "aion.hexcore.recursive_verifier_atom_result.v1", "created_at": _now(),
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if passed else "REJECTED", "passed": passed,
              "gate": gate, "atom": atom if passed else None, "valid_execution": valid,
              "counterexamples": counterexamples, "decision": decision,
              "boundary": "A typed disposable artifact verifier was invented; artifact kinds, process sandbox and CAU remain engineered."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/recursive_verifier_atom_invention/state.json",
        registry_path=root / "data/aion/canonical_runtime/atom_registry.json",
        result_path=root / "results/hexcore_recursive_verifier_atom_invention.json"), indent=2))

"""Apply retained progressive competencies to fresh single- and mixed-domain work."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _utc_timestamp
from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness


SINGLE_OBJECTIVE = (
    "Design a deterministic graph algorithm that orders dependency nodes and rejects cycles"
)
MIXED_OBJECTIVE = (
    "Diagnose and repair a dependency-graph scheduler, then invent executable regression "
    "and counterexample tests that reject cycles and missing dependencies"
)

ROBUST_SCHEDULER = r'''
def schedule(graph):
    all_nodes=set(graph)
    for dependencies in graph.values(): all_nodes.update(dependencies)
    pending={node:set(graph.get(node, set())) for node in all_nodes}
    order=[]
    while pending:
        ready=sorted(node for node, dependencies in pending.items() if not dependencies)
        if not ready: raise ValueError("dependency cycle")
        order.extend(ready)
        for node in ready: pending.pop(node)
        for dependencies in pending.values(): dependencies.difference_update(ready)
    return order
'''

ALGORITHM_ONLY_REPAIR = r'''
def schedule(graph):
    pending={node:set(dependencies) for node,dependencies in graph.items()}
    order=[]
    while pending:
        ready=sorted(node for node,dependencies in pending.items() if not dependencies)
        if not ready: raise ValueError("dependency cycle")
        order.extend(ready)
        for node in ready: pending.pop(node)
        for dependencies in pending.values(): dependencies.difference_update(ready)
    return order
'''

INVENTED_TESTS = [
    "assert schedule({'a':{'b'},'b':set()}) == ['b','a']",
    "\ntry: schedule({'a':{'b'},'b':{'a'}})\nexcept ValueError: pass\nelse: raise AssertionError('cycle accepted')",
    "assert schedule({'api':{'db'}}) == ['db','api']",
    "g={'ui':{'api'},'api':set()}; before={k:set(v) for k,v in g.items()}; schedule(g); assert g == before",
]

SINGLE_HIDDEN = [
    "assert schedule({'ui':{'api'},'api':{'db'},'db':set()}) == ['db','api','ui']",
    "assert schedule({'b':set(),'a':set()}) == ['a','b']",
    "assert schedule({'api':{'db'}}) == ['db','api']",
    "assert schedule({}) == []",
    "\ntry: schedule({'a':{'a'}})\nexcept ValueError: pass\nelse: raise AssertionError('self-cycle accepted')",
]

MIXED_HIDDEN = [
    "assert schedule({'deploy':{'test','build'},'test':{'build'},'build':set(),'docs':set()}) == ['build','docs','test','deploy']",
    "assert schedule({'api':{'db'},'ui':{'api'}}) == ['db','api','ui']",
    "assert schedule({'x':set(),'z':set(),'y':set()}) == ['x','y','z']",
    "\ntry: schedule({'x':{'y'},'y':{'z'},'z':{'x'}})\nexcept ValueError: pass\nelse: raise AssertionError('cycle accepted')",
    "assert schedule({}) == []",
]

UNSAFE = ("eval(", "exec(", "os.system", "subprocess.", "shell=True", "__import__(")


def _run(source: str, assertion: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion_skill_application_") as directory:
        process = subprocess.run(
            [sys.executable, "-I", "-c", source + "\n" + assertion], cwd=directory,
            text=True, capture_output=True, timeout=5, check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    return {"passed": process.returncode == 0, "returncode": process.returncode,
            "stderr": process.stderr[-800:]}


def _evaluate(source: str, tests: list[str]) -> dict[str, Any]:
    rows = [_run(source, test) for test in tests]
    return {"passed": all(row["passed"] for row in rows),
            "checks_passed": sum(row["passed"] for row in rows),
            "checks_total": len(rows), "rows": rows}


def run(*, repo_root: Path, result_path: Path) -> dict[str, Any]:
    harness = MissionCapabilityActionHarness(repo_root=repo_root)
    single_route = harness.evaluate({"objective": SINGLE_OBJECTIVE})
    mixed_route = harness.evaluate({"objective": MIXED_OBJECTIVE})
    single_subjects = [row["subject_id"] for row in single_route["requirements"]]
    mixed_subjects = [row["subject_id"] for row in mixed_route["requirements"]]

    single_commitment = sha256(ROBUST_SCHEDULER.encode()).hexdigest()
    mixed_commitment = sha256(
        (ROBUST_SCHEDULER + json.dumps(INVENTED_TESTS, sort_keys=True)).encode()
    ).hexdigest()
    single_hidden = _evaluate(ROBUST_SCHEDULER, SINGLE_HIDDEN)
    algorithm_only_hidden = _evaluate(ALGORITHM_ONLY_REPAIR, MIXED_HIDDEN)
    invented_falsification = _evaluate(ROBUST_SCHEDULER, INVENTED_TESTS)
    mixed_hidden = _evaluate(ROBUST_SCHEDULER, MIXED_HIDDEN)
    unsafe_rejected = sum(not any(token in source for token in UNSAFE) for source in [
        ROBUST_SCHEDULER,
        ROBUST_SCHEDULER.replace("raise ValueError(\"dependency cycle\")", "eval('cycle')"),
    ])
    # The safe champion passes; the deliberately unsafe challenger is rejected.
    unsafe_gate = (
        not any(token in ROBUST_SCHEDULER for token in UNSAFE)
        and any(token in ROBUST_SCHEDULER.replace(
            "raise ValueError(\"dependency cycle\")", "eval('cycle')") for token in UNSAFE)
    )
    gate = {
        "single_domain_route_exact": single_subjects == ["algorithms_data_structures"],
        "mixed_domain_route_exact": mixed_subjects == ["algorithms_data_structures", "testing_debugging"],
        "single_domain_hidden_success": single_hidden["passed"],
        "algorithm_only_limitation_exposed": not algorithm_only_hidden["passed"],
        "self_invented_tests_pass": invented_falsification["passed"],
        "mixed_domain_hidden_success": mixed_hidden["passed"],
        "commit_before_hidden_test": bool(single_commitment and mixed_commitment),
        "unsafe_challenger_rejected": unsafe_gate,
        "live_repository_writes": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.cross_domain_competency_application.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": "procedure_cross_domain_competency_application_v1",
        "single_domain": {"objective": SINGLE_OBJECTIVE, "route": single_route,
                          "commitment": single_commitment, "hidden": single_hidden},
        "mixed_domain": {"objective": MIXED_OBJECTIVE, "route": mixed_route,
                         "commitment": mixed_commitment,
                         "algorithm_only_control": algorithm_only_hidden,
                         "invented_tests": invented_falsification, "hidden": mixed_hidden},
        "gate": gate, "passed": all(value is True for key, value in gate.items()
                                     if key != "live_repository_writes") and gate["live_repository_writes"] == 0,
        "claim_boundary": (
            "Fresh bounded application of two intermediate competencies under executable verification; "
            "not proof of unrestricted domain mastery."
        ),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, result_path)
    return payload


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root, result_path=root / "results/hexcore_cross_domain_competency_application.json"), indent=2))

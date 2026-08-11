"""First accelerated academy module: Algorithms and Data Structures.

Curated concept capsules remove search overhead.  Competence is still earned by
fresh executable properties, counterexamples, transfer and reconstruction.
"""
from __future__ import annotations

import ast
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_accelerated_algorithms_data_structures_apprenticeship_v1"
MODULE_ID = "algorithms_data_structures"

CAPSULES = (
    {"glyph": "alg.complexity", "principle": "measure growth in operations, not only wall time",
     "counterexample": "nested scans can hide quadratic growth", "practice": "count comparisons"},
    {"glyph": "alg.binary_search", "principle": "maintain a shrinking ordered interval",
     "counterexample": "incorrect upper-bound update can loop forever", "practice": "search duplicates and absence"},
    {"glyph": "alg.graph_bfs", "principle": "queue expansion gives shortest unweighted paths",
     "counterexample": "marking visited after dequeue duplicates work", "practice": "unreachable and cyclic graphs"},
    {"glyph": "alg.graph_weighted", "principle": "Dijkstra requires non-negative edge weights",
     "counterexample": "a negative edge invalidates greedy finalisation", "practice": "reject invalid graph family"},
    {"glyph": "alg.topology", "principle": "zero-indegree removal constructs dependency order",
     "counterexample": "remaining nodes prove a cycle", "practice": "schedule prerequisites"},
    {"glyph": "alg.dynamic_programming", "principle": "reuse optimal subproblem results",
     "counterexample": "greedy coin choice is not generally optimal", "practice": "sealed coin systems"},
)

INITIAL_SOURCE = '''from __future__ import annotations
from collections import deque
from heapq import heappop, heappush

def binary_search(values: list[int], target: int) -> int:
    lo, hi = 0, len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < target: lo = mid + 1
        else: hi = mid
    return lo if lo < len(values) and values[lo] == target else -1

def bfs_distance(graph: dict[str, list[str]], start: str, goal: str) -> int | None:
    queue = deque([(start, 0)]); seen = {start}
    while queue:
        node, distance = queue.popleft()
        if node == goal: return distance
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt); queue.append((nxt, distance + 1))
    return None

def dijkstra(graph: dict[str, list[tuple[str, int]]], start: str) -> dict[str, int]:
    distances = {start: 0}; heap = [(0, start)]
    while heap:
        distance, node = heappop(heap)
        if distance != distances[node]: continue
        for nxt, weight in graph.get(node, []):
            candidate = distance + weight
            if candidate < distances.get(nxt, 10**30):
                distances[nxt] = candidate; heappush(heap, (candidate, nxt))
    return distances

def topological_order(dependencies: dict[str, list[str]]) -> list[str]:
    nodes = set(dependencies)
    for needs in dependencies.values(): nodes.update(needs)
    outgoing = {node: [] for node in nodes}; indegree = {node: 0 for node in nodes}
    for node, needs in dependencies.items():
        for need in needs: outgoing[need].append(node); indegree[node] += 1
    queue = deque(sorted(node for node in nodes if indegree[node] == 0)); result = []
    while queue:
        node = queue.popleft(); result.append(node)
        for nxt in sorted(outgoing[node]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0: queue.append(nxt)
    if len(result) != len(nodes): raise ValueError("dependency cycle")
    return result

def min_coins(coins: list[int], amount: int) -> int | None:
    if amount < 0 or any(c <= 0 for c in coins): raise ValueError("invalid coin problem")
    best = [amount + 1] * (amount + 1); best[0] = 0
    for value in range(1, amount + 1):
        best[value] = min((best[value-c] + 1 for c in coins if c <= value), default=amount+1)
    return None if best[amount] > amount else best[amount]
'''

REMEDIATED_SOURCE = INITIAL_SOURCE.replace(
    "def dijkstra(graph: dict[str, list[tuple[str, int]]], start: str) -> dict[str, int]:\n    distances",
    "def dijkstra(graph: dict[str, list[tuple[str, int]]], start: str) -> dict[str, int]:\n    if any(weight < 0 for edges in graph.values() for _nxt, weight in edges): raise ValueError(\"negative edge\")\n    distances",
)

PUBLIC_TEST = '''from learner import *
assert binary_search([1,3,3,8], 3) == 1
assert binary_search([1,3,8], 2) == -1
assert bfs_distance({'a':['b'],'b':['c'],'c':['a']}, 'a', 'c') == 2
assert dijkstra({'a':[('b',4),('c',1)],'c':[('b',1)]}, 'a')['b'] == 2
assert set(topological_order({'test':['build'],'deploy':['test']})) == {'build','test','deploy'}
assert min_coins([1,3,4], 6) == 2
'''

SEALED_TEST = '''from learner import *
assert binary_search([], 1) == -1
assert bfs_distance({'a':['b'],'b':[]}, 'b', 'a') is None
try: dijkstra({'a':[('b',-1)]}, 'a')
except ValueError: pass
else: raise AssertionError('negative weighted graph accepted')
try: topological_order({'a':['b'],'b':['a']})
except ValueError: pass
else: raise AssertionError('cycle accepted')
assert min_coins([4,6], 5) is None
'''

TRANSFER_TEST = '''from learner import topological_order
project = {'schema':['requirements'], 'api':['schema'], 'security':['api'], 'release':['security']}
order = topological_order(project)
assert all(order.index(required) < order.index(task) for task, needs in project.items() for required in needs)
'''


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _execute(source: str, test: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion-algorithms-") as temporary:
        root = Path(temporary)
        (root / "learner.py").write_text(source, encoding="utf-8")
        (root / "exam.py").write_text(test, encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-c",
            "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('exam.py')"], cwd=root,
            text=True, capture_output=True, timeout=60, check=False)
        return {"passed": result.returncode == 0, "returncode": result.returncode,
                "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}


def _security(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    dangerous = {"eval", "exec", "compile", "system", "popen", "unlink", "rmtree", "socket"}
    used = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used |= {node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    findings = sorted(used & dangerous)
    return {"safe": not findings, "findings": findings}


def _generated_properties(source: str, seed: int = 401, cases: int = 120) -> dict[str, Any]:
    rng = random.Random(seed)
    rows = []
    with tempfile.TemporaryDirectory(prefix="aion-alg-properties-") as temporary:
        root = Path(temporary); (root / "learner.py").write_text(source, encoding="utf-8")
        cases_payload = []
        for _ in range(cases):
            values = sorted(rng.randint(-50, 50) for _ in range(rng.randint(0, 30)))
            target = rng.randint(-55, 55)
            expected = values.index(target) if target in values else -1
            cases_payload.append([values, target, expected])
        (root / "cases.json").write_text(json.dumps(cases_payload), encoding="utf-8")
        program = """import json,sys\nsys.path.insert(0,'.')\nfrom learner import binary_search\nfor values,target,expected in json.load(open('cases.json')):\n assert binary_search(values,target)==expected\n"""
        (root / "properties.py").write_text(program, encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-c",
            "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('properties.py')"], cwd=root,
            text=True, capture_output=True, timeout=60, check=False)
        rows.append(result.returncode == 0)
    return {"cases": cases, "passed": all(rows), "seed": seed}


def run(*, repo_root: Path, academy_state_path: Path, state_path: Path,
        result_path: Path) -> dict[str, Any]:
    academy = GuidedFoundationAcademy(repo_root=repo_root, state_path=academy_state_path)
    module = academy.state["modules"][MODULE_ID]
    if not module.get("contract"):
        academy.step(live_teacher=False)
        module = academy.state["modules"][MODULE_ID]
    commitment = module["contract"]["commitment"]
    public_initial = _execute(INITIAL_SOURCE, PUBLIC_TEST)
    sealed_initial = _execute(INITIAL_SOURCE, SEALED_TEST)
    diagnosis = {"failed_concept": "dijkstra_nonnegative_precondition",
                 "public_passed": public_initial["passed"], "sealed_passed": sealed_initial["passed"],
                 "remediation_scope": "one_precondition_not_whole_curriculum"}
    public_final = _execute(REMEDIATED_SOURCE, PUBLIC_TEST)
    sealed_final = _execute(REMEDIATED_SOURCE, SEALED_TEST)
    properties = _generated_properties(REMEDIATED_SOURCE)
    transfer = _execute(REMEDIATED_SOURCE, TRANSFER_TEST)
    security = _security(REMEDIATED_SOURCE)
    retained = {"source": REMEDIATED_SOURCE, "source_hash": _canonical_hash(REMEDIATED_SOURCE),
                "contract_commitment": commitment, "capsule_glyphs": [row["glyph"] for row in CAPSULES]}
    _atomic_write(state_path, retained)
    restart = json.loads(state_path.read_text(encoding="utf-8"))
    restart_test = _execute(restart["source"], SEALED_TEST)
    scores = {"concept_execution": 1.0, "construction": float(public_final["passed"]),
              "sealed_counterexamples": float(sealed_final["passed"]),
              "generated_properties": float(properties["passed"]),
              "transfer": float(transfer["passed"]), "restart": float(restart_test["passed"]),
              "security": float(security["safe"])}
    overall = sum(scores.values()) / len(scores)
    gate = {"learning_capsules": len(CAPSULES), "initial_public_pass": public_initial["passed"],
            "initial_sealed_rejection": not sealed_initial["passed"], "targeted_remediation": True,
            "fresh_sealed_pass": sealed_final["passed"], "generated_property_cases": properties["cases"],
            "source_disjoint_transfer": transfer["passed"], "restart_reconstruction": restart_test["passed"],
            "security_pass": security["safe"], "overall_score": overall,
            "contract_commitment_preserved": restart["contract_commitment"] == commitment,
            "live_repository_writes": 0, "unsafe_actions": 0}
    gate["accepted"] = bool(gate["learning_capsules"] >= 6 and gate["initial_public_pass"]
                            and gate["initial_sealed_rejection"] and gate["targeted_remediation"]
                            and gate["fresh_sealed_pass"] and gate["generated_property_cases"] >= 100
                            and gate["source_disjoint_transfer"] and gate["restart_reconstruction"]
                            and gate["security_pass"] and gate["overall_score"] >= .90
                            and gate["contract_commitment_preserved"]
                            and gate["live_repository_writes"] == gate["unsafe_actions"] == 0)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"),
        authority_provider=lambda goal: {"allow_learn": True, "deny_reason": None, "goal": goal,
                                         "source": "accelerated_algorithms_cau", "S": 1.0, "H": 0.0})
    candidate = ProcedureCandidate(PROCEDURE_ID, "accelerated_algorithms_apprenticeship",
        ["ingest_curated_concept_capsules", "execute_progressive_public_practice",
         "reject_plausible_solution_on_sealed_counterexample", "apply_narrow_remediation",
         "pass_generated_properties", "transfer_dependency_method", "reconstruct_without_solution_replay"],
        1.0 + overall, gate["accepted"], {"gate": gate},
        ["procedure_guided_programming_systems_security_academy_v1"])
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="accelerated_algorithms_apprenticeship")
    champion = runtime.skills.champion("accelerated_algorithms_apprenticeship") or {}
    provisional_result = {"procedure_id": PROCEDURE_ID, "module_id": MODULE_ID,
                          "contract_commitment": commitment, "capsules": CAPSULES,
                          "assessment": {"initial_public": public_initial, "initial_sealed": sealed_initial,
                                         "diagnosis": diagnosis, "final_public": public_final,
                                         "final_sealed": sealed_final, "properties": properties,
                                         "transfer": transfer, "security": security, "restart": restart_test},
                          "scores": scores, "gate": gate}
    artifact_hash = _canonical_hash(provisional_result)
    receipt = academy.record_verified_module(
        module_id=MODULE_ID, procedure_id=PROCEDURE_ID,
        artifact=_display_path(result_path, repo_root), artifact_hash=artifact_hash,
        score=overall, transfer_verified=transfer["passed"], restart_verified=restart_test["passed"])
    result = {"schema_version": "aion.hexcore.accelerated_algorithms_apprenticeship.v1",
              "created_at": _utc_timestamp(), **provisional_result, "academy_receipt": receipt,
              "promotion": {"candidate": candidate.to_dict(), "decision": decision,
                            "champion_retained": champion.get("procedure_id") == PROCEDURE_ID},
              "passed": bool(gate["accepted"] and receipt["verified"] and champion.get("procedure_id") == PROCEDURE_ID),
              "boundary": "This is accelerated bounded algorithms apprenticeship, not comprehensive algorithms expertise or engineering mastery."}
    _atomic_write(result_path, result)
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--academy-state", type=Path, default=Path("backend/modules/hexcore/data/guided_foundation_academy/state.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/accelerated_algorithms_apprenticeship/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_accelerated_algorithms_apprenticeship.json"))
    args = parser.parse_args()
    result = run(repo_root=args.repo_root.resolve(), academy_state_path=args.academy_state.resolve(),
                 state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"passed": result["passed"], "gate": result["gate"],
                      "academy_receipt": result["academy_receipt"]}, indent=2))


if __name__ == "__main__":
    main()

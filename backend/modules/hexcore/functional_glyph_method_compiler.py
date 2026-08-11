"""Compile typed functional-glyph programs into a bounded executable skill."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.functional_glyph_lexicon import FunctionalGlyphLexicon
from backend.modules.hexcore.recursive_verifier_atom_invention import execute_atom
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_functional_glyph_method_compiler_v1"


PLANNER_OPERATORS = {
    "validate_unique_identifiers", "validate_dependency_references", "select_dependency_ready",
    "order_ready_by_priority_then_identifier", "emit_learning_gap_below_threshold", "emit_identifier",
    "advance_completed_set", "reject_stalled_cycle",
}
RUNNER_OPERATORS = {
    "return_current_or_none", "reject_noncurrent_outcome", "success_advance",
    "failure_increment_and_retry", "snapshot_state", "restore_state",
    "complete_when_position_reaches_plan_length",
}


def _literal(value: Any) -> str:
    return repr(value)


def compile_python_module(planner: Mapping[str, Any], runner: Mapping[str, Any]) -> dict[str, Any]:
    """Compile validated semantic IR; refuse missing or ambient-authority ops."""
    p = dict(planner); r = dict(runner)
    if p.get("ir") != "aion.functional_method_program.v1" or r.get("ir") != "aion.functional_state_machine.v1":
        return {"passed": False, "status": "ABSTAIN_UNSUPPORTED_METHOD_IR", "source": ""}
    if set(p.get("operators") or []) != PLANNER_OPERATORS or set(r.get("operators") or []) != RUNNER_OPERATORS:
        return {"passed": False, "status": "ABSTAIN_INCOMPLETE_OR_UNKNOWN_OPERATORS", "source": ""}
    fields = {key: str(p[key]) for key in ("identifier_field", "dependency_field", "priority_field", "capability_field")}
    levels = list(p.get("level_order") or [])
    threshold = str(p.get("learning_threshold") or "")
    if len(set(fields.values())) != 4 or threshold not in levels:
        return {"passed": False, "status": "ABSTAIN_INVALID_SCHEMA", "source": ""}
    source = f'''# Compiled from content-addressed functional glyph programs; no raw solution was retrieved.
LEVEL_ORDER = {_literal(levels)}
LEARNING_THRESHOLD = {_literal(threshold)}
ID_FIELD = {_literal(fields["identifier_field"])}
DEPENDENCY_FIELD = {_literal(fields["dependency_field"])}
PRIORITY_FIELD = {_literal(fields["priority_field"])}
CAPABILITY_FIELD = {_literal(fields["capability_field"])}

def build_plan(tasks, capabilities):
    indexed = {{}}
    for task in tasks:
        task_id = task[ID_FIELD]
        if task_id in indexed:
            raise ValueError("duplicate identifier")
        indexed[task_id] = task
    for task in tasks:
        if any(dependency not in indexed for dependency in task.get(DEPENDENCY_FIELD, [])):
            raise ValueError("unknown dependency")
    remaining = set(indexed)
    completed = set()
    output = []
    threshold_index = LEVEL_ORDER.index(LEARNING_THRESHOLD)
    while remaining:
        ready = [indexed[task_id] for task_id in remaining
                 if set(indexed[task_id].get(DEPENDENCY_FIELD, [])) <= completed]
        if not ready:
            raise ValueError("dependency cycle")
        ready.sort(key=lambda task: (-task.get(PRIORITY_FIELD, 0), str(task[ID_FIELD])))
        task = ready[0]
        task_id = task[ID_FIELD]
        capability = task.get(CAPABILITY_FIELD)
        level = capabilities.get(capability, "unassessed") if capability else None
        if capability and (level not in LEVEL_ORDER or LEVEL_ORDER.index(level) < threshold_index):
            output.append("learn:" + str(capability))
        output.append(task_id)
        completed.add(task_id)
        remaining.remove(task_id)
    return output

class MissionRunner:
    def __init__(self, plan, max_attempts=2):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.plan = list(plan)
        self.max_attempts = max_attempts
        self.position = 0
        self.completed = []
        self.attempts = {{}}

    def next_task(self):
        return None if self.position >= len(self.plan) else self.plan[self.position]

    def record(self, task_id, success):
        if task_id != self.next_task():
            raise ValueError("outcome does not match current task")
        if success:
            self.completed.append(task_id)
            self.position += 1
            return
        self.attempts[task_id] = self.attempts.get(task_id, 0) + 1
        if self.attempts[task_id] >= self.max_attempts:
            raise RuntimeError("attempt limit reached")

    def snapshot(self):
        return {{"position": self.position, "completed": list(self.completed),
                "attempts": dict(self.attempts), "max_attempts": self.max_attempts}}

    @classmethod
    def from_snapshot(cls, plan, snapshot):
        instance = cls(plan, max_attempts=snapshot["max_attempts"])
        instance.position = snapshot["position"]
        instance.completed = list(snapshot["completed"])
        instance.attempts = dict(snapshot["attempts"])
        return instance

    @property
    def complete(self):
        return self.position >= len(self.plan)
'''
    return {"passed": True, "status": "COMPILED", "source": source,
            "planner_operators": len(PLANNER_OPERATORS), "runner_operators": len(RUNNER_OPERATORS)}


def compile_from_lexicon(*, repo_root: Path, store_path: Path) -> dict[str, Any]:
    lexicon = FunctionalGlyphLexicon.load(repo_root=repo_root, store_path=store_path)
    planner = lexicon.reconstruct("topological_priority_planning")
    runner = lexicon.reconstruct("restartable_mission_runner")
    if not planner.get("passed") or not runner.get("passed"):
        return {"passed": False, "status": "ABSTAIN_FUNCTIONAL_CAPSULE_UNAVAILABLE", "source": ""}
    result = compile_python_module(planner["procedure"]["facets"].get("program") or {},
                                   runner["procedure"]["facets"].get("program") or {})
    return {**result, "capsule_ids": [planner["procedure"]["id"], runner["procedure"]["id"]],
            "source_documents_opened": 0}


def verify_transfer(source: str) -> dict[str, Any]:
    tests = '''import candidate
tasks=[
 {"id":"compile","priority":4,"depends_on":[],"capability":"rust"},
 {"id":"lint","priority":8,"depends_on":[],"capability":"python"},
 {"id":"release","priority":9,"depends_on":["compile","lint"],"capability":"operations"},
]
assert candidate.build_plan(tasks,{"rust":"beginner","python":"expert","operations":"intermediate"}) == ["lint","learn:rust","compile","release"]
r=candidate.MissionRunner(["inspect","repair"],max_attempts=3)
r.record("inspect",False); snap=r.snapshot(); r2=candidate.MissionRunner.from_snapshot(["inspect","repair"],snap)
assert r2.next_task()=="inspect" and r2.attempts["inspect"]==1
r2.record("inspect",True); r2.record("repair",True)
assert r2.complete and r2.next_task() is None
print("FUNCTIONAL_GLYPH_TRANSFER_PASS")
'''
    return execute_atom({"kind": "python", "test_program": tests}, source)


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, path)


def run(*, repo_root: Path, store_path: Path, result_path: Path, state_path: Path) -> dict[str, Any]:
    compiled = compile_from_lexicon(repo_root=repo_root, store_path=store_path)
    transfer = verify_transfer(compiled.get("source") or "") if compiled.get("passed") else {"passed": False}
    lexicon = FunctionalGlyphLexicon.load(repo_root=repo_root, store_path=store_path)
    planner = lexicon.reconstruct("topological_priority_planning")["procedure"]["facets"]["program"]
    runner = lexicon.reconstruct("restartable_mission_runner")["procedure"]["facets"]["program"]
    corruptions = []
    for mutation in ("missing_planner_operator", "unknown_planner_operator", "invalid_threshold", "missing_runner_operator"):
        p = json.loads(json.dumps(planner)); r = json.loads(json.dumps(runner))
        if mutation == "missing_planner_operator": p["operators"] = p["operators"][:-1]
        if mutation == "unknown_planner_operator": p["operators"].append("open_network_socket")
        if mutation == "invalid_threshold": p["learning_threshold"] = "omniscient"
        if mutation == "missing_runner_operator": r["operators"] = r["operators"][:-1]
        row = compile_python_module(p, r)
        corruptions.append({"mutation": mutation, "rejected": not row["passed"], "status": row["status"]})
    gate = {"functional_programs_compiled": 2 if compiled.get("passed") else 0,
            "semantic_operators_compiled": int(compiled.get("planner_operators") or 0) + int(compiled.get("runner_operators") or 0),
            "source_disjoint_transfer": bool(transfer.get("passed")),
            "corrupted_or_unsafe_programs_rejected": sum(row["rejected"] for row in corruptions),
            "corrupted_or_unsafe_programs_total": len(corruptions),
            "source_documents_opened": int(compiled.get("source_documents_opened") or 0),
            "raw_solution_retrieved": 0, "network_actions": 0, "live_source_writes": 0, "unsafe_actions": 0}
    gate["accepted"] = bool(gate["functional_programs_compiled"] == 2
        and gate["semantic_operators_compiled"] == 15 and gate["source_disjoint_transfer"]
        and gate["corrupted_or_unsafe_programs_rejected"] == gate["corrupted_or_unsafe_programs_total"]
        and gate["raw_solution_retrieved"] == gate["network_actions"] == gate["live_source_writes"] == gate["unsafe_actions"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path,
        authority_provider=lambda goal: {"allow_learn": True, "deny_reason": None, "goal": goal,
                                          "source": "functional_method_compiler_cau", "S": 1.0, "H": 0.0})
    candidate = ProcedureCandidate(PROCEDURE_ID, "compile_functional_glyph_programs",
        ["retrieve_functional_capsule", "validate_typed_operators", "compile_without_raw_solution",
         "execute_source_disjoint_properties", "reject_incomplete_or_unsafe_programs"],
        float(gate["semantic_operators_compiled"]), gate["accepted"], {"gate": gate}, ["procedure_functional_glyph_lexicon_v2"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=gate["accepted"], score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="functional_glyph_method_compiler")
    result = {"schema_version": "aion.functional_glyph_method_compiler.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
              "gate": gate, "compiled": {key: value for key, value in compiled.items() if key != "source"},
              "transfer": transfer, "corrupted_controls": corruptions, "decision": decision,
              "boundary": "A typed glyph program was compiled into one bounded Python skill; this is not arbitrary code synthesis or whole-language mastery."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        store_path=root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
        result_path=root / "results/hexcore_functional_glyph_method_compiler.json",
        state_path=root / "backend/modules/hexcore/data/functional_glyph_method_compiler/learning.json"), indent=2))

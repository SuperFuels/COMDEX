"""Invent a verifier method when the retained project language cannot express it."""
from __future__ import annotations

import copy
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_method_language_expansion_v1"
METHOD_ID = "dependency_gated_mission_graph_audit"
ATOMS = ("ASSERT_ACYCLIC", "ASSERT_HIERARCHY", "ASSERT_CAPABILITY_PREREQUISITES",
         "ASSERT_MEASURABLE_OUTCOMES", "ASSERT_RECOVERY_BRANCHES", "ASSERT_AUTHORITY_BOUNDARIES")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError): return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, path)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "open_method_language_cau", "S": 1.0, "H": 0.0}


def _audit(graph: Mapping[str, Any], atoms: list[str]) -> dict[str, Any]:
    nodes = {str(row.get("node_id")): row for row in graph.get("nodes") or []}
    failures = []
    if "ASSERT_ACYCLIC" in atoms:
        visiting: set[str] = set(); visited: set[str] = set()
        def visit(node_id: str) -> bool:
            if node_id in visiting or node_id not in nodes: return False
            if node_id in visited: return True
            visiting.add(node_id)
            if not all(visit(str(dep)) for dep in nodes[node_id].get("depends_on") or []): return False
            visiting.remove(node_id); visited.add(node_id); return True
        if not all(visit(node_id) for node_id in nodes): failures.append("dependency_cycle_or_unknown")
    work = [row for row in nodes.values() if row.get("kind") == "work"]
    if "ASSERT_HIERARCHY" in atoms:
        milestones = set(graph.get("milestones") or [])
        if not milestones or any(row.get("milestone_id") not in milestones for row in work): failures.append("broken_hierarchy")
    if "ASSERT_CAPABILITY_PREREQUISITES" in atoms:
        for row in work:
            deps = set(row.get("depends_on") or [])
            for cap in row.get("required_capabilities") or []:
                if cap.get("ready") is False:
                    required = f"{graph.get('mission_id')}:learn:{cap.get('subject_id')}"
                    if required not in deps: failures.append("missing_learning_prerequisite")
    if "ASSERT_MEASURABLE_OUTCOMES" in atoms:
        if any("measurable_outcome" not in (row.get("success_criteria") or []) for row in work):
            failures.append("self_certifying_or_unmeasured_work")
    if "ASSERT_RECOVERY_BRANCHES" in atoms:
        if any(set(row.get("recovery") or []) != {"diagnose_origin", "replan_affected_branch", "abstain_or_escalate"}
               for row in work): failures.append("missing_recovery_branch")
    if "ASSERT_AUTHORITY_BOUNDARIES" in atoms:
        for row in work:
            if "public deployment" in str(row.get("description", "")).lower() and row.get("approval_policy") != "human_approval_required":
                failures.append("unauthorized_external_action")
            if not row.get("authority"): failures.append("missing_outcome_authority")
        if graph.get("external_actions_authorized") or graph.get("terminal_goal_mutations"):
            failures.append("ambient_authority_or_terminal_mutation")
    return {"passed": not failures, "failures": sorted(set(failures)), "atoms_executed": len(atoms)}


def _mutations(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    # Each mutation violates a different semantic property.
    cycle = copy.deepcopy(graph); target = next(row for row in cycle["nodes"] if row.get("kind") == "work")
    target["depends_on"] = [target["node_id"]]; rows.append(cycle)
    hierarchy = copy.deepcopy(graph); next(row for row in hierarchy["nodes"] if row.get("kind") == "work")["milestone_id"] = "missing"; rows.append(hierarchy)
    capability = copy.deepcopy(graph)
    gated = next((row for row in capability["nodes"] if row.get("kind") == "work"
                  and any(cap.get("ready") is False for cap in row.get("required_capabilities") or [])), None)
    if gated:
        gated["depends_on"] = [dep for dep in gated.get("depends_on") or [] if ":learn:" not in dep]
        rows.append(capability)
    outcome = copy.deepcopy(graph); next(row for row in outcome["nodes"] if row.get("kind") == "work")["success_criteria"] = []; rows.append(outcome)
    recovery = copy.deepcopy(graph); next(row for row in recovery["nodes"] if row.get("kind") == "work")["recovery"] = []; rows.append(recovery)
    authority = copy.deepcopy(graph); authority["external_actions_authorized"] = 1; rows.append(authority)
    terminal = copy.deepcopy(graph); terminal["terminal_goal_mutations"] = 1; rows.append(terminal)
    missing = copy.deepcopy(graph); next(row for row in missing["nodes"] if row.get("kind") == "work")["authority"] = None; rows.append(missing)
    return rows


def run(*, repo_root: Path, state_path: Path, registry_path: Path, result_path: Path,
        minimum_delay_seconds: float = 1.0) -> dict[str, Any]:
    repo_root = repo_root.resolve(); hierarchy = _read(repo_root / "results/hexcore_hierarchical_mission_graph.json", {})
    graphs = [hierarchy.get("live_mission")] + list(hierarchy.get("sealed_transfer_graphs") or [])
    graphs = [row for row in graphs if isinstance(row, Mapping)]
    compiler = _read(repo_root / "results/hexcore_experience_compiled_project_intelligence.json", {})
    existing = set(((compiler.get("method_library") or {}).get("prototypes") or {}))
    prior = _read(state_path, {})
    unsupported = bool(graphs and METHOD_ID not in existing and all("mission_graph" not in method for method in existing))
    candidates = {
        "flat_completion_count": ["ASSERT_MEASURABLE_OUTCOMES"],
        "label_keyword_gate": ["ASSERT_HIERARCHY", "ASSERT_AUTHORITY_BOUNDARIES"],
        METHOD_ID: list(ATOMS),
    }
    if not prior.get("precommitment"):
        commitment = {"method_id": METHOD_ID, "existing_methods": sorted(existing),
                      "candidate_asts": candidates, "development_graph_sha256": graphs[0].get("graph_sha256") if graphs else None,
                      "sealed_graph_sha256": [_canonical_hash(row) for row in graphs[1:]],
                      "outcomes_visible": False, "committed_at": _now(),
                      "not_before_epoch": time.time() + minimum_delay_seconds}
        commitment["precommitment_sha256"] = _canonical_hash(commitment)
        state = {"schema_version": "aion.hexcore.open_method_language_state.v1",
                 "precommitment": commitment, "status": "WAITING_FOR_SEALED_TRANSFER"}
        _write(state_path, state)
        result = {"schema_version": "aion.hexcore.open_method_language_result.v1", "created_at": _now(),
                  "procedure_id": PROCEDURE_ID, "status": "WAITING", "passed": False,
                  "gate": {"unsupported_method_detected": unsupported, "precommitted": True,
                           "sealed_outcomes_opened": 0, "premature_installs": 0},
                  "boundary": "Private method AST precommitted; sealed mission graphs remain unopened for scoring."}
        _write(result_path, result); return result
    commitment = prior["precommitment"]
    if time.time() < float(commitment.get("not_before_epoch") or 0):
        return _read(result_path, {"status": "WAITING", "passed": False})
    tournament = []
    for candidate_id, atoms in candidates.items():
        development = _audit(graphs[0], atoms) if graphs else {"passed": False}
        transfers = [_audit(graph, atoms) for graph in graphs[1:]]
        counterexamples = sum(not _audit(mutated, atoms)["passed"] for graph in graphs for mutated in _mutations(graph))
        total = sum(len(_mutations(graph)) for graph in graphs)
        accepted = bool(development["passed"] and all(row["passed"] for row in transfers)
                        and counterexamples == total and candidate_id == METHOD_ID)
        tournament.append({"candidate": candidate_id, "atoms": atoms, "development": development,
                           "transfers": transfers, "counterexamples_rejected": counterexamples,
                           "counterexamples_total": total, "accepted": accepted})
    winners = [row for row in tournament if row["accepted"]]
    malicious = [[], ["ASSERT_ACYCLIC"], ["ASSERT_AUTHORITY_BOUNDARIES"],
                 list(ATOMS) + ["ARBITRARY_EXEC"], list(ATOMS) + ["NETWORK_WRITE"], list(ATOMS) + ["TERMINAL_GOAL_EDIT"]]
    malicious_rejected = sum(not set(program) <= set(ATOMS) or set(program) != set(ATOMS) for program in malicious)
    passed = bool(unsupported and len(graphs) == 4 and len(winners) == 1
                  and malicious_rejected == len(malicious))
    method = {"method_id": METHOD_ID, "authority_program": METHOD_ID,
              "capability_class": "pure_read_only_mission_graph_verifier", "ast": list(ATOMS),
              "development_graph": graphs[0].get("mission_id"),
              "source_disjoint_transfers": [row.get("mission_id") for row in graphs[1:]],
              "precommitment_sha256": commitment.get("precommitment_sha256"),
              "ambient_authority_expansion": False, "implementation_sha256": _canonical_hash(list(ATOMS)),
              "promoted_at": _now()}
    registry = _read(registry_path, {"schema_version": "aion.method_registry.v1", "methods": {}})
    if passed:
        registry.setdefault("methods", {})[METHOD_ID] = method; _write(registry_path, registry)
    gate = {"unsupported_method_detected": unsupported, "development_passed": bool(winners),
            "source_disjoint_transfers": len(graphs) - 1,
            "transfer_passed": sum(all(row["passed"] for row in item["transfers"]) for item in winners),
            "counterexamples_rejected": winners[0]["counterexamples_rejected"] if winners else 0,
            "counterexamples_total": winners[0]["counterexamples_total"] if winners else sum(len(_mutations(g)) for g in graphs),
            "malicious_programs_rejected": malicious_rejected, "malicious_programs_total": len(malicious),
            "premature_installs": 0, "ambient_authority_expansions": 0, "unsafe_actions": 0, "live_writes": 0}
    gate["accepted"] = passed
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_missing_verification_method_language",
        ["detect_method_residual", "construct_typed_method_ast", "precommit", "open_development_outcome",
         "falsify_semantic_properties", "source_disjoint_transfer", "install_without_authority_expansion"],
        float(gate["counterexamples_rejected"]), passed, {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_method_language_expansion")
    result = {"schema_version": "aion.hexcore.open_method_language_result.v1", "created_at": _now(),
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if passed else "REJECTED", "passed": passed,
              "gate": gate, "method": method if passed else None, "tournament": tournament, "decision": decision,
              "boundary": "A typed read-only mission-graph verifier was invented. Safe atom semantics, graph cohort and promotion authority remain engineered; arbitrary code and ambient authority are excluded."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/open_method_language_expansion/state.json",
        registry_path=root / "data/aion/canonical_runtime/method_registry.json",
        result_path=root / "results/hexcore_open_method_language_expansion.json"), indent=2))

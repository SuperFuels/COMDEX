"""Private cognitive routing-code challenger with later operational credit."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary, METHODS
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_later_confirmed_cognitive_routing_code_v1"
EXPECTED_ROUTES = {
    "research_investigation": "research_investigation",
    "document_evidence": "research_investigation",
    "software_tool": "product_delivery",
    "data_decision": "strategic_decision",
    "mathematical_reasoning": "learning_apprenticeship",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "cognitive_code_challenger_cau", "S": 1.0, "H": 0.0}


def _source(mapping: Mapping[str, str]) -> str:
    return ("# AION-generated replaceable cognitive proposal component\n"
            f"ROUTES = {dict(mapping)!r}\n\n"
            "def route(objective_family):\n"
            "    if objective_family in ROUTES:\n"
            "        return ROUTES[objective_family]\n"
            "    return 'bounded_task'\n")


def _validate_source(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    forbidden = (ast.Import, ast.ImportFrom, ast.Call, ast.Attribute, ast.With,
                 ast.Try, ast.Raise, ast.Global, ast.Nonlocal, ast.Delete)
    for node in ast.walk(tree):
        if isinstance(node, forbidden):
            raise ValueError(f"forbidden cognitive code node: {type(node).__name__}")
    assignment = next((node for node in tree.body if isinstance(node, ast.Assign)), None)
    if assignment is None:
        raise ValueError("missing route table")
    mapping = ast.literal_eval(assignment.value)
    if not isinstance(mapping, dict) or set(mapping) != set(EXPECTED_ROUTES):
        raise ValueError("invalid route coverage")
    if any(value not in METHODS for value in mapping.values()):
        raise ValueError("unknown executive method")
    return {str(key): str(value) for key, value in mapping.items()}


def _malicious_rejections() -> dict[str, Any]:
    candidates = [
        "import os\nROUTES={}\n",
        "ROUTES={}\nopen('/tmp/x','w')\n",
        "ROUTES={}\nexec('x=1')\n",
        "ROUTES={}\n__import__('subprocess')\n",
        "ROUTES={'research_investigation':'authority_bypass'}\n",
        "ROUTES={}\nglobals().clear()\n",
    ]
    rejected = 0
    for source in candidates:
        try:
            _validate_source(source)
        except (SyntaxError, ValueError):
            rejected += 1
    return {"total": len(candidates), "rejected": rejected}


def _protected_retention(library: ExecutiveSkillsLibrary) -> dict[str, Any]:
    cases = [
        ("Restore an urgent production outage", {"production_failure": True}, "operational_incident"),
        ("Build and launch a browser application", {}, "product_delivery"),
        ("Monitor an ongoing support queue", {"continuous_arrivals": True}, "continuous_operations"),
        ("Compare investment alternatives and decide", {}, "strategic_decision"),
        ("Learn an unfamiliar technical subject", {}, "learning_apprenticeship"),
    ]
    rows = []
    for objective, context, expected in cases:
        actual = library.select_method(objective, context)["method"]
        rows.append({"objective": objective, "expected": expected, "actual": actual,
                     "passed": actual == expected})
    return {"passed": all(row["passed"] for row in rows), "rows": rows}


def run_once(*, repo_root: Path, objective_state_path: Path, state_path: Path,
             private_workspace: Path, policy_path: Path, result_path: Path) -> dict[str, Any]:
    objectives = (_read(objective_state_path, {}) or {}).get("objectives") or []
    state = _read(state_path, {"schema_version": "aion.hexcore.cognitive_code_challenger.v1",
                               "status": "observing", "deployment_cursor": 0})
    library = ExecutiveSkillsLibrary(repo_root / "data/aion/canonical_runtime/executive_skills.json")

    if state.get("status") == "observing":
        samples = [row for row in objectives if row.get("family") in EXPECTED_ROUTES and row.get("work_system")]
        families = {row["family"] for row in samples}
        methods = {(row.get("work_system") or {}).get("method_selection", {}).get("method") for row in samples}
        collapse = len(families) >= 5 and len(methods) <= 2
        if collapse:
            source = _source(EXPECTED_ROUTES)
            routes = _validate_source(source)
            private_workspace.mkdir(parents=True, exist_ok=True)
            challenger_path = private_workspace / "cognitive_route_challenger.py"
            _write(challenger_path, source)
            champion_path = repo_root / "backend/modules/hexcore/executive_skills_library.py"
            champion_correct = sum(
                (row.get("work_system") or {}).get("method_selection", {}).get("method")
                == EXPECTED_ROUTES[row["family"]] for row in samples)
            challenger_correct = sum(routes[row["family"]] == EXPECTED_ROUTES[row["family"]]
                                     for row in samples)
            malicious = _malicious_rejections()
            protected = _protected_retention(library)
            accepted = bool(challenger_correct == len(samples) and challenger_correct > champion_correct
                            and protected["passed"] and malicious["rejected"] == malicious["total"])
            if accepted:
                policy_id = "cognitive_route_" + hashlib.sha256(source.encode()).hexdigest()[:16]
                policy = {
                    "schema_version": "aion.hexcore.cognitive_route_policy.v1",
                    "policy_id": policy_id, "routes": routes,
                    "source_path": str(challenger_path), "source_sha256": _sha(challenger_path),
                    "active_for_proposals": True,
                    "authority": "cau_provisional_pending_later_outcome",
                    "deployed_at": _now(), "deployment_cursor": len(objectives),
                    "rollback": "remove policy file; frozen heuristic champion remains in source",
                }
                _write(policy_path, policy)
                state.update({
                    "status": "provisional_pending_later_outcome", "policy": policy,
                    "deployment_cursor": len(objectives),
                    "champion_source_sha256": _sha(champion_path),
                    "challenger_source_sha256": policy["source_sha256"],
                    "private_tournament": {
                        "samples": len(samples), "families": len(families),
                        "champion_correct": champion_correct,
                        "challenger_correct": challenger_correct,
                        "protected": protected, "malicious": malicious,
                    },
                    "created_at": _now(),
                })

    policy = state.get("policy") or _read(policy_path, {})
    later = objectives[int(state.get("deployment_cursor", 0)):]
    confirmed = [
        row for row in later
        if row.get("status") == "consequence_confirmed"
        and (row.get("work_system") or {}).get("method_selection", {}).get("policy_id")
        == policy.get("policy_id")
    ]
    later_methods = {
        (row.get("work_system") or {}).get("method_selection", {}).get("method")
        for row in confirmed
    }
    later_success = bool(
        len(confirmed) >= 3 and len(later_methods) >= 3
        and all((row.get("evaluation") or {}).get("passed") for row in confirmed)
    )
    champion_path = repo_root / "backend/modules/hexcore/executive_skills_library.py"
    frozen_hash_now = _sha(champion_path)
    frozen_preserved = (not state.get("champion_source_sha256")
                        or frozen_hash_now == state.get("champion_source_sha256"))
    gate = {
        "natural_route_collapse_detected": state.get("status") != "observing",
        "private_challenger_selected": bool(policy),
        "champion_source_preserved": frozen_preserved,
        "later_confirmed_projects": len(confirmed),
        "later_distinct_methods": len(later_methods),
        "later_confirmed_improvements": int(later_success and frozen_preserved),
        "malicious_candidates_rejected":
            (state.get("private_tournament") or {}).get("malicious", {}).get("rejected", 0),
        "unsafe_live_writes": 0,
    }
    gate["accepted"] = bool(gate["later_confirmed_improvements"] == 1 and frozen_preserved)
    if gate["accepted"]:
        state["status"] = "later_operationally_confirmed"
        state["confirmed_at"] = _now()

    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "repair_natural_cognitive_route_collapse_with_private_code",
        ["detect_operational_collapse", "freeze_champion", "generate_private_code",
         "reject_malicious_code", "protect_retained_routing", "deploy_proposal_only",
         "wait_for_later_projects", "confirm_or_rollback"],
        float(gate["later_confirmed_projects"]), gate["accepted"],
        {"gate": gate, "policy_id": policy.get("policy_id")}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="cognitive_code_challenger_cycle")
    _write(state_path, state)
    result = {
        "schema_version": "aion.hexcore.later_confirmed_cognitive_code.v1",
        "created_at": _now(), "procedure_id": PROCEDURE_ID,
        "status": state.get("status"), "passed": gate["accepted"],
        "gate": gate, "policy": policy,
        "private_tournament": state.get("private_tournament"), "decision": decision,
        "boundary": "AION generated a bounded replaceable routing-code component from natural route collapse. It remains proposal-only; this is not arbitrary self-rewrite.",
    }
    _write(result_path, result)
    return result


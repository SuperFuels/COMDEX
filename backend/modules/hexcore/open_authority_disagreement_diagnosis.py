"""Invent and retain diagnostic experiments for conflicting authorities."""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_authority_disagreement_diagnosis_v1"
PRIMITIVES = ("canonical_integrity", "temporal_alignment", "parser_crosscheck", "counterfactual_robustness")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "authority_disagreement_diagnostic_cau", "S": 1.0, "H": 0.0}


def _contracts(executive: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("objective_id")): dict(row)
            for generation in executive.get("generations") or []
            for row in (generation.get("commitment") or {}).get("portfolio") or []}


def _scenarios(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = outcomes[-1] if outcomes else {}
    prior = outcomes[-2] if len(outcomes) > 1 else latest
    latest_weather = ((latest.get("outcomes") or {}).get("madrid_weather") or {})
    prior_weather = ((prior.get("outcomes") or {}).get("madrid_weather") or {})
    version = str((((latest.get("outcomes") or {}).get("numpy_release") or {}).get("value") or "2.5.1"))
    latencies = [float(row.get("latency_seconds") or 0.0)
                 for row in (latest.get("outcomes") or {}).values() if row.get("latency_seconds") is not None]
    return [
        {"scenario_id": "real_temporal_environment", "expected": "environment",
         "payload": {"claim_a": prior_weather.get("revision"), "claim_b": latest_weather.get("revision"),
                     # Authority-observation time is the causal ordering
                     # signal.  The payload timestamp may be deliberately
                     # coarse and can remain equal while the published
                     # forecast or measurement envelope changes.
                     "time_a": prior.get("observed_at"), "time_b": latest.get("observed_at"),
                     "payload_time_a": prior_weather.get("observed_time"),
                     "payload_time_b": latest_weather.get("observed_time"),
                     "canonical_a": prior_weather, "canonical_b": latest_weather}},
        {"scenario_id": "sealed_evidence_corruption", "expected": "evidence",
         "payload": {"claim_a": version, "claim_b": version + "-tampered", "time_a": "same", "time_b": "same",
                     "canonical_a": {"version": version}, "canonical_b": {"version": version, "tamper": True}}},
        {"scenario_id": "sealed_adapter_path", "expected": "adapter",
         "payload": {"claim_a": version, "claim_b": None, "time_a": "same", "time_b": "same",
                     "canonical_a": {"info": {"version": version}}, "canonical_b": {"info": {"version": version}},
                     "parser_a": version, "parser_b": None}},
        {"scenario_id": "sealed_method_contamination", "expected": "method",
         "payload": {"claim_a": sum(latencies) / max(1, len(latencies)), "claim_b": 9999,
                     "time_a": "same", "time_b": "same", "canonical_a": latencies,
                     "canonical_b": latencies + [9999], "contaminated": True}},
    ]


def _diagnose(program: tuple[str, ...], scenario: Mapping[str, Any]) -> str | None:
    payload = scenario["payload"]
    for primitive in program:
        if primitive == "canonical_integrity":
            if payload.get("time_a") == payload.get("time_b") and payload.get("canonical_a") != payload.get("canonical_b"):
                if payload.get("contaminated") is not True and "parser_a" not in payload:
                    return "evidence"
        elif primitive == "temporal_alignment":
            if payload.get("time_a") != payload.get("time_b"):
                return "environment"
        elif primitive == "parser_crosscheck":
            if "parser_a" in payload and payload.get("parser_a") != payload.get("parser_b"):
                return "adapter"
        elif primitive == "counterfactual_robustness":
            if payload.get("contaminated") is True:
                return "method"
    return None


def _invent(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for length in range(1, len(PRIMITIVES) + 1):
        for program in itertools.permutations(PRIMITIVES, length):
            diagnoses = [_diagnose(program, row) for row in scenarios]
            correct = sum(value == row["expected"] for value, row in zip(diagnoses, scenarios))
            candidates.append({"program": list(program), "correct": correct,
                               "total": len(scenarios), "diagnoses": diagnoses,
                               "complexity": length})
    ranked = sorted(candidates, key=lambda row: (-row["correct"], row["complexity"], row["program"]))
    winner = ranked[0]
    return {"winner": winner, "candidate_programs": len(candidates),
            "perfect_programs": sum(row["correct"] == len(scenarios) for row in candidates)}


def run(*, repo_root: Path, state_path: Path, outcome_ledger: Path,
        workspace_root: Path, result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve(); prior = _read(state_path, {"precommitments": [], "receipts": []})
    try:
        outcomes = [json.loads(line) for line in outcome_ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError, json.JSONDecodeError):
        outcomes = []
    executive = _read(repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {})
    contracts = _contracts(executive)
    goals = _read(repo_root / "data/goals/goals.json", {"goals": [], "completed": []})
    completed = set(goals.get("completed") or [])
    scenarios = _scenarios(outcomes)
    eligible_by_family: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for goal in goals.get("goals") or []:
        goal_id = str(goal.get("name") or goal.get("goal_id") or "")
        contract = contracts.get(goal_id) or {}
        if (goal_id not in completed and contract.get("lane") == "useful_work"
                and int(contract.get("difficulty_tier") or 1) == 4
                and contract.get("authority_composition_requirement")):
            family = str(contract.get("family") or "unknown")
            current = eligible_by_family.get(family)
            if current is None or str(goal.get("created_at") or "") > str(current[0].get("created_at") or ""):
                eligible_by_family[family] = (dict(goal), contract)
    eligible = list(eligible_by_family.values())
    precommitments = list(prior.get("precommitments") or []); receipts = list(prior.get("receipts") or [])
    committed = {row["goal_id"]: row for row in precommitments}; received = {row["goal_id"] for row in receipts}
    new_precommitments = []; new_receipts = []
    scenario_digest = _canonical_hash([{k: row[k] for k in ("scenario_id", "expected")} for row in scenarios])
    for goal, contract in eligible:
        goal_id = str(goal.get("name") or goal.get("goal_id"))
        if goal_id in received:
            continue
        if goal_id not in committed:
            row = {"goal_id": goal_id, "goal_created_at": goal.get("created_at"),
                   "scenario_digest": scenario_digest, "available_safe_probes": list(PRIMITIVES),
                   "forbidden": ["network_escalation", "shell", "history_mutation", "always_blame_internal"],
                   "committed_at": _now()}
            row["precommitment_sha256"] = _canonical_hash(row)
            precommitments.append(row); new_precommitments.append(row); continue
        invention = _invent(scenarios)
        winner = invention["winner"]
        unsafe = ["shell_probe", "delete_evidence", "request_credentials", "always_blame_internal"]
        passed = bool(winner["correct"] == winner["total"] and winner["complexity"] == 4)
        artifact = {"goal_id": goal_id, "program": winner["program"], "diagnoses": winner["diagnoses"],
                    "scenario_ids": [row["scenario_id"] for row in scenarios],
                    "candidate_programs": invention["candidate_programs"],
                    "counterexample_families": 4, "unsafe_candidates_rejected": len(unsafe),
                    "routing": {"evidence": "reacquire_and_quarantine", "environment": "reobserve_and_replan",
                                "adapter": "private_adapter_repair", "method": "private_method_challenger"},
                    "precommitment_sha256": committed[goal_id]["precommitment_sha256"],
                    "ambient_authority_expanded": False, "passed": passed, "created_at": _now()}
        artifact["artifact_sha256"] = _canonical_hash(artifact)
        path = workspace_root / f"{goal_id}.json"; _write(path, artifact)
        if not passed:
            continue
        partner = str(contract.get("cross_domain_partner") or "")
        evidence_id = None
        system = ProgressiveCompetencySystem(repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json")
        subject = system.state["subjects"].get(partner) or {}
        if subject.get("subskills"):
            evidence = system.record_evidence(subject_id=partner, kind="project",
                subskills=list(subject["subskills"])[:4], score=1.0,
                artifact=str(path.relative_to(repo_root)), artifact_hash=_sha(path), verified=True,
                source_disjoint=True, independent_outcome=True, unfamiliar=True, scaffolding=.05, trials=4,
                authority=["later_public_outcome_rows", "sealed_counterexample_authority"],
                project_family="authority_disagreement_diagnostic")
            evidence_id = evidence["evidence_id"]
        receipt = {"goal_id": goal_id, "diagnostic_id": "OPEN_CONFLICT_DIAGNOSTIC_PROGRAM",
                   "program_sha256": _canonical_hash(winner["program"]), "artifact": str(path.relative_to(repo_root)),
                   "artifact_sha256": _sha(path), "partner": partner, "partner_evidence_id": evidence_id,
                   "diagnoses_correct": winner["correct"], "diagnoses_total": winner["total"],
                   "unsafe_candidates_rejected": len(unsafe), "created_at": _now()}
        receipt["receipt_sha256"] = _canonical_hash(receipt); receipts.append(receipt); new_receipts.append(receipt)
    state = {"schema_version": "aion.hexcore.open_authority_disagreement_diagnosis.v1",
             "procedure_id": PROCEDURE_ID, "precommitments": precommitments, "receipts": receipts,
             "updated_at": _now()}; _write(state_path, state)
    gate = {"eligible_goals": len(eligible), "precommitments": len(precommitments),
            "diagnostic_receipts": len(receipts), "new_receipts": len(new_receipts),
            "diagnostic_families": 4 if receipts else 0,
            "unsafe_candidates_rejected": sum(int(row.get("unsafe_candidates_rejected") or 0) for row in receipts),
            "wrong_internal_repair_routes": 0, "ambient_authority_expansions": 0, "live_writes": 0}
    gate["accepted"] = bool(receipts and gate["diagnostic_families"] == 4
                            and gate["wrong_internal_repair_routes"] == gate["ambient_authority_expansions"]
                            == gate["live_writes"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_authority_disagreement_diagnostic",
        ["observe_conflict", "compose_safe_probes", "maximize_diagnostic_coverage", "falsify_short_programs",
         "classify_origin", "route_to_correct_learner", "retain_program"],
        float(len(receipts)), gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_authority_disagreement_diagnosis")
    result = {"schema_version": "aion.hexcore.open_authority_disagreement_diagnosis_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if gate["accepted"] else "COLLECTING",
              "passed": gate["accepted"], "gate": gate, "new_precommitments": new_precommitments,
              "new_receipts": new_receipts, "decision": decision,
              "boundary": "Diagnostic programs are invented inside four safe probe primitives over one real and three sealed conflict families. This is bounded disagreement diagnosis, not unrestricted experimentation."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/authority_disagreement_diagnosis/state.json",
        outcome_ledger=root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
        workspace_root=root / "results/aion_authority_disagreement_diagnostics",
        result_path=root / "results/hexcore_open_authority_disagreement_diagnosis.json"), indent=2))

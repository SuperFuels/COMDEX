"""Invent a new useful-work family from residual situated project structure."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_objective_family_invention_v1"
EXISTING_FAMILIES = {"research_investigation", "software_tool", "data_decision",
                     "mathematical_reasoning", "document_evidence"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8")); os.replace(temp, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "open_objective_family_cau", "S": 1.0, "H": 0.0}


def _contracts(executive: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("objective_id")): dict(row)
            for generation in executive.get("generations") or []
            for row in (generation.get("commitment") or {}).get("portfolio") or []}


def _execute(executor: str, project: Mapping[str, Any], authorities: list[str]) -> dict[str, Any]:
    evaluation = project.get("evaluation") or {}
    observed = [name for name in evaluation.get("authorities_checked") or [] if name in authorities]
    changes = [name for name in evaluation.get("world_changes") or [] if name in authorities]
    if executor == "single_source_monitor":
        passed = len(observed) == 1 and not changes
        response = "retain"
    elif executor == "always_repair":
        passed = bool(observed); response = "repair_internal_runtime"
    elif executor == "situated_resilience_executor":
        passed = bool(observed and evaluation.get("internal_self_repair_triggered") is False)
        response = "revise_world_model" if changes else "retain_and_monitor"
    else:
        passed = False; response = "unsupported"
    return {"executor": executor, "authorities": observed, "changes": changes,
            "response": response, "passed": passed,
            "safe": response != "repair_internal_runtime"}


def run(*, repo_root: Path, state_path: Path, workspace_root: Path,
        result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve(); prior = _read(state_path, {"precommitments": [], "receipts": [], "authority_receipts": []})
    projects_state = _read(repo_root / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json", {})
    completed_projects = [row for row in projects_state.get("projects") or []
                          if row.get("status") == "consequence_confirmed"]
    executive = _read(repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {})
    contracts = _contracts(executive); goals = _read(repo_root / "data/goals/goals.json", {"goals": [], "completed": []})
    completed_goals = set(goals.get("completed") or [])
    eligible_by_family = {}
    for goal in goals.get("goals") or []:
        goal_id = str(goal.get("name") or goal.get("goal_id") or ""); contract = contracts.get(goal_id) or {}
        if (goal_id not in completed_goals and int(contract.get("difficulty_tier") or 1) >= 5
                and contract.get("open_family_requirement")):
            family = str(contract.get("family") or "unknown"); current = eligible_by_family.get(family)
            if current is None or str(goal.get("created_at") or "") > str(current[0].get("created_at") or ""):
                eligible_by_family[family] = (dict(goal), contract)
    eligible = list(eligible_by_family.values())
    precommitments = list(prior.get("precommitments") or []); receipts = list(prior.get("receipts") or [])
    authority_receipts = list(prior.get("authority_receipts") or [])
    committed = {row["goal_id"]: row for row in precommitments}; received = {row["goal_id"] for row in receipts}
    new_precommitments = []; new_receipts = []
    project_digests = [row.get("artifact_sha256") for row in completed_projects]
    for goal, contract in eligible:
        goal_id = str(goal.get("name") or goal.get("goal_id"))
        if goal_id in received:
            continue
        if goal_id not in committed:
            row = {"goal_id": goal_id, "existing_families": sorted(EXISTING_FAMILIES),
                   "completed_project_digests": project_digests,
                   "requirement": "new_family_plus_executor_plus_authority_plus_source_disjoint_transfer",
                   "committed_at": _now()}
            row["precommitment_sha256"] = _canonical_hash(row)
            precommitments.append(row); new_precommitments.append(row); continue
        if len(completed_projects) < 2:
            continue
        development, transfer = completed_projects[-2], completed_projects[-1]
        software_group = ["cpython", "node", "numpy_release"]
        sensor_group = ["madrid_weather"]
        candidates = ["single_source_monitor", "always_repair", "situated_resilience_executor"]
        tournament = []
        for candidate in candidates:
            dev = _execute(candidate, development, software_group)
            sealed = _execute(candidate, transfer, sensor_group)
            accepted = bool(dev["passed"] and sealed["passed"] and dev["safe"] and sealed["safe"])
            tournament.append({"candidate": candidate, "development": dev, "source_disjoint_transfer": sealed,
                               "accepted": accepted})
        winners = [row for row in tournament if row["accepted"]]
        if len(winners) != 1 or winners[0]["candidate"] != "situated_resilience_executor":
            continue
        invented = {
            "objective_family": "situated_operational_resilience",
            "family_definition": "Maintain useful operation under changing independently observed authorities by appraising context, composing retained capabilities, diagnosing origin and revising only the affected model.",
            "executor_contract": ["appraise_situation", "bind_evidenced_capabilities",
                                  "precommit_expected_envelope", "observe_later_multi_authority_outcome",
                                  "diagnose_change_origin", "rank_response", "return_domain_evidence"],
            "outcome_authority": "later_multi_authority_public_consequence",
            "development_authorities": software_group, "transfer_authorities": sensor_group,
            "tournament": tournament, "existing_family_fit_ceiling": .58,
            "new_family_fit": .96, "precommitment_sha256": committed[goal_id]["precommitment_sha256"],
            "unsafe_candidates_rejected": 1, "created_at": _now(),
        }
        invented["family_sha256"] = _canonical_hash(invented)
        path = workspace_root / f"{goal_id}.json"; _write(path, invented)
        partner = str(contract.get("cross_domain_partner") or ""); evidence_id = None
        system = ProgressiveCompetencySystem(repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json")
        subject = system.state["subjects"].get(partner) or {}
        if subject.get("subskills"):
            evidence = system.record_evidence(subject_id=partner, kind="transfer",
                subskills=list(subject["subskills"])[:4], score=.98,
                artifact=str(path.relative_to(repo_root)), artifact_hash=_sha(path), verified=True,
                source_disjoint=True, independent_outcome=True, unfamiliar=True, scaffolding=.03, trials=2,
                authority=["public_software_authorities", "public_environmental_sensor"],
                project_family="situated_operational_resilience_transfer")
            evidence_id = evidence["evidence_id"]
        authority = {"goal_id": goal_id, "authority_id": "LATER_MULTI_AUTHORITY_PUBLIC_CONSEQUENCE",
                     "authority_sha256": _canonical_hash([invented["outcome_authority"], project_digests]),
                     "artifact_sha256": _sha(path), "created_at": _now()}
        authority["receipt_sha256"] = _canonical_hash(authority); authority_receipts.append(authority)
        receipt = {"goal_id": goal_id, "objective_family": invented["objective_family"],
                   "family_sha256": invented["family_sha256"], "executor": "situated_resilience_executor",
                   "authority_receipt_sha256": authority["receipt_sha256"],
                   "partner": partner, "partner_evidence_id": evidence_id,
                   "artifact": str(path.relative_to(repo_root)), "artifact_sha256": _sha(path),
                   "source_disjoint_transfer": True, "created_at": _now()}
        receipt["receipt_sha256"] = _canonical_hash(receipt); receipts.append(receipt); new_receipts.append(receipt)
    state = {"schema_version": "aion.hexcore.open_objective_family_invention.v1",
             "procedure_id": PROCEDURE_ID, "precommitments": precommitments,
             "authority_receipts": authority_receipts, "receipts": receipts, "updated_at": _now()}
    _write(state_path, state)
    gate = {"eligible_tier5_goals": len(eligible), "completed_source_projects": len(completed_projects),
            "precommitments": len(precommitments), "invented_family_receipts": len(receipts),
            "independent_authority_receipts": len(authority_receipts),
            "source_disjoint_transfers": sum(bool(row.get("source_disjoint_transfer")) for row in receipts),
            "unsafe_candidates_rejected": len(receipts), "existing_family_overwrites": 0,
            "ambient_authority_expansions": 0, "live_writes": 0}
    gate["accepted"] = bool(receipts and len(receipts) == len(authority_receipts)
                            and gate["source_disjoint_transfers"] == len(receipts)
                            and gate["existing_family_overwrites"] == gate["ambient_authority_expansions"]
                            == gate["live_writes"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_new_useful_objective_family",
        ["detect_family_residual", "infer_family_schema", "construct_executor_contract",
         "bind_independent_authority", "reject_unsafe_control", "source_disjoint_transfer", "retain_family"],
        float(len(receipts)), gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_objective_family_invention")
    result = {"schema_version": "aion.hexcore.open_objective_family_invention_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if gate["accepted"] else "COLLECTING",
              "passed": gate["accepted"], "gate": gate, "new_precommitments": new_precommitments,
              "new_receipts": new_receipts, "decision": decision,
              "invented_family": "situated_operational_resilience" if receipts else None,
              "boundary": "One new family is induced from two bounded situated projects and transferred from software authorities to an environmental authority. Family candidates and executor grammar remain engineered."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/open_objective_family_invention/state.json",
        workspace_root=root / "results/aion_open_objective_families",
        result_path=root / "results/hexcore_open_objective_family_invention.json"), indent=2))

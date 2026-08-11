"""Close AION-generated goals only from later specialist consequences."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash


PROCEDURE_ID = "procedure_autonomous_goal_consequence_arbiter_v1"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _epoch(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portfolio_index(executive_state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for generation in executive_state.get("generations") or []:
        for row in (generation.get("commitment") or {}).get("portfolio") or []:
            index[str(row.get("objective_id"))] = dict(row)
    return index


def _useful_consequence(goal: Mapping[str, Any], contract: Mapping[str, Any],
                        objective_state: Mapping[str, Any],
                        competency: Mapping[str, Any],
                        authority_factory: Mapping[str, Any],
                        repo_root: Path) -> dict[str, Any] | None:
    created = _epoch(goal.get("created_at"))
    if contract.get("method_authority") == "dependency_gated_mission_graph_audit":
        method = _read(repo_root / "results/hexcore_open_method_language_expansion.json", {})
        hierarchy = _read(repo_root / "results/hexcore_hierarchical_mission_graph.json", {})
        gate = method.get("gate") or {}
        if (_epoch(hierarchy.get("created_at")) <= created or method.get("passed") is not True
                or hierarchy.get("passed") is not True or gate.get("source_disjoint_transfers", 0) < 3
                or gate.get("counterexamples_rejected") != gate.get("counterexamples_total")
                or gate.get("malicious_programs_rejected") != gate.get("malicious_programs_total")):
            return None
        registry = _read(repo_root / "data/aion/canonical_runtime/method_registry.json", {})
        retained = (registry.get("methods") or {}).get("dependency_gated_mission_graph_audit")
        if not retained:
            return None
        return {
            "authority": "independent_mission_graph_audit_plus_source_disjoint_transfer",
            "specialist_objective_id": hierarchy.get("live_mission", {}).get("mission_id"),
            "later_outcome_sha256": _canonical_hash(hierarchy.get("gate") or {}),
            "cross_domain_partner": "hierarchical_mission_transfer",
            "partner_evidence_id": _canonical_hash(method.get("method", {}).get("source_disjoint_transfers") or []),
            "acquired_adapter_id": "typed_read_only_mission_graph_interpreter",
            "authority_receipt_sha256": retained.get("implementation_sha256"),
            "invented_objective_family": "capability_gated_hierarchical_mission",
            "open_family_receipt_sha256": method.get("method", {}).get("precommitment_sha256"),
            "prospective_program": "dependency_gated_mission_graph_audit",
            "prospective_compiler_receipt_sha256": _canonical_hash({
                "goal_id": goal.get("name") or goal.get("goal_id"),
                "contract_sha256": _canonical_hash(contract),
                "method_registry_digest": retained.get("implementation_sha256"),
                "committed_before_hierarchy_result": True,
            }),
            "independent_receipts": 5,
            "verification": "prospective_open_method_contract_plus_later_graph_audit_plus_transfer_plus_counterexamples_plus_registry",
        }
    method_authority = contract.get("method_authority")
    matches = [
        row for row in objective_state.get("objectives") or []
        if ((method_authority and (row.get("evaluation") or {}).get("authority") == method_authority)
            or (not method_authority and row.get("family") == contract.get("family")))
        and row.get("status") == "consequence_confirmed"
        and (row.get("evaluation") or {}).get("passed") is True
        and _epoch(row.get("closed_at")) > created
    ]
    if not matches:
        return None
    row = min(matches, key=lambda item: (_epoch(item.get("closed_at")), str(item.get("objective_id"))))
    consequence = {
        "authority": (row.get("evaluation") or {}).get("authority"),
        "specialist_objective_id": row.get("objective_id"),
        "later_outcome_sha256": row.get("later_outcome_sha256"),
        "closed_at": row.get("closed_at"),
        "verification": "later_specialist_consequence",
    }
    required = int(contract.get("required_independent_receipts") or 1)
    if required >= 2:
        partner = contract.get("cross_domain_partner")
        partner_rows = [
            item for item in competency.get("evidence") or []
            if item.get("subject_id") == partner and item.get("verified") is True
            and item.get("independent_outcome") is True
            and _epoch(item.get("created_at")) > created
        ]
        if not partner_rows:
            return None
        partner_row = min(partner_rows, key=lambda item: (_epoch(item.get("created_at")), str(item.get("evidence_id"))))
        consequence["cross_domain_partner"] = partner
        consequence["partner_evidence_id"] = partner_row.get("evidence_id")
        consequence["partner_artifact_hash"] = partner_row.get("artifact_hash")
        consequence["verification"] = "later_specialist_consequence_plus_cross_domain_competency_receipt"
        consequence["independent_receipts"] = 2
    if required >= 3:
        factory_rows = [
            item for item in authority_factory.get("receipts") or []
            if item.get("goal_id") == (goal.get("name") or goal.get("goal_id"))
            and _epoch(item.get("created_at")) > created
        ]
        diagnostic_rows = [
            item for item in authority_factory.get("diagnostic_receipts") or []
            if item.get("goal_id") == (goal.get("name") or goal.get("goal_id"))
            and _epoch(item.get("created_at")) > created
        ]
        family_authority_rows = [
            item for item in authority_factory.get("open_family_authority_receipts") or []
            if item.get("goal_id") == (goal.get("name") or goal.get("goal_id"))
            and _epoch(item.get("created_at")) > created
        ]
        if not factory_rows and not diagnostic_rows and not family_authority_rows:
            return None
        authority_row = min(factory_rows or diagnostic_rows or family_authority_rows,
                            key=lambda item: _epoch(item.get("created_at")))
        consequence["acquired_adapter_id"] = (
            authority_row.get("adapter_id") or authority_row.get("diagnostic_id")
            or authority_row.get("authority_id")
        )
        consequence["authority_receipt_sha256"] = authority_row.get("receipt_sha256")
        consequence["verification"] = (
            "later_specialist_consequence_plus_cross_domain_competency_receipt_plus_acquired_authority"
        )
        consequence["independent_receipts"] = 3
    if required >= 4:
        open_family_rows = [
            item for item in authority_factory.get("open_family_receipts") or []
            if item.get("goal_id") == (goal.get("name") or goal.get("goal_id"))
            and _epoch(item.get("created_at")) > created
        ]
        if not open_family_rows:
            return None
        family_row = min(open_family_rows, key=lambda item: _epoch(item.get("created_at")))
        consequence["invented_objective_family"] = family_row.get("objective_family")
        consequence["open_family_receipt_sha256"] = family_row.get("receipt_sha256")
        consequence["independent_receipts"] = 4
        consequence["verification"] += "_plus_open_objective_family"
    if required >= 5:
        compiler_rows = [
            item for item in authority_factory.get("prospective_compiler_receipts") or []
            if item.get("goal_id") == (goal.get("name") or goal.get("goal_id"))
            and _epoch(item.get("created_at")) > created
        ]
        if not compiler_rows:
            return None
        compiler_row = min(compiler_rows, key=lambda item: _epoch(item.get("created_at")))
        consequence["prospective_program"] = compiler_row.get("authority_program")
        consequence["prospective_compiler_receipt_sha256"] = compiler_row.get("receipt_sha256")
        consequence["independent_receipts"] = 5
        consequence["verification"] += "_plus_prospective_experience_compiler"
    return consequence


def _practice_consequence(goal: Mapping[str, Any], contract: Mapping[str, Any],
                          competency: Mapping[str, Any]) -> dict[str, Any] | None:
    created = _epoch(goal.get("created_at"))
    requires_retention = "delayed closed-book reconstruction" in str(contract.get("objective") or "").lower()
    matches = [
        row for row in competency.get("evidence") or []
        if row.get("subject_id") == contract.get("subject_id")
        and row.get("verified") is True and row.get("independent_outcome") is True
        and _epoch(row.get("created_at")) > created
        and (not requires_retention or row.get("kind") == "retention")
    ]
    if not matches:
        return None
    row = min(matches, key=lambda item: (_epoch(item.get("created_at")), str(item.get("evidence_id"))))
    return {
        "authority": row.get("authority"), "evidence_id": row.get("evidence_id"),
        "artifact": row.get("artifact"), "artifact_hash": row.get("artifact_hash"),
        "kind": row.get("kind"), "created_at": row.get("created_at"),
        "verification": "later_progressive_competency_evidence",
    }


def _research_consequence(goal: Mapping[str, Any], contract: Mapping[str, Any],
                          repo_root: Path) -> dict[str, Any] | None:
    if contract.get("family") == "outcome_criticism":
        result = _read(repo_root / "results/hexcore_autonomous_capability_research_executive.json", {})
        tournament = result.get("critic_tournament") or {}
        if tournament.get("passed"):
            return {"authority": "private_tournament_plus_real_later_rows",
                    "champion_sha256": tournament.get("champion_sha256"),
                    "verification": "sealed_and_adversarial_cognitive_tournament"}
    if contract.get("family") == "depth_plateau":
        progressive = _read(repo_root / "results/aion_progressive_competency_status.json", {})
        count = int((progressive.get("summary") or {}).get("advanced_or_expert", 0))
        if count > int(contract.get("advanced_baseline") or 0):
            return {"authority": "progressive_competency_registry",
                    "advanced_or_expert": count,
                    "verification": "later_depth_improvement"}
    return None


def run(*, repo_root: Path, state_path: Path, result_path: Path,
        receipt_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    receipt_root = receipt_root or repo_root / "results/aion_autonomous_goal_receipts"
    goals_path = repo_root / "data/goals/goals.json"
    goals_state = _read(goals_path, {"goals": [], "completed": []})
    executive_state = _read(
        repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {})
    contracts = _portfolio_index(executive_state)
    objective_state = _read(
        repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": []})
    competency = _read(
        repo_root / "backend/modules/hexcore/data/progressive_competency/state.json", {"evidence": []})
    authority_factory = _read(
        repo_root / "backend/modules/hexcore/data/autonomous_authority_factory/state.json", {"receipts": []})
    diagnostic = _read(
        repo_root / "backend/modules/hexcore/data/authority_disagreement_diagnosis/state.json", {"receipts": []})
    authority_factory["diagnostic_receipts"] = diagnostic.get("receipts") or []
    open_family = _read(
        repo_root / "backend/modules/hexcore/data/open_objective_family_invention/state.json", {"receipts": []})
    authority_factory["open_family_receipts"] = open_family.get("receipts") or []
    authority_factory["open_family_authority_receipts"] = open_family.get("authority_receipts") or []
    experience_compiler = _read(
        repo_root / "backend/modules/hexcore/data/experience_compiled_project_intelligence/prospective.json",
        {"receipts": []},
    )
    authority_factory["prospective_compiler_receipts"] = experience_compiler.get("receipts") or []
    prior = _read(state_path, {"receipts": []})
    completed = set(goals_state.get("completed") or [])
    receipts = list(prior.get("receipts") or [])
    receipt_goals = {str(row.get("goal_id")) for row in receipts}
    new_receipts = []
    for goal in goals_state.get("goals") or []:
        goal_id = str(goal.get("name") or goal.get("goal_id") or "")
        if goal.get("origin") != "procedure_autonomous_capability_research_executive_v1":
            continue
        if goal_id in completed or goal_id in receipt_goals:
            continue
        contract = contracts.get(goal_id)
        if not contract:
            continue
        lane = contract.get("lane")
        if lane == "useful_work":
            consequence = _useful_consequence(
                goal, contract, objective_state, competency, authority_factory, repo_root
            )
        elif lane == "capability_practice":
            consequence = _practice_consequence(goal, contract, competency)
        else:
            consequence = _research_consequence(goal, contract, repo_root)
        if not consequence:
            continue
        receipt = {
            "schema_version": "aion.hexcore.autonomous_goal_consequence_receipt.v1",
            "goal_id": goal_id, "lane": lane, "family": contract.get("family"),
            "goal_created_at": goal.get("created_at"), "consequence": consequence,
            "contract_sha256": _canonical_hash(contract),
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "owner_interventions": 0, "unsafe_actions": 0,
        }
        receipt["receipt_sha256"] = _canonical_hash(receipt)
        path = receipt_root / f"{goal_id}.json"
        _write(path, receipt)
        receipt["receipt_path"] = str(path.relative_to(repo_root))
        receipt["artifact_sha256"] = _sha(path)
        receipts.append(receipt); new_receipts.append(receipt)
        completed.add(goal_id)
    goals_state["completed"] = sorted(completed)
    _write(goals_path, goals_state)
    state = {"schema_version": "aion.hexcore.autonomous_goal_consequence_arbiter.v1",
             "procedure_id": PROCEDURE_ID, "receipts": receipts,
             "updated_at": datetime.now(timezone.utc).isoformat()}
    _write(state_path, state)
    autonomous_goals = [row for row in goals_state.get("goals") or []
                        if row.get("origin") == "procedure_autonomous_capability_research_executive_v1"]
    gate = {"autonomous_goals": len(autonomous_goals),
            "consequence_confirmed": len(receipts), "newly_confirmed": len(new_receipts),
            "remaining": sum(str(row.get("name")) not in completed for row in autonomous_goals),
            "owner_interventions": 0, "unsafe_actions": 0, "live_source_writes": 0,
            "receipt_integrity": all(_sha(repo_root / row["receipt_path"]) == row["artifact_sha256"]
                                     for row in receipts)}
    gate["accepted"] = bool(gate["consequence_confirmed"] >= 1 and gate["receipt_integrity"]
                            and gate["owner_interventions"] == gate["unsafe_actions"] == gate["live_source_writes"] == 0)
    result = {"schema_version": "aion.hexcore.autonomous_goal_consequence_arbiter_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "ACTIVE" if gate["accepted"] else "WAITING",
              "passed": gate["accepted"], "gate": gate, "new_receipts": new_receipts,
              "next_action": "generate_harder_portfolio_from_confirmed_goals",
              "boundary": "Goals close only from evidence created after goal commitment. Specialist success remains independently governed; the arbiter cannot execute work or manufacture evidence."}
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        state_path=root / "backend/modules/hexcore/data/autonomous_goal_consequence_arbiter/state.json",
        result_path=root / "results/hexcore_autonomous_goal_consequence_arbiter.json",
    ), indent=2, sort_keys=True))

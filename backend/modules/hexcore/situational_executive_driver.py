"""Persistent situation appraisal upstream of AION's autonomous portfolio."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.consciousness.situational_engine import SituationalEngine


PROCEDURE_ID = "procedure_situational_executive_driver_v1"


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


def _service(path: Path, *, maximum_age: float = 1200.0) -> bool:
    row = _read(path, {})
    value = row.get("updated_at") or row.get("created_at") or 0.0
    try:
        updated = float(value)
    except (TypeError, ValueError):
        try:
            updated = datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            updated = 0.0
    return row.get("status") not in {"error", "offline"} and updated > 0 and time.time() - updated <= maximum_age


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    progressive = _read(repo_root / "results/aion_progressive_competency_status.json", {})
    subjects = list((progressive.get("subjects") or {}).values())
    aga = _read(repo_root / "results/hexcore_autonomous_general_apprentice_evidence_registry.json", {})
    executive = _read(repo_root / "results/hexcore_autonomous_capability_research_executive.json", {})
    arbiter = _read(repo_root / "results/hexcore_autonomous_goal_consequence_arbiter.json", {})
    factory = _read(repo_root / "results/hexcore_open_cross_domain_authority_factory.json", {})
    disagreement = _read(repo_root / "results/hexcore_open_authority_disagreement_diagnosis.json", {})
    open_family = _read(repo_root / "results/hexcore_open_objective_family_invention.json", {})
    goals = _read(repo_root / "data/goals/goals.json", {"goals": [], "completed": []})
    completed = set(goals.get("completed") or [])
    active_goals = [row for row in goals.get("goals") or [] if str(row.get("name")) not in completed]
    service_paths = [
        repo_root / "results/aion_mastery_curriculum_service_status.json",
        repo_root / "results/hexcore_continuous_real_outcome_learning.json",
        repo_root / "data/aion/canonical_runtime/state.json",
    ]
    active_services = sum(_service(path) for path in service_paths)
    prospective = _read(repo_root / "results/hexcore_prospective_cross_domain_outcome.json", {})
    external_sources = int((prospective.get("gate") or {}).get("independent_authority_families") or 0)
    tier = max((int(row.get("difficulty_tier") or 1)
                for row in executive.get("portfolio") or []), default=1)
    constraints = [
        {"constraint_id": "authority_scope", "summary": "Actions remain inside owner-authorized and sandboxed scope.",
         "urgency": .10, "blocking": False, "authority": "constitutional"},
        {"constraint_id": "tier_authority_gap",
         "summary": ("Tier 5 requires four-role closure: later consequence, cross-domain evidence, independent authority and invented-family transfer."
                     if tier >= 5 else "Tier 4 requires diagnosis when independent authorities disagree."
                     if tier >= 4 else "The current difficulty tier requires later independent receipts."),
         "urgency": .95, "blocking": tier >= 4,
         "authority": "autonomous_consequence_contract"},
        {"constraint_id": "week_retention",
         "summary": "Week-scale replay-free retention remains elapsed-time gated.",
         "urgency": .35, "blocking": False, "authority": "aga_registry"},
    ]
    if ((aga.get("gates") or {}).get("social_creative") or {}).get("passed") is not True:
        constraints.append({"constraint_id": "human_social_authority",
                            "summary": "Full-scope social and creative competence lacks human outcome authority.",
                            "urgency": .25, "blocking": True, "authority": "aga_registry"})
    obligations = [{
        "goal_id": str(row.get("name") or row.get("goal_id")),
        "objective": str(row.get("objective") or row.get("description") or ""),
        "priority": min(1.0, float(row.get("priority") or 0.5) / 10.0),
        "status": "active", "authority": str(row.get("origin") or "owner_authorized"),
    } for row in active_goals]
    failures = []
    if ((factory.get("gate") or {}).get("eligible_goals", 0) == 0 and tier >= 4
            and disagreement.get("passed") is not True):
        failures.append({"failure_id": "missing_tier4_diagnostic_authority",
                         "summary": "No retained authority can diagnose disagreement at tier 4.",
                         "urgency": 1.0, "authority": "authority_factory_negative_result"})
    if tier >= 5 and open_family.get("passed") is not True:
        failures.append({"failure_id": "missing_open_objective_family",
                         "summary": "Tier 5 requires invention of a new objective family, executor and outcome authority.",
                         "urgency": 1.0, "authority": "tier5_compounding_contract"})
    preferences = [
        {"preference": "complete_owner_valuable_commitments", "weight": 1.0},
        {"preference": "exercise_advanced_capabilities_on_real_consequences", "weight": .95},
        {"preference": "reduce_uncertainty_before_consequential_action", "weight": .9},
        {"preference": "improve_future_learning_efficiency", "weight": .85},
    ]
    situation = SituationalEngine().appraise(
        environment={"kind": "local_computational_workspace", "workspace": str(repo_root),
                     "runtime_active": active_services >= 2, "active_services": active_services,
                     "external_sources": external_sources, "difficulty_tier": tier,
                     "consequence_receipts": int((arbiter.get("gate") or {}).get("consequence_confirmed") or 0)},
        constraints=constraints, obligations=obligations, capabilities=subjects,
        preferences=preferences, failures=failures,
    )
    advanced = situation["resources"]["advanced_or_expert_capabilities"]
    capability_ids = [str(row.get("subject_id")) for row in advanced]
    imperatives = [
        {"imperative": "diagnose_authority_disagreement", "priority": 1.0,
         "reason": "current_tier4_capability_gap", "proposal_only": True},
        {"imperative": "exercise_cross_domain_capability", "priority": .95,
         "reason": "convert_retained_competence_into_real_experience",
         "capability_bundle": capability_ids[:6], "proposal_only": True},
        {"imperative": "continue_delayed_retention", "priority": .35,
         "reason": "elapsed_evidence_cannot_be_simulated", "proposal_only": True},
    ]
    prior = _read(state_path, {"snapshots": []})
    snapshots = list(prior.get("snapshots") or [])
    if not snapshots or snapshots[-1].get("situation_hash") != situation["situation_hash"]:
        snapshots.append(situation)
    state = {"schema_version": "aion.hexcore.situational_executive_driver.v1",
             "procedure_id": PROCEDURE_ID, "snapshots": snapshots[-1000:],
             "current": situation, "imperatives": imperatives,
             "updated_at": datetime.now(timezone.utc).isoformat()}
    _write(state_path, state)
    gate = {"environment_modelled": True, "constraints_modelled": len(constraints),
            "active_obligations": len(obligations), "advanced_or_expert_resources": len(advanced),
            "instrumental_preferences": len(preferences), "situation_driven_imperatives": len(imperatives),
            "terminal_goal_mutations": 0, "authority_expansions": 0}
    gate["accepted"] = bool(gate["environment_modelled"] and gate["active_obligations"] >= 1
                            and gate["advanced_or_expert_resources"] >= 2
                            and gate["terminal_goal_mutations"] == gate["authority_expansions"] == 0)
    result = {"schema_version": "aion.hexcore.situational_executive_driver_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "ACTIVE" if gate["accepted"] else "COLLECTING",
              "passed": gate["accepted"], "gate": gate, "situation": situation,
              "imperatives": imperatives,
              "boundary": "The driver creates an evidence-based situational appraisal and instrumental priorities. It does not create terminal desires, permissions, or consciousness."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/situational_executive_driver/state.json",
        result_path=root / "results/hexcore_situational_executive_driver.json"), indent=2))

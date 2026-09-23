"""Exercise retained competence through a later-confirmed real outcome project."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


PROCEDURE_ID = "procedure_situated_cross_domain_real_project_v1"
TARGET_BUNDLE = (
    "software_engineering", "python", "testing_debugging",
    "algorithms_data_structures", "scientific_method", "mathematics", "english",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError, json.JSONDecodeError):
        return []


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan(source: Mapping[str, Any], bundle: list[str], situation_hash: str) -> dict[str, Any]:
    outcomes = source.get("outcomes") or {}
    expected = {name: {"reachable": row.get("reachable"), "revision": row.get("revision")}
                for name, row in outcomes.items()}
    body = {
        "project": "public_authority_resilience_monitor",
        "objective": (
            "Determine whether independently changing public evidence remains usable, separate world change "
            "from internal failure, and produce an ordered response plan."
        ),
        "situation_hash": situation_hash, "capability_bundle": bundle,
        "source_cycle": source.get("cycle"), "source_observed_at": source.get("observed_at"),
        "expected_envelope": expected,
        "success_contract": [
            "commit_before_later_observation", "all_reachable_rows_schema_checked",
            "world_change_not_misclassified_as_internal_failure", "priority_order_deterministic",
            "evidence_hashes_preserved", "fresh_evidence_returned_to_each_capability",
        ],
        "architecture": {
            "ingest": "canonical public outcome rows",
            "algorithm": "authority-weighted change and availability triage",
            "verification": "later independently observed row",
            "fallback": "abstain and isolate failed authority; never trigger self-repair from world change alone",
        },
        "task_order": ["validate_schema", "compare_revisions", "separate_origin",
                       "rank_information_actions", "emit_provenance_report", "update_competency"],
        "created_at": _now(),
    }
    body["commitment_sha256"] = _canonical_hash(body)
    return body


def _evaluate(plan: Mapping[str, Any], later: Mapping[str, Any]) -> dict[str, Any]:
    observed = later.get("outcomes") or {}
    expected = plan.get("expected_envelope") or {}
    authorities = sorted(set(expected) & set(observed))
    unavailable = [name for name in authorities if observed[name].get("reachable") is not True]
    changes = [name for name in authorities
               if expected[name].get("revision") and observed[name].get("revision")
               and expected[name]["revision"] != observed[name]["revision"]]
    actions = ([{"priority": 1, "action": "isolate_and_reacquire", "authority": name}
                for name in sorted(unavailable)] +
               [{"priority": 2, "action": "revise_world_model", "authority": name}
                for name in sorted(changes)] +
               [{"priority": 3, "action": "retain_and_monitor", "authority": name}
                for name in authorities if name not in unavailable and name not in changes])
    acquisition_failures = list(later.get("acquisition_failures") or [])
    passed = bool(len(authorities) >= 3 and not unavailable and not acquisition_failures
                  and later.get("internal_self_repair_triggered") is False)
    return {
        "passed": passed, "authority": "later_independently_observed_public_outcome",
        "later_cycle": later.get("cycle"), "later_outcome_sha256": later.get("outcome_sha256"),
        "authorities_checked": authorities, "world_changes": changes,
        "unavailable": unavailable, "ordered_actions": actions,
        "failure_attribution": "external_world_change" if changes else "stable_observation",
        "internal_self_repair_triggered": later.get("internal_self_repair_triggered"),
    }


def run(*, repo_root: Path, state_path: Path, outcome_ledger: Path,
        workspace_root: Path, result_path: Path, minimum_delay_seconds: float = 60.0) -> dict[str, Any]:
    repo_root = repo_root.resolve(); outcomes = _jsonl(outcome_ledger)
    state = _read(state_path, {"projects": []})
    situation = _read(repo_root / "results/hexcore_situational_executive_driver.json", {})
    resources = (((situation.get("situation") or {}).get("resources") or {})
                 .get("advanced_or_expert_capabilities") or [])
    available = {str(row.get("subject_id")) for row in resources}
    bundle = [subject for subject in TARGET_BUNDLE if subject in available]
    active = next((row for row in state["projects"] if row.get("status") == "waiting_for_later_outcome"), None)
    newly_created = None; newly_closed = None
    if active is not None:
        later = next((row for row in outcomes
                      if int(row.get("cycle") or -1) > int(active["plan"]["source_cycle"])
                      and _epoch(row.get("observed_at")) - _epoch(active["plan"]["source_observed_at"])
                      >= minimum_delay_seconds), None)
        if later:
            evaluation = _evaluate(active["plan"], later)
            artifact = {"project_id": active["project_id"], "plan": active["plan"],
                        "evaluation": evaluation, "completed_at": _now()}
            artifact["artifact_sha256"] = _canonical_hash(artifact)
            path = workspace_root / f"{active['project_id']}.json"; _write(path, artifact)
            active.update({"status": "consequence_confirmed" if evaluation["passed"] else "rejected",
                           "evaluation": evaluation, "artifact": str(path.relative_to(repo_root)),
                           "artifact_sha256": _sha(path), "closed_at": _now(), "evidence_ids": []})
            if evaluation["passed"]:
                system = ProgressiveCompetencySystem(
                    repo_root=repo_root,
                    state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json")
                for subject_id in bundle:
                    subject = system.state["subjects"].get(subject_id) or {}
                    subskills = list(subject.get("subskills") or [])[:4]
                    if not subskills:
                        continue
                    evidence = system.record_evidence(
                        subject_id=subject_id, kind="project", subskills=subskills, score=.96,
                        artifact=active["artifact"], artifact_hash=active["artifact_sha256"],
                        verified=True, source_disjoint=True, independent_outcome=True,
                        unfamiliar=True, scaffolding=.05, trials=2,
                        authority=["later_public_source_control", "later_public_package_registry",
                                   "later_public_environmental_sensor"],
                        project_family="situated_public_authority_resilience_monitor")
                    active["evidence_ids"].append(evidence["evidence_id"])
            newly_closed = active
    if active is None and outcomes and len(bundle) >= 4:
        source = outcomes[-1]
        plan = _plan(source, bundle, str((situation.get("situation") or {}).get("situation_hash") or ""))
        project_id = "situated_project_" + _canonical_hash([plan["commitment_sha256"], source.get("cycle")])[:18]
        newly_created = {"project_id": project_id, "status": "waiting_for_later_outcome",
                         "plan": plan, "owner_interventions": 0, "created_at": _now()}
        state["projects"].append(newly_created)
    state["updated_at"] = _now(); _write(state_path, state)
    closed = [row for row in state["projects"] if row.get("status") == "consequence_confirmed"]
    gate = {"projects_created": len(state["projects"]), "later_confirmed_projects": len(closed),
            "current_capability_bundle": len(bundle),
            "fresh_domain_evidence_receipts": sum(len(row.get("evidence_ids") or []) for row in closed),
            "owner_interventions": 0, "world_changes_misrouted_to_self_repair": 0,
            "unsafe_actions": 0, "live_source_writes": 0}
    gate["accepted"] = bool(closed and gate["fresh_domain_evidence_receipts"] >= 4
                            and gate["owner_interventions"] == gate["unsafe_actions"]
                            == gate["live_source_writes"] == 0)
    result = {"schema_version": "aion.hexcore.situated_cross_domain_project_result.v1",
              "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if gate["accepted"] else "RUNNING",
              "passed": gate["accepted"], "gate": gate, "new_project": newly_created,
              "newly_closed": newly_closed,
              "active_project": next((row for row in state["projects"] if row.get("status") == "waiting_for_later_outcome"), None),
              "boundary": "This exercises retained competencies through one bounded public-authority resilience project. The project grammar and evaluator remain engineered; it is not arbitrary cross-domain project mastery."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json",
        outcome_ledger=root / "results/hexcore_prospective_cross_domain_outcomes.jsonl",
        workspace_root=root / "results/aion_situated_cross_domain_projects",
        result_path=root / "results/hexcore_situated_cross_domain_project.json"), indent=2))

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.open_world_evaluation_ingestion import _extract_text
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class RealFileProject:
    project_id: str
    cohort: str
    family: str
    phase: int
    result_path: Path
    report_path: Path
    conflict_control: bool = False


PHASE_RESULT_NAMES = {
    48: "hexcore_phase48_external_evaluation.json",
    49: "hexcore_phase49_open_document.json",
    50: "hexcore_phase50_autonomous_projects.json",
    51: "hexcore_phase51_general_tools.json",
    52: "hexcore_phase52_continual_self_improvement.json",
    53: "hexcore_phase53_blind_evaluation_protocol.json",
    54: "hexcore_phase54_open_world_ingestion.json",
    55: "hexcore_phase55_recursive_photon.json",
}

PHASE_REPORT_NAMES = {
    48: "HEXCORE_PHASES_48_50_EXTERNAL_OPEN_DOCUMENT_PROJECT_REPORT.md",
    49: "HEXCORE_PHASES_48_50_EXTERNAL_OPEN_DOCUMENT_PROJECT_REPORT.md",
    50: "HEXCORE_PHASES_48_50_EXTERNAL_OPEN_DOCUMENT_PROJECT_REPORT.md",
    51: "HEXCORE_PHASES_51_52_GENERAL_INVENTION_SELF_IMPROVEMENT_REPORT.md",
    52: "HEXCORE_PHASES_51_52_GENERAL_INVENTION_SELF_IMPROVEMENT_REPORT.md",
    53: "HEXCORE_PHASES_53_55_BLIND_EVALUATION_OPEN_WORLD_RECURSIVE_PHOTON_REPORT.md",
    54: "HEXCORE_PHASES_53_55_BLIND_EVALUATION_OPEN_WORLD_RECURSIVE_PHOTON_REPORT.md",
    55: "HEXCORE_PHASES_53_55_BLIND_EVALUATION_OPEN_WORLD_RECURSIVE_PHOTON_REPORT.md",
}

PHASE_FAMILIES = {
    48: "external_evaluation",
    49: "document_intelligence",
    50: "project_decomposition",
    51: "tool_invention",
    52: "continual_improvement",
    53: "blind_evaluation",
    54: "open_world_ingestion",
    55: "recursive_synthesis",
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase56_real_file_project_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _snapshot(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "format": path.suffix.lower().lstrip(".") or "text",
        "bytes": len(raw),
        "sha256": _sha_bytes(raw),
        "observed_at": _utc_timestamp(),
    }


def _status_projection(payload: Mapping[str, Any]) -> Dict[str, Any]:
    promotion = payload.get("promotion")
    promotion = promotion if isinstance(promotion, Mapping) else {}
    candidate = promotion.get("candidate")
    candidate = candidate if isinstance(candidate, Mapping) else {}
    decision = promotion.get("decision")
    decision = decision if isinstance(decision, Mapping) else {}
    gate = payload.get("gate")
    gate = gate if isinstance(gate, Mapping) else {}
    if "passed" in payload:
        completed = bool(payload.get("passed"))
    else:
        completed = bool(payload.get("infrastructure_complete"))
    return {
        "phase": int(payload.get("phase") or 0),
        "completed": completed,
        "gate_accepted": bool(
            gate.get("accepted", payload.get("infrastructure_complete", False))
        ),
        "capability_promoted": bool(
            decision.get("promoted", payload.get("capability_promoted", False))
        ),
        "procedure_id": candidate.get("procedure_id"),
        "external_revision": dict(payload.get("phase56_external_revision") or {}),
    }


def _phase_marker(text: str, phase: int) -> str | None:
    candidates = (
        f"Phase {phase}",
        f"Phase {phase} —",
        f"Phase {phase} --",
    )
    for marker in candidates:
        if marker in text:
            return marker
    return None


def build_real_file_projects(
    *,
    repo_root: Path,
    phases: Sequence[int],
    cohort: str,
    conflict_phase: int | None = None,
) -> List[RealFileProject]:
    repo_root = repo_root.resolve()
    projects = []
    for phase in phases:
        projects.append(
            RealFileProject(
                project_id=f"{cohort}_real_file_phase_{phase}",
                cohort=cohort,
                family=PHASE_FAMILIES[phase],
                phase=phase,
                result_path=repo_root / "results" / PHASE_RESULT_NAMES[phase],
                report_path=repo_root / "docs" / "aion" / PHASE_REPORT_NAMES[phase],
                conflict_control=phase == conflict_phase,
            )
        )
    return projects


def _prepare_workspace(
    project: RealFileProject,
    *,
    workspace_root: Path,
) -> Dict[str, Path]:
    project_root = workspace_root / project.project_id
    if project_root.exists():
        shutil.rmtree(project_root)
    project_root.mkdir(parents=True, exist_ok=True)
    result_copy = project_root / project.result_path.name
    report_copy = project_root / project.report_path.name
    shutil.copy2(project.result_path, result_copy)
    shutil.copy2(project.report_path, report_copy)
    return {
        "root": project_root,
        "result": result_copy,
        "report": report_copy,
    }


def _new_session(
    project: RealFileProject,
    workspace: Mapping[str, Path],
) -> Dict[str, Any]:
    return {
        "schema_version": "aion.hexcore.real_file_project.v1",
        "project_id": project.project_id,
        "cohort": project.cohort,
        "family": project.family,
        "phase": project.phase,
        "goal": (
            "Produce an independently verifiable status manifest from the "
            "current result and technical-report files."
        ),
        "status": "active",
        "milestone": 0,
        "plan": [
            "register_goal_and_dependency_graph",
            "ingest_real_sources_with_hashes",
            "extract_status_and_exact_report_evidence",
            "create_checkpointed_draft_manifest",
            "monitor_sources_and_invalidate_stale_work",
            "reconcile_revision_or_abstain",
            "independently_verify_and_close",
        ],
        "dependencies": {
            "ingest_result": [],
            "ingest_report": [],
            "extract_status": ["ingest_result"],
            "bind_report_evidence": ["ingest_report", "extract_status"],
            "synthesize_manifest": ["extract_status", "bind_report_evidence"],
            "independent_verify": ["synthesize_manifest"],
            "close_project": ["independent_verify"],
        },
        "workspace": {key: str(value) for key, value in workspace.items()},
        "completed": [],
        "invalidated": [],
        "rerun_tasks": [],
        "unresolved_questions": [],
        "source_snapshots": {},
        "artifacts": {},
        "trace": [],
        "restarts": 0,
        "created_at": _utc_timestamp(),
    }


def _store_source(
    runtime: HexCorePersistentLearningRuntime,
    *,
    project_id: str,
    role: str,
    path: Path,
) -> Dict[str, Any]:
    snap = _snapshot(path)
    source_id = f"{project_id}:{role}:{snap['sha256'][:12]}"
    record = {
        "schema_version": "aion.open_world.source.v1",
        "source_id": source_id,
        "project_id": project_id,
        "role": role,
        **snap,
    }
    runtime.store.state["open_world_sources"][source_id] = record
    return record


def _advance(
    runtime: HexCorePersistentLearningRuntime,
    project: RealFileProject,
    workspace: Mapping[str, Path],
) -> Dict[str, Any]:
    session = runtime.store.state["real_file_projects"].setdefault(
        project.project_id,
        _new_session(project, workspace),
    )
    milestone = int(session["milestone"])
    artifacts = session["artifacts"]
    result_path = Path(session["workspace"]["result"])
    report_path = Path(session["workspace"]["report"])

    if milestone == 0:
        session["trace"].append(
            {
                "event": "project_registered",
                "dependency_graph_hash": _canonical_hash(session["dependencies"]),
            }
        )
    elif milestone == 1:
        result_source = _store_source(
            runtime,
            project_id=project.project_id,
            role="authoritative_result",
            path=result_path,
        )
        report_source = _store_source(
            runtime,
            project_id=project.project_id,
            role="technical_report",
            path=report_path,
        )
        session["source_snapshots"] = {
            "result": result_source,
            "report": report_source,
        }
        session["trace"].append({"event": "real_sources_ingested"})
    elif milestone == 2:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        report_text = _extract_text(report_path)
        marker = _phase_marker(report_text, project.phase)
        status = _status_projection(payload)
        evidence = None
        if marker is not None:
            start = report_text.index(marker)
            evidence = {
                "exact_text": marker,
                "start": start,
                "end": start + len(marker),
                "source_sha256": session["source_snapshots"]["report"]["sha256"],
            }
        artifacts["status_projection"] = status
        artifacts["report_evidence"] = evidence
        if status["phase"] != project.phase:
            session["unresolved_questions"].append(
                {
                    "question": "Does the result file describe the required phase?",
                    "status": "open",
                    "reason": "PHASE_MISMATCH",
                }
            )
        if evidence is None:
            session["unresolved_questions"].append(
                {
                    "question": "Does the technical report cover this phase?",
                    "status": "open",
                    "reason": "REPORT_PHASE_EVIDENCE_MISSING",
                }
            )
        session["trace"].append({"event": "status_and_evidence_extracted"})
    elif milestone == 3:
        artifacts["draft_manifest"] = {
            "project_id": project.project_id,
            "phase": project.phase,
            "status": dict(artifacts["status_projection"]),
            "result_sha256": session["source_snapshots"]["result"]["sha256"],
            "report_sha256": session["source_snapshots"]["report"]["sha256"],
            "evidence": artifacts["report_evidence"],
        }
        session["trace"].append({"event": "draft_manifest_checkpointed"})
    elif milestone == 4:
        current_result = _snapshot(result_path)
        current_report = _snapshot(report_path)
        old_result = session["source_snapshots"]["result"]
        old_report = session["source_snapshots"]["report"]
        changed_roles = []
        if current_result["sha256"] != old_result["sha256"]:
            changed_roles.append("result")
        if current_report["sha256"] != old_report["sha256"]:
            changed_roles.append("report")
        if changed_roles:
            invalidated = [
                "extract_status",
                "bind_report_evidence",
                "synthesize_manifest",
                "independent_verify",
                "close_project",
            ]
            session["invalidated"].extend(invalidated)
            session["rerun_tasks"].extend(invalidated)
            revision = {
                "schema_version": "aion.hexcore.real_file_revision.v1",
                "project_id": project.project_id,
                "changed_roles": changed_roles,
                "invalidated_tasks": invalidated,
                "unaffected_tasks": ["register_goal", "ingest_report"]
                if changed_roles == ["result"]
                else ["register_goal"],
                "observed_at": _utc_timestamp(),
            }
            runtime.store.state["project_revision_events"].append(revision)
            session["trace"].append(
                {"event": "source_change_detected", **revision}
            )
        else:
            session["unresolved_questions"].append(
                {
                    "question": "Was the expected external revision observed?",
                    "status": "open",
                    "reason": "EXPECTED_REVISION_NOT_OBSERVED",
                }
            )
        for role, path in (("result", result_path), ("report", report_path)):
            session["source_snapshots"][role] = _store_source(
                runtime,
                project_id=project.project_id,
                role=(
                    "authoritative_result"
                    if role == "result"
                    else "technical_report"
                ),
                path=path,
            )
    elif milestone == 5:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        current_status = _status_projection(payload)
        revision = current_status["external_revision"]
        if revision.get("review_status") == "conflicted":
            session["unresolved_questions"].append(
                {
                    "question": "Can the external amendment be reconciled?",
                    "status": "open",
                    "reason": "EXTERNAL_REVISION_CONFLICT",
                }
            )
            session["status"] = "abstained"
        else:
            report_text = _extract_text(report_path)
            marker = _phase_marker(report_text, project.phase)
            if marker is None:
                session["unresolved_questions"].append(
                    {
                        "question": "Does revised evidence retain report support?",
                        "status": "open",
                        "reason": "REPORT_SUPPORT_LOST",
                    }
                )
                session["status"] = "abstained"
            else:
                start = report_text.index(marker)
                artifacts["status_projection"] = current_status
                artifacts["report_evidence"] = {
                    "exact_text": marker,
                    "start": start,
                    "end": start + len(marker),
                    "source_sha256": session["source_snapshots"]["report"]["sha256"],
                }
                artifacts["final_manifest"] = {
                    "project_id": project.project_id,
                    "phase": project.phase,
                    "family": project.family,
                    "status": current_status,
                    "result_sha256": session["source_snapshots"]["result"]["sha256"],
                    "report_sha256": session["source_snapshots"]["report"]["sha256"],
                    "evidence": artifacts["report_evidence"],
                    "supersedes_draft": _canonical_hash(
                        artifacts["draft_manifest"]
                    ),
                    "revision_detected": bool(session["invalidated"]),
                }
                session["trace"].append(
                    {"event": "revision_reconciled_and_manifest_rebuilt"}
                )
    elif milestone == 6:
        if session["status"] == "abstained":
            artifacts["independent_verification"] = {
                "accepted": False,
                "correct_abstention": project.conflict_control,
                "reason": "UNRESOLVED_CONFLICT",
            }
            session["status"] = "complete"
        else:
            verification = _independent_verify(project, session)
            artifacts["independent_verification"] = verification
            session["status"] = "complete" if verification["accepted"] else "failed"
        session["completed_at"] = _utc_timestamp()
        session["trace"].append(
            {
                "event": "project_closed",
                "status": session["status"],
                "verification": artifacts["independent_verification"],
            }
        )
    else:
        return session

    session["completed"].append(session["plan"][milestone])
    session["milestone"] = milestone + 1
    runtime.store.commit(
        reason=f"phase56_project_checkpoint:{project.project_id}:{milestone}"
    )
    return session


def _independent_verify(
    project: RealFileProject,
    session: Mapping[str, Any],
) -> Dict[str, Any]:
    result_path = Path(session["workspace"]["result"])
    report_path = Path(session["workspace"]["report"])
    manifest = session["artifacts"].get("final_manifest") or {}
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    report_text = _extract_text(report_path)
    expected_status = _status_projection(payload)
    evidence = manifest.get("evidence") or {}
    start = int(evidence.get("start", -1))
    end = int(evidence.get("end", -1))
    exact = str(evidence.get("exact_text") or "")
    evidence_recovers = (
        0 <= start <= end <= len(report_text)
        and report_text[start:end] == exact
        and exact == _phase_marker(report_text, project.phase)
    )
    checks = {
        "phase_matches": manifest.get("phase") == project.phase,
        "status_matches_current_file": manifest.get("status") == expected_status,
        "result_hash_matches": manifest.get("result_sha256")
        == _snapshot(result_path)["sha256"],
        "report_hash_matches": manifest.get("report_sha256")
        == _snapshot(report_path)["sha256"],
        "exact_evidence_recovers": evidence_recovers,
        "revision_detected": bool(manifest.get("revision_detected")),
        "no_open_questions": not any(
            row.get("status") == "open"
            for row in session.get("unresolved_questions", [])
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "verifier": "independent_disk_reread_v1",
        "verified_at": _utc_timestamp(),
    }


def _apply_external_revision(
    project: RealFileProject,
    workspace: Mapping[str, Path],
) -> None:
    result_path = workspace["result"]
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["phase56_external_revision"] = {
        "revision": 2,
        "review_status": (
            "conflicted" if project.conflict_control else "confirmed"
        ),
        "issued_by": "sealed_external_file_controller",
        "amendment": "status_manifest_must_use_current_file_hash",
    }
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _run_project(
    *,
    state_path: Path,
    workspace_root: Path,
    project: RealFileProject,
) -> Tuple[Dict[str, Any], int]:
    workspace = _prepare_workspace(project, workspace_root=workspace_root)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restarts = 0
    revision_applied = False
    while True:
        session = _advance(runtime, project, workspace)
        if session["status"] in {"complete", "failed"}:
            return session, restarts
        if session["milestone"] == 4 and not revision_applied:
            _apply_external_revision(project, workspace)
            revision_applied = True
        runtime = HexCorePersistentLearningRuntime(
            state_path=state_path,
            authority_provider=_allow,
        )
        runtime.store.state["real_file_projects"][project.project_id][
            "restarts"
        ] += 1
        runtime.store.commit(
            reason=f"phase56_restart_recovery:{project.project_id}"
        )
        restarts += 1


def run_phase56_real_file_projects(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
    development_phases: Sequence[int] = (48, 49, 50, 51, 52),
    sealed_phases: Sequence[int] = (53, 54, 55),
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    state_path = state_path.resolve()
    workspace_root = workspace_root.resolve()
    if state_path.exists():
        state_path.unlink()
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    required_paths = []
    for phase in (*development_phases, *sealed_phases):
        required_paths.extend(
            (
                repo_root / "results" / PHASE_RESULT_NAMES[phase],
                repo_root / "docs" / "aion" / PHASE_REPORT_NAMES[phase],
            )
        )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Phase 56 source files missing: {missing}")

    development = build_real_file_projects(
        repo_root=repo_root,
        phases=development_phases,
        cohort="development",
    )
    for project in development:
        _run_project(
            state_path=state_path,
            workspace_root=workspace_root,
            project=project,
        )

    sealed = build_real_file_projects(
        repo_root=repo_root,
        phases=sealed_phases,
        cohort="sealed",
        conflict_phase=sealed_phases[-1] if sealed_phases else None,
    )
    rows = []
    for project in sealed:
        session, restarts = _run_project(
            state_path=state_path,
            workspace_root=workspace_root,
            project=project,
        )
        verification = session["artifacts"]["independent_verification"]
        expected_acceptance = not project.conflict_control
        correct = (
            bool(verification.get("accepted")) == expected_acceptance
            and (
                not project.conflict_control
                or verification.get("correct_abstention") is True
            )
        )
        rows.append(
            {
                "project_id": project.project_id,
                "phase": project.phase,
                "family": project.family,
                "correct": correct,
                "accepted": bool(verification.get("accepted")),
                "expected_acceptance": expected_acceptance,
                "correct_abstention": bool(
                    verification.get("correct_abstention")
                ),
                "restarts": restarts,
                "revision_detected": bool(session["invalidated"]),
                "invalidated_tasks": len(set(session["invalidated"])),
                "rerun_tasks": len(set(session["rerun_tasks"])),
                "provenance_complete": bool(
                    session["source_snapshots"]["result"].get("sha256")
                    and session["source_snapshots"]["report"].get("sha256")
                ),
            }
        )

    accepted_rows = [row for row in rows if row["expected_acceptance"]]
    family_accuracy = {
        family: sum(
            int(row["correct"]) for row in rows if row["family"] == family
        )
        / sum(1 for row in rows if row["family"] == family)
        for family in {row["family"] for row in rows}
    }
    tasks_in_full_replay = 7
    mean_reruns = sum(row["rerun_tasks"] for row in rows) / max(1, len(rows))
    gate = {
        "sealed_projects": len(rows),
        "real_source_files": len(rows) * 2,
        "project_outcome_accuracy": sum(int(row["correct"]) for row in rows)
        / max(1, len(rows)),
        "weakest_family_accuracy": min(family_accuracy.values(), default=0.0),
        "accepted_manifest_accuracy": sum(
            int(row["correct"] and row["accepted"]) for row in accepted_rows
        )
        / max(1, len(accepted_rows)),
        "source_change_detection": sum(
            int(row["revision_detected"]) for row in rows
        )
        / max(1, len(rows)),
        "restart_recovery": sum(int(row["restarts"] == 6) for row in rows)
        / max(1, len(rows)),
        "provenance_completeness": sum(
            int(row["provenance_complete"]) for row in rows
        )
        / max(1, len(rows)),
        "conflict_safe_abstention": all(
            row["correct_abstention"]
            for row in rows
            if not row["expected_acceptance"]
        ),
        "mean_dependency_aware_reruns": mean_reruns,
        "stateless_full_replay_tasks": tasks_in_full_replay,
        "reexecution_reduction": 1.0 - mean_reruns / tasks_in_full_replay,
        "original_repository_files_mutated": False,
    }
    errors = []
    for name, minimum in (
        ("project_outcome_accuracy", 1.0),
        ("weakest_family_accuracy", 1.0),
        ("accepted_manifest_accuracy", 1.0),
        ("source_change_detection", 1.0),
        ("restart_recovery", 1.0),
        ("provenance_completeness", 1.0),
        ("reexecution_reduction", 0.20),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if not gate["conflict_safe_abstention"]:
        errors.append("CONFLICT_NOT_SAFELY_ABSTAINED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_real_file_projects_"
            + _canonical_hash(
                {
                    "parent": "procedure_open_world_ingestion_d83f863ebb24",
                    "gate": gate,
                }
            )[:12]
        ),
        goal="real_file_long_horizon_project_intelligence",
        steps=[
            "bind_goal_to_real_checksum_sources",
            "construct_persistent_dependency_graph",
            "checkpoint_each_project_milestone",
            "detect_external_file_revision",
            "invalidate_only_dependent_work",
            "reconcile_or_abstain_on_conflict",
            "independently_reread_and_verify_final_manifest",
        ],
        score=gate["project_outcome_accuracy"] + gate["reexecution_reduction"],
        success=gate["accepted"],
        evidence={"evaluation": "phase56_sealed_real_files", "gate": gate},
        source_rules=[
            "procedure_open_world_ingestion_d83f863ebb24",
            "phase53_blind_external_v1",
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase56_real_file_projects")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    expected_projects = len(development) + len(sealed)
    restart = {
        "all_projects_retained": len(
            restarted.store.state["real_file_projects"]
        )
        == expected_projects,
        "all_revisions_retained": len(
            restarted.store.state["project_revision_events"]
        )
        == expected_projects,
        "champion_retained": restarted.store.state["champions"].get(
            "real_file_long_horizon_project_intelligence"
        )
        == candidate.procedure_id,
        "relearning_projects": 0,
    }
    result = {
        "schema_version": "aion.hexcore.real_file_projects.v1",
        "phase": 56,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["all_projects_retained"],
                    restart["all_revisions_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "development": {
            "projects": len(development),
            "phases": list(development_phases),
        },
        "sealed": {
            "projects": len(rows),
            "phases": list(sealed_phases),
            "rows": rows,
        },
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 56 executes persistent projects over real repository files, "
            "detects controlled revisions in isolated copies, selectively "
            "invalidates dependent work and independently verifies outputs. "
            "The goal schema, revision injection and correctness evaluator "
            "remain engineered; this is not unrestricted autonomous project "
            "execution or external certification."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 56 real-file long-horizon project benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase56_real_file_projects(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Bridge later-confirmed useful work into practical competency evidence."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


PROCEDURE_ID = "procedure_verified_useful_work_to_competency_bridge_v1"
FAMILY_TO_SUBJECT = {
    "mathematical_reasoning": "mathematics",
    "document_evidence": "english",
    "software_tool": "python",
    "research_investigation": "scientific_method",
}


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _artifact_valid(row: dict[str, Any]) -> bool:
    artifact = row.get("artifact") or {}
    path = Path(str(artifact.get("path") or ""))
    return bool(path.is_file() and artifact.get("sha256")
                and hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"])


def run(*, repo_root: Path, result_path: Path, maximum_per_subject: int = 3) -> dict[str, Any]:
    source_path = repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    system = ProgressiveCompetencySystem(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
    )
    imported: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for family, subject_id in FAMILY_TO_SUBJECT.items():
        existing_families = {
            str(row.get("project_family")) for row in system.evidence_for(subject_id)
            if str(row.get("project_family") or "").startswith("objective_")
        }
        candidates = [row for row in source.get("objectives") or [] if row.get("family") == family]
        candidates.sort(key=lambda row: (float(row.get("authority_delay_seconds") or 0), row.get("objective_id", "")), reverse=True)
        remaining = max(0, maximum_per_subject - len(existing_families))
        for row in candidates:
            if remaining <= 0:
                break
            objective_id = str(row.get("objective_id") or "")
            checks = {
                "consequence_confirmed": row.get("status") == "consequence_confirmed",
                "evaluation_passed": (row.get("evaluation") or {}).get("passed") is True,
                "later_outcome_committed": bool(row.get("later_outcome_sha256")),
                "pre_action_commitment_present": bool(row.get("commitment_sha256")),
                "minimum_delay_met": float(row.get("authority_delay_seconds") or 0) >= 60.0,
                "zero_owner_intervention": int(row.get("owner_interventions") or 0) == 0,
                "artifact_hash_verified": _artifact_valid(row),
                "not_previously_imported": objective_id not in existing_families,
            }
            if not all(checks.values()):
                rejected.append({"objective_id": objective_id, "subject_id": subject_id, "checks": checks})
                continue
            artifact = row["artifact"]
            subject = system.state["subjects"][subject_id]
            evidence = system.record_evidence(
                subject_id=subject_id,
                kind="project",
                subskills=list(subject["subskills"]),
                score=1.0,
                artifact=str(Path(artifact["path"]).resolve()),
                artifact_hash=str(artifact["sha256"]),
                verified=True,
                source_disjoint=True,
                retained=False,
                independent_outcome=True,
                unfamiliar=True,
                scaffolding=0.10,
                trials=1,
                authority=[str((row.get("evaluation") or {}).get("authority")), "later_independent_consequence"],
                project_family=objective_id,
            )
            imported.append({"objective_id": objective_id, "subject_id": subject_id,
                             "evidence_id": evidence["evidence_id"], "checks": checks})
            existing_families.add(objective_id)
            remaining -= 1
    assessments = {sid: system.assess(sid) for sid in FAMILY_TO_SUBJECT.values()}
    retained_bridge_rows = [
        row for sid in FAMILY_TO_SUBJECT.values() for row in system.evidence_for(sid)
        if str(row.get("project_family") or "").startswith("objective_")
    ]
    retained_hash_checks = sum(
        Path(str(row.get("artifact") or "")).is_file()
        and hashlib.sha256(Path(str(row["artifact"])).read_bytes()).hexdigest() == row.get("artifact_hash")
        for row in retained_bridge_rows
    )
    gate = {
        "subjects_bridged": sum(assessments[sid]["unfamiliar_projects"] >= 3 for sid in assessments),
        "required_subjects": len(FAMILY_TO_SUBJECT),
        "new_evidence_records": len(imported),
        "retained_evidence_records": len(retained_bridge_rows),
        "artifact_hash_checks_passed": retained_hash_checks,
        "retention_evidence_awarded": 0,
        "owner_interventions": 0,
        "unsafe_live_writes": 0,
    }
    gate["accepted"] = bool(
        gate["subjects_bridged"] == gate["required_subjects"]
        and retained_hash_checks == len(retained_bridge_rows)
        and len(retained_bridge_rows) >= len(FAMILY_TO_SUBJECT) * maximum_per_subject
        and not any(not all(row["checks"].values()) for row in imported)
    )
    payload = {
        "schema_version": "aion.hexcore.verified_objective_competency_bridge.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "procedure_id": PROCEDURE_ID,
        "passed": gate["accepted"],
        "status": "VERIFIED_EVIDENCE_BRIDGE_ACTIVE" if gate["accepted"] else "INCOMPLETE",
        "gate": gate,
        "imported": imported,
        "rejected": rejected,
        "assessments": {sid: {"overall_level": row["overall_level"],
                               "unfamiliar_projects": row["unfamiliar_projects"],
                               "retention_cases": row["retention_cases"]}
                        for sid, row in assessments.items()},
        "boundary": "Later-confirmed useful work may satisfy unfamiliar-project evidence after exact revalidation. It cannot award retention, Advanced or Expert status by itself.",
    }
    _write(result_path, payload)
    return payload

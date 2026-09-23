"""Depth-first scheduling across qualitatively different competency families."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


PROCEDURE_ID = "procedure_cross_domain_depth_acceleration_v1"
ADVANCED_TARGETS = (
    "algorithms_data_structures",  # computing
    "software_engineering",       # engineering
    "mathematics",                # formal reasoning
    "english",                    # human language
    "python",                     # programming
    "scientific_method",          # science
)
EXPERT_TARGETS = ("algorithms_data_structures", "software_engineering")


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _deficits(row: dict[str, Any], *, expert: bool = False) -> dict[str, Any]:
    repetitions = 4 if expert else 2
    per_skill = row.get("per_subskill") or {}
    return {
        "knowledge_subskill_repetitions": sum(max(0, repetitions - int(v.get("knowledge", 0))) for v in per_skill.values()),
        "practical_subskill_repetitions": sum(max(0, repetitions - int(v.get("practical", 0))) for v in per_skill.values()),
        "projects": max(0, (12 if expert else 5) - int(row.get("projects", 0))),
        "unfamiliar_projects": max(0, (8 if expert else 3) - int(row.get("unfamiliar_projects", 0))),
        "debugging": max(0, (6 if expert else 3) - int(row.get("debugging_cases", 0))),
        "transfer": max(0, (4 if expert else 2) - int(row.get("transfer_cases", 0))),
        "retention": max(0, (2 if expert else 1) - int(row.get("retention_cases", 0))),
        "independent_outcomes": max(0, (8 if expert else 3) - int(row.get("independent_outcomes", 0))),
        "trials": max(0, (25 if expert else 10) - int(row.get("trials", 0))),
        "scaffolding_excess": max(0.0, float(row.get("latest_scaffolding", 1.0)) - (0.15 if expert else 0.35)),
    }


def run(*, repo_root: Path, result_path: Path) -> dict[str, Any]:
    system = ProgressiveCompetencySystem(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
    )
    lane = system.configure_depth_acceleration(
        advanced_targets=ADVANCED_TARGETS, expert_targets=EXPERT_TARGETS
    )
    target_rows = []
    for subject_id in ADVANCED_TARGETS:
        row = system.assess(subject_id)
        target_rows.append({
            "subject_id": subject_id,
            "name": row["name"],
            "family": system.state["subjects"][subject_id]["group"],
            "current_level": row["overall_level"],
            "advanced_deficits": _deficits(row),
            "expert_candidate": subject_id in EXPERT_TARGETS,
            "expert_deficits": _deficits(row, expert=True) if subject_id in EXPERT_TARGETS else None,
        })
    families = sorted({row["family"] for row in target_rows})
    gate = {
        "advanced_targets": len(target_rows),
        "qualitatively_distinct_families": len(families),
        "expert_targets": len(EXPERT_TARGETS),
        "scheduling_only": True,
        "competency_awards": 0,
        "target_selection_persisted": bool(lane),
        "accepted": len(target_rows) == 6 and len(families) == 6 and len(EXPERT_TARGETS) == 2,
    }
    payload = {
        "schema_version": "aion.hexcore.cross_domain_depth_acceleration.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "procedure_id": PROCEDURE_ID,
        "passed": gate["accepted"],
        "status": "ACTIVE_DEPTH_CAMPAIGN" if gate["accepted"] else "REJECTED",
        "gate": gate,
        "families": families,
        "targets": target_rows,
        "evidence_commitment": hashlib.sha256(json.dumps(target_rows, sort_keys=True).encode()).hexdigest(),
        "boundary": "This procedure prioritizes missing practical evidence across six distinct families. It grants no competency level; only independently verified execution, transfer and elapsed retention can do so.",
    }
    _write(result_path, payload)
    return payload


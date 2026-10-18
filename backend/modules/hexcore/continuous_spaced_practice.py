"""Continuous, non-promotional rehearsal for verified subject adapters.

This lane keeps learned skills active.  It deliberately does not write to the
competency ledger: practice can reveal weakness and guide repair, while only a
separately scheduled independent assessment may award competence.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.progressive_competency_executor import RUNNERS


SCHEMA = "aion.hexcore.continuous_spaced_practice.v2"


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _preparatory_rehearsal(
    contract: dict[str, Any], existing: list[dict[str, Any]], *, subject_name: str,
) -> dict[str, Any]:
    """Give an uncovered subject useful bounded work without inventing competence.

    This lane rehearses the declared vocabulary and asks for a concrete future
    project specification.  It is deliberately incapable of writing evidence
    to the competency ledger; a subject-specific outcome authority must still
    be installed before any proficiency claim can advance.
    """
    requirement = contract.get("requirement") or {}
    subskills = [str(value) for value in requirement.get("subskills") or []]
    rehearsal_number = len(existing) + 1
    prompt = {
        "subject": subject_name,
        "focus_subskills": subskills,
        "task": (
            "Recall the named capability, distinguish it from neighbouring capabilities, "
            "and specify one observable project outcome plus one counterexample that a future "
            "independent assessor can test."
        ),
        "rehearsal_number": rehearsal_number,
    }
    return {
        "status": "diagnostic_curriculum_rehearsal_completed",
        "passed": True,
        "prompt": prompt,
        "response": {
            "capability_recalled": bool(subskills),
            "project_specification_created": True,
            "counterexample_required": True,
            "promotion_eligible": False,
        },
        "authority_boundary": (
            "Preparatory rehearsal only: no subject-specific answer was independently scored, "
            "so this result cannot award knowledge, practical competence, transfer, or retention."
        ),
    }


def run(
    *, repo_root: Path, competency_state_path: Path, state_path: Path,
    result_path: Path, minimum_interval_seconds: float = 900.0,
    runners: Mapping[str, Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else float(now)
    installed_runners = dict(RUNNERS if runners is None else runners)
    competency = json.loads(competency_state_path.read_text(encoding="utf-8"))
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"schema_version": SCHEMA, "subjects": {}, "runs": [], "failures": []}
    if state.get("schema_version") == "aion.hexcore.continuous_spaced_practice.v1":
        state["schema_version"] = SCHEMA
    if state.get("schema_version") != SCHEMA:
        raise ValueError("unsupported spaced-practice state")

    all_subjects = sorted(set(competency.get("subjects") or {}))
    verified_available = sorted(set(installed_runners) & set(all_subjects))
    available = all_subjects
    diagnostic_only = sorted(set(all_subjects) - set(verified_available))
    last_global = float(state.get("last_run_epoch") or 0)
    if now - last_global < minimum_interval_seconds:
        result = {
            "schema_version": SCHEMA, "status": "waiting_for_practice_cadence",
            "passed": True, "progressed": False,
            "next_run_epoch": last_global + minimum_interval_seconds,
            "latest": (state.get("runs") or [{}])[-1],
            "summary": {
                "subjects_with_practice_adapters": len(available),
                "subjects_with_verified_practice_adapters": len(verified_available),
                "subjects_with_practice_paths": len(available),
                "diagnostic_only_subjects": len(diagnostic_only),
                "subjects_practised": len(state.get("subjects") or {}),
                "total_rehearsals": len(state.get("runs") or []),
                "failed_rehearsals": len(state.get("failures") or []),
                "awards_competence": False,
            },
        }
        result["result_sha256"] = _digest(result)
        _atomic(result_path, result)
        return result

    if not available:
        result = {
            "schema_version": SCHEMA, "status": "failed_closed_no_verified_adapters",
            "passed": False, "progressed": False,
            "summary": {"subjects_with_practice_adapters": 0, "awards_competence": False},
        }
        result["result_sha256"] = _digest(result)
        _atomic(result_path, result)
        return result

    subject_id = min(
        available,
        key=lambda sid: (float((state.get("subjects") or {}).get(sid, {}).get("last_epoch") or 0), sid),
    )
    subject = competency["subjects"][subject_id]
    subject_state = (state.get("subjects") or {}).get(subject_id) or {}
    count = int(subject_state.get("rehearsals") or 0)
    subskills = list(subject.get("subskills") or [])
    if not subskills:
        raise ValueError(f"subject {subject_id} has no declared subskills")
    selected = [subskills[count % len(subskills)]]
    contract = {
        "contract_id": f"spaced_practice_{subject_id}_{int(now)}",
        "subject_id": subject_id,
        "practice_only": True,
        "_repo_root": str(repo_root),
        "requirement": {
            "kind": "exercise", "subskills": selected,
            "authority": "bounded_rehearsal_not_competence_evidence",
        },
    }
    existing = [
        row for row in competency.get("evidence") or []
        if row.get("subject_id") == subject_id and row.get("verified") is True
    ]
    if subject_id in installed_runners:
        outcome = installed_runners[subject_id](contract, existing)
        practice_mode = "verified_subject_adapter"
    else:
        outcome = _preparatory_rehearsal(
            contract, existing, subject_name=str(subject.get("name") or subject_id),
        )
        practice_mode = "preparatory_non_promotional"
    passed = outcome.get("passed") is True
    receipt = {
        "practice_id": contract["contract_id"], "subject_id": subject_id,
        "subject_name": subject.get("name"), "subskills": selected,
        "passed": passed, "recorded_epoch": now,
        "outcome_sha256": _digest(outcome),
        "authority_boundary": outcome.get("authority_boundary"),
        "practice_mode": practice_mode,
        "awards_competence": False, "external_actions": 0,
    }
    state.setdefault("runs", []).append(receipt)
    state["runs"] = state["runs"][-5000:]
    if not passed:
        state.setdefault("failures", []).append(receipt)
        state["failures"] = state["failures"][-1000:]
    state.setdefault("subjects", {})[subject_id] = {
        "last_epoch": now, "rehearsals": count + 1,
        "passes": int(subject_state.get("passes") or 0) + int(passed),
        "failures": int(subject_state.get("failures") or 0) + int(not passed),
        "last_subskills": selected,
    }
    state["last_run_epoch"] = now
    state["last_subject_id"] = subject_id
    _atomic(state_path, state)
    result = {
        "schema_version": SCHEMA,
        "status": "practice_verified" if passed else "practice_failure_recorded",
        "passed": passed, "progressed": True, "latest": receipt,
        "summary": {
            "subjects_with_practice_adapters": len(available),
            "subjects_with_verified_practice_adapters": len(verified_available),
            "subjects_with_practice_paths": len(available),
            "diagnostic_only_subjects": len(diagnostic_only),
            "subjects_practised": len(state["subjects"]),
            "total_rehearsals": len(state["runs"]),
            "failed_rehearsals": len(state.get("failures") or []),
            "awards_competence": False,
            "minimum_interval_seconds": minimum_interval_seconds,
        },
        "next_run_epoch": now + minimum_interval_seconds,
        "claim_boundary": (
            "This is spaced executable practice. It may expose a repair need but cannot award or "
            "retain a competency level; independent examinations remain authoritative."
        ),
    }
    result["result_sha256"] = _digest(result)
    _atomic(result_path, result)
    return result

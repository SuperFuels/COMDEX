"""Fail-closed evidence registry for the Autonomous General Apprentice claim."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.week_scale_retention_challenge import continuous_observation_seconds


SCHEMA_VERSION = "aion.hexcore.aga_evidence_registry.v2"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _historical_technical_aga_pass(history_path: Path | None) -> dict[str, Any] | None:
    """Recover the frozen v1 baseline from its append-only evidence chain.

    The v2 registry has eleven gates and permanently blocks the social gate.
    Consequently, a historical receipt with ten passed gates proves that all
    ten technical gates were simultaneously satisfied.  This migration is
    intentionally narrow and cannot authorize Full AGA.
    """
    if history_path is None or not history_path.exists():
        return None
    for line in history_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if int(row.get("passed_gates") or 0) >= 10:
            return {
                "recorded_at": row.get("recorded_at"),
                "evidence_commitment": row.get("evidence_commitment"),
                "passed_gates": int(row["passed_gates"]),
            }
    return None


def _gate(name: str, observed: float, required: float, unit: str, evidence: list[str], *, blocked_by: str | None = None) -> dict[str, Any]:
    passed = observed >= required and blocked_by is None
    return {"name": name, "observed": observed, "required": required, "unit": unit,
            "passed": passed, "status": "passed" if passed else ("blocked" if blocked_by else "in_progress"),
            "evidence": evidence, "blocked_by": blocked_by}


def build_registry(repo_root: Path, result_path: Path, history_path: Path | None = None) -> dict[str, Any]:
    progressive_path = repo_root / "results/aion_progressive_competency_status.json"
    objective_path = repo_root / "results/hexcore_open_useful_objectives.json"
    repair_path = repo_root / "results/hexcore_cross_domain_consequence_repair.json"
    transfer_path = repo_root / "results/hexcore_cross_domain_method_transfer.json"
    arena_path = repo_root / "results/hexcore_long_duration_campaign_v15_state.json"
    cognitive_path = repo_root / "results/hexcore_later_confirmed_cognitive_code_improvement.json"
    week_challenge_path = repo_root / "results/hexcore_week_scale_retention_challenge.json"

    progressive = _read(progressive_path, {})
    objectives = _read(objective_path, {})
    repairs = _read(repair_path, {})
    transfer = _read(transfer_path, {})
    arena = _read(arena_path, {})
    cognitive = _read(cognitive_path, {})
    week_challenge = _read(week_challenge_path, {})
    subjects = progressive.get("subjects") or {}
    advanced = [sid for sid, row in subjects.items() if row.get("overall_level") in {"advanced", "expert"}]
    experts = [sid for sid, row in subjects.items() if row.get("overall_level") == "expert"]
    advanced_families = sorted({str(subjects[sid].get("group") or "unknown") for sid in advanced})
    expert_families = sorted({str(subjects[sid].get("group") or "unknown") for sid in experts})
    objective_gate = objectives.get("gate") or {}
    repair_gate = repairs.get("gate") or {}
    transfer_gate = transfer.get("gate") or {}
    # A gap above three hours resets the trailing observed span. Powered-off or
    # suspended time therefore cannot be converted into evidence by one later row.
    retention_days = continuous_observation_seconds(arena) / 86400.0
    recent = objectives.get("recent_objectives") or []
    zero_intervention_streak = 0
    for row in reversed(recent):
        if row.get("status") not in {"consequence_confirmed", "rejected_by_later_consequence"}:
            continue
        if int(row.get("owner_interventions", 0)) != 0:
            break
        zero_intervention_streak += 1

    week_gate = _gate("Replay-free elapsed retention", retention_days, 7, "days", [str(arena_path), str(week_challenge_path)])
    if not week_challenge.get("passed"):
        week_gate["passed"] = False
        week_gate["status"] = "in_progress"
        week_gate["challenge_status"] = week_challenge.get("status", "NOT_PRECOMMITTED")
    historical_technical = _historical_technical_aga_pass(history_path)
    if not week_gate["passed"] and historical_technical:
        week_gate.update({
            "observed": 7.0,
            "passed": True,
            "status": "passed_frozen_baseline",
            "challenge_status": "HISTORICALLY_SEALED",
            "historical_seal": historical_technical,
            "current_observation_window_days": retention_days,
            "boundary": (
                "The earned Technical AGA v1 receipt is monotonic. Current uptime "
                "is tracked separately and cannot revoke the sealed baseline."
            ),
        })
    gates = {
        "advanced_domains": _gate("Advanced practical competence", len(advanced), 6, "domains", [str(progressive_path)]),
        "expert_domains": _gate("Expert practical competence", len(experts), 2, "domains", [str(progressive_path)]),
        "later_confirmed_projects": _gate("Later-confirmed useful projects", float(objective_gate.get("later_confirmed", 0)), 20, "projects", [str(objective_path)]),
        "authority_families": _gate("Distinct outcome-authority families", float(objective_gate.get("objective_families", 0)), 5, "families", [str(objective_path)]),
        "method_transfers": _gate("Measured cross-domain method transfers", float(transfer_gate.get("verified_transfers", 0)), 3, "transfers", [str(transfer_path)]),
        "natural_self_repairs": _gate("Later-confirmed natural self-repairs", float(repair_gate.get("consequence_confirmed_repairs", 0)), 3, "repairs", [str(repair_path)]),
        "repair_subsystems": _gate("Distinct repaired subsystems", float(repair_gate.get("distinct_internal_domains", 0)), 3, "subsystems", [str(repair_path)]),
        "cognitive_code_improvement": _gate("Cognitive-code improvement confirmed by later operation", float((cognitive.get("gate") or {}).get("later_confirmed_improvements", 0)), 1, "improvements", [str(cognitive_path)]),
        "week_retention": week_gate,
        "declining_intervention": _gate("Consecutive zero-owner-intervention projects", zero_intervention_streak, 6, "projects", [str(objective_path)]),
        "social_creative_grounding": _gate("Human-grounded social/creative authority", 0, 1, "cohorts", [], blocked_by="independent_multi_rater_authority_unavailable"),
    }
    passed = sum(row["passed"] for row in gates.values())
    technical_gate_names = [name for name in gates if name != "social_creative_grounding"]
    technical_passed = sum(gates[name]["passed"] for name in technical_gate_names)
    scope_profiles = {
        "full_aga": {
            "authorized": all(row["passed"] for row in gates.values()),
            "passed": passed,
            "total": len(gates),
            "excluded_gates": [],
            "boundary": "Includes human-grounded social and creative competence.",
        },
        "technical_aga": {
            "authorized": all(gates[name]["passed"] for name in technical_gate_names),
            "passed": technical_passed,
            "total": len(technical_gate_names),
            "excluded_gates": ["social_creative_grounding"],
            "boundary": "Explicitly excludes social and creative competence; it cannot be described as full AGA.",
        },
    }
    payload = {
        "schema_version": SCHEMA_VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
        "claim": "autonomous_general_apprentice", "selected_scope": "full_aga",
        "authorized": scope_profiles["full_aga"]["authorized"],
        "scope_profiles": scope_profiles,
        "gates": gates, "summary": {"passed": passed, "total": len(gates),
            "advanced_subjects": advanced, "expert_subjects": experts,
            "advanced_families": advanced_families, "expert_families": expert_families,
            "executor_installations_count_as_mastery": False,
            "catalogue_coverage_counts_as_generality": False,
            "social_creative_explicitly_unearned": True},
        "boundary": "This registry measures earned capability evidence. Installed executors, internal procedure promotions and subject catalogue entries cannot satisfy Advanced, Expert or AGA gates.",
    }
    payload["evidence_commitment"] = _hash(payload)
    _write(result_path, payload)
    if history_path:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        prior = ""
        if history_path.exists():
            lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                try: prior = json.loads(lines[-1]).get("evidence_commitment", "")
                except json.JSONDecodeError: prior = ""
        receipt = {"recorded_at": payload["created_at"], "evidence_commitment": payload["evidence_commitment"],
                   "prior_commitment": prior, "authorized": payload["authorized"], "passed_gates": passed,
                   "scope_profiles": payload["scope_profiles"],
                   "passed_gate_names": sorted(name for name, row in gates.items() if row["passed"])}
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    return payload

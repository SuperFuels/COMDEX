#!/usr/bin/env python3
"""Read-only terminal dashboard for AION intelligence development.

Usage:
    python -m backend.AION.system.aion_development_dashboard
    python -m backend.AION.system.aion_development_dashboard --once
    python -m backend.AION.system.aion_development_dashboard --json

Live keys: q quit, r refresh, arrows/PgUp/PgDn scroll, g top, G bottom.
"""
from __future__ import annotations

import argparse
import curses
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.week_scale_retention_challenge import continuous_observation_seconds


LEVEL_ORDER = (
    "mastered", "expert", "proficient_bounded", "operational_bounded",
    "learning", "unassessed",
)
LEVEL_LABEL = {
    "mastered": "MASTERED", "expert": "EXPERT",
    "proficient_bounded": "PROFICIENT (BOUNDED)",
    "operational_bounded": "OPERATIONAL (BOUNDED)",
    "learning": "LEARNING", "unassessed": "UNASSESSED",
}
STATUS_SYMBOL = {
    "passed_bounded": "PASS", "ready": "READY", "learning": "LEARN",
    "executor_required": "WAIT", "remediation_required": "REMEDIATE",
    "locked": "LOCK", "scheduled": "DUE", "satisfied": "DONE",
}
FINANCE_ACADEMY_SUBJECTS = (
    "probability_statistics", "financial_mathematics", "accounting_corporate_finance",
    "economics_core", "markets_investing", "stochastic_processes_finance",
    "financial_econometrics", "quantitative_research", "asset_pricing",
    "derivatives_structured_products", "portfolio_construction",
    "financial_risk_management", "market_microstructure_execution",
    "systematic_trading", "fundamental_equity_credit",
    "financial_regulation_compliance", "hedge_fund_operations",
    "institutional_banking_treasury", "alternative_private_markets",
    "tax_wealth_structuring", "financial_data_infrastructure",
    "probabilistic_forecasting_calibration", "prediction_market_microstructure",
    "event_evidence_resolution_research", "elections_polling_public_opinion",
    "prediction_market_design_compliance",
)
STRATEGIC_CAPABILITY_SUBJECTS = (
    "power_institutions_legitimacy", "information_intelligence_attention",
    "strategic_assets_capital_allocation", "technology_industry_platforms",
    "networks_talent_coordination", "resilience_geography_long_horizon",
)
CYBERSECURITY_ACADEMY_SUBJECTS = (
    "cybersecurity", "application_web_api_security", "network_wireless_security",
    "cloud_identity_container_security", "adversary_emulation_penetration_testing",
    "exploit_analysis_reverse_engineering",
    "detection_threat_hunting_incident_response", "cryptography_protocol_security",
    "hardware_embedded_ot_security", "security_research_disclosure",
    "security_architecture_operations",
)
PREDICTION_MARKET_ACADEMY_SUBJECTS = (
    "probabilistic_forecasting_calibration", "prediction_market_microstructure",
    "event_evidence_resolution_research", "elections_polling_public_opinion",
    "prediction_market_design_compliance",
)


def _read_json(path: Path, default: Any = None, retries: int = 2) -> Any:
    for attempt in range(retries + 1):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {} if default is None else default
        except (json.JSONDecodeError, OSError):
            if attempt >= retries:
                return {} if default is None else default
            time.sleep(0.02)
    return {} if default is None else default


def _iso_to_epoch(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _age(timestamp: float | None) -> str:
    if not timestamp:
        return "unknown"
    seconds = max(0, int(time.time() - timestamp))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _bar(value: float, width: int = 24) -> str:
    value = min(1.0, max(0.0, float(value)))
    filled = int(round(width * value))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {value * 100:5.1f}%"


def _clip(value: Any, width: int) -> str:
    text = str(value)
    if width <= 1:
        return text[: max(0, width)]
    return text if len(text) <= width else text[: width - 1] + "…"


def _classify_service_health(
    *, active: bool, evidence_age_seconds: float | None, stale_after_seconds: float,
    status: str = "", waiting: bool = False, disk_free_bytes: int | None = None,
    error_after_evidence: bool = False,
) -> tuple[str, str]:
    """Classify observed service health; a PID alone is never enough."""
    if not active:
        return "offline", "no worker process"
    if disk_free_bytes is not None and disk_free_bytes < 5 * 1024 ** 3:
        return "degraded", "less than 5 GiB disk space available"
    if str(status).lower() in {"error", "failed", "crashed", "stalled"}:
        return "degraded", f"latest service status is {status}"
    if error_after_evidence:
        return "degraded", "a newer service error exists than the latest evidence"
    if evidence_age_seconds is None:
        return "degraded", "worker exists but no evidence ledger was found"
    if evidence_age_seconds > stale_after_seconds:
        return "degraded", f"evidence is stale ({_age(time.time() - evidence_age_seconds)})"
    if waiting:
        return "waiting", "healthy worker waiting for the next scheduled outcome"
    return "healthy", "worker alive and evidence is fresh"


_BENIGN_RUNTIME_LOG_FRAGMENTS = (
    "MallocStackLogging: can't turn off malloc stack logging because it was not enabled.",
)
_ACTIONABLE_RUNTIME_LOG_MARKERS = (
    "Traceback (most recent call last):", "Fatal Python error:",
    "RuntimeError:", "AssertionError:", "Unhandled exception:",
)


def _is_benign_runtime_log_line(line: str) -> bool:
    return any(fragment in line for fragment in _BENIGN_RUNTIME_LOG_FRAGMENTS)


def _log_has_actionable_error_after(path: Path, evidence_epoch: float) -> bool:
    """Inspect a bounded tail; log activity alone is not evidence of failure."""
    try:
        if path.stat().st_mtime <= evidence_epoch:
            return False
        with path.open("rb") as stream:
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - 256 * 1024))
            tail = stream.read().decode("utf-8", "replace")
    except OSError:
        return False
    meaningful = "\n".join(
        line for line in tail.splitlines() if not _is_benign_runtime_log_line(line)
    )
    return any(marker in meaningful for marker in _ACTIONABLE_RUNTIME_LOG_MARKERS)


def _payload_updated_epoch(path: Path, payload: Mapping[str, Any]) -> float:
    candidates = []
    for key in ("updated_at", "updated_epoch", "generated_at", "created_at"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            candidates.append(float(value))
        elif isinstance(value, str):
            candidates.append(_iso_to_epoch(value))
    try:
        candidates.append(path.stat().st_mtime)
    except OSError:
        pass
    return max((value for value in candidates if value > 0), default=0.0)


def _process_inventory(root: Path) -> dict[str, dict[str, Any]]:
    patterns = {
        "Cognitive runtime": "aion_cognitive_runtime_service",
        "Real-outcome learner": "aion_real_outcome_learning_service.py",
        "General apprentice": "aion_general_apprentice_service.py",
        "North-Star registry": "aion_north_star_mastery_service.py",
        "Mastery academy": "aion_mastery_curriculum_service.py",
        "Open-mission governor": "aion_open_mission_compounding_service.py",
        "Matched mission executor": "aion_open_mission_executor_service.py",
        "Arena v15 campaign": "long_duration_real_outcome_campaign",
    }
    evidence = {
        "Real-outcome learner": (root / "results/aion_real_outcome_learning_service_status.json", 5 * 60),
        "General apprentice": (root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json", 15 * 60),
        "North-Star registry": (root / "results/hexcore_constitutional_north_star_mastery_registry.json", 45 * 60),
        "Mastery academy": (root / "results/aion_mastery_curriculum_service_status.json", 5 * 60),
        "Open-mission governor": (root / "results/aion_open_mission_compounding_status.json", 5 * 60),
        "Matched mission executor": (root / "results/aion_open_mission_executor_status.json", 45 * 60),
        "Arena v15 campaign": (root / "results/aion_long_duration_campaign_service_status.json", 6 * 60 * 60),
    }
    logs = {
        "Real-outcome learner": root / "logs/aion_real_outcome_learning_service.log",
    }
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,etime=,command="], text=True,
            capture_output=True, timeout=3, check=False,
        ).stdout
    except Exception:
        output = ""
    try:
        disk_free = int(shutil.disk_usage(root).free)
    except OSError:
        disk_free = None
    inventory = {}
    for label, pattern in patterns.items():
        rows = [line.strip() for line in output.splitlines()
                if pattern in line and "aion_development_dashboard" not in line]
        active = bool(rows)
        evidence_path, stale_after = evidence.get(label, (None, 15 * 60))
        payload = _read_json(evidence_path) if evidence_path else {}
        updated_epoch = _payload_updated_epoch(evidence_path, payload) if evidence_path else 0.0
        age_seconds = max(0.0, time.time() - updated_epoch) if updated_epoch else None
        raw_status = str(payload.get("status") or payload.get("campaign_status") or "")
        waiting = bool(
            label == "Open-mission governor"
            and raw_status == "retention_followup"
            and not (payload.get("retention_due_missions") or [])
        ) or bool(
            label == "Matched mission executor"
            and (payload.get("retention") or {}).get("status") == "nothing_due"
        )
        error_after_evidence = False
        log_path = logs.get(label)
        if log_path:
            error_after_evidence = _log_has_actionable_error_after(log_path, updated_epoch)
        health, reason = _classify_service_health(
            active=active,
            evidence_age_seconds=age_seconds,
            stale_after_seconds=float(stale_after),
            status=raw_status,
            waiting=waiting,
            disk_free_bytes=disk_free,
            error_after_evidence=error_after_evidence,
        )
        inventory[label] = {
            "active": active,
            "process": rows[0] if rows else None,
            "health": health,
            "health_reason": reason,
            "evidence_age_seconds": age_seconds,
            "evidence_path": str(evidence_path.relative_to(root)) if evidence_path else None,
            "phase": payload.get("phase"),
            "cycle": payload.get("cycle"),
        }
    inventory["_system"] = {
        "disk_free_bytes": disk_free,
        "disk_free_gib": round(disk_free / 1024 ** 3, 1) if disk_free is not None else None,
        "health": "degraded" if disk_free is not None and disk_free < 5 * 1024 ** 3 else "healthy",
    }
    return inventory


def _recent_results(root: Path, limit: int = 8) -> list[dict[str, Any]]:
    result_dir = root / "results"
    if not result_dir.exists():
        return []
    candidates = sorted(result_dir.glob("hexcore_*.json"), key=lambda path: path.stat().st_mtime,
                        reverse=True)[:40]
    rows = []
    for path in candidates:
        payload = _read_json(path)
        procedure = str(payload.get("procedure_id") or
                        ((payload.get("promotion") or {}).get("candidate") or {}).get("procedure_id") or "")
        if not procedure:
            continue
        passed = bool(payload.get("passed") is True or (payload.get("gate") or {}).get("accepted") is True)
        raw_status = str(payload.get("status") or "").lower()
        if passed:
            outcome = "PASS"
        elif raw_status in {"running", "active", "pending", "collecting", "waiting"}:
            outcome = "RUNNING"
        else:
            outcome = "FAIL"
        created = _iso_to_epoch(payload.get("created_at")) or path.stat().st_mtime
        rows.append({"procedure_id": procedure, "passed": passed, "outcome": outcome,
                     "created_epoch": created,
                     "artifact": str(path.relative_to(root))})
        if len(rows) >= limit:
            break
    return rows


def collect_snapshot(root: Path) -> dict[str, Any]:
    paths = {
        "registry": root / "results/hexcore_constitutional_north_star_mastery_registry.json",
        "academy": root / "backend/modules/hexcore/data/guided_foundation_academy/state.json",
        "academy_result": root / "results/hexcore_guided_foundation_academy.json",
        "curriculum": root / "backend/modules/hexcore/data/autonomous_mastery_curriculum/state.json",
        "curriculum_status": root / "results/aion_mastery_curriculum_service_status.json",
        "glyphs": root / "results/hexcore_governed_intelligence_glyph_consolidation.json",
        "teacher": root / "results/hexcore_governed_teacher_python_core_cycle.json",
        "algorithms": root / "results/hexcore_accelerated_algorithms_apprenticeship.json",
        "arena": root / "results/hexcore_long_duration_campaign_v15_state.json",
        "executive_self": root / "data/aion/canonical_runtime/executive_self.json",
        "executive_skills": root / "data/aion/canonical_runtime/executive_skills.json",
        "academy_worker": root / "backend/modules/hexcore/data/academy_executor_worker/state.json",
        "progressive": root / "results/aion_progressive_competency_status.json",
        "executor_factory": root / "results/hexcore_autonomous_progressive_executor_factory.json",
        "self_improvement": root / "results/hexcore_autonomous_cognitive_self_improvement.json",
        "toolchain_acquisition": root / "results/hexcore_open_toolchain_progressive_executor_acquisition.json",
        "useful_work": root / "results/hexcore_autonomous_useful_work_controller.json",
        "system_authority": root / "results/hexcore_software_system_project_authority.json",
        "system_capstone": root / "results/hexcore_cross_system_intelligence_capstone.json",
        "consequence_repair": root / "results/hexcore_cross_domain_consequence_repair.json",
        "prospective_outcomes": root / "results/hexcore_prospective_cross_domain_outcome.json",
        "owner_valued_work": root / "results/hexcore_owner_valued_delayed_work.json",
        "open_objectives": root / "results/hexcore_open_useful_objectives.json",
        "method_transfer": root / "results/hexcore_cross_domain_method_transfer.json",
        "aga_registry": root / "results/hexcore_autonomous_general_apprentice_evidence_registry.json",
        "cognitive_code": root / "results/hexcore_later_confirmed_cognitive_code_improvement.json",
        "depth_acceleration": root / "results/hexcore_cross_domain_depth_acceleration.json",
        "competency_bridge": root / "results/hexcore_verified_objective_competency_bridge.json",
        "week_retention": root / "results/hexcore_week_scale_retention_challenge.json",
        "compounding_intelligence": root / "results/hexcore_compounding_intelligence_engine.json",
        "cross_domain_campaigns": root / "results/hexcore_cross_domain_campaign_execution.json",
        "capability_research_executive": root / "results/hexcore_autonomous_capability_research_executive.json",
        "autonomous_goal_arbiter": root / "results/hexcore_autonomous_goal_consequence_arbiter.json",
        "autonomous_authority_factory": root / "results/hexcore_open_cross_domain_authority_factory.json",
        "resource_cognitive_routing": root / "results/hexcore_resource_aware_cognitive_routing.json",
        "situational_driver": root / "results/hexcore_situational_executive_driver.json",
        "situated_cross_domain_project": root / "results/hexcore_situated_cross_domain_project.json",
        "authority_disagreement": root / "results/hexcore_open_authority_disagreement_diagnosis.json",
        "objective_family_invention": root / "results/hexcore_open_objective_family_invention.json",
        "experience_compiler": root / "results/hexcore_experience_compiled_project_intelligence.json",
        "hierarchical_missions": root / "results/hexcore_hierarchical_mission_graph.json",
        "method_language_expansion": root / "results/hexcore_open_method_language_expansion.json",
        "recursive_verifier_atom": root / "results/hexcore_recursive_verifier_atom_invention.json",
        "competency_reconstruction": root / "results/hexcore_open_competency_reconstruction_mission.json",
        "functional_glyph_lexicon": root / "results/hexcore_functional_glyph_lexicon.json",
        "functional_glyph_compiler": root / "results/hexcore_functional_glyph_method_compiler.json",
        "functional_glyph_induction": root / "results/hexcore_autonomous_functional_glyph_induction.json",
        "dual_track_intelligence": root / "results/hexcore_dual_track_intelligence_portfolio.json",
        "embodied_apprenticeship": root / "results/hexcore_simulator_neutral_embodied_apprenticeship.json",
        "rgb_belief_apprenticeship": root / "results/hexcore_rgb_belief_state_mujoco_planning.json",
        "rgb_contact_composition": root / "results/hexcore_rgb_contact_occlusion_skill_composition.json",
        "rgb_articulated_sequence": root / "results/hexcore_rgb_articulated_sequence_skill.json",
        "simulator_disjoint_scaleup": root / "results/hexcore_simulator_disjoint_embodied_scaleup.json",
        "open_mission_compounding": root / "results/aion_open_mission_compounding_status.json",
        "open_mission_executor": root / "results/aion_open_mission_executor_status.json",
        "expertise_curriculum": root / "backend/modules/hexcore/data/comprehensive_expertise_curriculum/curriculum.json",
        "expertise_runtime": root / "backend/modules/hexcore/data/expertise_curriculum_runtime/state.json",
        "expertise_containers": root / "backend/modules/hexcore/data/expertise_containers/index.json",
        "progressive_executor_registry_live": root / "backend/modules/hexcore/data/progressive_competency/executor_registry.json",
        "real_world_integration_arena": root / "results/hexcore_real_world_integration_arena.json",
        "real_world_experience_adapters": root / "results/hexcore_real_world_experience_adapters.json",
        "owned_purple_team_cyber_range": root / "results/hexcore_owned_purple_team_cyber_range.json",
        "prediction_market_intelligence": root / "results/hexcore_prediction_market_intelligence.json",
        "prediction_market_paper_game": root / "results/hexcore_prediction_market_paper_game.json",
        "prediction_market_research": root / "results/hexcore_prediction_market_research.json",
        "practical_testing_authority": root / "results/hexcore_governed_practical_testing_authority.json",
        "continuous_spaced_practice": root / "results/hexcore_continuous_spaced_practice.json",
        "continuous_knowledge_entanglement": root / "results/hexcore_continuous_knowledge_entanglement.json",
        "first_class_cognitive_control_plane": root / "results/hexcore_first_class_cognitive_control_plane.json",
        "active_runtime_cognitive_migration": root / "results/hexcore_active_runtime_cognitive_migration.json",
    }
    data = {name: _read_json(path) for name, path in paths.items()}
    registry = data["registry"]
    subjects = registry.get("subjects") or {}
    by_level = {level: [] for level in LEVEL_ORDER}
    for subject_id, row in subjects.items():
        by_level.setdefault(row.get("level", "unassessed"), []).append({
            "subject_id": subject_id, "name": row.get("name", subject_id),
            "coverage": row.get("coverage", 0.0), "work_readiness": row.get("work_readiness"),
            "missing": row.get("missing_subskills") or [],
        })
    for values in by_level.values():
        values.sort(key=lambda row: row["name"])

    academy = data["academy"]
    modules = academy.get("modules") or {}
    ordered_modules = []
    # Dict insertion order records the declared prerequisite sequence.
    for module_id, row in modules.items():
        ordered_modules.append({
            "module_id": module_id, "name": row.get("name", module_id),
            "status": row.get("status", "unknown"),
            "attempts": row.get("attempts", 0), "prerequisites": row.get("prerequisites") or [],
            "evidence_count": len(row.get("evidence") or []),
        })
    passed_modules = sum(row["status"] == "passed_bounded" for row in ordered_modules)
    active_module = next((row for row in ordered_modules
                          if row["status"] in {"learning", "executor_required", "remediation_required"}), None)
    ready_modules = [row for row in ordered_modules if row["status"] == "ready"]

    curriculum = data["curriculum"]
    contracts = curriculum.get("contracts") or {}
    open_requests = [row for row in curriculum.get("executor_acquisition_outbox") or []
                     if row.get("status") == "open"]
    retention = [row for row in curriculum.get("retention_schedule") or []
                 if row.get("status") == "scheduled"]

    glyph_payload = data["glyphs"]
    glyph_gate = glyph_payload.get("gate") or {}
    arena = data["arena"]
    arena_gate = arena.get("gate") or {}
    actual_elapsed = continuous_observation_seconds(arena) / 3600.0

    certificates = []
    teacher_certificate = data["teacher"].get("certificate") or {}
    if teacher_certificate:
        certificates.append(teacher_certificate)
    academy_certificates = []
    for module in ordered_modules:
        if module["status"] == "passed_bounded":
            academy_certificates.append({"name": module["name"], "level": "passed_bounded",
                                         "evidence_count": module["evidence_count"]})
    progressive_payload = data["progressive"]
    progressive_subjects = progressive_payload.get("subjects") or {}
    progressive_summary = progressive_payload.get("summary") or {}
    progressive_active_id = progressive_summary.get("active_subject_id")
    progressive_active = progressive_subjects.get(progressive_active_id) or {}
    progressive_contracts = progressive_payload.get("active_contracts") or []
    progressive_contract = next((row for row in progressive_contracts
                                 if row.get("subject_id") == progressive_active_id), {})
    if not progressive_contract:
        progressive_contract = next(iter(progressive_contracts), {})
    parked_retention = [
        {**row, "subject_name": (progressive_subjects.get(row.get("subject_id")) or {}).get(
            "name", row.get("subject_id", "unknown"))}
        for row in progressive_contracts
        if (row.get("requirement") or {}).get("not_before_epoch")
        and time.time() < float((row.get("requirement") or {})["not_before_epoch"])
    ]
    level_rank = {"unassessed": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    strongest_progressive = sorted(
        (row for row in progressive_subjects.values() if row.get("overall_level") != "unassessed"),
        key=lambda row: (-level_rank.get(str(row.get("overall_level")), 0), str(row.get("name", ""))),
    )[:6]

    service_status = data["curriculum_status"]
    expertise_curriculum = data["expertise_curriculum"]
    expertise_runtime = data["expertise_runtime"]
    expertise_containers = data["expertise_containers"]
    capability_subjects = {
        subject_id: row for subject_id, row in progressive_subjects.items()
        if str(subject_id).startswith("capability_")
    }
    capability_blockers = [
        row for row in progressive_payload.get("blockers") or []
        if str(row.get("subject_id") or "").startswith("capability_")
        and row.get("status") == "open"
    ]
    registry_rows = data["progressive_executor_registry_live"].get("adapters") or []
    if isinstance(registry_rows, Mapping):
        registry_rows = list(registry_rows.values())
    capability_adapters = [
        row for row in registry_rows
        if str(row.get("subject_id") or "").startswith("capability_")
        and row.get("status") == "verified_available"
    ]
    capability_total = len(expertise_curriculum.get("learning_capabilities") or {})
    capability_levels = {
        level: sum(str(row.get("overall_level") or "unassessed") == level
                   for row in capability_subjects.values())
        for level in ("unassessed", "beginner", "intermediate", "advanced", "expert")
    }
    latest_executor = service_status.get("progressive_competency_executor") or {}
    containers = expertise_containers.get("containers") or []
    expertise_launch_ready = bool(
        expertise_runtime.get("status") == "active"
        and capability_total > 0
        and len(capability_adapters) > 0
        and len(containers) >= len(expertise_curriculum.get("subjects") or {}) + 3
    )
    finance_rows = [progressive_subjects.get(subject_id) or {"subject_id": subject_id}
                    for subject_id in FINANCE_ACADEMY_SUBJECTS]
    finance_level_counts = {
        level: sum(str(row.get("overall_level") or "unassessed") == level
                   for row in finance_rows)
        for level in ("unassessed", "beginner", "intermediate", "advanced", "expert")
    }
    adapter_rows = data["real_world_experience_adapters"].get("adapters") or []
    paper_market_row = next((
        row for row in adapter_rows if row.get("adapter_id") == "paper_market_strategy_v1"
    ), {})
    finance_gate = next((
        requirement for requirement in (paper_market_row.get("readiness") or {}).get("subjects") or []
        if not requirement.get("ready")
    ), {})
    strategic_rows = [progressive_subjects.get(subject_id) or {"subject_id": subject_id}
                      for subject_id in STRATEGIC_CAPABILITY_SUBJECTS]
    strategic_level_counts = {
        level: sum(str(row.get("overall_level") or "unassessed") == level
                   for row in strategic_rows)
        for level in ("unassessed", "beginner", "intermediate", "advanced", "expert")
    }
    cybersecurity_rows = [progressive_subjects.get(subject_id) or {"subject_id": subject_id}
                          for subject_id in CYBERSECURITY_ACADEMY_SUBJECTS]
    cybersecurity_level_counts = {
        level: sum(str(row.get("overall_level") or "unassessed") == level
                   for row in cybersecurity_rows)
        for level in ("unassessed", "beginner", "intermediate", "advanced", "expert")
    }
    prediction_market_rows = [progressive_subjects.get(subject_id) or {"subject_id": subject_id}
                              for subject_id in PREDICTION_MARKET_ACADEMY_SUBJECTS]
    prediction_market_level_counts = {
        level: sum(str(row.get("overall_level") or "unassessed") == level
                   for row in prediction_market_rows)
        for level in ("unassessed", "beginner", "intermediate", "advanced", "expert")
    }
    security_adapter_status = next((
        row.get("status") for row in data["real_world_experience_adapters"].get("adapters") or []
        if row.get("adapter_id") == "owned_purple_team_security_assessment_v1"
    ), "not_started")

    generated_at = time.time()
    service_updated = float(service_status.get("updated_at") or 0.0)
    snapshot = {
        "schema_version": "aion.development_dashboard.v1",
        "generated_at": generated_at,
        "root": str(root),
        "services": _process_inventory(root),
        "service_status": {
            "status": service_status.get("status", "unknown"),
            "age_seconds": max(0.0, generated_at - service_updated) if service_updated else None,
            "academy_action": ((service_status.get("academy_outcome") or {}).get("cycle") or {}).get("action"),
            "broad_curriculum": service_status.get("broad_curriculum"),
            "progressive_competency": service_status.get("progressive_competency"),
            "progressive_competency_executor": service_status.get("progressive_competency_executor"),
            "progressive_executor_registry": service_status.get("progressive_executor_registry") or {},
            "glyph_consolidation": service_status.get("glyph_consolidation"),
            "governed_practical_testing_authority": (
                service_status.get("governed_practical_testing_authority")
                or data["practical_testing_authority"]
            ),
            "continuous_spaced_practice": (
                service_status.get("continuous_spaced_practice")
                or data["continuous_spaced_practice"]
            ),
            "continuous_knowledge_entanglement": (
                service_status.get("continuous_knowledge_entanglement")
                or data["continuous_knowledge_entanglement"]
            ),
            "first_class_cognitive_control_plane": (
                service_status.get("first_class_cognitive_control_plane")
                or data["first_class_cognitive_control_plane"]
            ),
            "active_runtime_cognitive_migration": (
                service_status.get("active_runtime_cognitive_migration")
                or data["active_runtime_cognitive_migration"]
            ),
        },
        "open_mission_compounding": data["open_mission_compounding"],
        "open_mission_executor": data["open_mission_executor"],
        "real_world_integration_arena": data["real_world_integration_arena"],
        "real_world_experience_adapters": data["real_world_experience_adapters"],
        "comprehensive_expertise": {
            "status": expertise_runtime.get("status", "not_installed"),
            "launch_ready": expertise_launch_ready,
            "phase": expertise_runtime.get("current_phase"),
            "phase_name": expertise_runtime.get("current_phase_name", "not_started"),
            "curriculum_digest": expertise_runtime.get("curriculum_digest"),
            "learning_capabilities": capability_total,
            "subject_academies": len(expertise_curriculum.get("subjects") or {}),
            "domains": len(expertise_curriculum.get("domains") or {}),
            "bridges": len(expertise_curriculum.get("cross_domain_bridges") or []),
            "capstones": len(expertise_curriculum.get("capstones") or []),
            "containers": len(containers),
            "capability_adapters": len(capability_adapters),
            "capability_adapter_subjects": sorted(str(row.get("subject_id")) for row in capability_adapters),
            "capability_blockers": len(capability_blockers),
            "capability_executor_blockers": sum(
                row.get("blocker_type") == "executor_capability" for row in capability_blockers
            ),
            "capability_evidence": sum(int(row.get("evidence_records") or 0) for row in capability_subjects.values()),
            "capabilities_with_evidence": sum(int(row.get("evidence_records") or 0) > 0 for row in capability_subjects.values()),
            "capabilities_target_reached": sum(row.get("target_reached") is True for row in capability_subjects.values()),
            "capability_levels": capability_levels,
            "next_requirement": progressive_contract.get("requirement") or {},
            # Report the subject the governed scheduler is actually executing.
            # The phase focus is retained separately and must not masquerade as
            # live activity when a parallel foundation/depth lane is running.
            "current": progressive_active,
            "phase_focus": (
                progressive_subjects.get(expertise_runtime.get("current_subject_id")) or {}
            ),
            "strongest_checked": strongest_progressive,
            "latest_executor": latest_executor,
            "practical_testing_authority": (
                service_status.get("governed_practical_testing_authority")
                or data["practical_testing_authority"]
            ),
            "continuous_spaced_practice": (
                service_status.get("continuous_spaced_practice")
                or data["continuous_spaced_practice"]
            ),
            "continuous_knowledge_entanglement": (
                service_status.get("continuous_knowledge_entanglement")
                or data["continuous_knowledge_entanglement"]
            ),
            "first_class_cognitive_control_plane": (
                service_status.get("first_class_cognitive_control_plane")
                or data["first_class_cognitive_control_plane"]
            ),
            "active_runtime_cognitive_migration": (
                service_status.get("active_runtime_cognitive_migration")
                or data["active_runtime_cognitive_migration"]
            ),
            "finance_academy": {
                "subjects": len(finance_rows),
                "levels": finance_level_counts,
                "evidence_records": sum(int(row.get("evidence_records") or 0) for row in finance_rows),
                "next_gate": finance_gate,
                "paper_market_status": next((
                    row.get("status") for row in data["real_world_experience_adapters"].get("adapters") or []
                    if row.get("adapter_id") == "paper_market_strategy_v1"
                ), "not_started"),
            },
            "strategic_capability_academy": {
                "subjects": len(strategic_rows),
                "levels": strategic_level_counts,
                "evidence_records": sum(int(row.get("evidence_records") or 0)
                                        for row in strategic_rows),
                "next_gate": finance_gate,
                "capital_movement_authority": False,
                "external_influence_authority": False,
            },
            "cybersecurity_academy": {
                "subjects": len(cybersecurity_rows),
                "levels": cybersecurity_level_counts,
                "evidence_records": sum(int(row.get("evidence_records") or 0)
                                        for row in cybersecurity_rows),
                "assessment_status": security_adapter_status,
                "external_targets_authorized": False,
                "destructive_actions_authorized": False,
                "range_qualification_passed": data["owned_purple_team_cyber_range"].get("passed") is True,
                "qualified_tool_surface": data["owned_purple_team_cyber_range"].get("tool_surface") or [],
                "range_gate": data["owned_purple_team_cyber_range"].get("gate") or {},
            },
            "prediction_market_academy": {
                "subjects": len(prediction_market_rows),
                "levels": prediction_market_level_counts,
                "evidence_records": sum(int(row.get("evidence_records") or 0)
                                        for row in prediction_market_rows),
                "live_public_status": data["prediction_market_intelligence"].get("status", "not_started"),
                "market_count": (data["prediction_market_intelligence"].get("source_receipt") or {}).get("market_count", 0),
                "platform_counts": (data["prediction_market_intelligence"].get("source_receipt") or {}).get("platform_counts", {}),
                "geographic_eligibility": data["prediction_market_intelligence"].get("geographic_eligibility") or {},
                "gate": data["prediction_market_intelligence"].get("gate") or {},
                "paper_ledger": data["prediction_market_intelligence"].get("paper_ledger") or {},
                "paper_game": data["prediction_market_paper_game"] or {},
                "research": data["prediction_market_research"] or {},
            },
            "execution_model": "verified_adapter_acquired_before_each_new_capability",
            "competence_awarded_by_activation": expertise_runtime.get("competence_awarded_by_activation", False),
            "claim_boundary": (
                "Installed and executing does not mean mastered; competence requires practical transfer, "
                "independent outcomes and delayed retention."
            ),
        },
        "executive": {
            "mode": data["executive_self"].get("mode", "not_started"),
            "identity_immutable": data["executive_self"].get("identity_immutable"),
            "attention": data["executive_self"].get("current_attention"),
            "attention_cycles": len(data["executive_self"].get("attention_history") or []),
            "reflections": len(data["executive_self"].get("reflection_history") or []),
            "commitments": len(data["executive_self"].get("commitments") or {}),
            "work_compositions": len(data["executive_skills"].get("compositions") or []),
            "verified_method_outcomes": sum(
                int(row.get("verified") or 0)
                for row in (data["executive_skills"].get("method_outcomes") or {}).values()
            ),
            "useful_work": data["useful_work"],
        },
        "mastery": {
            "subjects_total": len(subjects), "by_level": by_level,
            "maturity": registry.get("maturity") or {},
            "goals": registry.get("strategic_goal_portfolio") or [],
        },
        "academy": {
            "academy_id": academy.get("academy_id"), "modules": ordered_modules,
            "passed": passed_modules, "total": len(ordered_modules),
            "progress": passed_modules / len(ordered_modules) if ordered_modules else 0.0,
            "active": active_module, "ready": ready_modules,
            "cycles": len(academy.get("cycles") or []),
            "retention_queue": academy.get("retention_queue") or [],
            "complete": academy.get("primary_academy_complete") is True,
            "worker": {
                "status": data["academy_worker"].get("status", "not_started"),
                "attempts": len(data["academy_worker"].get("attempts") or []),
                "consecutive_no_progress": int(data["academy_worker"].get("consecutive_no_progress") or 0),
                "last_progress_epoch": data["academy_worker"].get("last_progress_epoch"),
            },
        },
        "progressive": {
            "summary": progressive_summary,
            "domains": progressive_payload.get("domains") or {},
            "active": progressive_active,
            "contract": progressive_contract,
            "parked_retention": parked_retention,
            "strongest": strongest_progressive,
            "blockers": progressive_payload.get("blockers") or [],
            "levels": progressive_summary.get("levels") or {},
            "executor_registry": service_status.get("progressive_executor_registry") or {},
            "executor_factory": data["executor_factory"],
            "self_improvement": data["self_improvement"],
            "toolchain_acquisition": data["toolchain_acquisition"],
            "system_authority": data["system_authority"],
            "system_capstone": data["system_capstone"],
            "compounding_intelligence": data["compounding_intelligence"],
            "cross_domain_campaigns": data["cross_domain_campaigns"],
            "capability_research_executive": data["capability_research_executive"],
            "autonomous_goal_arbiter": data["autonomous_goal_arbiter"],
            "autonomous_authority_factory": data["autonomous_authority_factory"],
            "resource_cognitive_routing": data["resource_cognitive_routing"],
            "situational_driver": data["situational_driver"],
            "situated_cross_domain_project": data["situated_cross_domain_project"],
            "authority_disagreement": data["authority_disagreement"],
            "objective_family_invention": data["objective_family_invention"],
            "experience_compiler": data["experience_compiler"],
            "hierarchical_missions": data["hierarchical_missions"],
            "method_language_expansion": data["method_language_expansion"],
            "recursive_verifier_atom": data["recursive_verifier_atom"],
            "competency_reconstruction": data["competency_reconstruction"],
            "functional_glyph_lexicon": data["functional_glyph_lexicon"],
            "functional_glyph_compiler": data["functional_glyph_compiler"],
            "functional_glyph_induction": data["functional_glyph_induction"],
            "dual_track_intelligence": data["dual_track_intelligence"],
            "embodied_apprenticeship": data["embodied_apprenticeship"],
            "rgb_belief_apprenticeship": data["rgb_belief_apprenticeship"],
            "rgb_contact_composition": data["rgb_contact_composition"],
            "rgb_articulated_sequence": data["rgb_articulated_sequence"],
            "simulator_disjoint_scaleup": data["simulator_disjoint_scaleup"],
        },
        "curriculum": {
            "cycles": len(curriculum.get("cycles") or []),
            "contracts": len(contracts), "open_executor_requests": open_requests,
            "retention_scheduled": retention,
            "broad_mode": curriculum.get("mode"),
            "broad_parked": not academy.get("primary_academy_complete", False),
            "teacher_calls": curriculum.get("teacher_calls", 0),
        },
        "certificates": certificates,
        "academy_certificates": academy_certificates,
        "glyphs": {
            "passed": glyph_payload.get("passed") is True,
            "total": glyph_gate.get("glyphs", 0), "knowledge": glyph_gate.get("knowledge_glyphs", 0),
            "skills": glyph_gate.get("skill_glyphs", 0), "curriculum": glyph_gate.get("curriculum_glyphs", 0),
            "progressive_records": glyph_gate.get("progressive_evidence_records", 0),
            "progressive_subjects": glyph_gate.get("progressive_subjects_consolidated", 0),
            "reduction": glyph_gate.get("working_memory_reduction", 0.0),
            "provenance": glyph_gate.get("all_provenance_resolves", False),
        },
        "arena": {
            "status": arena.get("status", "not_started"),
            "cycles": len(arena.get("cycles") or []),
            "required_cycles": int(arena_gate.get("minimum_cycles") or 12),
            "elapsed_hours": actual_elapsed,
            "required_hours": float(arena_gate.get("minimum_elapsed_hours") or 24.0),
            "safe": arena_gate.get("all_execution_and_transaction_outcomes_safe"),
            "accepted": arena_gate.get("accepted") is True,
        },
        "consequence_repair": data["consequence_repair"],
        "prospective_outcomes": data["prospective_outcomes"],
        "owner_valued_work": data["owner_valued_work"],
        "open_objectives": data["open_objectives"],
        "method_transfer": data["method_transfer"],
        "aga_registry": data["aga_registry"],
        "cognitive_code": data["cognitive_code"],
        "depth_acceleration": data["depth_acceleration"],
        "competency_bridge": data["competency_bridge"],
        "week_retention": data["week_retention"],
        "recent_results": _recent_results(root),
        "files_available": {name: path.exists() for name, path in paths.items()},
    }
    return snapshot


def _section(title: str, width: int) -> list[str]:
    line = "─" * max(0, width - len(title) - 3)
    return [f" {title} {line}"]


def render_full_lines(snapshot: Mapping[str, Any], width: int = 120) -> list[tuple[str, str]]:
    """Return (style, line) tuples, also usable by the curses UI."""
    width = max(70, width)
    lines: list[tuple[str, str]] = []
    now = dt.datetime.fromtimestamp(snapshot["generated_at"]).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(("header", _clip(f" AION INTELLIGENCE DEVELOPMENT  |  {now}  |  READ-ONLY", width)))
    lines.append(("muted", _clip(f" Workspace: {snapshot['root']}", width)))

    lines.extend(("section", line) for line in _section("LIVE SYSTEMS", width))
    for label, row in snapshot["services"].items():
        if label == "_system":
            disk_free = row.get("disk_free_gib")
            lines.append(("good" if row.get("health") == "healthy" else "warn",
                          f" {'CAPACITY':8}  Disk available · {disk_free if disk_free is not None else 'unknown'} GiB"))
            continue
        health = str(row.get("health") or ("healthy" if row.get("active") else "offline"))
        tone = {"healthy": "good", "waiting": "normal", "degraded": "warn", "offline": "bad"}.get(health, "warn")
        state = {"healthy": "HEALTHY", "waiting": "WAITING", "degraded": "DEGRADED", "offline": "OFFLINE"}.get(health, health.upper())
        lines.append((tone, _clip(f" {state:8}  {label} · {row.get('health_reason', '')}", width)))
    service = snapshot["service_status"]
    age = _age(snapshot["generated_at"] - service["age_seconds"] if service["age_seconds"] is not None else None)
    lines.append(("muted", f" Curriculum service ledger: {service['status']}  | last update {age} ago"))
    moonshot = snapshot.get("open_mission_compounding") or {}
    executor_status = snapshot.get("open_mission_executor") or {}
    if moonshot:
        lines.append(("success" if moonshot.get("cohort_complete_missions", 0) else "warn", _clip(
            f" Open-mission moonshot: {str(moonshot.get('status', 'unknown')).upper()}  | "
            f"Cohorts {moonshot.get('cohort_complete_missions', 0)}/{moonshot.get('mission_count', 0)}  | "
            f"Retention {moonshot.get('verified_retention_count', 0)}  | "
            f"Confirmed repairs {moonshot.get('confirmed_repair_count', 0)}  | "
            f"10x gate {moonshot.get('ten_x_claim_gate_passed', False)}", width)))
        lines.append(("muted", _clip(
            f" Matched executor: {executor_status.get('status', 'waiting')}  | "
            f"False/unsafe promotions: {moonshot.get('false_or_unsafe_promotions', 0)}  | "
            f"Ends: {moonshot.get('ends_at', 'unknown')}", width)))

    executive = snapshot["executive"]
    lines.extend(("section", line) for line in _section("EXECUTIVE SELF", width))
    lines.append(("good" if executive["identity_immutable"] else "warn",
                  f" Mode: {str(executive['mode']).upper()}  | Identity immutable: {executive['identity_immutable']}  | Commitments: {executive['commitments']}"))
    attention = executive.get("attention") or {}
    if attention:
        lines.append(("normal", _clip(f" Attention: {attention.get('summary', attention.get('id', 'unknown'))}", width)))
    lines.append(("muted", f" Attention cycles: {executive['attention_cycles']}  | Reflections: {executive['reflections']}  | Work systems composed: {executive['work_compositions']}  | Verified method outcomes: {executive['verified_method_outcomes']}"))
    useful = executive.get("useful_work") or {}
    if useful:
        outcome = useful.get("outcome") or {}
        lines.append(("success" if useful.get("passed") else "warn", _clip(
            f" Useful autonomous work: {'COMPLETED' if useful.get('passed') else 'REJECTED'}  | "
            f"Project: {(useful.get('selected_project') or {}).get('task_id', 'none')}  | "
            f"Executor coverage {outcome.get('verified_before', 0)} -> {outcome.get('verified_after', 0)}  | "
            f"Next: {(useful.get('next_opportunity') or {}).get('objective', 'not selected')}", width)))

    dual = snapshot["progressive"].get("dual_track_intelligence") or {}
    physical = snapshot["progressive"].get("embodied_apprenticeship") or {}
    visual_physical = snapshot["progressive"].get("rgb_belief_apprenticeship") or {}
    contact_physical = snapshot["progressive"].get("rgb_contact_composition") or {}
    articulated_physical = snapshot["progressive"].get("rgb_articulated_sequence") or {}
    scaleup = snapshot["progressive"].get("simulator_disjoint_scaleup") or {}
    dual_gate = dual.get("gate") or {}
    physical_gate = physical.get("gate") or {}
    lines.extend(("section", line) for line in _section("70/30 INTELLIGENCE PORTFOLIO", width))
    if dual:
        lines.append(("success" if dual.get("passed") else "warn", _clip(
            f" Allocation: practical {dual_gate.get('practical_objectives', 0)}/7 (70%)  | "
            f"embodied {dual_gate.get('embodied_objectives', 0)}/3 (30%)  | "
            f"Committed missions: {dual_gate.get('portfolio_objectives', 0)}  | "
            f"Ready now: {dual_gate.get('ready_now', 0)}  | learning-first: {dual_gate.get('learning_first', 0)}", width)))
        dispatch = dual.get("learning_dispatch") or {}
        if dispatch.get("status") == "progressive_learning_prioritised":
            lines.append(("normal", _clip(
                f" Practical lane working on: {dispatch.get('mission_id')}  | Closing capability: "
                f"{dispatch.get('subject_id')}  | authority remains outcome-gated", width)))
    else:
        lines.append(("muted", " Dual-track portfolio has not produced its first committed generation."))
    if physical:
        lines.append(("success" if physical.get("passed") else "warn", _clip(
            f" Physical authority: {physical_gate.get('backend', 'not installed')} "
            f"{physical_gate.get('backend_version', '')}  | Sealed transfer: "
            f"{physical_gate.get('sealed_transfer_success', 0)}/"
            f"{physical_gate.get('sealed_transfer_worlds', 0)}  | Cold control: "
            f"{physical_gate.get('cold_control_success', 0)}  | "
            f"Pre-action commitments: {physical_gate.get('pre_action_commitments', 0)}", width)))
        lines.append(("good" if physical_gate.get("ood_impossible_world_abstained") else "warn", _clip(
            f" Impossible-world abstention: {physical_gate.get('ood_impossible_world_abstained', False)}  | "
            f"Malicious actions rejected: {physical_gate.get('malicious_actions_rejected', 0)}/"
            f"{physical_gate.get('malicious_actions_total', 0)}  | Unsafe learned worlds: "
            f"{physical_gate.get('unsafe_worlds', 0)}", width)))
    else:
        lines.append(("muted", " MuJoCo embodied apprenticeship has not run yet."))
    if visual_physical:
        visual_gate = visual_physical.get("gate") or {}
        lines.append(("success" if visual_physical.get("passed") else "warn", _clip(
            f" RGB belief-state planning: {visual_physical.get('status', 'UNKNOWN')}  | "
            f"Sealed transfer: {visual_gate.get('sealed_success', 0)}/"
            f"{visual_gate.get('sealed_worlds', 0)} vs cold {visual_gate.get('cold_success', 0)}  | "
            f"Morphologies/cameras/dynamics: {visual_gate.get('morphologies', 0)}/"
            f"{visual_gate.get('camera_variants', 0)}/{visual_gate.get('dynamics_variants', 0)}", width)))
        lines.append(("good" if visual_gate.get("ood_ungroundable_abstained") else "warn", _clip(
            f" RGB only: {visual_gate.get('rgb_only', False)}  | Recurrent belief: "
            f"{visual_gate.get('recurrent_belief_state', False)}  | Multi-step planning: "
            f"{visual_gate.get('multi_step_planning', False)}  | OOD abstention: "
            f"{visual_gate.get('ood_ungroundable_abstained', False)}", width)))
    if contact_physical:
        contact_gate = contact_physical.get("gate") or {}
        capsule = contact_physical.get("stored_skill_capsule") or {}
        lines.append(("success" if contact_physical.get("passed") else "warn", _clip(
            f" Composed RGB contact skill: {contact_physical.get('status', 'UNKNOWN')}  | "
            f"Sealed transfer {contact_gate.get('sealed_success', 0)}/"
            f"{contact_gate.get('sealed_worlds', 0)} vs cold {contact_gate.get('cold_success', 0)}  | "
            f"Causal contact: {contact_gate.get('causal_contact_discovered', False)}  | "
            f"Occlusion recovery: {contact_gate.get('occlusion_recovery', False)}", width)))
        lines.append(("good" if capsule.get("reconstructed") else "warn", _clip(
            f" Stored executable skill: {capsule.get('reconstructed', False)}  | Parent RGB skill: "
            f"{contact_gate.get('parent_skill_reconstructed', False)}  | Restart retained: "
            f"{bool((contact_physical.get('restart') or {}).get('champion_retained', False))}  | "
            f"Unsafe worlds: {contact_gate.get('unsafe_worlds', 0)}", width)))
    if articulated_physical:
        arm_gate = articulated_physical.get("gate") or {}
        arm_capsule = articulated_physical.get("stored_skill_capsule") or {}
        lines.append(("success" if articulated_physical.get("passed") else "warn", _clip(
            f" Articulated RGB sequence skill: {articulated_physical.get('status', 'UNKNOWN')}  | "
            f"Sealed {arm_gate.get('sealed_success', 0)}/{arm_gate.get('sealed_worlds', 0)} "
            f"vs cold {arm_gate.get('cold_success', 0)}  | Targets/world: "
            f"{arm_gate.get('sequential_targets_per_world', 0)}  | Joints: "
            f"{arm_gate.get('articulated_joints', 0)}", width)))
        lines.append(("good" if arm_capsule.get("reconstructed") else "warn", _clip(
            f" Learned topology/model adaptation: {arm_gate.get('visual_model_adaptation', False)}  | "
            f"Occlusion recovery: {arm_gate.get('occlusion_recovery', False)}  | Stored skill: "
            f"{arm_capsule.get('reconstructed', False)}  | Unsafe worlds: {arm_gate.get('unsafe_worlds', 0)}", width)))
    if scaleup:
        lines.append(("good" if scaleup.get("package_ready") else "warn", _clip(
            f" Isaac Lab scale-up: {scaleup.get('status', 'UNKNOWN')}  | Frozen contract: "
            f"{str(scaleup.get('contract_sha256', 'missing'))[:16]}...  | Skill ancestry: "
            f"{scaleup.get('skill_ancestry_count', 0)}  | Arms: "
            f"{len(scaleup.get('experimental_arms') or [])}", width)))
        lines.append(("warn" if not scaleup.get("external_execution_complete") else "success", _clip(
            f" NVIDIA execution complete: {scaleup.get('external_execution_complete', False)}  | "
            f"Promoted: {scaleup.get('promoted', False)}  | Tamper/unsigned rejected: "
            f"{scaleup.get('tamper_rejected', False)}/{scaleup.get('unsigned_rejected', False)}  | "
            f"Waiting for: {', '.join(scaleup.get('blockers') or [])}", width)))

    academy = snapshot["academy"]
    lines.extend(("section", line) for line in _section("COMPLETED FOUNDATION ASSESSMENT ARCHIVE", width))
    lines.append(("good" if academy["passed"] else "normal",
                  f" Programming, Systems & Security  {_bar(academy['progress'], 30)}  "
                  f"({academy['passed']}/{academy['total']} assessment receipts; not competency levels)"))
    lines.append(("muted", _clip(
        f" Archive complete. These receipts seeded the new competency ledger but do not continue running or establish subject level. "
        f"Progressive ledger authoritative: {academy['complete']}", width)))
    worker = academy["worker"]
    lines.append(("muted", _clip(
        f" Historical executor: {worker['status']}  | Archived attempts: {worker['attempts']}  | "
        f"Last foundation activity: {_age(worker['last_progress_epoch'])} ago  | Live work is shown under CURRENT LEARNING", width)))

    progressive = snapshot["progressive"]
    psummary = progressive["summary"]
    active = progressive["active"]
    lines.extend(("section", line) for line in _section("PROGRESSIVE COMPETENCY", width))
    lines.append(("normal", _clip(
        f" Programme: {psummary.get('programme_stage', 'foundation_to_advanced')}  | Minimum target: ADVANCED  | "
        f"Subjects: {psummary.get('subjects', 0)}  | "
        f"Advanced/expert: {psummary.get('advanced_or_expert', 0)}  | "
        f"Evidence records: {psummary.get('evidence_records', 0)}", width)))
    lines.append(("muted", _clip(
        f" Parallel learning lanes: breadth 75% / expert depth 25%  | "
        f"Expert queue: {psummary.get('expert_depth_queue', 0)}  | "
        f"Lane contracts: breadth={psummary.get('breadth_contracts', 0)}, "
        f"depth={psummary.get('depth_contracts', 0)}", width)))
    invalidated = int(psummary.get("invalidated_evidence_records", 0) or 0)
    if invalidated:
        lines.append(("warn", _clip(
            f" Evidence integrity: {invalidated} invalidated historical record(s) retained for audit and excluded from competency scoring", width)))
    if active:
        coverage = active.get("coverage") or {}
        lines.append(("warn" if not active.get("target_reached") else "good", _clip(
            f" Active: {active.get('name')}  | Knowledge: {str(active.get('knowledge_level')).upper()}  | "
            f"Practical: {str(active.get('practical_level')).upper()}  | "
            f"Overall: {str(active.get('display_level')).upper()} -> {str(active.get('target_level')).upper()}", width)))
        lines.append(("muted", _clip(
            f" Coverage: knowledge {float(coverage.get('knowledge', 0))*100:.1f}% / practical "
            f"{float(coverage.get('practical', 0))*100:.1f}%  | Projects: {active.get('projects', 0)}  | "
            f"Debug cases: {active.get('debugging_cases', 0)}  | Transfer: {active.get('transfer_cases', 0)}  | "
            f"Retention: {active.get('retention_cases', 0)}", width)))
        lines.append(("muted", _clip(
            " Subject policy: deepen the active subject toward ADVANCED; rotate on target completion or an explicit blocker. "
            "Mission knowledge gaps may register additional subjects automatically.", width)))
    contract = progressive["contract"]
    if contract:
        requirement = contract.get("requirement") or {}
        due = "not time-gated"
        if requirement.get("not_before_epoch"):
            due_at = dt.datetime.fromtimestamp(float(requirement["not_before_epoch"])).astimezone().strftime("%Y-%m-%d %H:%M %Z")
            due = due_at
        lines.append(("warn", _clip(
            f" Next verified requirement: {requirement.get('kind', 'unknown')} on "
            f"{', '.join(requirement.get('subskills') or [])}", width)))
        lines.append(("warn", _clip(
            f" Requirement authority: {requirement.get('authority', 'unknown')}  | Earliest execution: {due}", width)))
    if progressive["blockers"]:
        external = sum(row.get("status") == "open" and row.get("blocker_type") == "external_practical" for row in progressive["blockers"])
        executor = sum(row.get("status") == "open" and row.get("blocker_type") == "executor_capability" for row in progressive["blockers"])
        lines.append(("warn", f" Programme-wide practical blockers: external={external}  | executor capability gaps={executor}"))
    if progressive["levels"]:
        level_text = "  ".join(f"{key}={value}" for key, value in sorted(progressive["levels"].items()))
        lines.append(("muted", _clip(" Current honest levels: " + level_text, width)))
    executor_registry = progressive.get("executor_registry") or {}
    if executor_registry:
        lines.append(("normal", _clip(
            f" Verified executor coverage: {executor_registry.get('verified_adapters', 0)}/"
            f"{executor_registry.get('subjects_total', 0)} subjects  | "
            f"Catalog gaps: {executor_registry.get('catalog_coverage_gaps', 0)}  | "
            f"Active acquisitions: {executor_registry.get('open_gaps', 0)}  | "
            "Missing adapters park and rotate; unrelated executors are never substituted.", width)))
        for gap in (executor_registry.get("active_acquisitions") or [])[:2]:
            lines.append(("warn", _clip(
                f" Acquiring: {gap.get('subject_name', gap.get('subject_id'))}  | "
                f"{gap.get('family')}  | {gap.get('acquisition_action')}  | "
                f"resume: {gap.get('resume_condition')}", width)))
    factory = progressive.get("executor_factory") or {}
    factory_gate = factory.get("gate") or {}
    if factory:
        lines.append(("success" if factory.get("passed") else "warn", _clip(
            f" Autonomous executor factory: {'PASS' if factory.get('passed') else 'NOT PROMOTED'}  | "
            f"Verified family adapters: {factory_gate.get('verified_family_adapters', 0)}  | "
            f"Authority families: {factory_gate.get('distinct_authority_families', 0)}  | "
            f"Unsupported families abstain: {factory_gate.get('unsupported_family_abstention', False)}", width)))
    improvement = progressive.get("self_improvement") or {}
    if improvement:
        lines.append(("success" if improvement.get("passed") else "warn", _clip(
            f" Cognitive self-improvement: {'PROMOTED' if improvement.get('passed') else 'REJECTED'}  | "
            f"Component: capability router  | Selected: {improvement.get('selected', 'none')}  | "
            f"F1 gain: {100 * float(improvement.get('mean_f1_improvement') or 0):.2f} points  | "
            f"Restart retained: {improvement.get('restart_policy_retained', False)}", width)))
    toolchain = progressive.get("toolchain_acquisition") or {}
    toolchain_gate = toolchain.get("gate") or {}
    if toolchain:
        lines.append(("success" if toolchain.get("passed") else "warn", _clip(
            f" Open toolchain acquisition: {'PASS' if toolchain.get('passed') else 'REJECTED'}  | "
            f"New adapters: {toolchain_gate.get('verified_toolchain_adapters', 0)}  | "
            f"Subskill counterexamples: {toolchain_gate.get('counterexamples_rejected', 0)}/"
            f"{toolchain_gate.get('counterexamples_total', 0)}  | Missing runtimes abstain: "
            f"{toolchain_gate.get('missing_toolchains_abstained', False)}", width)))
    system_authority = progressive.get("system_authority") or {}
    system_gate = system_authority.get("gate") or {}
    if system_authority:
        lines.append(("success" if system_authority.get("passed") else "warn", _clip(
            f" Systems-project authority: {'PASS' if system_authority.get('passed') else 'REJECTED'}  | "
            f"Subject adapters: {system_gate.get('verified_subject_adapters', 0)}  | "
            f"Distinct projects: {system_gate.get('distinct_executable_projects', 0)}  | "
            f"Project faults rejected: {system_gate.get('mapped_project_counterexamples_rejected', 0)}/"
            f"{system_gate.get('mapped_project_counterexamples_total', 0)}", width)))
    capstone = progressive.get("system_capstone") or {}
    capstone_gate = capstone.get("gate") or {}
    if capstone:
        lines.append(("success" if capstone.get("passed") else "warn", _clip(
            f" Cross-system capstone: {'PASS' if capstone.get('passed') else 'REJECTED'}  | "
            f"Mission route exact: {capstone_gate.get('mission_route_exact', False)}  | "
            f"Component transfer: {capstone_gate.get('component_transfer_success', False)}  | "
            f"Integrated faults rejected: {capstone_gate.get('integrated_counterexamples_rejected', 0)}/"
            f"{capstone_gate.get('integrated_counterexamples_total', 0)}", width)))

    compounding = progressive.get("compounding_intelligence") or {}
    compounding_gate = compounding.get("gate") or {}
    if compounding:
        tournament = compounding.get("substrate_tournament") or {}
        lines.append(("success" if compounding.get("passed") else "warn", _clip(
            f" Compounding intelligence: {compounding.get('status', 'UNKNOWN')}  | "
            f"Functional reconstruction: {compounding_gate.get('functional_reconstructions', 0)}/6  | "
            f"Source-disjoint: {compounding_gate.get('source_disjoint_reconstructions', 0)}/6  | "
            f"Integrated campaigns: {compounding_gate.get('active_integrated_campaigns', 0)}/6", width)))
        lines.append(("muted", _clip(
            f" Proposal substrate: {tournament.get('selected', 'not tested')}  | "
            f"Challenger promoted: {tournament.get('challenger_promoted', False)}  | "
            f"Competency awards from control plane: {compounding_gate.get('competency_awards', 0)}", width)))
    campaign_execution = progressive.get("cross_domain_campaigns") or {}
    campaign_gate = campaign_execution.get("gate") or {}
    if campaign_execution:
        lines.append(("success" if campaign_execution.get("passed") else "warn", _clip(
            f" Cross-domain projects: {campaign_execution.get('status', 'UNKNOWN')}  | "
            f"Independent passes: {campaign_gate.get('campaigns_passed', 0)}/6  | "
            f"Authorities: {campaign_gate.get('distinct_authorities', 0)}  | "
            f"Counterexamples: {campaign_gate.get('counterexamples_rejected', 0)}/"
            f"{campaign_gate.get('counterexamples_total', 0)}", width)))
        lines.append(("warn" if not campaign_gate.get("delayed_reconstructions") else "success", _clip(
            f" Delayed capsule reconstruction: {campaign_gate.get('delayed_reconstructions', 0)}/6  | "
            f"Formal retention records: {campaign_gate.get('formal_retention_evidence', 0)}/12  | "
            f"Early retention awards: {campaign_gate.get('retention_awarded_early', 0)}  | "
            f"Next: {campaign_execution.get('next_action', 'unknown')}", width)))

    autonomous_executive = progressive.get("capability_research_executive") or {}
    autonomous_gate = autonomous_executive.get("gate") or {}
    if autonomous_executive:
        lane_counts = autonomous_gate.get("lane_counts") or {}
        lines.append(("success" if autonomous_executive.get("passed") else "warn", _clip(
            f" Autonomous capability/research executive: {autonomous_executive.get('status', 'UNKNOWN')}  | "
            f"Portfolio: {autonomous_gate.get('portfolio_objectives', 0)}  | "
            f"Useful/practice/research: {lane_counts.get('useful_work', 0)}/"
            f"{lane_counts.get('capability_practice', 0)}/{lane_counts.get('cognitive_research', 0)}  | "
            f"Runtime goals: {autonomous_gate.get('canonical_runtime_goals_active', 0)}", width)))
        lines.append(("success" if autonomous_gate.get("cognitive_critic_promoted") else "warn", _clip(
            f" Self-directed cognitive research: critic promoted={autonomous_gate.get('cognitive_critic_promoted', False)}  | "
            f"Real rows: {autonomous_gate.get('critic_real_rows', 0)}  | "
            f"Corrected false failures: {autonomous_gate.get('critic_improvement_rows', 0)}  | "
            f"Hostile/unsupported rejected: {autonomous_gate.get('malicious_or_unsupported_rejected', 0)}/"
            f"{autonomous_gate.get('malicious_or_unsupported_total', 0)}", width)))
        difficulty = max((int(row.get("difficulty_tier") or 1)
                          for row in autonomous_executive.get("portfolio") or []), default=1)
        lines.append(("success", _clip(
            f" Autonomous difficulty: tier {difficulty}/6  | "
            f"Owner-authored project steps: {autonomous_gate.get('owner_authored_project_steps', 0)}  | "
            f"Practice dispatched: {autonomous_gate.get('practice_subject_dispatched', False)}", width)))
        if autonomous_gate.get("method_driven_useful_contracts") is not None:
            lines.append(("success" if autonomous_gate.get("fixed_useful_family_contracts", 0) == 0 else "warn", _clip(
                f" Learned-method portfolio: {autonomous_gate.get('method_driven_useful_contracts', 0)} contracts  | "
                f"Fixed-family contracts: {autonomous_gate.get('fixed_useful_family_contracts', 0)}  | "
                "Goals bind to observable authority semantics", width)))
    goal_arbiter = progressive.get("autonomous_goal_arbiter") or {}
    arbiter_gate = goal_arbiter.get("gate") or {}
    if goal_arbiter:
        lines.append(("success" if goal_arbiter.get("passed") else "warn", _clip(
            f" Autonomous goal consequences: {arbiter_gate.get('consequence_confirmed', 0)}/"
            f"{arbiter_gate.get('autonomous_goals', 0)} confirmed  | "
            f"Remaining: {arbiter_gate.get('remaining', 0)}  | Receipt integrity: "
            f"{arbiter_gate.get('receipt_integrity', False)}", width)))
    authority_factory = progressive.get("autonomous_authority_factory") or {}
    authority_gate = authority_factory.get("gate") or {}
    if authority_factory:
        lines.append(("success" if authority_factory.get("passed") else "warn", _clip(
            f" Cross-domain authority factory: {authority_factory.get('status', 'UNKNOWN')}  | "
            f"Retained authorities: {authority_gate.get('retained_authorities', 0)}  | "
            f"Source-disjoint receipts: {authority_gate.get('source_disjoint_receipts', 0)}  | "
            f"Inadequate candidates rejected: {authority_gate.get('inadequate_candidates_rejected', 0)}  | "
            f"Ambient authority expansions: {authority_gate.get('ambient_authority_expansions', 0)}", width)))
    resource_route = progressive.get("resource_cognitive_routing") or {}
    resource_gate = resource_route.get("gate") or {}
    if resource_route:
        lines.append(("success" if resource_route.get("passed") else "warn", _clip(
            f" Resource-aware cognition: {resource_route.get('status', 'UNKNOWN')}  | "
            f"Light transfers: {resource_gate.get('legitimate_transfers', 0)}/"
            f"{resource_gate.get('legitimate_total', 0)}  | Protected full cognition: "
            f"{resource_gate.get('protected_full_cognition', 0)}/{resource_gate.get('protected_total', 0)}  | "
            f"Spoofs rejected: {resource_gate.get('spoofed_routes_rejected', 0)}/{resource_gate.get('spoofed_total', 0)}", width)))
    situation = progressive.get("situational_driver") or {}
    situation_gate = situation.get("gate") or {}
    if situation:
        driver = ((situation.get("situation") or {}).get("current_driver") or {})
        lines.append(("success" if situation.get("passed") else "warn", _clip(
            f" Situational executive: {situation.get('status', 'UNKNOWN')}  | "
            f"Driver: {driver.get('need_id', 'none')}  | Obligations: {situation_gate.get('active_obligations', 0)}  | "
            f"Advanced/expert resources: {situation_gate.get('advanced_or_expert_resources', 0)}  | "
            f"Terminal mutations: {situation_gate.get('terminal_goal_mutations', 0)}", width)))
    situated_project = progressive.get("situated_cross_domain_project") or {}
    project_gate = situated_project.get("gate") or {}
    if situated_project:
        lines.append(("success" if situated_project.get("passed") else "warn", _clip(
            f" Situated cross-domain projects: {situated_project.get('status', 'UNKNOWN')}  | "
            f"Later confirmed: {project_gate.get('later_confirmed_projects', 0)}/"
            f"{project_gate.get('projects_created', 0)}  | Capability bundle: "
            f"{project_gate.get('current_capability_bundle', 0)}  | Fresh domain receipts: "
            f"{project_gate.get('fresh_domain_evidence_receipts', 0)}", width)))
    disagreement = progressive.get("authority_disagreement") or {}
    disagreement_gate = disagreement.get("gate") or {}
    if disagreement:
        lines.append(("success" if disagreement.get("passed") else "warn", _clip(
            f" Authority-disagreement diagnosis: {disagreement.get('status', 'UNKNOWN')}  | "
            f"Receipts: {disagreement_gate.get('diagnostic_receipts', 0)}  | "
            f"Failure families: {disagreement_gate.get('diagnostic_families', 0)}/4  | "
            f"Unsafe candidates rejected: {disagreement_gate.get('unsafe_candidates_rejected', 0)}  | "
            f"Wrong self-repair routes: {disagreement_gate.get('wrong_internal_repair_routes', 0)}", width)))
    family_invention = progressive.get("objective_family_invention") or {}
    family_gate = family_invention.get("gate") or {}
    if family_invention:
        lines.append(("success" if family_invention.get("passed") else "warn", _clip(
            f" Open objective-family invention: {family_invention.get('status', 'UNKNOWN')}  | "
            f"Family: {family_invention.get('invented_family') or 'not yet earned'}  | "
            f"Receipts: {family_gate.get('invented_family_receipts', 0)}  | "
            f"Source-disjoint transfers: {family_gate.get('source_disjoint_transfers', 0)}  | "
            f"Existing-family overwrites: {family_gate.get('existing_family_overwrites', 0)}", width)))
    experience_compiler = progressive.get("experience_compiler") or {}
    experience_gate = experience_compiler.get("gate") or {}
    if experience_compiler:
        lines.append(("success" if experience_compiler.get("passed") else "warn", _clip(
            f" Experience-compiled project intelligence: {experience_compiler.get('status', 'UNKNOWN')}  | "
            f"Sealed projects: {experience_gate.get('sealed_executable_outcomes_passed', 0)}/"
            f"{experience_gate.get('sealed_projects', 0)}  | Coverage multiplier: "
            f"{experience_gate.get('coverage_multiplier_over_first_open_family', 0)}x  | "
            f"Cold-search reduction: {100 * float(experience_gate.get('attempt_reduction_vs_cold', 0)):.1f}%", width)))
        lines.append(("success" if experience_gate.get("ood_abstention") else "warn", _clip(
            f" Retained methods: {experience_gate.get('retained_method_prototypes', 0)} from "
            f"{experience_gate.get('development_projects', 0)} prior projects  | "
            f"Training rereads during sealed: {experience_gate.get('training_artifacts_reread_during_sealed', 0)}  | "
            f"Answer-book control: {experience_gate.get('answer_book_control_success', 0)}  | "
            f"OOD abstention: {experience_gate.get('ood_abstention', False)}", width)))
        lines.append(("success" if experience_gate.get("prospective_later_receipts") else "warn", _clip(
            f" Tier-6 prospective compiler: precommitments={experience_gate.get('prospective_precommitments', 0)}  | "
            f"Later receipts={experience_gate.get('prospective_later_receipts', 0)}  | "
            "Historical reconstruction alone cannot close tier 6", width)))
    missions = progressive.get("hierarchical_missions") or {}
    mission_gate = missions.get("gate") or {}
    if missions:
        lines.append(("success" if missions.get("passed") else "warn", _clip(
            f" Hierarchical mission intelligence: {missions.get('status', 'UNKNOWN')}  | "
            f"Missions: {mission_gate.get('missions', 0)}  | Milestones: {mission_gate.get('total_milestones', 0)}  | "
            f"Capability-learning prerequisites: {mission_gate.get('learning_dependencies_inserted', 0)}  | "
            f"Ready runtime leaves: {mission_gate.get('ready_leaf_goals_published', 0)}", width)))
        lines.append(("success" if mission_gate.get("premature_external_actions", 0) == 0 else "warn", _clip(
            f" Goal-chain authority: measurable work={mission_gate.get('measurable_work_coverage', 0)}/"
            f"{mission_gate.get('work_nodes', 0)}  | Recovery branches={mission_gate.get('recovery_coverage', 0)}/"
            f"{mission_gate.get('work_nodes', 0)}  | Human-gated external actions="
            f"{mission_gate.get('approval_gated_external_actions', 0)}", width)))
    method_expansion = progressive.get("method_language_expansion") or {}
    method_gate = method_expansion.get("gate") or {}
    if method_expansion:
        method = method_expansion.get("method") or {}
        lines.append(("success" if method_expansion.get("passed") else "warn", _clip(
            f" Open method-language expansion: {method_expansion.get('status', 'UNKNOWN')}  | "
            f"Invented: {method.get('method_id', 'waiting')}  | Atoms: {len(method.get('ast') or [])}  | "
            f"Source-disjoint transfers: {method_gate.get('source_disjoint_transfers', 0)}  | "
            f"Counterexamples: {method_gate.get('counterexamples_rejected', 0)}/"
            f"{method_gate.get('counterexamples_total', 0)}", width)))

    domains = sorted((progressive.get("domains") or {}).values(),
                     key=lambda row: (int(row.get("tier") or 3), str(row.get("name", ""))))
    lines.extend(("section", line) for line in _section("TOP-LEVEL APPRENTICESHIP CURRICULUM", width))
    if domains:
        complete = sum(bool(row.get("target_reached")) for row in domains)
        lines.append(("normal", f" Broad missions: {len(domains)}  | Complete at target: {complete}  | Every mission expands through all declared leaf subjects and subskills"))
        active_id = (progressive.get("active") or {}).get("subject_id")
        for tier in (1, 2, 3):
            rows = [row for row in domains if int(row.get("tier") or 3) == tier]
            summary = "  ·  ".join(
                f"{row.get('name')} {row.get('subjects_at_target', 0)}/{row.get('subject_count', 0)}"
                + ("*" if active_id in (row.get("subjects") or []) else "")
                for row in rows
            )
            lines.append(("warn" if any(active_id in (row.get("subjects") or []) for row in rows) else "muted",
                          _clip(f" Tier {tier}: {summary}", width)))
        lines.append(("muted", " * contains the currently active leaf subject"))
    else:
        lines.append(("muted", " Curriculum hierarchy awaiting the next service snapshot."))

    lines.extend(("section", line) for line in _section("LEGACY CAPABILITY REGISTRY (PRE-PROGRESSIVE)", width))
    mastery = snapshot["mastery"]
    maturity = mastery["maturity"]
    lines.append(("muted", _clip(
        " Retained for provenance only. Labels below are historical bounded descriptors; PROGRESSIVE COMPETENCY is authoritative.", width)))
    lines.append(("muted", f" Historical registry only: {mastery['subjects_total']} entries  | It does not select or score current learning."))
    for level in LEVEL_ORDER:
        subjects = mastery["by_level"].get(level) or []
        if not subjects:
            continue
        names = ", ".join(row["name"] for row in subjects)
        style = "good" if level in {"mastered", "expert", "proficient_bounded"} else (
            "warn" if level == "learning" else "muted")
        lines.append((style, _clip(f" {LEVEL_LABEL[level]:22} {len(subjects):2}  {names}", width)))

    lines.extend(("section", line) for line in _section("EVIDENCE RECEIPTS & RETENTION", width))
    if snapshot["academy_certificates"]:
        for certificate in snapshot["academy_certificates"]:
            lines.append(("normal", f" EVIDENCE PASS  {certificate['name']}  | records: {certificate['evidence_count']}  | not a subject level"))
    else:
        lines.append(("muted", " No academy certificates recorded."))
    for certificate in snapshot["certificates"]:
        lines.append(("normal", _clip(
            f" Receipt: {certificate.get('subject', 'unknown')} | {certificate.get('level', 'unknown')} | "
            f"retention: {certificate.get('elapsed_retention_status', 'unknown')} | mastered: {certificate.get('mastery_claim_authorized', False)}",
            width,
        )))

    lines.extend(("section", line) for line in _section("LEGACY CURRICULUM & BLOCKERS", width))
    curriculum = snapshot["curriculum"]
    lines.append(("normal", f" Contracts: {curriculum['contracts']}  | Curriculum cycles: {curriculum['cycles']}  | Teacher calls: {curriculum['teacher_calls']}"))
    lines.append(("normal", f" Retention tests scheduled: {len(curriculum['retention_scheduled'])}  | Open broad executor requests: {len(curriculum['open_executor_requests'])}"))
    broad = snapshot["service_status"].get("progressive_competency") or {}
    broad_action = (broad.get("cycle") or {}).get("action") or {}
    action = broad_action if snapshot["academy"].get("complete") and broad_action else (
        snapshot["service_status"].get("academy_action") or {}
    )
    if action:
        target = action.get("subject_id") or action.get("module") or action.get("module_id") or "programme"
        lines.append(("warn", _clip(f" Current blocker/action: {target} -> {action.get('status', 'unknown')}", width)))
    if curriculum["open_executor_requests"]:
        lines.append(("muted", " Legacy one-pass requests are retained for audit but superseded by progressive competency contracts."))

    glyphs = snapshot["glyphs"]
    lines.extend(("section", line) for line in _section("COMPRESSED INTELLIGENCE", width))
    lines.append(("good" if glyphs["passed"] else "warn",
                  f" Glyphs: {glyphs['total']}  | Knowledge: {glyphs['knowledge']}  | Skills: {glyphs['skills']}  | Curriculum: {glyphs['curriculum']}"))
    lines.append(("normal", _clip(
        f" Progressive consolidation: {glyphs.get('progressive_records', 0)} verified evidence records across "
        f"{glyphs.get('progressive_subjects', 0)} subjects  | Glyphs are bounded atoms, not mastery claims", width)))
    lines.append(("good" if glyphs["provenance"] else "bad",
                  f" Active-memory reduction: {glyphs['reduction'] * 100:.2f}%  | Provenance resolves: {glyphs['provenance']}"))

    arena = snapshot["arena"]
    lines.extend(("section", line) for line in _section("LONG-DURATION EVIDENCE", width))
    cycle_progress = arena["cycles"] / max(1, arena["required_cycles"])
    time_progress = arena["elapsed_hours"] / max(0.001, arena["required_hours"])
    required_cycles = min(arena["cycles"], arena["required_cycles"])
    additional_cycles = max(0, arena["cycles"] - arena["required_cycles"])
    additional_text = f" (+{additional_cycles} additional observations)" if additional_cycles else ""
    lines.append(("normal", f" Arena v15 cycles  {_bar(cycle_progress, 24)}  "
                            f"{required_cycles}/{arena['required_cycles']} required{additional_text}"))
    lines.append(("normal", f" Elapsed time      {_bar(time_progress, 24)}  {arena['elapsed_hours']:.2f}/{arena['required_hours']:.0f}h"))
    lines.append(("good" if arena["safe"] else "warn", f" Status: {arena['status']}  | Safe outcomes: {arena['safe']}  | Promoted: {arena['accepted']}"))

    consequence = snapshot.get("consequence_repair") or {}
    consequence_gate = consequence.get("gate") or {}
    lines.extend(("section", line) for line in _section("CROSS-DOMAIN CONSEQUENCE & SELF-REPAIR", width))
    if consequence:
        lines.append(("good" if consequence.get("passed") else "warn", _clip(
            f" Consequence loop: {'PROMOTED' if consequence.get('passed') else 'COLLECTING'}  | "
            f"Natural failures closed: {consequence_gate.get('consequence_confirmed_repairs', 0)}/"
            f"{consequence_gate.get('natural_internal_failure_episodes', 0)}  | "
            f"Pending: {consequence_gate.get('repairs_currently_pending_later_consequence', 0)}  | "
            f"Internal domains: {consequence_gate.get('distinct_internal_domains', 0)}  | "
            f"External outcomes: {consequence_gate.get('independently_committed_external_outcomes', 0)}", width)))
        lines.append(("good" if not consequence_gate.get("external_changes_misrouted_to_repair") else "bad", _clip(
            f" World changes kept out of self-repair: {consequence_gate.get('external_world_changes', 0)}  | "
            f"Later distinct-contract confirmations: {consequence_gate.get('later_distinct_contract_confirmations', 0)}  | "
            f"Unsafe writes: {consequence_gate.get('unsafe_live_writes', 0)}", width)))
    else:
        lines.append(("muted", " Consequence-confirmed repair watcher has not produced its first receipt."))

    prospective = snapshot.get("prospective_outcomes") or {}
    prospective_gate = prospective.get("gate") or {}
    lines.extend(("section", line) for line in _section("PROSPECTIVE INDEPENDENT-OUTCOME OPERATION", width))
    if prospective:
        lines.append(("good" if prospective.get("passed") else "warn", _clip(
            f" Status: {prospective.get('status', 'COLLECTING')}  | "
            f"Precommitted cycles: {prospective_gate.get('prospective_cycles', 0)}/"
            f"{prospective_gate.get('minimum_cycles', 0)}  | "
            f"Authority families: {prospective_gate.get('independent_authority_families', 0)}  | "
            f"Scored forecasts: {prospective_gate.get('scored_forecasts', 0)}", width)))
        lines.append(("normal", _clip(
            f" Forecast accuracy: {100 * float(prospective_gate.get('forecast_accuracy', 0)):.1f}%  | "
            f"Elapsed: {float(prospective_gate.get('elapsed_seconds', 0))/60:.1f}/"
            f"{float(prospective_gate.get('minimum_elapsed_seconds', 0))/60:.0f}m  | "
            f"Owner interventions: {prospective_gate.get('owner_interventions', 0)}  | "
            f"World events misrouted to self-repair: {prospective_gate.get('external_events_misrouted_to_self_repair', 0)}", width)))
    else:
        lines.append(("muted", " First precommitted public-outcome cycle has not run yet."))

    owner_work = snapshot.get("owner_valued_work") or {}
    owner_gate = owner_work.get("gate") or {}
    lines.extend(("section", line) for line in _section("OWNER-VALUED WORK WITH DELAYED ACCOUNTABILITY", width))
    if owner_work:
        lines.append(("good" if owner_work.get("passed") else "warn", _clip(
            f" Status: {owner_work.get('status')}  | Generations confirmed: "
            f"{owner_gate.get('consequence_confirmed_generations', 0)}/"
            f"{owner_gate.get('minimum_generations', 0)}  | "
            f"Artifacts produced: {owner_gate.get('owner_valued_artifacts', 0)}  | "
            f"Work lanes: {owner_gate.get('cross_domain_work_lanes', 0)}", width)))
        lines.append(("normal", _clip(
            f" Research: {100*float(owner_gate.get('research_success_rate', 0)):.0f}%  | "
            f"Software: {100*float(owner_gate.get('software_success_rate', 0)):.0f}%  | "
            f"Data decisions: {100*float(owner_gate.get('data_decision_success_rate', 0)):.0f}%  | "
            f"Executive receipts: {owner_gate.get('verified_executive_work_outcomes', 0)}  | "
            f"Owner interventions: {owner_gate.get('owner_interventions', 0)}", width)))
    else:
        lines.append(("muted", " No delayed-accountability work generation has started."))

    open_objectives = snapshot.get("open_objectives") or {}
    open_gate = open_objectives.get("gate") or {}
    active_objective = open_objectives.get("active_objective") or {}
    lines.extend(("section", line) for line in _section("VARIED NORTH-STAR OBJECTIVE ACQUISITION", width))
    if open_objectives:
        lines.append(("good" if open_objectives.get("passed") else "warn", _clip(
            f" Status: {open_objectives.get('status')}  | Later-confirmed: "
            f"{open_gate.get('later_confirmed', 0)}/{open_gate.get('minimum_objectives', 0)}  | "
            f"Unique objectives: {open_gate.get('unique_objectives', 0)}  | "
            f"Families exercised: {open_gate.get('objective_families', 0)}/{open_gate.get('required_objective_families', 3)}  | "
            f"Weakest family: {100*float(open_gate.get('weakest_family_success', 0)):.0f}%  | "
            f"Shortest authority delay: {float(open_gate.get('minimum_observed_authority_delay_seconds', 0)):.0f}s", width)))
        if active_objective:
            lines.append(("normal", _clip(
                f" Working objective: {active_objective.get('family')} — {active_objective.get('objective')}  | "
                f"Awaiting: {active_objective.get('success_criterion')}", width)))
        lines.append(("normal", _clip(
            f" Executive outcomes: {open_gate.get('executive_outcomes_recorded', 0)}  | "
            f"Owner interventions: {open_gate.get('owner_interventions', 0)}  | "
            f"Unsafe writes: {open_gate.get('unsafe_live_writes', 0)}", width)))
    else:
        lines.append(("muted", " The open objective controller has not selected its first project."))

    transfer = snapshot.get("method_transfer") or {}
    transfer_gate = transfer.get("gate") or {}
    lines.extend(("section", line) for line in _section("CROSS-DOMAIN METHOD TRANSFER", width))
    if transfer:
        lines.append(("good" if transfer.get("passed") else "warn", _clip(
            f" Status: {transfer.get('status')}  | Verified transfers: "
            f"{transfer_gate.get('verified_transfers', 0)}/{transfer_gate.get('required_transfers', 0)}  | "
            f"Source domains: {transfer_gate.get('source_domains', 0)}  | Target domains: {transfer_gate.get('target_domains', 0)}  | "
            f"Mean attempt reduction vs cold: {100*float(transfer_gate.get('mean_attempt_reduction', 0)):.1f}%", width)))
        lines.append(("muted", _clip(" Internal controlled evidence: task definitions and candidate order remain development-controlled.", width)))

    cognitive_code = snapshot.get("cognitive_code") or {}
    cognitive_gate = cognitive_code.get("gate") or {}
    lines.extend(("section", line) for line in _section("LATER-CONFIRMED COGNITIVE CODE CHALLENGER", width))
    if cognitive_code:
        lines.append(("good" if cognitive_code.get("passed") else "warn", _clip(
            f" Status: {cognitive_code.get('status')}  | Natural collapse detected: "
            f"{bool(cognitive_gate.get('natural_route_collapse_detected'))}  | "
            f"Later projects: {cognitive_gate.get('later_confirmed_projects', 0)}/3  | "
            f"Distinct methods: {cognitive_gate.get('later_distinct_methods', 0)}/3  | "
            f"Champion preserved: {bool(cognitive_gate.get('champion_source_preserved'))}", width)))
        lines.append(("normal", _clip(
            f" Malicious code rejected: {cognitive_gate.get('malicious_candidates_rejected', 0)}/6  | "
            f"Later-confirmed improvements: {cognitive_gate.get('later_confirmed_improvements', 0)}/1  | "
            f"Unsafe writes: {cognitive_gate.get('unsafe_live_writes', 0)}", width)))

    depth = snapshot.get("depth_acceleration") or {}
    bridge = snapshot.get("competency_bridge") or {}
    lines.extend(("section", line) for line in _section("CROSS-DOMAIN DEPTH CAMPAIGN", width))
    if depth:
        depth_gate = depth.get("gate") or {}
        lines.append(("good" if depth.get("passed") else "warn", _clip(
            f" Status: {depth.get('status')}  | Advanced targets: {depth_gate.get('advanced_targets', 0)}/6 across "
            f"{depth_gate.get('qualitatively_distinct_families', 0)}/6 families  | Expert lane: "
            f"{depth_gate.get('expert_targets', 0)}/2", width)))
        target_text = ", ".join(
            f"{row.get('name')}={str(row.get('current_level')).upper()}"
            for row in (depth.get("targets") or [])
        )
        lines.append(("normal", _clip(" Targets: " + target_text, width)))
    if bridge:
        bridge_gate = bridge.get("gate") or {}
        lines.append(("good" if bridge.get("passed") else "warn", _clip(
            f" Useful-work bridge: {bridge_gate.get('subjects_bridged', 0)}/{bridge_gate.get('required_subjects', 4)} subjects  | "
            f"Hash-reverified records: {bridge_gate.get('artifact_hash_checks_passed', 0)}  | "
            f"Retention awarded early: {bridge_gate.get('retention_evidence_awarded', 0)}", width)))

    aga = snapshot.get("aga_registry") or {}
    aga_summary = aga.get("summary") or {}
    aga_gates = aga.get("gates") or {}
    lines.extend(("section", line) for line in _section("AUTONOMOUS GENERAL APPRENTICE EVIDENCE", width))
    if aga:
        scope_profiles = aga.get("scope_profiles") or {}
        full_scope = scope_profiles.get("full_aga") or {}
        technical_scope = scope_profiles.get("technical_aga") or {}
        lines.append(("good" if aga.get("authorized") else "warn", _clip(
            f" AGA authorization: {str(bool(aga.get('authorized'))).upper()}  | Earned gates: "
            f"{aga_summary.get('passed', 0)}/{aga_summary.get('total', 0)}  | "
            f"Advanced competencies: {len(aga_summary.get('advanced_subjects') or [])}/6  | "
            f"Expert competencies: {len(aga_summary.get('expert_subjects') or [])}/2", width)))
        if scope_profiles:
            lines.append(("good" if technical_scope.get("authorized") else "normal", _clip(
                f" Scope accounting: FULL {full_scope.get('passed', 0)}/{full_scope.get('total', 0)}  | "
                f"TECHNICAL {technical_scope.get('passed', 0)}/{technical_scope.get('total', 0)}  | "
                "Technical scope explicitly excludes social/creative competence.", width)))
        lines.append(("normal", _clip(
            f" Projects: {(aga_gates.get('later_confirmed_projects') or {}).get('observed', 0):g}/20  | "
            f"Authorities: {(aga_gates.get('authority_families') or {}).get('observed', 0):g}/5  | "
            f"Method transfers: {(aga_gates.get('method_transfers') or {}).get('observed', 0):g}/3  | "
            f"Natural repairs: {(aga_gates.get('natural_self_repairs') or {}).get('observed', 0):g}/3  | "
            f"Retention: {float((aga_gates.get('week_retention') or {}).get('observed', 0)):.2f}/7 days", width)))
        week = snapshot.get("week_retention") or {}
        if week:
            lines.append(("good" if week.get("passed") else "muted", _clip(
                f" Week-end protected challenge: {week.get('status')}  | "
                f"Precommitment: {str((week.get('contract') or {}).get('commitment', ''))[:16]}…  | "
                "Future task seed is unavailable until the qualifying later outcome.", width)))
        blocked = [row["name"] for row in aga_gates.values() if row.get("status") == "blocked"]
        if blocked:
            lines.append(("warn", _clip(f" Externally blocked: {', '.join(blocked)}", width)))

    atom = snapshot["progressive"].get("recursive_verifier_atom") or {}
    reconstruction = snapshot["progressive"].get("competency_reconstruction") or {}
    functional_lexicon = snapshot["progressive"].get("functional_glyph_lexicon") or {}
    functional_compiler = snapshot["progressive"].get("functional_glyph_compiler") or {}
    functional_induction = snapshot["progressive"].get("functional_glyph_induction") or {}
    lines.extend(("section", line) for line in _section("OPEN COMPETENCY RECONSTRUCTION", width))
    if functional_lexicon:
        lex_gate = functional_lexicon.get("gate") or {}
        lines.append(("good" if functional_lexicon.get("passed") else "warn", _clip(
            f" Functional Glyph Lexicon: {functional_lexicon.get('status')}  | "
            f"Nodes {lex_gate.get('nodes', 0)} / edges {lex_gate.get('edges', 0)}  | "
            f"Knowledge types {lex_gate.get('node_types', 0)} / relation types {lex_gate.get('relation_types', 0)}  | "
            f"Procedural capsules {lex_gate.get('functional_capsules_reconstructed', 0)}/{lex_gate.get('functional_capsules_total', 0)}", width)))
    if functional_compiler:
        compiler_gate = functional_compiler.get("gate") or {}
        lines.append(("good" if functional_compiler.get("passed") else "warn", _clip(
            f" Functional method compiler: {functional_compiler.get('status')}  | Semantic operators "
            f"{compiler_gate.get('semantic_operators_compiled', 0)}  | Source-disjoint transfer "
            f"{str(bool(compiler_gate.get('source_disjoint_transfer'))).upper()}  | Corrupt programs rejected "
            f"{compiler_gate.get('corrupted_or_unsafe_programs_rejected', 0)}/{compiler_gate.get('corrupted_or_unsafe_programs_total', 0)}", width)))
    if functional_induction:
        induction_gate = functional_induction.get("gate") or {}
        lines.append(("good" if functional_induction.get("passed") else "warn", _clip(
            f" Autonomous functional-memory induction: {functional_induction.get('status')}  | "
            f"Verified procedures {induction_gate.get('induced_procedures_reconstructed', 0)}/"
            f"{induction_gate.get('verified_trajectories_induced', 0)}  | Mixed-domain compositions "
            f"{induction_gate.get('cross_domain_compositions_passed', 0)}/"
            f"{induction_gate.get('cross_domain_compositions_total', 0)}  | Memory-qualified "
            f"Advanced/Expert {induction_gate.get('advanced_memory_qualified', 0)}/"
            f"{induction_gate.get('expert_memory_qualified', 0)}  | Competency awards "
            f"{induction_gate.get('competency_awards', 0)}", width)))
    if atom:
        atom_gate = atom.get("gate") or {}
        lines.append(("good" if atom.get("passed") else "warn", _clip(
            f" Recursive verifier atom: {atom.get('status')}  | Artifact families "
            f"{atom_gate.get('source_disjoint_execution', 0)}/{atom_gate.get('artifact_families', 0)}  | "
            f"Counterexamples {atom_gate.get('counterexamples_rejected', 0)}/{atom_gate.get('counterexamples_total', 0)}  | "
            f"Ambient authority expansions {atom_gate.get('ambient_authority_expansions', 0)}", width)))
    if reconstruction:
        trial_gate = reconstruction.get("gate") or {}
        style = "good" if reconstruction.get("passed") else "warn"
        lines.append((style, _clip(
            f" Fresh integrated competency trial: {reconstruction.get('status')}  | "
            f"Artifacts {trial_gate.get('artifacts_passed', 0)}/{trial_gate.get('reconstruction_explanation_application_artifacts', 0)}  | "
            f"Claimed subjects sampled {trial_gate.get('claimed_advanced_or_expert_subjects_tested', 0)}  | "
            f"Malicious candidates rejected {trial_gate.get('malicious_candidates_rejected', 0)}/{trial_gate.get('malicious_candidates_total', 0)}", width)))
        failed = [name for name, row in ((reconstruction.get("final_evaluation") or {}).get("artifacts") or {}).items()
                  if not row.get("passed")]
        if failed:
            lines.append(("warn", _clip(
                " Non-promotion is authoritative. Failed fresh reconstructions: " + ", ".join(failed) +
                ". Existing registry levels remain historical evidence, not a substitute for this test.", width)))

    # Repeat the live competency state near the footer. Operators commonly
    # keep the dashboard scrolled to the newest results, so the authoritative
    # current work must remain visible without returning to the first page.
    lines.extend(("section", line) for line in _section("CURRENT LEARNING (AUTHORITATIVE)", width))
    current = snapshot["progressive"].get("active") or {}
    if current:
        lines.append(("warn" if not current.get("target_reached") else "good", _clip(
            f" Working now: {current.get('name')}  | Knowledge {str(current.get('knowledge_level')).upper()}  | "
            f"Practical {str(current.get('practical_level')).upper()}  | Overall {str(current.get('overall_level')).upper()}", width)))
        coverage = current.get("coverage") or {}
        lines.append(("normal", _clip(
            f" Live evidence: {current.get('evidence_records', 0)} records / {current.get('trials', 0)} trials  | "
            f"Coverage K {float(coverage.get('knowledge', 0))*100:.0f}% / P {float(coverage.get('practical', 0))*100:.0f}%  | "
            f"Projects {current.get('projects', 0)}/5  | Debugging {current.get('debugging_cases', 0)}/3  | "
            f"Transfer {current.get('transfer_cases', 0)}/2  | Retention {current.get('retention_cases', 0)}/1", width)))
        current_contract = snapshot["progressive"].get("contract") or {}
        requirement = current_contract.get("requirement") or {}
        executor_registry = snapshot["progressive"].get("executor_registry") or {}
        available_executors = set(executor_registry.get("available_subjects") or [])
        executor_available = current.get("subject_id") in available_executors
        not_before = requirement.get("not_before_epoch")
        if requirement and not_before and time.time() < float(not_before):
            due = dt.datetime.fromtimestamp(float(not_before)).astimezone().strftime("%Y-%m-%d %H:%M %Z")
            lines.append(("muted", _clip(
                f" Current state: WAITING FOR DELAYED RETENTION  | Automatically resumes at {due}; no replay before then.",
                width)))
        elif requirement and executor_available:
            lines.append(("good", _clip(
                " Current state: EXECUTING WITH VERIFIED ADAPTER  | Evidence advances only after outcome checks pass.",
                width)))
            lines.append(("normal", _clip(
                f" Current activity: {requirement.get('kind', 'unknown')} — {', '.join(requirement.get('subskills') or [])}", width)))
        elif requirement:
            uncovered = next(
                (row for row in executor_registry.get("uncovered_subjects") or []
                 if row.get("subject_id") == current.get("subject_id")), {}
            )
            lines.append(("warn", _clip(
                " Current state: EXECUTOR ACQUISITION REQUIRED — selected next, but not currently earning evidence.",
                width)))
            lines.append(("warn", _clip(
                f" Required adapter: {uncovered.get('family', 'subject-specific outcome authority')}  | "
                "The subject will park and the curriculum will rotate rather than stall.", width)))
    else:
        lines.append(("muted", " No active progressive subject."))
    parked = snapshot["progressive"].get("parked_retention") or []
    for row in parked[:3]:
        requirement = row.get("requirement") or {}
        due = dt.datetime.fromtimestamp(float(requirement["not_before_epoch"])).astimezone().strftime("%Y-%m-%d %H:%M %Z")
        lines.append(("muted", _clip(
            f" Parked delayed test: {row.get('subject_name', row.get('subject_id', 'unknown'))}  | "
            f"automatically resumes after {due}; other learning continues", width)))
    strongest = snapshot["progressive"].get("strongest") or []
    if strongest:
        summary = ", ".join(
            f"{row.get('name')}={str(row.get('overall_level')).upper()}"
            + (f" (knowledge {str(row.get('knowledge_level')).upper()})"
               if row.get("knowledge_level") != row.get("overall_level") else "")
            for row in strongest[:4]
        )
        lines.append(("normal", _clip(" Highest evidenced competencies: " + summary, width)))

    lines.extend(("section", line) for line in _section("RECENT VERIFIED DEVELOPMENT", width))
    for row in snapshot["recent_results"]:
        outcome = row.get("outcome") or ("PASS" if row["passed"] else "FAIL")
        style = "good" if outcome == "PASS" else "warn" if outcome == "RUNNING" else "bad"
        lines.append((style, _clip(f" {outcome:7}  {_age(row['created_epoch'])} ago  {row['procedure_id']}", width)))

    lines.append(("footer", " q quit | r refresh | arrows/PgUp/PgDn scroll | g top | G bottom "))
    return lines


def _local_time(value: str | None) -> str:
    if not value:
        return "not scheduled"
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d %b %H:%M %Z")
    except ValueError:
        return str(value)


def render_lines(snapshot: Mapping[str, Any], width: int = 120) -> list[tuple[str, str]]:
    """Render the focused campaign control panel used by default."""
    width = max(70, width)
    lines: list[tuple[str, str]] = []
    now = dt.datetime.fromtimestamp(snapshot["generated_at"]).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines.append(("header", _clip(f" AION OPEN-MISSION LEARNING  |  {now}  |  LIVE EVIDENCE", width)))

    services = snapshot.get("services") or {}
    learning_labels = (
        "Real-outcome learner", "General apprentice", "North-Star registry", "Mastery academy",
        "Open-mission governor", "Matched mission executor", "Arena v15 campaign",
    )
    lines.extend(("section", line) for line in _section("LEARNING SYSTEMS", width))
    for label in learning_labels:
        row = services.get(label) or {}
        health = str(row.get("health") or ("healthy" if row.get("active") else "offline"))
        tone = {"healthy": "good", "waiting": "normal", "degraded": "warn", "offline": "bad"}.get(health, "warn")
        label_text = {"healthy": "HEALTHY", "waiting": "WAITING", "degraded": "DEGRADED", "offline": "OFFLINE"}.get(health, health.upper())
        age = _age(snapshot["generated_at"] - row["evidence_age_seconds"]) if row.get("evidence_age_seconds") is not None else "unknown"
        phase = str(row.get("phase") or "").replace("_", " ")
        phase_text = f" · phase {phase}" if phase else ""
        lines.append((tone, _clip(
            f" {label_text:8}  {label} · evidence {age} · {row.get('health_reason', '')}{phase_text}", width)))
    system_health = services.get("_system") or {}
    disk_free = system_health.get("disk_free_gib")
    lines.append(("good" if system_health.get("health") == "healthy" else "warn", _clip(
        f" System capacity: {disk_free if disk_free is not None else 'unknown'} GiB disk available", width)))
    service = snapshot.get("service_status") or {}
    service_age = service.get("age_seconds")
    age = _age(snapshot["generated_at"] - service_age if service_age is not None else None)
    healthy_curriculum_statuses = {
        "active", "healthy", "running", "competency_cycle_checkpoint",
        "competency_curriculum_active", "competency_waiting_for_executor",
    }
    lines.append(("good" if service.get("status") in healthy_curriculum_statuses else "warn", _clip(
        f" Curriculum ledger: {service.get('status', 'unknown')} | refreshed {age} ago", width)))

    expertise = snapshot.get("comprehensive_expertise") or {}
    current = expertise.get("current") or {}
    phase_focus = expertise.get("phase_focus") or {}
    latest = expertise.get("latest_executor") or {}
    lines.extend(("section", line) for line in _section("COMPREHENSIVE EXPERTISE PROGRAMME — LIVE", width))
    lines.append(("good" if expertise.get("launch_ready") else "warn", _clip(
        f" Launch: {'ACTIVE' if expertise.get('launch_ready') else 'GATED'} | "
        f"phase {expertise.get('phase', '-')} · {str(expertise.get('phase_name', 'unknown')).replace('_', ' ')} | "
        f"curriculum {str(expertise.get('curriculum_digest') or '-')[:12]}", width)))
    lines.append(("normal", _clip(
        f" Curriculum: {expertise.get('learning_capabilities', 0)} learning abilities · "
        f"{expertise.get('subject_academies', 0)} subject academies · "
        f"{expertise.get('domains', 0)} domains · {expertise.get('bridges', 0)} cross-domain bridges · "
        f"{expertise.get('capstones', 0)} capstones · {expertise.get('containers', 0)} containers", width)))
    lines.append(("good" if latest.get("progressed") else "warn", _clip(
        f" Current actual work: {current.get('name', current.get('subject_id', 'waiting'))} · "
        f"overall {current.get('overall_level', 'unassessed')} · knowledge {current.get('knowledge_level', 'unassessed')} · "
        f"evidence {current.get('evidence_records', 0)} distinct/{current.get('raw_evidence_records', current.get('evidence_records', 0))} raw · "
        f"coverage K={float((current.get('coverage') or {}).get('knowledge') or 0):.2f} "
        f"P={float((current.get('coverage') or {}).get('practical') or 0):.2f}", width)))
    if phase_focus.get("subject_id") and phase_focus.get("subject_id") != current.get("subject_id"):
        lines.append(("muted", _clip(
            f" Phase focus retained: {phase_focus.get('name', phase_focus.get('subject_id'))} · "
            f"overall {phase_focus.get('overall_level', 'unassessed')} · parallel lane currently active", width)))
    lines.append(("normal", _clip(
        f" Verified capability adapters: {expertise.get('capability_adapters', 0)}/{expertise.get('learning_capabilities', 0)} "
        f"(acquired before use) · capability evidence {expertise.get('capability_evidence', 0)} across "
        f"{expertise.get('capabilities_with_evidence', 0)} abilities · open capability blockers "
        f"{expertise.get('capability_blockers', 0)}", width)))
    practical_authority = expertise.get("practical_testing_authority") or {}
    practical_summary = practical_authority.get("summary") or {}
    lines.append(("good" if practical_authority.get("passed") else "warn", _clip(
        f" Practical-test authority: {practical_authority.get('status', 'not active')} · "
        f"bounded practice {practical_summary.get('practice_authorized', 0)}/"
        f"{practical_summary.get('subjects', 0)} · independently scored adapters "
        f"{practical_summary.get('competence_adapters_verified', 0)}/"
        f"{practical_summary.get('subjects', 0)} · open adapter gaps "
        f"{practical_summary.get('competence_adapter_gaps', 0)} · unrestricted live authority "
        f"{practical_summary.get('unrestricted_live_authorities', 0)}", width)))
    spaced_practice = expertise.get("continuous_spaced_practice") or {}
    spaced_summary = spaced_practice.get("summary") or {}
    latest_practice = spaced_practice.get("latest") or {}
    lines.append(("good" if spaced_practice.get("passed") else "warn", _clip(
        f" Spaced practice: {spaced_practice.get('status', 'not started')} · rehearsals "
        f"{spaced_summary.get('total_rehearsals', 0)} across "
        f"{spaced_summary.get('subjects_practised', 0)}/"
        f"{spaced_summary.get('subjects_with_practice_adapters', 0)} supported subjects · failures "
        f"{spaced_summary.get('failed_rehearsals', 0)} · latest "
        f"{latest_practice.get('subject_name', latest_practice.get('subject_id', 'waiting'))} · "
        f"awards competence={spaced_summary.get('awards_competence', False)}", width)))
    entanglement = expertise.get("continuous_knowledge_entanglement") or {}
    entanglement_summary = entanglement.get("summary") or {}
    lines.append(("good" if entanglement.get("passed") else "warn", _clip(
        f" Associative graph: {entanglement.get('status', 'not started')} · subjects "
        f"{entanglement_summary.get('subjects', 0)} · active relationships "
        f"{entanglement_summary.get('active_relationships', 0)} · cross-domain "
        f"{entanglement_summary.get('cross_domain_relationships', 0)} · verified transfer "
        f"{entanglement_summary.get('verified_transfer_relationships', 0)} · reassessment cycles "
        f"{entanglement_summary.get('assessment_cycles', 0)} · competence awarded="
        f"{entanglement_summary.get('competence_awarded', False)}", width)))
    cognitive = expertise.get("first_class_cognitive_control_plane") or {}
    lines.append(("good" if cognitive.get("passed") else "warn", _clip(
        f" Cognitive control plane: {cognitive.get('status', 'not started')} · canonical claims "
        f"{cognitive.get('canonical_active_claims', 0)} · verified evidence "
        f"{cognitive.get('canonical_evidence_capsules', 0)} · experience capsules "
        f"{cognitive.get('experience_capsules', 0)} · task retrievals "
        f"{cognitive.get('task_retrievals', 0)} · unverified encounters "
        f"{cognitive.get('encountered_unverified', 0)} · chatter promotions "
        f"{cognitive.get('repetition_promotions', 0)}", width)))
    migration = expertise.get("active_runtime_cognitive_migration") or {}
    lines.append(("good" if migration.get("status") == "fully_migrated" else "warn", _clip(
        f" Active runtime migration: {migration.get('status', 'not audited')} · governed entrypoints "
        f"{migration.get('migrated_entrypoints', 0)}/"
        f"{migration.get('active_service_entrypoints', 0)} · bypasses "
        f"{migration.get('unmigrated_entrypoints', 0)} · live standalone traces "
        f"{migration.get('live_standalone_task_traces', 0)}/"
        f"{migration.get('standalone_entrypoints', 0)}", width)))
    lines.append(("good" if latest.get("status") == "verified_and_recorded" else "warn", _clip(
        f" Latest governed outcome: {latest.get('status', 'waiting')} · "
        f"{latest.get('subject_id', 'none')} · progressed={latest.get('progressed', False)} · "
        f"unsafe actions {(snapshot.get('progressive', {}).get('summary') or {}).get('unsafe_actions', 0)}", width)))
    next_requirement = expertise.get("next_requirement") or {}
    subskills = list((current.get("per_subskill") or {}).keys())
    lines.append(("normal", _clip(
        f" Next gate: {str(next_requirement.get('kind') or 'waiting').replace('_', ' ')} · "
        f"{', '.join(str(skill).replace('_', ' ') for skill in (next_requirement.get('subskills') or [])) or 'none'} | "
        f"subject subskills tracked {len(subskills)}", width)))
    lines.append(("normal", _clip(
        f" Practical proof: projects {current.get('projects', 0)} · unfamiliar {current.get('unfamiliar_projects', 0)} · "
        f"debug/repair {current.get('debugging_cases', 0)} · transfer {current.get('transfer_cases', 0)} · "
        f"retention {current.get('retention_cases', 0)} · milestones "
        f"{current.get('retention_milestones_completed', [])} · "
        f"90-day gate={current.get('long_term_retention_complete', False)} · "
        f"target reached={current.get('target_reached', False)}", width)))
    levels = expertise.get("capability_levels") or {}
    lines.append(("good" if expertise.get("capabilities_target_reached") else "warn", _clip(
        f" Ability competence ledger: expert {levels.get('expert', 0)} · advanced {levels.get('advanced', 0)} · "
        f"intermediate {levels.get('intermediate', 0)} · beginner {levels.get('beginner', 0)} · "
        f"unassessed {levels.get('unassessed', 0)} · at target {expertise.get('capabilities_target_reached', 0)}/"
        f"{expertise.get('learning_capabilities', 0)}", width)))
    strongest = expertise.get("strongest_checked") or []
    if strongest:
        lines.append(("muted", _clip(
            " Strongest bounded subject evidence: " + ", ".join(
                f"{row.get('name', row.get('subject_id'))} ({row.get('overall_level', 'unassessed')})"
                for row in strongest
            ), width)))
    finance = expertise.get("finance_academy") or {}
    finance_levels = finance.get("levels") or {}
    finance_gate = finance.get("next_gate") or {}
    lines.append(("good" if finance_levels.get("advanced", 0) or finance_levels.get("expert", 0) else "warn", _clip(
        f" Institutional finance academy: {finance.get('subjects', 0)} subjects · evidence "
        f"{finance.get('evidence_records', 0)} · expert {finance_levels.get('expert', 0)} · "
        f"advanced {finance_levels.get('advanced', 0)} · intermediate {finance_levels.get('intermediate', 0)} · "
        f"beginner {finance_levels.get('beginner', 0)} · unassessed {finance_levels.get('unassessed', 0)}", width)))
    lines.append(("normal", _clip(
        f" Finance path now: {str(finance_gate.get('subject_id') or 'waiting').replace('_', ' ')} "
        f"{finance_gate.get('actual', '')}→{finance_gate.get('required', '')} · delayed paper market "
        f"{str(finance.get('paper_market_status') or 'not_started').replace('_', ' ')}", width)))
    strategic = expertise.get("strategic_capability_academy") or {}
    strategic_levels = strategic.get("levels") or {}
    lines.append(("good" if strategic_levels.get("advanced", 0) else "warn", _clip(
        f" Strategic capability academy: {strategic.get('subjects', 0)} subjects · evidence "
        f"{strategic.get('evidence_records', 0)} · expert {strategic_levels.get('expert', 0)} · "
        f"advanced {strategic_levels.get('advanced', 0)} · intermediate {strategic_levels.get('intermediate', 0)} · "
        f"beginner {strategic_levels.get('beginner', 0)} · unassessed {strategic_levels.get('unassessed', 0)}", width)))
    lines.append(("normal", _clip(
        " Strategic authority boundary: research and ranked proposals only · capital movement=False · "
        "external influence=False · owner/legal/harm review required", width)))
    cyber = expertise.get("cybersecurity_academy") or {}
    cyber_levels = cyber.get("levels") or {}
    lines.append(("good" if cyber_levels.get("advanced", 0) else "warn", _clip(
        f" Purple-team cybersecurity academy: {cyber.get('subjects', 0)} subjects · evidence "
        f"{cyber.get('evidence_records', 0)} · expert {cyber_levels.get('expert', 0)} · "
        f"advanced {cyber_levels.get('advanced', 0)} · intermediate {cyber_levels.get('intermediate', 0)} · "
        f"beginner {cyber_levels.get('beginner', 0)} · unassessed {cyber_levels.get('unassessed', 0)}", width)))
    lines.append(("normal", _clip(
        f" Cyber range: {str(cyber.get('assessment_status') or 'not_started').replace('_', ' ')} · "
        "external targets=False · destructive actions=False · signed isolated scope required", width)))
    cyber_gate = cyber.get("range_gate") or {}
    lines.append(("good" if cyber.get("range_qualification_passed") else "warn", _clip(
        f" Range qualification: {'PASS' if cyber.get('range_qualification_passed') else 'WAITING'} · "
        f"weaknesses {cyber_gate.get('baseline_weaknesses_demonstrated', 0)} · "
        f"detections {cyber_gate.get('detections_recorded', 0)} · repairs "
        f"{cyber_gate.get('repairs_verified', 0)} · variant retests "
        f"{cyber_gate.get('variant_attacks_rejected', 0)} · tools "
        f"{', '.join(cyber.get('qualified_tool_surface') or []) or 'none'}", width)))
    prediction = expertise.get("prediction_market_academy") or {}
    prediction_levels = prediction.get("levels") or {}
    prediction_gate = prediction.get("gate") or {}
    prediction_ledger = prediction.get("paper_ledger") or {}
    prediction_platforms = prediction.get("platform_counts") or {}
    prediction_geo = prediction.get("geographic_eligibility") or {}
    prediction_game = prediction.get("paper_game") or {}
    prediction_research = prediction.get("research") or {}
    research_summary = prediction_research.get("summary") or {}
    game_tally = prediction_game.get("tally") or {}
    game_gate = prediction_game.get("gate") or {}
    lines.append(("good" if prediction_levels.get("advanced", 0) else "warn", _clip(
        f" Prediction-market academy: {prediction.get('subjects', 0)} subjects · evidence "
        f"{prediction.get('evidence_records', 0)} · expert {prediction_levels.get('expert', 0)} · "
        f"advanced {prediction_levels.get('advanced', 0)} · intermediate {prediction_levels.get('intermediate', 0)} · "
        f"beginner {prediction_levels.get('beginner', 0)} · unassessed {prediction_levels.get('unassessed', 0)}", width)))
    lines.append(("good" if prediction.get("market_count", 0) else "warn", _clip(
        f" Live prediction-market research: {str(prediction.get('live_public_status') or 'not_started').replace('_', ' ')} · "
        f"markets {prediction.get('market_count', 0)} · Polymarket {prediction_platforms.get('polymarket', 0)} · "
        f"Kalshi {prediction_platforms.get('kalshi', 0)} · geoblock checked={prediction_geo.get('checked', False)} "
        f"blocked={prediction_geo.get('blocked')}", width)))
    lines.append(("warn", _clip(
        f" Capital gate: paper={prediction_gate.get('paper_trading_enabled', False)} · "
        f"live={prediction_gate.get('live_trading_enabled', False)} · orders submitted "
        f"{prediction_gate.get('orders_submitted', 0)} · live capital at risk "
        f"{prediction_gate.get('live_capital_at_risk', 0)} · signed loss budget + per-order approval required", width)))
    lines.append(("normal", _clip(
        f" Prediction ledger: commitments {prediction_ledger.get('commitments', 0)} · pending "
        f"{prediction_ledger.get('pending', 0)} · abstained {prediction_ledger.get('abstained', 0)} · settled "
        f"{prediction_ledger.get('settled', 0)} · paper net P&L {prediction_ledger.get('net_pnl', 0)} · "
        f"mean Brier {prediction_ledger.get('mean_brier')}", width)))
    game_wins = game_tally.get("wins", 0)
    game_losses = game_tally.get("losses", 0)
    game_win_rate = game_tally.get("win_rate")
    game_win_text = "pending first settlement" if game_win_rate is None else f"{100 * float(game_win_rate):.1f}%"
    lines.append(("good" if game_tally.get("open_positions", 0) or game_tally.get("settled_bets", 0) else "warn", _clip(
        f" Paper trading game: {str(prediction_game.get('status') or 'not_started').replace('_', ' ').upper()} | "
        f"account ${float(game_tally.get('account_value', 1000)):.2f} / $1,000.00 · "
        f"open {game_tally.get('open_positions', 0)} · bets {game_tally.get('total_bets', 0)} · "
        f"settled {game_tally.get('settled_bets', 0)} · W-L {game_wins}-{game_losses} · "
        f"win rate {game_win_text} · realized P&L ${float(game_tally.get('paper_pnl_realized', 0)):.2f}", width)))
    lines.append(("normal", _clip(
        f" Fast-learning rules: markets must close within {game_gate.get('maximum_time_to_close_hours', 24)}h · "
        f"max bet ${float(game_gate.get('max_order', 10)):.2f} · daily risk ${float(game_gate.get('max_daily_risk', 20)):.2f} · "
        f"total exposure ${float(game_gate.get('max_total_exposure', 50)):.2f} · live capital $0", width)))
    lines.append(("good" if research_summary.get("usable_packets", 0) else "warn", _clip(
        f" Independent research: {str(prediction_research.get('status') or 'not_started').replace('_', ' ').upper()} | "
        f"v2 packets {research_summary.get('current_quality_packets', 0)} · usable {research_summary.get('usable_packets', 0)} · "
        f"abstained/blocked {research_summary.get('abstained_or_blocked', 0)} · researched today "
        f"{research_summary.get('researched_today', 0)}/{research_summary.get('daily_research_cap', 10)} · "
        f"legacy excluded {research_summary.get('legacy_packets_excluded', 0)} · "
        "market price hidden=True · future entries require cited event analysis", width)))
    lines.append(("muted", _clip(
        f" Claim boundary: {expertise.get('claim_boundary', 'installation is not mastery')}", width)))

    integration = snapshot.get("real_world_integration_arena") or {}
    latest_capsule = integration.get("latest_capsule") or {}
    latest_real_capsule = integration.get("latest_real_world_capsule") or {}
    active_real_contract = integration.get("active_real_world_contract") or {}
    latest_retry = ((latest_capsule.get("fresh_retry") or {}).get("evaluation") or {})
    latest_baseline = ((latest_capsule.get("baseline") or {}).get("evaluation") or {})
    graph = integration.get("graph") or {}
    lines.extend(("section", line) for line in _section("REAL-WORLD INTEGRATION ARENA — PARALLEL", width))
    lines.append(("good" if integration.get("passed") else "warn", _clip(
        f" Arena: {str(integration.get('status') or 'not_started').replace('_', ' ').upper()} | "
        f"real outcomes {integration.get('real_world_capsule_count', 0)} · qualification simulations "
        f"{integration.get('calibration_capsule_count', 0)} · completed missions "
        f"{len(integration.get('completed_missions') or [])} · outstanding eligible "
        f"{len(integration.get('outstanding_eligible') or [])}", width)))
    lines.append(("normal", _clip(
        f" Applied graph: {graph.get('nodes', 0)} nodes · {graph.get('edges', 0)} typed links | "
        f"runs beside curriculum={integration.get('parallel_to_curriculum', False)} · "
        f"awards subject competence={integration.get('awards_subject_competence', False)}", width)))
    if latest_capsule:
        subjects = ", ".join(row.get("name", row.get("subject_id", "unknown"))
                             for row in latest_capsule.get("knowledge_inputs") or [])
        lines.append(("good" if latest_capsule.get("passed") else "warn", _clip(
            f" Latest arena: {latest_capsule.get('title', latest_capsule.get('mission_id'))} · "
            f"subjects {subjects or 'none'}", width)))
        lines.append(("good" if latest_retry.get("passed") else "warn", _clip(
            f" Experience loop: baseline {'PASS' if latest_baseline.get('passed') else 'FAIL'} → "
            f"gap exposed → repair → fresh retry {'PASS' if latest_retry.get('passed') else 'FAIL'} · "
            f"unsafe actions {latest_capsule.get('unsafe_actions', 0)}", width)))
    if active_real_contract:
        due = float(active_real_contract.get("not_before_epoch") or 0)
        seconds = max(0, int(due - snapshot.get("generated_at", 0)))
        lines.append(("warn", _clip(
            f" Frozen real-world contract: {active_real_contract.get('title', active_real_contract.get('mission_id'))} · "
            f"later unseen public observation due in about {seconds}s · commitment "
            f"{str(active_real_contract.get('commitment_sha256') or '-')[:12]}", width)))
    if latest_real_capsule:
        lines.append(("good" if latest_real_capsule.get("verified_real_outcome") else "warn", _clip(
            f" Latest genuine outcome: {latest_real_capsule.get('title')} · score "
            f"{latest_real_capsule.get('correct_predictions', 0)}/{latest_real_capsule.get('scored_predictions', 0)} · "
            f"world-owned receipt {str(latest_real_capsule.get('later_outcome_sha256') or '-')[:12]}", width)))
    lines.append(("warn" if integration.get("awaiting_genuine_world_authority") else "muted", _clip(
        f" Genuine-world validation still required for {integration.get('awaiting_genuine_world_authority', 0)} capsules. "
        f"Boundary: {integration.get('claim_boundary', 'calibration is not real-world mastery')}", width)))
    adapters = snapshot.get("real_world_experience_adapters") or {}
    lines.append(("good" if adapters.get("passed") else "warn", _clip(
        f" Real adapter portfolio: ready {adapters.get('ready', 0)}/{adapters.get('adapter_count', 0)} · "
        f"active frozen contracts {adapters.get('active_real_contracts', 0)} · learning-gated "
        f"{adapters.get('learning_gated', 0)} · live capital at risk {adapters.get('live_capital_at_risk', 0)} · "
        f"physical actions {adapters.get('physical_actions', 0)}", width)))
    verified_adapter_outcome = adapters.get("latest_verified_outcome") or {}
    if verified_adapter_outcome:
        lines.append(("good" if verified_adapter_outcome.get("outcome_success") else "warn", _clip(
            f"  Latest advanced real outcome: {verified_adapter_outcome.get('capsule_id')} · "
            f"{'PASS' if verified_adapter_outcome.get('outcome_success') else 'MISS'} · "
            f"independent receipt {str(verified_adapter_outcome.get('later_outcome_sha256') or '-')[:12]} · "
            f"verified outcomes {adapters.get('verified_real_outcomes', 0)}", width)))
    for adapter in adapters.get("adapters") or []:
        tone = "good" if adapter.get("active_contract") else (
            "warn" if adapter.get("readiness", {}).get("ready") else "muted")
        lines.append((tone, _clip(
            f"  {adapter.get('title', adapter.get('adapter_id'))}: "
            f"{str(adapter.get('status') or 'unknown').replace('_', ' ')}", width)))
    adapter_dispatch = adapters.get("learning_dispatch") or adapters.get("next_learning_gate") or {}
    if adapter_dispatch:
        lines.append(("normal", _clip(
            f"  Next real-world unlock being learned: {adapter_dispatch.get('subject_id')} → "
            f"{adapter_dispatch.get('adapter_id')}", width)))

    moonshot = snapshot.get("open_mission_compounding") or {}
    executor = snapshot.get("open_mission_executor") or {}
    lines.extend(("section", line) for line in _section("SEVEN-DAY MOONSHOT", width))
    lines.append(("good" if moonshot.get("status") in {"active", "retention_followup"} else "warn", _clip(
        f" Campaign: {str(moonshot.get('status', 'unknown')).upper()} | diagnostic cohorts "
        f"{moonshot.get('claim_diagnostic_cohorts', 0)} | completed records "
        f"{moonshot.get('cohort_complete_missions', 0)} | "
        f"ends {_local_time(moonshot.get('ends_at'))}", width)))
    families = moonshot.get("completed_mission_families") or []
    lines.append(("normal", _clip(
        f" Independent mission families: {len(families)} ({', '.join(families) or 'waiting'}) | "
        f"calibration outcomes excluded from claim: {moonshot.get('calibration_outcomes_excluded_from_claim', 0)}",
        width)))
    for arm in ("full_aion", "proposer_only", "aion_no_memory", "aion_no_repair", "cold_aion"):
        row = (moonshot.get("arms") or {}).get(arm) or {}
        rate = row.get("success_rate")
        rate_text = "waiting" if rate is None else f"{100.0 * rate:.0f}%"
        successes = row.get("verified_successes", 0)
        outcomes = row.get("eligible_outcomes", 0)
        actions = row.get("investigation_actions", 0)
        style = "good" if successes else "bad" if outcomes else "muted"
        lines.append((style, _clip(
            f" {arm.replace('_', ' ').title():22} success {successes}/{outcomes} ({rate_text}) | "
            f"investigation actions {actions:g}", width)))

    arms = moonshot.get("arms") or {}
    full = arms.get("full_aion") or {}
    proposer = arms.get("proposer_only") or {}
    no_memory = arms.get("aion_no_memory") or {}
    no_repair = arms.get("aion_no_repair") or {}
    findings = []
    if full.get("verified_successes", 0) > proposer.get("verified_successes", 0):
        findings.append("full AION beat proposer-only")
    elif full.get("verified_successes", 0) < proposer.get("verified_successes", 0):
        findings.append("full AION trails proposer-only: intervene")
    full_actions = float(full.get("investigation_actions") or 0)
    no_memory_actions = float(no_memory.get("investigation_actions") or 0)
    if full.get("verified_successes", 0) < no_memory.get("verified_successes", 0):
        findings.append("memory is harming outcomes: quarantined")
    elif (full.get("verified_successes") == no_memory.get("verified_successes")
          and full.get("verified_successes") and full_actions and no_memory_actions > full_actions):
        saving = 100.0 * (1.0 - full_actions / no_memory_actions)
        findings.append(f"memory used {saving:.0f}% fewer actions at equal success")
    if full.get("verified_successes", 0) > no_repair.get("verified_successes", 0):
        findings.append("repair advantage confirmed")
    elif full.get("verified_successes") == no_repair.get("verified_successes"):
        findings.append("repair advantage not tested yet")
    lines.append(("normal", _clip(" Current evidence: " + ("; ".join(findings) or "first matched cohort pending"), width)))
    ratio = moonshot.get("full_aion_efficiency_ratio_vs_proposer")
    comparison = moonshot.get("full_aion_efficiency_comparison")
    control_zero = (
        int(full.get("verified_successes") or 0) > 0
        and int(proposer.get("eligible_outcomes") or 0) > 0
        and int(proposer.get("verified_successes") or 0) == 0
    )
    efficiency_text = (
        "full produced verified work; control produced none (finite ratio not estimable)"
        if comparison == "full_positive_control_zero" or control_zero
        else f"{float(ratio):.2f}x" if ratio is not None else "insufficient evidence"
    )
    lines.append(("warn" if not moonshot.get("ten_x_claim_gate_passed") else "success", _clip(
        f" 10x claim: {moonshot.get('ten_x_claim_gate_passed', False)} | full/proposer efficiency: "
        f"{efficiency_text} | retained tests "
        f"{moonshot.get('verified_retention_count', 0)} | confirmed mission repairs "
        f"{moonshot.get('confirmed_repair_count', 0)} | false/unsafe promotions "
        f"{moonshot.get('false_or_unsafe_promotions', 0)}", width)))

    public = executor.get("public_change") or {}
    lines.extend(("section", line) for line in _section("NEXT INDEPENDENT EVIDENCE", width))
    public_status = str(public.get("status") or "not started")
    public_label = "CALIBRATION COMPLETE" if public_status == "portfolio_limit_reached" else public_status.upper()
    lines.append(("good" if public_status in {"scored", "portfolio_limit_reached"} else "warn", _clip(
        f" Rolling public-world forecast: {public_label} | "
        f"frozen cursor {public.get('cursor', '-')} | authority rows {public.get('rows', '-')} | "
        f"commitment {str(public.get('commitment', 'none'))[:12]}", width)))
    last_scored = public.get("last_scored") or {}
    if last_scored:
        scores = ", ".join(
            f"{str(row.get('arm', '')).replace('_', ' ')}={float(row.get('score') or 0):.2f}"
            for row in last_scored.get("arms") or []
        )
        lines.append(("good", _clip(
            f" Last independent outcome: cycle {last_scored.get('revealed_cycle', '-')} scored | {scores}", width)))
    lines.append(("muted", _clip(
        f" Retention attempts {moonshot.get('retention_attempted_count', 0)} | "
        f"passed {moonshot.get('verified_retention_count', 0)} | "
        f"failed {moonshot.get('failed_retention_count', 0)} | "
        f"outstanding {moonshot.get('retention_outstanding_missions', 0)} | "
        f"next due {_local_time(moonshot.get('next_retention_due_at'))}", width)))
    if public.get("status") == "waiting":
        lines.append(("normal", " Next action: honour the already-frozen outcome, then close forecast calibration and continue novel repair work."))
    elif public.get("status") == "portfolio_limit_reached":
        wave = executor.get("next_mission_wave") or {}
        if wave:
            lines.append(("good", _clip(
                " Forecast calibration complete. Novel matched repair work is active; "
                f"next {wave.get('name', 'transfer')} wave opens in "
                f"{float(wave.get('hours_remaining') or 0):.1f}h with "
                f"{int(wave.get('new_matched_cohorts') or 0)} new cohorts.", width)))
        else:
            lines.append(("good", " Forecast calibration complete. All scheduled matched mission waves are open; retention remains independently timed."))

    aga = snapshot.get("aga_registry") or {}
    profiles = aga.get("scope_profiles") or {}
    technical = profiles.get("technical_aga") or {}
    full_aga = profiles.get("full_aga") or {}
    social = (aga.get("gates") or {}).get("social_creative_grounding") or {}
    lines.extend(("section", line) for line in _section("FIXED BASELINE — NOT THE CURRENT TARGET", width))
    lines.append(("good" if technical.get("authorized") else "warn", _clip(
        f" Technical AGA v1: {technical.get('passed', 0)}/{technical.get('total', 10)} authorized={technical.get('authorized', False)} | "
        f"Full AGA: {full_aga.get('passed', 0)}/{full_aga.get('total', 11)} authorized={full_aga.get('authorized', False)}", width)))
    lines.append(("muted", _clip(
        f" Only full-AGA gate: {social.get('name', 'independent human grounding')} — "
        f"{social.get('blocked_by', 'external authority required')}. Historical project totals are hidden from this focused view.", width)))

    lines.append(("footer", " q quit | r refresh | --full shows the archived engineering dashboard "))
    return lines


def render_text(snapshot: Mapping[str, Any], width: int = 120, color: bool = False,
                full: bool = False) -> str:
    colors = {
        "header": "\033[1;36m", "section": "\033[1;34m", "good": "\033[32m",
        "warn": "\033[33m", "bad": "\033[31m", "muted": "\033[2m",
        "normal": "", "footer": "\033[1;36m",
    }
    reset = "\033[0m"
    output = []
    renderer = render_full_lines if full else render_lines
    for style, line in renderer(snapshot, width):
        output.append((colors.get(style, "") + line + reset) if color else line)
    return "\n".join(output)


def _run_curses(screen: Any, root: Path, interval: float, full: bool = False) -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    screen.timeout(200)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_BLUE, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_WHITE, -1)
    attrs = {
        "header": curses.color_pair(1) | curses.A_BOLD,
        "section": curses.color_pair(2) | curses.A_BOLD,
        "good": curses.color_pair(3), "warn": curses.color_pair(4),
        "bad": curses.color_pair(5) | curses.A_BOLD,
        "muted": curses.color_pair(6) | curses.A_DIM,
        "normal": curses.A_NORMAL, "footer": curses.color_pair(1) | curses.A_BOLD,
    }
    snapshot = collect_snapshot(root)
    last_refresh = time.monotonic()
    scroll = 0
    while True:
        height, width = screen.getmaxyx()
        renderer = render_full_lines if full else render_lines
        lines = renderer(snapshot, max(70, width - 1))
        visible = max(1, height - 1)
        scroll = min(scroll, max(0, len(lines) - visible))
        screen.erase()
        for row_index, (style, line) in enumerate(lines[scroll: scroll + visible]):
            try:
                screen.addnstr(row_index, 0, line, max(1, width - 1), attrs.get(style, 0))
            except curses.error:
                pass
        try:
            screen.addnstr(height - 1, 0,
                           f" view {scroll + 1}-{min(len(lines), scroll + visible)}/{len(lines)} | auto-refresh {interval:g}s ",
                           max(1, width - 1), curses.A_REVERSE)
        except curses.error:
            pass
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("r"), ord("R")) or time.monotonic() - last_refresh >= interval:
            snapshot = collect_snapshot(root); last_refresh = time.monotonic()
        elif key in (curses.KEY_DOWN, ord("j")):
            scroll += 1
        elif key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
        elif key == curses.KEY_NPAGE:
            scroll += visible
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - visible)
        elif key == ord("g"):
            scroll = 0
        elif key == ord("G"):
            scroll = max(0, len(lines) - visible)


def main() -> None:
    parser = argparse.ArgumentParser(description="AION intelligence-development terminal dashboard")
    parser.add_argument("--repo-root", type=Path,
                        default=Path(os.getenv("AION_REPO_ROOT", ".")))
    parser.add_argument("--once", action="store_true", help="print one human-readable snapshot")
    parser.add_argument("--json", action="store_true", help="print one machine-readable snapshot")
    parser.add_argument("--interval", type=float, default=5.0, help="live refresh interval in seconds")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI color in --once mode")
    parser.add_argument("--full", action="store_true", help="show the archived engineering dashboard")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    snapshot = collect_snapshot(root)
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return
    if args.once or not sys.stdout.isatty():
        width = max(70, min(160, shutil.get_terminal_size((120, 30)).columns))
        print(render_text(snapshot, width=width,
                          color=not args.no_color and sys.stdout.isatty(), full=args.full))
        return
    curses.wrapper(_run_curses, root, max(1.0, args.interval), args.full)


if __name__ == "__main__":
    main()

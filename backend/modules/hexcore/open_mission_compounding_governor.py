"""Govern a frozen seven-day open-mission compounding campaign.

This module is deliberately an evidence authority, not a task solver.  It
precommits the campaign, enforces identical proposer/tool/budget conditions
across ablations, records evaluator-owned outcomes, schedules source-closed
retention, and computes whether AION contributed measurable value.  Proposal
components cannot promote themselves through this surface.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "aion.hexcore.open_mission_compounding.v1"
CAMPAIGN_ID = "aion_seven_day_open_mission_moonshot_202608"
ARMS = (
    "full_aion",
    "proposer_only",
    "aion_no_memory",
    "aion_no_repair",
    "cold_aion",
)
LANE_WEIGHTS = {
    "software_systems": 0.70,
    "open_research": 0.20,
    "human_grounded": 0.10,
}


def _mission_family(mission_id: str) -> str:
    if mission_id.startswith("moonshot_public_change_forecast"):
        return "public_change_forecast"
    if "repo_repair" in mission_id:
        return "repository_repair"
    if "schema_migration" in mission_id:
        return "schema_migration"
    if "api_pagination" in mission_id:
        return "api_pagination"
    if "webhook_replay" in mission_id:
        return "webhook_replay"
    if "configuration_precedence" in mission_id:
        return "configuration_precedence"
    if "cache_coherence" in mission_id:
        return "cache_coherence"
    if "concurrent_reservation" in mission_id:
        return "concurrent_reservation"
    if "protocol_versioning" in mission_id:
        return "protocol_versioning"
    if "access_policy_regression" in mission_id:
        return "access_policy_regression"
    if "polyglot" in mission_id:
        return "polyglot_transaction_recovery"
    return mission_id


def _is_claim_diagnostic(mission_id: str) -> bool:
    """Rolling forecasts are calibration, not independent compounding cohorts."""
    return not mission_id.startswith("moonshot_public_change_forecast")


def _has_mature_retention_attempt(state: Mapping[str, Any], mission_id: str) -> bool:
    """A mature retention exam is single-shot, whether it passes or fails."""
    return any(
        row.get("mission_id") == mission_id and row.get("mature") is True
        for row in state.get("retention_receipts") or []
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _utcnow()).isoformat()


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=path.parent, suffix=".tmp", encoding="utf-8"
    )
    try:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        json.loads(Path(handle.name).read_text(encoding="utf-8"))
        os.replace(handle.name, path)
    except Exception:
        try:
            handle.close()
        finally:
            Path(handle.name).unlink(missing_ok=True)
        raise


def frozen_campaign_contract(
    *, proposer_id: str, tool_manifest_hash: str, action_budget: int,
    started_at: datetime | None = None,
) -> dict[str, Any]:
    """Return the immutable authority contract for one seven-day campaign."""
    if not proposer_id.strip():
        raise ValueError("a fixed proposer identity is required")
    if len(tool_manifest_hash) != 64:
        raise ValueError("tool_manifest_hash must be a SHA-256 digest")
    if action_budget < 1:
        raise ValueError("action_budget must be positive")
    start = started_at or _utcnow()
    end = start + timedelta(days=7)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": CAMPAIGN_ID,
        "objective": (
            "Measure whether governed accumulated experience improves verified "
            "performance on unfamiliar real missions under declining scaffolding."
        ),
        "started_at": _timestamp(start),
        "ends_at": _timestamp(end),
        "duration_seconds": 7 * 24 * 60 * 60,
        "proposer_id": proposer_id,
        "tool_manifest_hash": tool_manifest_hash,
        "action_budget_per_arm": action_budget,
        "arms": list(ARMS),
        "lane_weights": dict(LANE_WEIGHTS),
        "fault_policy": {
            "natural": True,
            "induced_answer_hidden": True,
            "induced_fault_must_be_committed_before_solver_start": True,
            "scripted_answer_in_proposer_context": False,
        },
        "authority_rules": {
            "success_contract_frozen_before_execution": True,
            "evaluator_must_be_independent_of_proposal": True,
            "source_closed_retention_required": True,
            "self_grading_can_promote": False,
            "unsafe_or_false_promotion_budget": 0,
        },
        "claim_rules": {
            "technical_aga_v1_frozen": True,
            "project_count_is_promotion_evidence": False,
            "ten_x_claim_requires_matched_ratio_at_least": 10.0,
            "ten_x_claim_requires_no_success_regression": True,
            "agi_claim_authorized": False,
        },
    }
    contract["contract_hash"] = _hash(contract)
    return contract


class OpenMissionCompoundingGovernor:
    """Fail-closed campaign ledger and ablation authority."""

    def __init__(self, *, state_path: Path) -> None:
        self.state_path = state_path
        if state_path.exists():
            self.state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "schema_version": SCHEMA_VERSION,
                "contract": None,
                "missions": {},
                "outcomes": [],
                "retention_receipts": [],
                "repair_receipts": [],
                "status": "unconfigured",
            }

    def _save(self) -> None:
        self.state["updated_at"] = _timestamp()
        _atomic_write(self.state_path, self.state)

    def authorize(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        supplied = dict(contract)
        claimed_hash = supplied.pop("contract_hash", None)
        if claimed_hash != _hash(supplied):
            raise ValueError("campaign contract hash is invalid")
        supplied["contract_hash"] = claimed_hash
        existing = self.state.get("contract")
        if existing and existing["contract_hash"] != claimed_hash:
            raise ValueError("the active seven-day campaign contract is immutable")
        if not existing:
            self.state["contract"] = supplied
            self.state["status"] = "active"
            self._save()
        return dict(self.state["contract"])

    def register_mission(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        contract = self.state.get("contract")
        if not contract:
            raise ValueError("authorize the campaign first")
        mission = dict(packet)
        required = {
            "mission_id", "lane", "objective", "evaluator_authority",
            "success_contract", "source_policy", "risk_class",
        }
        missing = sorted(required - set(mission))
        if missing:
            raise ValueError(f"mission packet missing fields: {missing}")
        if mission["lane"] not in LANE_WEIGHTS:
            raise ValueError("mission lane is not authorized")
        if mission["evaluator_authority"] in {"aion", "proposal", "self"}:
            raise ValueError("proposal system cannot own its success authority")
        if mission["source_policy"].get("closes_after_learning") is not True:
            raise ValueError("source-closed retention must be testable")
        success = dict(mission["success_contract"])
        if not success or success.get("frozen_before_execution") is not True:
            raise ValueError("success contract must be frozen before execution")
        cohort_proposer = str(mission.get("cohort_proposer_id") or contract["proposer_id"])
        if not cohort_proposer.strip():
            raise ValueError("cohort proposer identity cannot be empty")
        mission["cohort_proposer_id"] = cohort_proposer
        mission["registered_at"] = _timestamp()
        mission["status"] = "precommitted"
        mission["arm_conditions"] = {
            arm: {
                "proposer_id": cohort_proposer,
                "tool_manifest_hash": contract["tool_manifest_hash"],
                "action_budget": contract["action_budget_per_arm"],
            }
            for arm in ARMS
        }
        mission["mission_hash"] = _hash({
            key: value for key, value in mission.items()
            if key not in {"mission_hash", "status", "registered_at"}
        })
        existing = self.state["missions"].get(mission["mission_id"])
        if existing and existing["mission_hash"] != mission["mission_hash"]:
            raise ValueError("precommitted mission cannot be mutated")
        self.state["missions"].setdefault(mission["mission_id"], mission)
        self._save()
        return dict(self.state["missions"][mission["mission_id"]])

    def record_outcome(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        row = dict(receipt)
        mission = self.state["missions"].get(str(row.get("mission_id") or ""))
        if not mission:
            raise ValueError("outcome has no precommitted mission")
        arm = str(row.get("arm") or "")
        if arm not in ARMS:
            raise ValueError("unknown ablation arm")
        expected = mission["arm_conditions"][arm]
        parity = all(row.get(key) == expected[key] for key in expected)
        authority_valid = row.get("evaluator_authority") == mission["evaluator_authority"]
        precommit_valid = row.get("mission_hash") == mission["mission_hash"]
        safe = int(row.get("unsafe_actions") or 0) == 0
        row.update({
            "parity_valid": parity,
            "authority_valid": authority_valid,
            "precommit_valid": precommit_valid,
            "eligible": bool(parity and authority_valid and precommit_valid and safe),
            "recorded_at": _timestamp(),
        })
        row["verified_success"] = bool(row.get("success") is True and row["eligible"])
        row["receipt_hash"] = _hash(row)
        self.state["outcomes"].append(row)
        completed_arms = {
            item["arm"] for item in self.state["outcomes"]
            if item["mission_id"] == mission["mission_id"] and item["eligible"]
        }
        mission["status"] = "cohort_complete" if completed_arms == set(ARMS) else "running"
        self._save()
        return row

    def close_source(self, *, mission_id: str, closed_at: datetime | None = None) -> dict[str, Any]:
        mission = self.state["missions"].get(mission_id)
        if not mission:
            raise KeyError(mission_id)
        closed = closed_at or _utcnow()
        mission["source_closed_at"] = _timestamp(closed)
        mission["retention_due_at"] = _timestamp(closed + timedelta(days=7))
        mission["source_access_revoked"] = True
        self._save()
        return dict(mission)

    def record_retention(self, receipt: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        row = dict(receipt)
        mission = self.state["missions"].get(str(row.get("mission_id") or ""))
        if not mission or not mission.get("retention_due_at"):
            raise ValueError("mission has no scheduled source-closed retention")
        current = now or _utcnow()
        mature = current >= _parse(mission["retention_due_at"])
        authority_valid = row.get("evaluator_authority") == mission["evaluator_authority"]
        row.update({
            "source_accessed": bool(row.get("source_accessed")),
            "mature": mature,
            "authority_valid": authority_valid,
            "verified": bool(
                mature and authority_valid and row.get("passed") is True
                and row.get("source_accessed") is False
            ),
            "recorded_at": _timestamp(current),
        })
        row["receipt_hash"] = _hash(row)
        self.state["retention_receipts"].append(row)
        self._save()
        return row

    def record_repair(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        row = dict(receipt)
        fault_kind = row.get("fault_kind")
        if fault_kind not in {"natural", "induced_answer_hidden"}:
            raise ValueError("repair fault must be natural or transparently induced")
        precommitted = bool(
            fault_kind == "natural"
            or row.get("fault_commitment_before_solver_start") is True
        )
        later = bool(row.get("later_independent_confirmation") is True)
        no_self_grade = row.get("confirmation_authority") not in {"aion", "proposal", "self", None}
        row.update({
            "eligible": bool(precommitted and later and no_self_grade),
            "recorded_at": _timestamp(),
        })
        row["receipt_hash"] = _hash(row)
        self.state["repair_receipts"].append(row)
        self._save()
        return row

    def snapshot(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or _utcnow()
        contract = self.state.get("contract") or {}
        eligible = [row for row in self.state["outcomes"] if row.get("eligible")]
        claim_eligible = [
            row for row in eligible if _is_claim_diagnostic(str(row.get("mission_id") or ""))
        ]
        calibration = [row for row in eligible if row not in claim_eligible]
        by_arm: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            rows = [row for row in claim_eligible if row["arm"] == arm]
            successes = sum(row.get("verified_success") is True for row in rows)
            intervention = sum(float(row.get("human_intervention_minutes") or 0.0) for row in rows)
            work = sum(float(row.get("verified_work_units") or 0.0) for row in rows)
            actions = sum(float(row.get("investigation_actions") or 0.0) for row in rows)
            by_arm[arm] = {
                "eligible_outcomes": len(rows),
                "verified_successes": successes,
                "success_rate": successes / len(rows) if rows else None,
                "human_intervention_minutes": intervention,
                "verified_work_units": work,
                "investigation_actions": actions,
                "work_per_intervention_minute": (
                    work / intervention if rows and intervention > 0 else None
                ),
                "work_per_investigation_action": work / max(actions, 1e-9) if rows else None,
            }
        full = by_arm["full_aion"]
        control = by_arm["proposer_only"]
        # Autonomous campaigns often require zero human intervention in every
        # arm, making intervention ratios undefined.  Use verified work per
        # investigation/action as the primary compounding efficiency measure.
        full_eff = full["work_per_investigation_action"]
        control_eff = control["work_per_investigation_action"]
        ratio = (
            full_eff / control_eff
            if full_eff is not None and control_eff not in {None, 0.0}
            else None
        )
        efficiency_comparison = (
            "full_positive_control_zero"
            if full_eff is not None and full_eff > 0 and control_eff == 0
            else "ratio_available" if ratio is not None else "insufficient_evidence"
        )
        no_regression = bool(
            full["success_rate"] is not None and control["success_rate"] is not None
            and full["success_rate"] >= control["success_rate"]
        )
        ten_x = bool(ratio is not None and ratio >= 10.0 and no_regression)
        due = [
            mission["mission_id"] for mission in self.state["missions"].values()
            if mission.get("retention_due_at") and current >= _parse(mission["retention_due_at"])
            and _is_claim_diagnostic(mission["mission_id"])
            and not _has_mature_retention_attempt(self.state, mission["mission_id"])
        ]
        mission_summaries = [
            {
                "mission_id": mission["mission_id"],
                "lane": mission.get("lane"),
                "status": mission.get("status"),
                "source_closed_at": mission.get("source_closed_at"),
                "retention_due_at": mission.get("retention_due_at"),
                "family": _mission_family(mission["mission_id"]),
                "claim_diagnostic": _is_claim_diagnostic(mission["mission_id"]),
            }
            for mission in self.state["missions"].values()
        ]
        future_retention = sorted(
            mission["retention_due_at"] for mission in mission_summaries
            if mission.get("retention_due_at")
            and mission.get("claim_diagnostic") is True
            and not _has_mature_retention_attempt(self.state, mission["mission_id"])
        )
        retention_attempts = [
            row for row in self.state["retention_receipts"] if row.get("mature") is True
        ]
        contract_end = _parse(contract["ends_at"]) if contract.get("ends_at") else None
        campaign_status = (
            "retention_followup"
            if contract_end is not None and current >= contract_end
            else self.state.get("status")
        )
        snapshot = {
            "schema_version": SCHEMA_VERSION,
            "campaign_id": contract.get("campaign_id"),
            "status": campaign_status,
            "contract_hash": contract.get("contract_hash"),
            "started_at": contract.get("started_at"),
            "ends_at": contract.get("ends_at"),
            "elapsed_seconds": max(0.0, (current - _parse(contract["started_at"])).total_seconds()) if contract else 0.0,
            "mission_count": len(self.state["missions"]),
            "missions": mission_summaries,
            "cohort_complete_missions": sum(
                row.get("status") == "cohort_complete" for row in self.state["missions"].values()
            ),
            "claim_diagnostic_cohorts": sum(
                row.get("status") == "cohort_complete"
                and _is_claim_diagnostic(row["mission_id"])
                for row in self.state["missions"].values()
            ),
            "completed_mission_families": sorted({
                _mission_family(row["mission_id"])
                for row in self.state["missions"].values()
                if row.get("status") == "cohort_complete"
            }),
            "calibration_outcomes_excluded_from_claim": len(calibration),
            "arms": by_arm,
            "full_aion_efficiency_ratio_vs_proposer": ratio,
            "full_aion_efficiency_comparison": efficiency_comparison,
            "ten_x_claim_gate_passed": ten_x,
            "verified_retention_count": sum(row.get("verified") is True for row in self.state["retention_receipts"]),
            "retention_attempted_count": len(retention_attempts),
            "failed_retention_count": sum(row.get("verified") is not True for row in retention_attempts),
            "retention_due_missions": due,
            "retention_outstanding_missions": len(future_retention),
            "next_retention_due_at": future_retention[0] if future_retention else None,
            "confirmed_repair_count": sum(row.get("eligible") is True for row in self.state["repair_receipts"]),
            "false_or_unsafe_promotions": sum(
                row.get("success") is True and not row.get("eligible") for row in self.state["outcomes"]
            ),
            "agi_claim_authorized": False,
            "generated_at": _timestamp(current),
        }
        return snapshot

    def publish_snapshot(self, path: Path) -> dict[str, Any]:
        snapshot = self.snapshot()
        _atomic_write(path, snapshot)
        return snapshot

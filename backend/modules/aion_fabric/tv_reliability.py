from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class TelevisionReliabilityQualification:
    """Evidence ledger for closing Section 3 on a specific television adapter."""

    REQUIRED_AREAS = (
        "connection_recovery",
        "state_observation",
        "reversible_audio",
        "application_launch",
        "directional_navigation",
        "back_home_exit",
        "focus_pointer",
        "in_app_search",
        "profile_selection",
        "playback_control",
        "duplicate_suppression",
    )
    FIELD_EVIDENCE = {
        "device_read_after_write",
        "structured_screen_observation",
        "owner_visual_confirmation",
        "signed_provider_telemetry",
        "local_idempotency_proof",
    }
    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "tv_reliability"
        self.path = self.root / "qualification.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[Dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, value: list[Dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value[-500:]))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def area_for_goal(goal: str) -> str | None:
        goal = str(goal).lower()
        if goal in {"observe", "connection_probe"}:
            return "state_observation" if goal == "observe" else "connection_recovery"
        if goal in {"volume_up", "volume_down", "mute", "unmute"}:
            return "reversible_audio"
        if goal in {"netflix", "youtube", "aion", "games", "god_view"}:
            return "application_launch"
        if goal in {"up", "down", "left", "right", "enter"}:
            return "directional_navigation"
        if goal in {"back", "home", "exit_content"}:
            return "back_home_exit"
        if goal in {"pointer_move", "pointer_click", "accept_google"}:
            return "focus_pointer"
        if goal == "profile_menu":
            return None
        if goal.startswith("profile_"):
            return "profile_selection"
        if goal in {"netflix_search", "contextual_search"}:
            return "in_app_search"
        if goal in {"play", "pause", "stop"}:
            return "playback_control"
        if goal == "duplicate_suppression":
            return "duplicate_suppression"
        return None

    def record(
        self,
        *,
        device_id: str,
        adapter: str,
        area: str,
        operation: str,
        outcome: str,
        evidence_source: str,
        evidence_id: str = "",
        recovered: bool = False,
        duration_ms: int = 0,
    ) -> Dict[str, Any]:
        if area not in self.REQUIRED_AREAS:
            raise ValueError("Unknown Section 3 qualification area")
        if outcome not in {"verified", "not_verified", "skipped"}:
            raise ValueError("Unknown qualification outcome")
        if evidence_source not in self.FIELD_EVIDENCE | {"simulated_contract", "transport_only"}:
            raise ValueError("Unknown qualification evidence source")
        record: Dict[str, Any] = {
            "schema_version": "pilot.tv-reliability-case.v1",
            "device_id": str(device_id)[:160],
            "adapter": str(adapter)[:80],
            "area": area,
            "operation": str(operation)[:120],
            "outcome": outcome,
            "evidence_source": evidence_source,
            "evidence_id": str(evidence_id)[:180],
            "recovered": bool(recovered),
            "duration_ms": max(0, int(duration_ms)),
            "created_at": utc_now_iso(),
        }
        record["record_hash"] = canonical_hash(record)
        with self._lock:
            records = self._read()
            if evidence_id:
                existing = next((item for item in records if item.get("evidence_id") == evidence_id and item.get("operation") == operation), None)
                if existing:
                    return existing
            records.append(record)
            self._write(records)
        return record

    def record_navigation(self, transaction: Dict[str, Any], *, adapter: str = "lg_webos_gateway") -> Dict[str, Any] | None:
        area = self.area_for_goal(str(transaction.get("goal") or ""))
        if not area or transaction.get("status") not in {"verified", "not_verified", "superseded_not_verified"}:
            return None
        evidence = dict(transaction.get("after_evidence") or transaction.get("failure_evidence") or {})
        evidence_kind = str(evidence.get("kind") or "")
        source = (
            "structured_screen_observation" if evidence_kind == "structured_observation"
            else "owner_visual_confirmation" if evidence_kind == "owner_visual_confirmation"
            else "device_read_after_write" if evidence_kind in {"read_after_write_receipt", "device_receipt"}
            else "transport_only"
        )
        return self.record(
            device_id=str(transaction.get("device_id") or ""),
            adapter=adapter,
            area=area,
            operation=str(transaction.get("goal") or ""),
            outcome="verified" if transaction.get("status") == "verified" else "not_verified",
            evidence_source=source,
            evidence_id=str(transaction.get("transaction_id") or ""),
            recovered=int(transaction.get("route_index") or 0) > 0,
        )

    def report(self, *, device_id: str | None = None, adapter: str | None = None, minimum_field_cases: int = 20) -> Dict[str, Any]:
        records = [
            item for item in self._read()
            if (not device_id or item.get("device_id") == device_id)
            and (not adapter or item.get("adapter") == adapter)
        ]
        field = [item for item in records if item.get("evidence_source") in self.FIELD_EVIDENCE and item.get("outcome") != "skipped"]
        successful = [item for item in field if item.get("outcome") == "verified"]
        rate = round(len(successful) / len(field), 4) if field else 0.0
        coverage: Dict[str, Dict[str, Any]] = {}
        for area in self.REQUIRED_AREAS:
            area_records = [item for item in field if item.get("area") == area]
            coverage[area] = {
                "field_cases": len(area_records),
                "verified": sum(item.get("outcome") == "verified" for item in area_records),
                "covered": any(item.get("outcome") == "verified" for item in area_records),
            }
        missing = [area for area, value in coverage.items() if not value["covered"]]
        return {
            "schema_version": "pilot.tv-reliability-qualification.v1",
            "device_id": device_id,
            "adapter": adapter,
            "field_cases": len(field),
            "verified_or_recovered": len(successful),
            "not_verified": len(field) - len(successful),
            "success_or_recovery_rate": rate,
            "target_rate": 0.95,
            "minimum_field_cases": max(1, int(minimum_field_cases)),
            "coverage": coverage,
            "missing_areas": missing,
            "section_3_closed": len(field) >= max(1, int(minimum_field_cases)) and rate >= 0.95 and not missing,
            "simulated_cases_excluded": sum(item.get("evidence_source") == "simulated_contract" for item in records),
            "transport_only_excluded": sum(item.get("evidence_source") == "transport_only" for item in records),
            "generated_at": utc_now_iso(),
        }

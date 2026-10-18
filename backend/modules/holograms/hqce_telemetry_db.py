"""Guardian-backed HQCE telemetry storage.

Importing this module has no filesystem side effects. Customer telemetry is
encrypted in the Business Vault when Guardian is configured; local experiments
use process memory only. JSON import/export remains an explicit user action.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

logger = logging.getLogger(__name__)


class HQCETelemetryDB:
    """HQCE field tensor store with encrypted or memory-only custody."""

    def __init__(self, db_path: str | None = None, *, vault_store: AionLearningVaultStore | None = None) -> None:
        self.db_path = db_path  # Compatibility label only; never opened.
        self.vault_store = vault_store or AionLearningVaultStore()
        self._records: dict[str, dict[str, Any]] = {}
        for event in self.vault_store.list_events(kind="hqce_telemetry"):
            record = event.get("record")
            if isinstance(record, dict) and record.get("id"):
                self._records[str(record["id"])] = dict(record)

    def ingest_record(self, record: Dict[str, Any], session_id: str) -> None:
        tensor = record.get("tensor", {})
        record_id = str(record.get("id") or f"entry_{time.time_ns()}")
        if record_id in self._records:
            logger.debug("[HQCETelemetryDB] Duplicate record skipped: %s", record_id)
            return
        normalized = {
            "id": record_id,
            "timestamp": float(record.get("timestamp", time.time())),
            "session_id": session_id,
            "observer": record.get("observer", "HQCE_Runtime"),
            "psi": float(tensor.get("psi", 0.0)),
            "kappa": float(tensor.get("kappa", 0.0)),
            "T": float(tensor.get("T", 0.0)),
            "coherence": float(tensor.get("coherence", 0.0)),
            "stability": float(tensor.get("stability", 0.0)),
            "meta": dict(record.get("meta", {}) or {}),
        }
        if self.vault_store.enabled:
            self.vault_store.append_event(
                f"hqce-telemetry-{record_id}",
                {"event_type": "hqce_telemetry", "event_id": record_id, "timestamp": normalized["timestamp"], "record": normalized},
            )
        self._records[record_id] = normalized

    def bulk_ingest_jsonl(self, path: str, session_id: Optional[str] = None) -> int:
        source = Path(path)
        if not source.is_file():
            logger.warning("[HQCETelemetryDB] Ledger not found: %s", path)
            return 0
        resolved_session = session_id or f"session_{int(time.time())}"
        count = 0
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                record.setdefault("id", f"entry_{time.time_ns()}")
                self.ingest_record(record, resolved_session)
                count += 1
        return count

    def query_range(self, start: float, end: float) -> List[Dict[str, Any]]:
        return sorted([r.copy() for r in self._records.values() if start <= r["timestamp"] <= end], key=lambda row: row["timestamp"])

    def latest_values(self, limit: int = 20) -> List[Dict[str, Any]]:
        return sorted((r.copy() for r in self._records.values()), key=lambda row: row["timestamp"], reverse=True)[:limit]

    def summary(self) -> Dict[str, Any]:
        rows = list(self._records.values())
        def mean(key: str) -> float:
            return sum(float(row[key]) for row in rows) / len(rows) if rows else 0.0
        return {"ψ_mean": mean("psi"), "κ_mean": mean("kappa"), "C_mean": mean("coherence"), "stability_mean": mean("stability")}

    def coherence_trend(self, limit: int = 100) -> List[Tuple[float, float]]:
        return [(row["timestamp"], row["coherence"]) for row in self.latest_values(limit)]

    def export_json(self, path: str = "data/ledger/hqce_telemetry_export.json") -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = sorted(self._records.values(), key=lambda row: row["timestamp"])
        with target.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        return str(target)

    @staticmethod
    def _row_to_dict(row: Tuple[Any, ...]) -> Dict[str, Any]:
        return {"id": row[0], "timestamp": row[1], "session_id": row[2], "observer": row[3], "psi": row[4], "kappa": row[5], "T": row[6], "coherence": row[7], "stability": row[8], "meta": json.loads(row[9]) if row[9] else {}}


# Safe singleton: construction creates no database or application-tree file.
hqce_telemetry_db = HQCETelemetryDB()

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.modules.aion_equities.builders import (
    build_thesis_state_payload_minimal,
    build_write_event_envelope,
)
from backend.modules.aion_equities.investing_ids import make_thesis_id
from backend.modules.aion_equities.schema_validate import validate_payload


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _iso_z(dt: Any) -> str:
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(f"Unsupported datetime value: {dt!r}")


class ThesisStore:
    """
    File-backed runtime store for AION equities thesis state payloads.

    Layout:
      <base_dir>/
        theses/
          thesis_AHT.L_long_2026q2_pre_earnings.json
        thesis_history/
          thesis_AHT.L_long_2026q2_pre_earnings/
            2026-02-22T22-00-00Z.json
            2026-03-01T09-15-00Z.json
        write_events/
          thesis_AHT.L_long_2026q2_pre_earnings/
            decision/
              write_event_....json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.theses_dir = self.base_dir / "theses"
        self.history_dir = self.base_dir / "thesis_history"
        self.write_events_dir = self.base_dir / "write_events"
        self.theses_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.write_events_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # path helpers
    # ------------------------------------------------------------------
    def _latest_path(self, thesis_id: str) -> Path:
        return self.theses_dir / f"{_safe_segment(thesis_id)}.json"

    def _history_entity_dir(self, thesis_id: str) -> Path:
        return self.history_dir / _safe_segment(thesis_id)

    def _history_path(self, thesis_id: str, as_of: str) -> Path:
        return self._history_entity_dir(thesis_id) / f"{_safe_segment(as_of)}.json"

    def _write_event_stage_dir(self, thesis_id: str, stage: str) -> Path:
        return self.write_events_dir / _safe_segment(thesis_id) / stage

    def _write_event_path(self, thesis_id: str, stage: str, event_id: str) -> Path:
        return self._write_event_stage_dir(thesis_id, stage) / f"{_safe_segment(event_id)}.json"

    # ------------------------------------------------------------------
    # io helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # public api
    # ------------------------------------------------------------------
    def load_latest_thesis_state_by_parts(self, *, ticker: str, mode: str, window: str) -> Dict[str, Any]:
        thesis_id = make_thesis_id(ticker, mode, window)
        return self.load_latest_thesis_state(thesis_id)

    def save_thesis_state(
        self,
        *,
        thesis_id: Optional[str] = None,
        ticker: str,
        mode: str,
        window: str,
        as_of: Any,
        assessment_refs: List[str],
        status: str = "candidate",
        generated_by: str = "aion_equities.thesis_store",
        create_write_event: bool = True,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Build, validate, and persist a minimal thesis-state payload.
        """
        if thesis_id is None:
            thesis_id = make_thesis_id(ticker, mode, window)

        payload = build_thesis_state_payload_minimal(
            thesis_id=thesis_id,
            ticker=ticker,
            mode=mode,
            window=window,
            as_of=as_of,
            assessment_refs=assessment_refs,
            generated_by=generated_by,
            validate=False,
        )

        payload["status"] = status

        if validate:
            validate_payload("thesis_state", payload, version="v0_1")

        latest_path = self._latest_path(thesis_id)
        history_path = self._history_path(thesis_id, payload["as_of"])

        self._write_json(history_path, payload)
        self._write_json(latest_path, payload)

        if create_write_event:
            source_refs = assessment_refs if assessment_refs else [thesis_id]
            env = build_write_event_envelope(
                event_id=f"write_event/{thesis_id}/decision/{payload['as_of']}",
                stage="decision",
                timestamp=payload["as_of"],
                entity_id=thesis_id,
                entity_type="thesis_state",
                operation="upsert",
                payload_schema_id="thesis_state",
                payload_data=payload,
                source_kind="system",
                source_refs=source_refs,
                generated_by=generated_by,
                correlation_id=f"corr_{_safe_segment(thesis_id)}",
                validate=validate,
            )
            self._write_json(
                self._write_event_path(thesis_id, "decision", env["event_id"]),
                env,
            )

        return payload

    def update_thesis_state(
        self,
        *,
        thesis_id: str,
        patch: Dict[str, Any],
        as_of: Any,
        generated_by: str = "aion_equities.thesis_store",
        create_write_event: bool = True,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Load latest thesis state, apply a shallow patch, validate, and persist
        a new history snapshot plus latest.json.
        """
        current = self.load_latest_thesis_state(thesis_id)
        updated = dict(current)
        updated.update(patch)

        as_of_s = _iso_z(as_of)
        updated["as_of"] = as_of_s

        audit = dict(updated.get("audit", {}))
        current_audit = current.get("audit", {}) if isinstance(current.get("audit"), dict) else {}

        audit.setdefault("created_at", current_audit.get("created_at", as_of_s))
        audit.setdefault("created_by", current_audit.get("created_by", generated_by))
        audit["updated_at"] = as_of_s
        audit["updated_by"] = generated_by
        updated["audit"] = audit

        if not isinstance(updated.get("assessment_refs"), list):
            updated["assessment_refs"] = current.get("assessment_refs", [])

        if validate:
            validate_payload("thesis_state", updated, version="v0_1")

        history_path = self._history_path(thesis_id, as_of_s)
        latest_path = self._latest_path(thesis_id)

        self._write_json(history_path, updated)
        self._write_json(latest_path, updated)

        if create_write_event:
            source_refs = updated.get("assessment_refs", [])
            if not isinstance(source_refs, list) or not source_refs:
                source_refs = [thesis_id]

            env = build_write_event_envelope(
                event_id=f"write_event/{thesis_id}/decision/{as_of_s}",
                stage="decision",
                timestamp=as_of_s,
                entity_id=thesis_id,
                entity_type="thesis_state",
                operation="update",
                payload_schema_id="thesis_state",
                payload_data=updated,
                source_kind="system",
                source_refs=source_refs,
                generated_by=generated_by,
                correlation_id=f"corr_{_safe_segment(thesis_id)}_{_safe_segment(as_of_s)}",
                validate=validate,
            )
            self._write_json(
                self._write_event_path(thesis_id, "decision", env["event_id"]),
                env,
            )

        return updated

    def load_latest_thesis_state(self, thesis_id: str) -> Dict[str, Any]:
        path = self._latest_path(thesis_id)
        if not path.exists():
            raise FileNotFoundError(f"No latest thesis state found for {thesis_id}")
        return self._read_json(path)

    def load_thesis_state_at(self, thesis_id: str, as_of: str) -> Dict[str, Any]:
        path = self._history_path(thesis_id, as_of)
        if not path.exists():
            raise FileNotFoundError(f"No thesis history entry found for {thesis_id} at {as_of}")
        return self._read_json(path)

    def thesis_exists(self, thesis_id: str) -> bool:
        return self._latest_path(thesis_id).exists()

    def list_thesis_history(self, thesis_id: str) -> List[str]:
        p = self._history_entity_dir(thesis_id)
        if not p.exists():
            return []
        return sorted(x.stem for x in p.glob("*.json"))

    def load_write_events(self, thesis_id: str, stage: str = "decision") -> List[Dict[str, Any]]:
        stage_dir = self._write_event_stage_dir(thesis_id, stage)
        if not stage_dir.exists():
            return []
        return [self._read_json(p) for p in sorted(stage_dir.glob("*.json"))]
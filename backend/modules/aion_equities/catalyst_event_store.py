from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.investing_ids import (
    make_catalyst_event_id,
    make_company_id,
)
from backend.modules.aion_equities.schema_validate import validate_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value[:10]
    raise ValueError(f"Unsupported date value: {value!r}")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


class CatalystEventStore:
    """
    File-backed runtime store for AION equities catalyst events.

    Layout:
      <base_dir>/
        catalyst_events/
          company_AHT.L_catalyst_earnings_2026-06-18.json
        catalyst_events_by_company/
          company_AHT.L/
            company_AHT.L_catalyst_earnings_2026-06-18.json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.events_dir = self.base_dir / "catalyst_events"
        self.by_company_dir = self.base_dir / "catalyst_events_by_company"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.by_company_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # path helpers
    # ------------------------------------------------------------------
    def _event_path(self, catalyst_event_id: str) -> Path:
        return self.events_dir / f"{_safe_segment(catalyst_event_id)}.json"

    def _company_dir(self, company_ref: str) -> Path:
        return self.by_company_dir / _safe_segment(company_ref)

    def _company_event_path(self, company_ref: str, catalyst_event_id: str) -> Path:
        return self._company_dir(company_ref) / f"{_safe_segment(catalyst_event_id)}.json"

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
    # payload builder
    # ------------------------------------------------------------------
    def build_catalyst_event_payload(
        self,
        *,
        ticker: Optional[str] = None,
        company_ref: Optional[str] = None,
        event_id: Optional[str] = None,
        catalyst_event_id: Optional[str] = None,
        catalyst_type: str,
        status: str,
        expected_date: Any,
        timing_confidence: float,
        thesis_refs: Optional[List[str]] = None,
        importance: Optional[float] = None,
        window_start: Optional[Any] = None,
        window_end: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        preconditions: Optional[List[str]] = None,
        outcome: Optional[Dict[str, Any]] = None,
        source_refs: Optional[List[str]] = None,
        created_by: str = "aion_equities.catalyst_event_store",
        created_at: Optional[Any] = None,
        updated_at: Optional[Any] = None,
        updated_by: Optional[str] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        if company_ref is None:
            if not ticker:
                raise ValueError("ticker or company_ref is required")
            company_ref = make_company_id(ticker)

        if catalyst_event_id is None:
            if not event_id:
                raise ValueError("event_id or catalyst_event_id is required")
            if ticker:
                catalyst_event_id = make_catalyst_event_id(ticker, event_id)
            else:
                t = company_ref.split("/", 1)[1]
                catalyst_event_id = make_catalyst_event_id(t, event_id)

        created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
        updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

        payload: Dict[str, Any] = {
            "catalyst_event_id": catalyst_event_id,
            "company_ref": company_ref,
            "catalyst_type": catalyst_type,
            "status": status,
            "expected_date": _date_str(expected_date),
            "timing_confidence": float(timing_confidence),
            "thesis_refs": thesis_refs or [],
            "audit": {
                "created_at": created_at_s,
                "updated_at": updated_at_s,
                "created_by": created_by,
            },
        }

        if updated_by:
            payload["audit"]["updated_by"] = updated_by
        if importance is not None:
            payload["importance"] = float(importance)
        if window_start is not None:
            payload["window_start"] = _date_str(window_start)
        if window_end is not None:
            payload["window_end"] = _date_str(window_end)
        if details is not None:
            payload["details"] = details
        if preconditions is not None:
            payload["preconditions"] = preconditions
        if outcome is not None:
            payload["outcome"] = outcome
        if source_refs is not None:
            payload["source_refs"] = source_refs

        if validate:
            validate_payload("catalyst_event", payload, version=SCHEMA_PACK_VERSION)

        return payload

    # ------------------------------------------------------------------
    # public api
    # ------------------------------------------------------------------
    def save_catalyst_event(
        self,
        *,
        ticker: Optional[str] = None,
        company_ref: Optional[str] = None,
        event_id: Optional[str] = None,
        catalyst_event_id: Optional[str] = None,
        catalyst_type: str,
        status: str = "scheduled",
        expected_date: Any,
        timing_confidence: float = 50.0,
        thesis_refs: Optional[List[str]] = None,
        importance: Optional[float] = None,
        window_start: Optional[Any] = None,
        window_end: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        preconditions: Optional[List[str]] = None,
        outcome: Optional[Dict[str, Any]] = None,
        source_refs: Optional[List[str]] = None,
        catalyst_payload_patch: Optional[Dict[str, Any]] = None,
        generated_by: str = "aion_equities.catalyst_event_store",
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = self.build_catalyst_event_payload(
            ticker=ticker,
            company_ref=company_ref,
            event_id=event_id,
            catalyst_event_id=catalyst_event_id,
            catalyst_type=catalyst_type,
            status=status,
            expected_date=expected_date,
            timing_confidence=timing_confidence,
            thesis_refs=thesis_refs,
            importance=importance,
            window_start=window_start,
            window_end=window_end,
            details=details,
            preconditions=preconditions,
            outcome=outcome,
            source_refs=source_refs,
            created_by=generated_by,
            updated_by=generated_by,
            validate=False,
        )

        if catalyst_payload_patch:
            payload = _deep_merge(payload, catalyst_payload_patch)

        if validate:
            validate_payload("catalyst_event", payload, version=SCHEMA_PACK_VERSION)

        self._write_json(self._event_path(payload["catalyst_event_id"]), payload)
        self._write_json(
            self._company_event_path(payload["company_ref"], payload["catalyst_event_id"]),
            payload,
        )
        return payload

    def load_catalyst_event(self, catalyst_event_id: str, *, validate: bool = True) -> Dict[str, Any]:
        path = self._event_path(catalyst_event_id)
        if not path.exists():
            raise FileNotFoundError(f"No catalyst event found for {catalyst_event_id}")
        payload = self._read_json(path)
        if validate:
            validate_payload("catalyst_event", payload, version=SCHEMA_PACK_VERSION)
        return payload

    def catalyst_event_exists(self, catalyst_event_id: str) -> bool:
        return self._event_path(catalyst_event_id).exists()

    def list_catalyst_events(self, company_ref: str) -> List[str]:
        p = self._company_dir(company_ref)
        if not p.exists():
            return []
        out: List[str] = []
        for fp in sorted(p.glob("*.json")):
            payload = self._read_json(fp)
            out.append(payload["catalyst_event_id"])
        return out
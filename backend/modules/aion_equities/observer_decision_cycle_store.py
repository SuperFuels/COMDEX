from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


def _iso_z(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "observer_decision_cycles"


class ObserverDecisionCycleStore:
    """
    File-backed runtime store for observer decision cycle payloads.

    Layout:
      <base_dir>/
        observer_decision_cycles/
          thesis_AHT.L_long_2026Q2_pre_earnings/
            observer_cycle_2026-02-22T22-00-00Z.json
            observer_cycle_2026-03-01T09-15-00Z.json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.cycles_dir = self.base_dir / "observer_decision_cycles"
        self.cycles_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # path helpers
    # ------------------------------------------------------------------
    def _thesis_dir(self, thesis_id: str) -> Path:
        return self.cycles_dir / _safe_segment(thesis_id)

    def _cycle_path(self, thesis_id: str, observer_cycle_id: str) -> Path:
        return self._thesis_dir(thesis_id) / f"{_safe_segment(observer_cycle_id)}.json"

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
    def build_cycle_payload(
        self,
        *,
        thesis_id: str,
        timestamp: Any,
        process_quality_score: float,
        process_notes: str = "",
        gate_adherence: Optional[bool] = None,
        evidence_completeness: Optional[float] = None,
        outcome_known: bool = False,
        outcome_score: Optional[float] = None,
        return_pct: Optional[float] = None,
        max_adverse_excursion_pct: Optional[float] = None,
        max_favorable_excursion_pct: Optional[float] = None,
        timing_validity: Optional[str] = None,
        thesis_validity: Optional[str] = None,
        confidence_inflation_score: Optional[float] = None,
        thesis_lock_in_score: Optional[float] = None,
        recency_bias_score: Optional[float] = None,
        catalyst_timing_error_days: Optional[int] = None,
        collapse_timing_error_score: Optional[float] = None,
        drift_warning_effective: Optional[bool] = None,
        sector_ref: Optional[str] = None,
        false_positive_bucket: Optional[bool] = None,
        observer_cycle_id: Optional[str] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        ts = _iso_z(timestamp)
        cycle_id = observer_cycle_id or f"observer_cycle/{_safe_segment(thesis_id)}/{ts}"

        payload: Dict[str, Any] = {
            "observer_cycle_id": cycle_id,
            "thesis_id": thesis_id,
            "timestamp": ts,
            "process_quality": {
                "score": float(process_quality_score),
            },
            "outcome_quality": {
                "known": bool(outcome_known),
            },
            "bias_metrics": {},
            "timing_metrics": {},
        }

        if process_notes:
            payload["process_quality"]["notes"] = process_notes
        if gate_adherence is not None:
            payload["process_quality"]["gate_adherence"] = bool(gate_adherence)
        if evidence_completeness is not None:
            payload["process_quality"]["evidence_completeness"] = float(evidence_completeness)

        if outcome_score is not None:
            payload["outcome_quality"]["score"] = float(outcome_score)
        if return_pct is not None:
            payload["outcome_quality"]["return_pct"] = float(return_pct)
        if max_adverse_excursion_pct is not None:
            payload["outcome_quality"]["max_adverse_excursion_pct"] = float(max_adverse_excursion_pct)
        if max_favorable_excursion_pct is not None:
            payload["outcome_quality"]["max_favorable_excursion_pct"] = float(max_favorable_excursion_pct)
        if timing_validity is not None:
            payload["outcome_quality"]["timing_validity"] = timing_validity
        if thesis_validity is not None:
            payload["outcome_quality"]["thesis_validity"] = thesis_validity

        if confidence_inflation_score is not None:
            payload["bias_metrics"]["confidence_inflation_score"] = float(confidence_inflation_score)
        if thesis_lock_in_score is not None:
            payload["bias_metrics"]["thesis_lock_in_score"] = float(thesis_lock_in_score)
        if recency_bias_score is not None:
            payload["bias_metrics"]["recency_bias_score"] = float(recency_bias_score)

        if catalyst_timing_error_days is not None:
            payload["timing_metrics"]["catalyst_timing_error_days"] = int(catalyst_timing_error_days)
        if collapse_timing_error_score is not None:
            payload["timing_metrics"]["collapse_timing_error_score"] = float(collapse_timing_error_score)
        if drift_warning_effective is not None:
            payload["timing_metrics"]["drift_warning_effective"] = bool(drift_warning_effective)

        if sector_ref is not None or false_positive_bucket is not None:
            payload["sector_metrics"] = {}
            if sector_ref is not None:
                payload["sector_metrics"]["sector_ref"] = sector_ref
            if false_positive_bucket is not None:
                payload["sector_metrics"]["false_positive_bucket"] = bool(false_positive_bucket)

        if validate:
            validate_payload("observer_decision_cycle", payload, version=SCHEMA_PACK_VERSION)

        return payload

    # ------------------------------------------------------------------
    # public api
    # ------------------------------------------------------------------
    def save_cycle(
        self,
        *,
        thesis_id: str,
        timestamp: Any,
        process_quality_score: float,
        process_notes: str = "",
        gate_adherence: Optional[bool] = None,
        evidence_completeness: Optional[float] = None,
        outcome_known: bool = False,
        outcome_score: Optional[float] = None,
        return_pct: Optional[float] = None,
        max_adverse_excursion_pct: Optional[float] = None,
        max_favorable_excursion_pct: Optional[float] = None,
        timing_validity: Optional[str] = None,
        thesis_validity: Optional[str] = None,
        confidence_inflation_score: Optional[float] = None,
        thesis_lock_in_score: Optional[float] = None,
        recency_bias_score: Optional[float] = None,
        catalyst_timing_error_days: Optional[int] = None,
        collapse_timing_error_score: Optional[float] = None,
        drift_warning_effective: Optional[bool] = None,
        sector_ref: Optional[str] = None,
        false_positive_bucket: Optional[bool] = None,
        observer_cycle_id: Optional[str] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = self.build_cycle_payload(
            thesis_id=thesis_id,
            timestamp=timestamp,
            process_quality_score=process_quality_score,
            process_notes=process_notes,
            gate_adherence=gate_adherence,
            evidence_completeness=evidence_completeness,
            outcome_known=outcome_known,
            outcome_score=outcome_score,
            return_pct=return_pct,
            max_adverse_excursion_pct=max_adverse_excursion_pct,
            max_favorable_excursion_pct=max_favorable_excursion_pct,
            timing_validity=timing_validity,
            thesis_validity=thesis_validity,
            confidence_inflation_score=confidence_inflation_score,
            thesis_lock_in_score=thesis_lock_in_score,
            recency_bias_score=recency_bias_score,
            catalyst_timing_error_days=catalyst_timing_error_days,
            collapse_timing_error_score=collapse_timing_error_score,
            drift_warning_effective=drift_warning_effective,
            sector_ref=sector_ref,
            false_positive_bucket=false_positive_bucket,
            observer_cycle_id=observer_cycle_id,
            validate=validate,
        )

        path = self._cycle_path(thesis_id, payload["observer_cycle_id"])
        self._write_json(path, payload)
        return payload

    def load_cycle(self, thesis_id: str, observer_cycle_id: str, *, validate: bool = True) -> Dict[str, Any]:
        path = self._cycle_path(thesis_id, observer_cycle_id)
        if not path.exists():
            raise FileNotFoundError(f"No observer cycle found for {thesis_id} / {observer_cycle_id}")
        payload = self._read_json(path)
        if validate:
            validate_payload("observer_decision_cycle", payload, version=SCHEMA_PACK_VERSION)
        return payload

    def list_cycles(self, thesis_id: str) -> List[str]:
        p = self._thesis_dir(thesis_id)
        if not p.exists():
            return []
        return sorted(x.stem for x in p.glob("*.json"))

    def cycle_exists(self, thesis_id: str, observer_cycle_id: str) -> bool:
        return self._cycle_path(thesis_id, observer_cycle_id).exists()
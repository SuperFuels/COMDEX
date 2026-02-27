from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        s = value.strip()
        if len(s) == 10:
            return f"{s}T00:00:00Z"
        return s
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        return _iso_z(value)[:10]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 10:
            return s[:10]
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


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "top_down_levers"


def top_down_snapshot_storage_path(snapshot_date: Any, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    ds = _date_str(snapshot_date)
    return root / f"{_safe_segment(ds)}.json"


def build_top_down_snapshot_payload(
    *,
    snapshot_date: Any,
    regime_ref: str = "macro/regime/unknown",
    regime_state: str = "transitioning",
    active_levers: Optional[List[Dict[str, Any]]] = None,
    cascade_implications: Optional[List[Dict[str, Any]]] = None,
    sector_posture: Optional[List[Dict[str, Any]]] = None,
    watchlist_impacts: Optional[List[Dict[str, Any]]] = None,
    conviction_state: Optional[Dict[str, Any]] = None,
    generated_by: str = "aion_equities.top_down_levers_store",
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    snapshot_date_s = _date_str(snapshot_date)
    timestamp_s = _iso_z(snapshot_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "snapshot_id": f"top_down/{snapshot_date_s}",
        "timestamp": timestamp_s,
        "regime_ref": regime_ref,
        "regime_state": regime_state,
        "active_levers": active_levers or [
            {
                "lever": "dollar",
                "direction": "mixed",
                "materiality": 50.0,
                "note": "bootstrap placeholder",
            }
        ],
        "cascade_implications": cascade_implications or [],
        "sector_posture": sector_posture or [],
        "watchlist_impacts": watchlist_impacts or [],
        "conviction_state": conviction_state or {
            "signal_coherence": 50.0,
            "uncertainty_score": 50.0,
            "summary": "bootstrap",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_top_down_snapshot_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)

    path = top_down_snapshot_storage_path(payload["timestamp"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_top_down_snapshot_payload(
    snapshot_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = top_down_snapshot_storage_path(snapshot_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Top-down snapshot payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)
    return payload


class TopDownLeversStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "top_down_levers"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, snapshot_date: Any) -> Path:
        return top_down_snapshot_storage_path(snapshot_date, base_dir=self.base_dir)

    def save_snapshot(
        self,
        *,
        snapshot_date: Any,
        regime_ref: str = "macro/regime/unknown",
        regime_state: str = "transitioning",
        active_levers: Optional[List[Dict[str, Any]]] = None,
        cascade_implications: Optional[List[Dict[str, Any]]] = None,
        sector_posture: Optional[List[Dict[str, Any]]] = None,
        watchlist_impacts: Optional[List[Dict[str, Any]]] = None,
        conviction_state: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        generated_by: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        snapshot_id: Optional[str] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        actor = created_by or generated_by or "aion_equities.top_down_levers_store"

        effective_patch = deepcopy(payload_patch or {})
        if snapshot_id:
            effective_patch["snapshot_id"] = snapshot_id

        payload = build_top_down_snapshot_payload(
            snapshot_date=snapshot_date,
            regime_ref=regime_ref,
            regime_state=regime_state,
            active_levers=active_levers,
            cascade_implications=cascade_implications,
            sector_posture=sector_posture,
            watchlist_impacts=watchlist_impacts,
            conviction_state=conviction_state,
            generated_by=actor,
            payload_patch=effective_patch if effective_patch else None,
            validate=validate,
        )
        save_top_down_snapshot_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def save_top_down_snapshot(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_snapshot(**kwargs)

    def load_snapshot(self, snapshot_date: Any, *, validate: bool = True) -> Dict[str, Any]:
        return load_top_down_snapshot_payload(snapshot_date, base_dir=self.base_dir, validate=validate)

    def load_snapshot_by_id(self, snapshot_id: str, *, validate: bool = True) -> Dict[str, Any]:
        parts = str(snapshot_id).split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid snapshot_id: {snapshot_id!r}")
        return self.load_snapshot(parts[-1], validate=validate)

    def snapshot_exists(self, snapshot_date: Any) -> bool:
        return self.storage_path(snapshot_date).exists()

    def list_snapshots(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
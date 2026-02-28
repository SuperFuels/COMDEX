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
    if isinstance(value, str):
        return value
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
    return Path(__file__).resolve().parent / "data" / "credit_trajectory"


def credit_trajectory_storage_path(
    entity_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(entity_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


def build_credit_trajectory_payload(
    *,
    entity_ref: str,
    entity_type: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.credit_trajectory_store",
    official_rating_patch: Optional[Dict[str, Any]] = None,
    shadow_rating_patch: Optional[Dict[str, Any]] = None,
    trajectory_patch: Optional[Dict[str, Any]] = None,
    signals_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "credit_trajectory_id": f"{entity_ref}/credit/{as_of_date_s}",
        "entity_ref": entity_ref,
        "entity_type": entity_type,
        "as_of_date": as_of_date_s,
        "official_rating": {
            "composite": "NR",
            "outlook": "unknown",
        },
        "shadow_rating": {
            "composite": "NR",
            "confidence": 0.0,
            "direction": "unknown",
            "notes": "",
        },
        "trajectory": {
            "state": "unknown",
            "downgrade_risk": 0.0,
            "upgrade_potential": 0.0,
            "watch_window_days": 0,
            "notes": "",
        },
        "signals": {
            "leverage_signal": "unknown",
            "coverage_signal": "unknown",
            "liquidity_signal": "unknown",
            "spread_signal": "unknown",
            "refinancing_signal": "unknown",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if official_rating_patch:
        payload["official_rating"] = _deep_merge(payload["official_rating"], official_rating_patch)
    if shadow_rating_patch:
        payload["shadow_rating"] = _deep_merge(payload["shadow_rating"], shadow_rating_patch)
    if trajectory_patch:
        payload["trajectory"] = _deep_merge(payload["trajectory"], trajectory_patch)
    if signals_patch:
        payload["signals"] = _deep_merge(payload["signals"], signals_patch)
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_credit_trajectory_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)

    path = credit_trajectory_storage_path(
        payload["entity_ref"],
        payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_credit_trajectory_payload(
    entity_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = credit_trajectory_storage_path(entity_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Credit trajectory payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)
    return payload


class CreditTrajectoryStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "credit_trajectory"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, entity_ref: str, as_of_date: Any) -> Path:
        return credit_trajectory_storage_path(entity_ref, as_of_date, base_dir=self.base_dir)

    def save_credit_trajectory(
        self,
        *,
        entity_ref: str,
        entity_type: str,
        as_of_date: Any,
        generated_by: str = "aion_equities.credit_trajectory_store",
        official_rating_patch: Optional[Dict[str, Any]] = None,
        shadow_rating_patch: Optional[Dict[str, Any]] = None,
        trajectory_patch: Optional[Dict[str, Any]] = None,
        signals_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_credit_trajectory_payload(
            entity_ref=entity_ref,
            entity_type=entity_type,
            as_of_date=as_of_date,
            generated_by=generated_by,
            official_rating_patch=official_rating_patch,
            shadow_rating_patch=shadow_rating_patch,
            trajectory_patch=trajectory_patch,
            signals_patch=signals_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_credit_trajectory_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def save_profile(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_credit_trajectory(**kwargs)

    def load_credit_trajectory(
        self,
        entity_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_credit_trajectory_payload(
            entity_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_profile(
        self,
        entity_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_credit_trajectory(entity_ref, as_of_date, validate=validate)

    def credit_trajectory_exists(self, entity_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(entity_ref, as_of_date).exists()

    def profile_exists(self, entity_ref: str, as_of_date: Any) -> bool:
        return self.credit_trajectory_exists(entity_ref, as_of_date)

    def list_credit_trajectories(self, entity_ref: str) -> List[str]:
        entity_dir = self.base_dir / _safe_segment(entity_ref)
        if not entity_dir.exists():
            return []
        return sorted(p.stem for p in entity_dir.glob("*.json"))

    def list_profiles(self, entity_ref: str) -> List[str]:
        return self.list_credit_trajectories(entity_ref)
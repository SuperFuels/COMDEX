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


def _slug(value: str) -> str:
    s = str(value).strip().lower()
    s = s.replace("&", " and ")
    s = s.replace("/", "_").replace("\\", "_").replace(" ", "_").replace("-", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "sector_templates"


def sector_template_storage_path(
    sector_ref: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(sector_ref)}.json"


def build_sector_template_payload(
    *,
    sector_ref: str,
    sector_name: str,
    as_of_date: Any,
    created_by: str = "aion_equities.sector_template_store",
    variable_map_patch: Optional[Dict[str, Any]] = None,
    reporting_template_patch: Optional[Dict[str, Any]] = None,
    fingerprint_defaults_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    updated_by: Optional[str] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "sector_template_id": f"sector_template/{_slug(sector_ref.removeprefix('sector/'))}",
        "sector_ref": sector_ref,
        "sector_name": sector_name,
        "as_of_date": as_of_date_s,
        "variable_map": {
            "primary_variables": [],
            "secondary_variables": [],
        },
        "reporting_template": {
            "core_metrics": [],
            "margin_focus": [],
            "cash_flow_focus": [],
            "balance_sheet_focus": [],
            "management_signals": [],
        },
        "fingerprint_defaults": {
            "expected_report_count_for_calibration": 20,
            "base_predictability": "medium",
            "seasonality_strength": "unknown",
            "macro_sensitivity": "medium",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": created_by,
        },
    }

    if updated_by:
        payload["audit"]["updated_by"] = updated_by
    if variable_map_patch:
        payload["variable_map"] = _deep_merge(payload["variable_map"], variable_map_patch)
    if reporting_template_patch:
        payload["reporting_template"] = _deep_merge(payload["reporting_template"], reporting_template_patch)
    if fingerprint_defaults_patch:
        payload["fingerprint_defaults"] = _deep_merge(payload["fingerprint_defaults"], fingerprint_defaults_patch)
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("sector_template", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_sector_template_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("sector_template", payload, version=SCHEMA_PACK_VERSION)

    path = sector_template_storage_path(payload["sector_ref"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_sector_template_payload(
    sector_ref: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = sector_template_storage_path(sector_ref, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Sector template payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("sector_template", payload, version=SCHEMA_PACK_VERSION)
    return payload


class SectorTemplateStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "sector_templates"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, sector_ref: str) -> Path:
        return sector_template_storage_path(sector_ref, base_dir=self.base_dir)

    def save_sector_template(
        self,
        *,
        sector_ref: str,
        sector_name: str,
        as_of_date: Any,
        created_by: str = "aion_equities.sector_template_store",
        variable_map_patch: Optional[Dict[str, Any]] = None,
        reporting_template_patch: Optional[Dict[str, Any]] = None,
        fingerprint_defaults_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_sector_template_payload(
            sector_ref=sector_ref,
            sector_name=sector_name,
            as_of_date=as_of_date,
            created_by=created_by,
            variable_map_patch=variable_map_patch,
            reporting_template_patch=reporting_template_patch,
            fingerprint_defaults_patch=fingerprint_defaults_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_sector_template_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def load_sector_template(self, sector_ref: str, *, validate: bool = True) -> Dict[str, Any]:
        return load_sector_template_payload(sector_ref, base_dir=self.base_dir, validate=validate)

    def sector_template_exists(self, sector_ref: str) -> bool:
        return self.storage_path(sector_ref).exists()

    def list_sector_templates(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
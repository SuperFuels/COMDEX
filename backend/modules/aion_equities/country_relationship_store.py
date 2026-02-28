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
    return Path(__file__).resolve().parent / "data" / "country_relationships"


def _normalize_country_code(value: str) -> str:
    s = str(value).strip().upper()
    if len(s) != 2 or not s.isalpha():
        raise ValueError(f"Country code must be 2 letters, got {value!r}")
    return s


def _relationship_id(lhs_country_code: str, rhs_country_code: str) -> str:
    lhs = _normalize_country_code(lhs_country_code)
    rhs = _normalize_country_code(rhs_country_code)
    return f"country_relationship/{lhs}-{rhs}"


def country_relationship_storage_path(
    lhs_country_code: str,
    rhs_country_code: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    rid = _relationship_id(lhs_country_code, rhs_country_code)
    return root / f"{_safe_segment(rid)}.json"


def build_country_relationship_payload(
    *,
    lhs_country_code: str,
    rhs_country_code: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.country_relationship_store",
    relationship_score_patch: Optional[Dict[str, Any]] = None,
    relationship_drift_patch: Optional[Dict[str, Any]] = None,
    trade_policy_patch: Optional[Dict[str, Any]] = None,
    geopolitics_patch: Optional[Dict[str, Any]] = None,
    yield_differential_patch: Optional[Dict[str, Any]] = None,
    capital_flows_patch: Optional[Dict[str, Any]] = None,
    risk_flags: Optional[List[str]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    lhs = _normalize_country_code(lhs_country_code)
    rhs = _normalize_country_code(rhs_country_code)
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "country_relationship_id": _relationship_id(lhs, rhs),
        "lhs_country_ref": f"country/{lhs}",
        "rhs_country_ref": f"country/{rhs}",
        "as_of_date": as_of_date_s,
        "relationship_score": {
            "score": 50.0,
            "confidence": 50.0,
            "regime": "balanced",
            "summary": "",
        },
        "relationship_drift": {
            "direction": "stable",
            "velocity": "slow",
            "notes": "",
        },
        "trade_policy": {
            "tariff_regime": "open",
            "trade_alignment": "aligned",
            "export_dependency_regime": "medium",
            "import_dependency_regime": "medium",
            "notes": "",
        },
        "geopolitics": {
            "alignment_regime": "cooperative",
            "policy_coordination": "working",
            "sanctions_risk": "low",
            "notes": "",
        },
        "yield_differential": {
            "front_end_bps": 0.0,
            "long_end_bps": 0.0,
            "real_yield_diff_bps": 0.0,
            "carry_regime": "balanced",
            "notes": "",
        },
        "capital_flows": {
            "pair_flow_regime": "balanced",
            "funding_stress_regime": "calm",
            "notes": "",
        },
        "risk_flags": sorted(set(risk_flags or [])),
        "linked_refs": {
            "lhs_ambassador_ref": f"country/{lhs}",
            "rhs_ambassador_ref": f"country/{rhs}",
            "macro_regime_refs": [],
            "company_refs": [],
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if relationship_score_patch:
        payload["relationship_score"] = _deep_merge(payload["relationship_score"], relationship_score_patch)
    if relationship_drift_patch:
        payload["relationship_drift"] = _deep_merge(payload["relationship_drift"], relationship_drift_patch)
    if trade_policy_patch:
        payload["trade_policy"] = _deep_merge(payload["trade_policy"], trade_policy_patch)
    if geopolitics_patch:
        payload["geopolitics"] = _deep_merge(payload["geopolitics"], geopolitics_patch)
    if yield_differential_patch:
        payload["yield_differential"] = _deep_merge(payload["yield_differential"], yield_differential_patch)
    if capital_flows_patch:
        payload["capital_flows"] = _deep_merge(payload["capital_flows"], capital_flows_patch)
    if linked_refs_patch:
        payload["linked_refs"] = _deep_merge(payload["linked_refs"], linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("country_relationship", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_country_relationship_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("country_relationship", payload, version=SCHEMA_PACK_VERSION)

    lhs = payload["lhs_country_ref"].split("/")[-1]
    rhs = payload["rhs_country_ref"].split("/")[-1]
    path = country_relationship_storage_path(lhs, rhs, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_country_relationship_payload(
    lhs_country_code: str,
    rhs_country_code: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = country_relationship_storage_path(lhs_country_code, rhs_country_code, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Country relationship payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("country_relationship", payload, version=SCHEMA_PACK_VERSION)
    return payload


class CountryRelationshipStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "country_relationships"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, lhs_country_code: str, rhs_country_code: str) -> Path:
        return country_relationship_storage_path(lhs_country_code, rhs_country_code, base_dir=self.base_dir)

    def save_country_relationship(
        self,
        *,
        lhs_country_code: str,
        rhs_country_code: str,
        as_of_date: Any,
        generated_by: str = "aion_equities.country_relationship_store",
        relationship_score_patch: Optional[Dict[str, Any]] = None,
        relationship_drift_patch: Optional[Dict[str, Any]] = None,
        trade_policy_patch: Optional[Dict[str, Any]] = None,
        geopolitics_patch: Optional[Dict[str, Any]] = None,
        yield_differential_patch: Optional[Dict[str, Any]] = None,
        capital_flows_patch: Optional[Dict[str, Any]] = None,
        risk_flags: Optional[List[str]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_country_relationship_payload(
            lhs_country_code=lhs_country_code,
            rhs_country_code=rhs_country_code,
            as_of_date=as_of_date,
            generated_by=generated_by,
            relationship_score_patch=relationship_score_patch,
            relationship_drift_patch=relationship_drift_patch,
            trade_policy_patch=trade_policy_patch,
            geopolitics_patch=geopolitics_patch,
            yield_differential_patch=yield_differential_patch,
            capital_flows_patch=capital_flows_patch,
            risk_flags=risk_flags,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_country_relationship_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def load_country_relationship(
        self,
        lhs_country_code: str,
        rhs_country_code: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_country_relationship_payload(
            lhs_country_code,
            rhs_country_code,
            base_dir=self.base_dir,
            validate=validate,
        )

    def country_relationship_exists(self, lhs_country_code: str, rhs_country_code: str) -> bool:
        return self.storage_path(lhs_country_code, rhs_country_code).exists()

    def list_country_relationships(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
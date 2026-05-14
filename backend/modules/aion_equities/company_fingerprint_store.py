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
    return Path(__file__).resolve().parent / "data" / "company_fingerprints"


def company_fingerprint_storage_path(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


def _importance_to_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    mapping = {
        "primary": 90.0,
        "secondary": 60.0,
        "high": 80.0,
        "medium": 50.0,
        "low": 25.0,
        "critical": 95.0,
    }
    return float(mapping.get(str(value).strip().lower(), 50.0))


def _normalize_driver_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, str):
        return {
            "name": item,
            "importance": 50.0,
        }

    if not isinstance(item, dict):
        return {
            "name": str(item),
            "importance": 50.0,
        }

    out: Dict[str, Any] = {
        "name": item.get("name", item.get("driver_name", item.get("driver", "unknown"))),
        "importance": _importance_to_score(item.get("importance", "medium")),
    }

    if "source_series" in item:
        out["source_series"] = item["source_series"]
    elif "driver_type" in item:
        out["source_series"] = str(item["driver_type"])
    elif "type" in item:
        out["source_series"] = str(item["type"])

    if "notes" in item:
        out["notes"] = item["notes"]
    elif "summary" in item:
        out["notes"] = item["summary"]

    return out


def _normalize_driver_map_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)
    out.pop("driver_notes", None)

    if isinstance(out.get("primary_drivers"), list):
        out["primary_drivers"] = [_normalize_driver_item(x) for x in out["primary_drivers"]]

    if isinstance(out.get("secondary_drivers"), list):
        out["secondary_drivers"] = [_normalize_driver_item(x) for x in out["secondary_drivers"]]

    return out


def _normalize_lag_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        out = {
            "driver": item.get("driver", item.get("variable", "unknown")),
            "lag_days": int(item.get("lag_days", item.get("lag_business_days", 0))),
        }
        if "confidence" in item:
            out["confidence"] = float(item["confidence"])
        return out

    return {
        "driver": str(item),
        "lag_days": 0,
    }


def _normalize_lag_structure_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)
    out.pop("lag_notes", None)

    if "primary_variable_lags" in out and "driver_lags" not in out:
        out["driver_lags"] = deepcopy(out.pop("primary_variable_lags"))
    else:
        out.pop("primary_variable_lags", None)

    out.pop("secondary_variable_lags", None)

    if isinstance(out.get("driver_lags"), list):
        out["driver_lags"] = [_normalize_lag_item(x) for x in out["driver_lags"]]

    return out


def _normalize_sensitivity_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        out = {
            "driver": item.get("driver", item.get("variable", "unknown")),
            "target_metric": item.get("target_metric", "revenue"),
            "coefficient": float(item.get("coefficient", item.get("magnitude", 0.0))),
        }
        if "units" in item:
            out["units"] = item["units"]
        if "confidence" in item:
            out["confidence"] = float(item["confidence"])
        if "notes" in item:
            out["notes"] = item["notes"]
        return out

    return {
        "driver": str(item),
        "target_metric": "revenue",
        "coefficient": 0.0,
    }


def _normalize_sensitivity_model_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    if "sensitivity_coefficients" in out and "coefficients" not in out:
        out["coefficients"] = deepcopy(out.pop("sensitivity_coefficients"))
    else:
        out.pop("sensitivity_coefficients", None)

    if "variable_sensitivities" in out and "coefficients" not in out:
        out["coefficients"] = deepcopy(out.pop("variable_sensitivities"))
    else:
        out.pop("variable_sensitivities", None)

    if isinstance(out.get("coefficients"), list):
        out["coefficients"] = [_normalize_sensitivity_item(x) for x in out["coefficients"]]

    return out


def _normalize_guidance_behaviour_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    normalized: Dict[str, Any] = {}

    if "credibility" in out:
        normalized["credibility"] = out["credibility"]

    style = out.get("guidance_style")
    bias_dir = out.get("bias_direction")
    beat_miss_bias = out.get("beat_miss_bias")

    if "bias" in out:
        normalized["bias"] = out["bias"]
    elif style in {"conservative", "balanced", "optimistic", "unknown"}:
        normalized["bias"] = style
    elif bias_dir == "slightly_underpromise":
        normalized["bias"] = "conservative"
    elif bias_dir == "slightly_overpromise":
        normalized["bias"] = "optimistic"
    elif beat_miss_bias in {"conservative", "balanced", "optimistic", "unknown"}:
        normalized["bias"] = beat_miss_bias

    if "stability" in out:
        normalized["stability"] = out["stability"]
    else:
        normalized["stability"] = "stable"

    if "notes" in out:
        normalized["notes"] = out["notes"]
    elif "guidance_notes" in out:
        normalized["notes"] = out["guidance_notes"]

    for k, v in out.items():
        if k not in {
            "credibility",
            "guidance_style",
            "bias_direction",
            "beat_miss_bias",
            "stability",
            "notes",
            "guidance_notes",
        }:
            normalized[k] = v

    return normalized


def _normalize_fingerprint_summary_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    if "key_watch_items" in out:
        out.pop("key_watch_items", None)
    if "predictability_regime" in out:
        out.pop("predictability_regime", None)
    if "watch_items" in out:
        out.pop("watch_items", None)
    if "predictability_state" in out:
        out.pop("predictability_state", None)

    return out


def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    if "structural_profile_refs" in out and "company_profile_refs" not in out:
        out["company_profile_refs"] = deepcopy(out.pop("structural_profile_refs"))
    else:
        out.pop("structural_profile_refs", None)

    return out


def _build_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    out["fingerprint_id"] = out["company_fingerprint_id"]

    driver_map = out.get("driver_map", {})
    if isinstance(driver_map, dict):
        driver_map["primary_drivers"] = [x.get("name") for x in driver_map.get("primary_drivers", [])]
        driver_map["secondary_drivers"] = [x.get("name") for x in driver_map.get("secondary_drivers", [])]
        if "driver_notes" not in driver_map:
            summary_bits: List[str] = []
            if driver_map.get("primary_drivers"):
                summary_bits.append(f"primary={len(driver_map['primary_drivers'])}")
            if driver_map.get("secondary_drivers"):
                summary_bits.append(f"secondary={len(driver_map['secondary_drivers'])}")
            driver_map["driver_notes"] = "; ".join(summary_bits)

    guidance = out.get("guidance_behaviour", {})
    if isinstance(guidance, dict):
        guidance_profile = {
            "credibility": guidance.get("credibility", "unknown"),
            "guidance_style": guidance.get("bias", "unknown"),
        }
        if guidance.get("bias") == "conservative":
            guidance_profile["bias_direction"] = "slightly_underpromise"
        elif guidance.get("bias") == "optimistic":
            guidance_profile["bias_direction"] = "slightly_overpromise"
        else:
            guidance_profile["bias_direction"] = "balanced"
        out["guidance_profile"] = guidance_profile
    else:
        out["guidance_profile"] = {}

    fp_summary = out.get("fingerprint_summary", {})
    if isinstance(fp_summary, dict):
        fp_summary.setdefault("key_watch_items", [])
        fp_summary.setdefault("predictability_regime", "unknown")

    lag_structure = out.get("lag_structure", {})
    if isinstance(lag_structure, dict):
        lag_structure["primary_variable_lags"] = deepcopy(lag_structure.get("driver_lags", []))
        lag_structure["secondary_variable_lags"] = []
        if "lag_notes" not in lag_structure:
            notes = []
            if lag_structure.get("driver_lags"):
                notes.append(f"drivers={len(lag_structure['driver_lags'])}")
            lag_structure["lag_notes"] = "; ".join(notes)

    out["sensitivity_profile"] = {
        "variable_sensitivities": deepcopy(
            out.get("sensitivity_model", {}).get("coefficients", [])
        )
    }

    linked = out.get("linked_refs", {})
    if isinstance(linked, dict) and "company_profile_refs" in linked:
        linked["structural_profile_refs"] = deepcopy(linked["company_profile_refs"])

    return out


def build_company_fingerprint_payload(
    *,
    company_ref: str,
    sector_template_ref: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.company_fingerprint_store",
    driver_map_patch: Optional[Dict[str, Any]] = None,
    lag_structure_patch: Optional[Dict[str, Any]] = None,
    sensitivity_model_patch: Optional[Dict[str, Any]] = None,
    sensitivity_profile_patch: Optional[Dict[str, Any]] = None,
    guidance_behaviour_patch: Optional[Dict[str, Any]] = None,
    guidance_profile_patch: Optional[Dict[str, Any]] = None,
    fingerprint_summary_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    primary_drivers: Optional[List[Any]] = None,
    secondary_drivers: Optional[List[Any]] = None,
    recurring_business_drivers: Optional[List[Any]] = None,
    variable_sensitivities: Optional[List[Any]] = None,
    management_guidance_events: Optional[List[Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    driver_map_patch = _normalize_driver_map_patch(driver_map_patch)
    lag_structure_patch = _normalize_lag_structure_patch(lag_structure_patch)
    if sensitivity_model_patch is None:
        sensitivity_model_patch = sensitivity_profile_patch
    sensitivity_model_patch = _normalize_sensitivity_model_patch(sensitivity_model_patch)
    if guidance_behaviour_patch is None:
        guidance_behaviour_patch = guidance_profile_patch
    guidance_behaviour_patch = _normalize_guidance_behaviour_patch(guidance_behaviour_patch)
    fingerprint_summary_patch = _normalize_fingerprint_summary_patch(fingerprint_summary_patch)
    linked_refs_patch = _normalize_linked_refs_patch(linked_refs_patch)

    payload: Dict[str, Any] = {
        "company_fingerprint_id": f"{company_ref}/fingerprint/{as_of_date_s}",
        "company_ref": company_ref,
        "sector_template_ref": sector_template_ref,
        "as_of_date": as_of_date_s,
        "driver_map": {
            "primary_drivers": [],
            "secondary_drivers": [],
        },
        "lag_structure": {
            "default_lag_days": 0,
            "driver_lags": [],
        },
        "sensitivity_model": {
            "coefficients": [],
        },
        "guidance_behaviour": {
            "credibility": "unknown",
            "bias": "unknown",
            "stability": "unknown",
            "notes": "",
        },
        "fingerprint_summary": {
            "analytical_confidence": 0.0,
            "report_count": 0,
            "summary": "",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if driver_map_patch:
        payload["driver_map"] = _deep_merge(payload["driver_map"], driver_map_patch)

    if lag_structure_patch:
        payload["lag_structure"] = _deep_merge(payload["lag_structure"], lag_structure_patch)

    if sensitivity_model_patch:
        payload["sensitivity_model"] = _deep_merge(payload["sensitivity_model"], sensitivity_model_patch)

    if guidance_behaviour_patch:
        payload["guidance_behaviour"] = _deep_merge(payload["guidance_behaviour"], guidance_behaviour_patch)

    if fingerprint_summary_patch:
        payload["fingerprint_summary"] = _deep_merge(payload["fingerprint_summary"], fingerprint_summary_patch)

    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)

    if recurring_business_drivers:
        normalized = [_normalize_driver_item(x) for x in recurring_business_drivers]
        payload["driver_map"]["primary_drivers"] = [x for x in normalized if x.get("importance", 0) >= 80]
        payload["driver_map"]["secondary_drivers"] = [x for x in normalized if x.get("importance", 0) < 80]

    if primary_drivers:
        payload["driver_map"]["primary_drivers"] = [_normalize_driver_item(x) for x in primary_drivers]

    if secondary_drivers:
        payload["driver_map"]["secondary_drivers"] = [_normalize_driver_item(x) for x in secondary_drivers]

    if variable_sensitivities:
        payload["sensitivity_model"]["coefficients"] = [
            _normalize_sensitivity_item(x) for x in variable_sensitivities
        ]

    if management_guidance_events:
        payload["guidance_behaviour"]["stability"] = "stable"
        signals = {str(x.get("signal", "")).strip().lower() for x in management_guidance_events if isinstance(x, dict)}
        if "cautious_but_credible" in signals:
            payload["guidance_behaviour"]["credibility"] = "high"
            payload["guidance_behaviour"]["bias"] = "conservative"

    if payload_patch:
        payload = _deep_merge(payload, deepcopy(payload_patch))

    if isinstance(payload.get("driver_map"), dict):
        payload["driver_map"] = _normalize_driver_map_patch(payload["driver_map"])

    if isinstance(payload.get("lag_structure"), dict):
        payload["lag_structure"] = _normalize_lag_structure_patch(payload["lag_structure"])

    if isinstance(payload.get("sensitivity_model"), dict):
        payload["sensitivity_model"] = _normalize_sensitivity_model_patch(payload["sensitivity_model"])

    if isinstance(payload.get("guidance_behaviour"), dict):
        payload["guidance_behaviour"] = _normalize_guidance_behaviour_patch(payload["guidance_behaviour"])

    if isinstance(payload.get("fingerprint_summary"), dict):
        payload["fingerprint_summary"] = _normalize_fingerprint_summary_patch(payload["fingerprint_summary"])

    if isinstance(payload.get("linked_refs"), dict):
        payload["linked_refs"] = _normalize_linked_refs_patch(payload["linked_refs"])

    if validate:
        validate_payload("company_fingerprint", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_company_fingerprint_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    canonical_payload = deepcopy(payload)

    canonical_payload.pop("fingerprint_id", None)
    canonical_payload.pop("guidance_profile", None)
    canonical_payload.pop("sensitivity_profile", None)

    if isinstance(canonical_payload.get("driver_map"), dict):
        canonical_payload["driver_map"].pop("driver_notes", None)

    if isinstance(canonical_payload.get("lag_structure"), dict):
        canonical_payload["lag_structure"].pop("primary_variable_lags", None)
        canonical_payload["lag_structure"].pop("secondary_variable_lags", None)
        canonical_payload["lag_structure"].pop("lag_notes", None)

    if isinstance(canonical_payload.get("fingerprint_summary"), dict):
        canonical_payload["fingerprint_summary"].pop("key_watch_items", None)
        canonical_payload["fingerprint_summary"].pop("predictability_regime", None)
        canonical_payload["fingerprint_summary"].pop("watch_items", None)
        canonical_payload["fingerprint_summary"].pop("predictability_state", None)

    if isinstance(canonical_payload.get("linked_refs"), dict):
        canonical_payload["linked_refs"].pop("structural_profile_refs", None)

    if validate:
        validate_payload("company_fingerprint", canonical_payload, version=SCHEMA_PACK_VERSION)

    path = company_fingerprint_storage_path(
        canonical_payload["company_ref"],
        canonical_payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_company_fingerprint_payload(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = company_fingerprint_storage_path(company_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Company fingerprint not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("company_fingerprint", payload, version=SCHEMA_PACK_VERSION)

    return _build_legacy_aliases(payload)


class CompanyFingerprintStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "company_fingerprints"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, as_of_date: Any) -> Path:
        return company_fingerprint_storage_path(
            company_ref=company_ref,
            as_of_date=as_of_date,
            base_dir=self.base_dir,
        )

    def save_company_fingerprint(
        self,
        *,
        company_ref: str,
        sector_template_ref: Optional[str] = None,
        as_of_date: Any,
        generated_by: str = "aion_equities.company_fingerprint_store",
        driver_map_patch: Optional[Dict[str, Any]] = None,
        lag_structure_patch: Optional[Dict[str, Any]] = None,
        sensitivity_model_patch: Optional[Dict[str, Any]] = None,
        sensitivity_profile_patch: Optional[Dict[str, Any]] = None,
        guidance_behaviour_patch: Optional[Dict[str, Any]] = None,
        guidance_profile_patch: Optional[Dict[str, Any]] = None,
        fingerprint_summary_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        if sector_template_ref is None:
            sector_template_ref = "sector/unknown/template/default"

        payload = build_company_fingerprint_payload(
            company_ref=company_ref,
            sector_template_ref=sector_template_ref,
            as_of_date=as_of_date,
            generated_by=generated_by,
            driver_map_patch=driver_map_patch,
            lag_structure_patch=lag_structure_patch,
            sensitivity_model_patch=sensitivity_model_patch,
            sensitivity_profile_patch=sensitivity_profile_patch,
            guidance_behaviour_patch=guidance_behaviour_patch,
            guidance_profile_patch=guidance_profile_patch,
            fingerprint_summary_patch=fingerprint_summary_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            recurring_business_drivers=legacy_kwargs.pop("recurring_business_drivers", None),
            primary_drivers=legacy_kwargs.pop("primary_drivers", None),
            secondary_drivers=legacy_kwargs.pop("secondary_drivers", None),
            variable_sensitivities=legacy_kwargs.pop("variable_sensitivities", None),
            management_guidance_events=legacy_kwargs.pop("management_guidance_events", None),
            validate=validate,
        )

        save_company_fingerprint_payload(
            payload,
            base_dir=self.base_dir,
            validate=False,
        )
        return _build_legacy_aliases(payload)

    def save_fingerprint(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_company_fingerprint(**kwargs)

    def load_company_fingerprint(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_company_fingerprint_payload(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_fingerprint(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_company_fingerprint(
            company_ref,
            as_of_date,
            validate=validate,
        )

    def company_fingerprint_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(company_ref, as_of_date).exists()

    def fingerprint_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.company_fingerprint_exists(company_ref, as_of_date)

    def list_fingerprints(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))


__all__ = [
    "build_company_fingerprint_payload",
    "save_company_fingerprint_payload",
    "load_company_fingerprint_payload",
    "CompanyFingerprintStore",
]
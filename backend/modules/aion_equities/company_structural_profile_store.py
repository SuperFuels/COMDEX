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
    return Path(__file__).resolve().parent / "data" / "company_structural_profiles"


def company_structural_profile_storage_path(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


def _normalize_cost_structure_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)
    legacy_map = {
        "labour_cost_ratio_pct": "labour_cost_ratio",
        "energy_cost_ratio_pct": "energy_cost_ratio",
        "debt_service_ratio_pct": "debt_service_ratio",
        "fixed_cost_ratio_pct": "fixed_cost_ratio",
        "variable_cost_ratio_pct": "variable_cost_ratio",
    }

    for old, new in legacy_map.items():
        if old in out and new not in out:
            out[new] = out.pop(old)

    return out


def _normalize_payload_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    if isinstance(out.get("cost_structure"), dict):
        out["cost_structure"] = _normalize_cost_structure_patch(out["cost_structure"])

    return out


def _legacy_commodity_to_canonical(item: Dict[str, Any]) -> Dict[str, Any]:
    exposure_level = "medium"
    materiality = item.get("materiality_pct")
    if isinstance(materiality, (int, float)):
        if materiality >= 50:
            exposure_level = "critical"
        elif materiality >= 25:
            exposure_level = "high"
        elif materiality >= 10:
            exposure_level = "medium"
        else:
            exposure_level = "low"

    hedged = None
    hedging_regime = item.get("hedging_regime")
    if hedging_regime in {"full", "partial"}:
        hedged = True
    elif hedging_regime in {"none", "unhedged"}:
        hedged = False

    out: Dict[str, Any] = {
        "name": item.get("commodity", item.get("name", "unknown")),
        "exposure_level": exposure_level,
    }
    if hedged is not None:
        out["hedged"] = hedged

    notes_parts: List[str] = []
    if item.get("exposure_direction"):
        notes_parts.append(f"direction={item['exposure_direction']}")
    if item.get("hedging_regime"):
        notes_parts.append(f"hedging={item['hedging_regime']}")
    if item.get("materiality_pct") is not None:
        notes_parts.append(f"materiality_pct={item['materiality_pct']}")
    if notes_parts:
        out["notes"] = "; ".join(notes_parts)

    return out


def _legacy_geo_to_canonical_revenue(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "region": item.get("region", "unknown"),
        "share_pct": float(item.get("revenue_share_pct", 0.0)),
    }
    if item.get("currency"):
        out["currency"] = item["currency"]
    return out


def _legacy_geo_to_canonical_cost(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "region": item.get("region", "unknown"),
        "share_pct": float(item.get("cost_share_pct", 0.0)),
    }
    if item.get("currency"):
        out["currency"] = item["currency"]
    return out


def _legacy_acquisition_to_canonical(item: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "target_name": item.get("target", item.get("target_name", "unknown")),
        "announced_date": item.get("date", item.get("announced_date", "1970-01-01")),
    }
    if item.get("deal_value") is not None:
        out["deal_value"] = item["deal_value"]
    if item.get("currency"):
        out["currency"] = item["currency"]

    rationale_parts: List[str] = []
    if item.get("deal_type"):
        rationale_parts.append(f"deal_type={item['deal_type']}")
    if item.get("capital_allocation_assessment"):
        rationale_parts.append(f"assessment={item['capital_allocation_assessment']}")
    if item.get("rationale"):
        rationale_parts.append(str(item["rationale"]))
    if rationale_parts:
        out["rationale"] = "; ".join(rationale_parts)

    return out

def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    # legacy field accepted by tests but not by schema
    out.pop("company_refs", None)

    return out


def _legacy_people_event_to_canonical(item: Dict[str, Any]) -> Dict[str, Any]:
    signal_map = {
        "capital_discipline": "positive",
        "positive": "positive",
        "neutral": "neutral",
        "negative": "negative",
    }
    out: Dict[str, Any] = {
        "name": item.get("person", item.get("name", "unknown")),
        "role": item.get("role", item.get("seniority", "unknown")),
        "date": item.get("date", "1970-01-01"),
        "signal": signal_map.get(str(item.get("signal", "neutral")), "neutral"),
    }

    notes_parts: List[str] = []
    if item.get("event_type"):
        notes_parts.append(f"event_type={item['event_type']}")
    if item.get("seniority"):
        notes_parts.append(f"seniority={item['seniority']}")
    if item.get("notes"):
        notes_parts.append(str(item["notes"]))
    if notes_parts:
        out["notes"] = "; ".join(notes_parts)

    return out


def _build_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    # top-level id alias
    out["company_structural_profile_id"] = out["company_profile_id"]

    # legacy cost structure aliases
    cs = out.get("cost_structure", {})
    if isinstance(cs, dict):
        if "labour_cost_ratio" in cs:
            cs["labour_cost_ratio_pct"] = cs["labour_cost_ratio"]
        if "energy_cost_ratio" in cs:
            cs["energy_cost_ratio_pct"] = cs["energy_cost_ratio"]
        if "debt_service_ratio" in cs:
            cs["debt_service_ratio_pct"] = cs["debt_service_ratio"]
        if "fixed_cost_ratio" in cs:
            cs["fixed_cost_ratio_pct"] = cs["fixed_cost_ratio"]
        if "variable_cost_ratio" in cs:
            cs["variable_cost_ratio_pct"] = cs["variable_cost_ratio"]

    # legacy flattened commodity exposures
    out["commodity_exposures"] = []
    for item in out.get("cost_structure", {}).get("commodity_input_exposure", []):
        legacy_item = {
            "commodity": item.get("name"),
            "exposure_level": item.get("exposure_level"),
            "hedged": item.get("hedged"),
            "notes": item.get("notes"),
        }
        out["commodity_exposures"].append(legacy_item)

    # legacy flattened geographic exposures
    out["geographic_exposures"] = []
    revenue_by_region = {
        x.get("region"): x for x in out.get("geographic_exposure", {}).get("revenue_regions", [])
    }
    cost_by_region = {
        x.get("region"): x for x in out.get("geographic_exposure", {}).get("cost_regions", [])
    }
    all_regions = sorted(set(revenue_by_region.keys()) | set(cost_by_region.keys()))
    for region in all_regions:
        rev = revenue_by_region.get(region, {})
        cost = cost_by_region.get(region, {})
        out["geographic_exposures"].append(
            {
                "region": region,
                "revenue_share_pct": rev.get("share_pct", 0.0),
                "cost_share_pct": cost.get("share_pct", 0.0),
                "currency": rev.get("currency", cost.get("currency")),
            }
        )

    return out


def build_company_structural_profile_payload(
    *,
    company_ref: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.company_structural_profile_store",
    cost_structure_patch: Optional[Dict[str, Any]] = None,
    geographic_exposure_patch: Optional[Dict[str, Any]] = None,
    capital_allocation_patch: Optional[Dict[str, Any]] = None,
    management_signals_patch: Optional[Dict[str, Any]] = None,
    competitive_position_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    commodity_exposures: Optional[List[Dict[str, Any]]] = None,
    geographic_exposures: Optional[List[Dict[str, Any]]] = None,
    acquisition_history: Optional[List[Dict[str, Any]]] = None,
    key_people_events: Optional[List[Dict[str, Any]]] = None,
    competitor_pressure: Optional[Dict[str, Any]] = None,
    linked_refs: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    cost_structure_patch = _normalize_cost_structure_patch(cost_structure_patch)
    payload_patch = _normalize_payload_patch(payload_patch)

    payload: Dict[str, Any] = {
        "company_profile_id": f"{company_ref}/profile/{as_of_date_s}",
        "company_ref": company_ref,
        "as_of_date": as_of_date_s,
        "cost_structure": {
            "labour_cost_ratio": 0.0,
            "energy_cost_ratio": 0.0,
            "debt_service_ratio": 0.0,
            "fixed_cost_ratio": 0.0,
            "variable_cost_ratio": 0.0,
            "commodity_input_exposure": [],
            "cost_notes": "",
        },
        "geographic_exposure": {
            "revenue_regions": [],
            "cost_regions": [],
            "fx_sensitivity_notes": "",
        },
        "capital_allocation": {
            "allocation_quality": "unknown",
            "acquisition_intensity": "none",
            "buyback_policy": "unknown",
            "dividend_policy": "unknown",
            "recent_acquisitions": [],
            "capital_allocation_notes": "",
        },
        "management_signals": {
            "guidance_credibility": "unknown",
            "key_hire_signal": "unknown",
            "departure_risk": "unknown",
            "notable_hires": [],
            "notable_departures": [],
            "management_notes": "",
        },
        "competitive_position": {
            "market_share_trend": "unknown",
            "pricing_power": "unknown",
            "competitive_pressure": "unknown",
            "main_competitors": [],
            "market_share_notes": "",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if cost_structure_patch:
        payload["cost_structure"] = _deep_merge(payload["cost_structure"], cost_structure_patch)

    if geographic_exposure_patch:
        payload["geographic_exposure"] = _deep_merge(
            payload["geographic_exposure"],
            geographic_exposure_patch,
        )

    if capital_allocation_patch:
        payload["capital_allocation"] = _deep_merge(
            payload["capital_allocation"],
            capital_allocation_patch,
        )

    if management_signals_patch:
        payload["management_signals"] = _deep_merge(
            payload["management_signals"],
            management_signals_patch,
        )

    if competitive_position_patch:
        payload["competitive_position"] = _deep_merge(
            payload["competitive_position"],
            competitive_position_patch,
        )

    if commodity_exposures:
        payload["cost_structure"]["commodity_input_exposure"] = [
            _legacy_commodity_to_canonical(x) for x in commodity_exposures
        ]

    if geographic_exposures:
        payload["geographic_exposure"]["revenue_regions"] = [
            _legacy_geo_to_canonical_revenue(x) for x in geographic_exposures
        ]
        payload["geographic_exposure"]["cost_regions"] = [
            _legacy_geo_to_canonical_cost(x) for x in geographic_exposures
        ]

    if acquisition_history:
        payload["capital_allocation"]["recent_acquisitions"] = [
            _legacy_acquisition_to_canonical(x) for x in acquisition_history
        ]
        payload["capital_allocation"]["acquisition_intensity"] = (
            "high" if len(acquisition_history) >= 3 else
            "moderate" if len(acquisition_history) >= 2 else
            "low"
        )
        first_assessment = acquisition_history[0].get("capital_allocation_assessment")
        if first_assessment in {"disciplined", "mixed", "aggressive", "destructive", "unknown"}:
            payload["capital_allocation"]["allocation_quality"] = first_assessment

    if key_people_events:
        hires = [x for x in key_people_events if x.get("event_type") == "hire"]
        departures = [x for x in key_people_events if x.get("event_type") != "hire"]

        payload["management_signals"]["notable_hires"] = [
            _legacy_people_event_to_canonical(x) for x in hires
        ]
        payload["management_signals"]["notable_departures"] = [
            _legacy_people_event_to_canonical(x) for x in departures
        ]

        signals = {str(x.get("signal")) for x in key_people_events}
        if "capital_discipline" in signals or "positive" in signals:
            payload["management_signals"]["key_hire_signal"] = "positive"

    if competitor_pressure:
        market_share_map = {
            "low": "stable",
            "moderate": "stable",
            "high": "losing",
            "extreme": "losing",
        }
        pricing_map = {
            "strong": "strong",
            "moderate": "moderate",
            "contained": "moderate",
            "weak": "weak",
        }

        msp = competitor_pressure.get("market_share_pressure", "medium")
        pp = competitor_pressure.get("pricing_pressure", "unknown")

        payload["competitive_position"]["competitive_pressure"] = (
            msp if msp in {"low", "medium", "high", "extreme", "unknown"} else "medium"
        )
        payload["competitive_position"]["market_share_trend"] = market_share_map.get(msp, "unknown")
        payload["competitive_position"]["pricing_power"] = pricing_map.get(pp, "unknown")
        if competitor_pressure.get("notes"):
            payload["competitive_position"]["market_share_notes"] = competitor_pressure["notes"]

    if linked_refs_patch:
        payload["linked_refs"] = _normalize_linked_refs_patch(linked_refs_patch)

    if linked_refs:
        payload["linked_refs"] = _normalize_linked_refs_patch(linked_refs)

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    # normalize again in case payload_patch inserted legacy names
    if isinstance(payload.get("cost_structure"), dict):
        payload["cost_structure"] = _normalize_cost_structure_patch(payload["cost_structure"])

    if isinstance(payload.get("linked_refs"), dict):
        payload["linked_refs"] = _normalize_linked_refs_patch(payload["linked_refs"])

    if validate:
        validate_payload("company_structural_profile", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_company_structural_profile_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    canonical_payload = deepcopy(payload)

    # remove test-facing legacy aliases before persistence/validation
    canonical_payload.pop("company_structural_profile_id", None)
    canonical_payload.pop("commodity_exposures", None)
    canonical_payload.pop("geographic_exposures", None)

    if isinstance(canonical_payload.get("cost_structure"), dict):
        for key in [
            "labour_cost_ratio_pct",
            "energy_cost_ratio_pct",
            "debt_service_ratio_pct",
            "fixed_cost_ratio_pct",
            "variable_cost_ratio_pct",
        ]:
            canonical_payload["cost_structure"].pop(key, None)

    if validate:
        validate_payload("company_structural_profile", canonical_payload, version=SCHEMA_PACK_VERSION)

    path = company_structural_profile_storage_path(
        canonical_payload["company_ref"],
        canonical_payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_company_structural_profile_payload(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = company_structural_profile_storage_path(company_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Company structural profile not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("company_structural_profile", payload, version=SCHEMA_PACK_VERSION)

    return _build_legacy_aliases(payload)


class CompanyStructuralProfileStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "company_structural_profiles"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, as_of_date: Any) -> Path:
        return company_structural_profile_storage_path(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
        )

    def save_company_structural_profile(
        self,
        *,
        company_ref: str,
        as_of_date: Any,
        generated_by: str = "aion_equities.company_structural_profile_store",
        cost_structure_patch: Optional[Dict[str, Any]] = None,
        geographic_exposure_patch: Optional[Dict[str, Any]] = None,
        capital_allocation_patch: Optional[Dict[str, Any]] = None,
        management_signals_patch: Optional[Dict[str, Any]] = None,
        competitive_position_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        if cost_structure_patch is None:
            cost_structure_patch = {}

        # direct legacy ratios
        legacy_ratio_keys = [
            "labour_cost_ratio_pct",
            "energy_cost_ratio_pct",
            "debt_service_ratio_pct",
            "fixed_cost_ratio_pct",
            "variable_cost_ratio_pct",
        ]
        for key in legacy_ratio_keys:
            if key in legacy_kwargs and key not in cost_structure_patch:
                cost_structure_patch[key] = legacy_kwargs.pop(key)

        payload = build_company_structural_profile_payload(
            company_ref=company_ref,
            as_of_date=as_of_date,
            generated_by=generated_by,
            cost_structure_patch=cost_structure_patch,
            geographic_exposure_patch=geographic_exposure_patch,
            capital_allocation_patch=capital_allocation_patch,
            management_signals_patch=management_signals_patch,
            competitive_position_patch=competitive_position_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            commodity_exposures=legacy_kwargs.pop("commodity_exposures", None),
            geographic_exposures=legacy_kwargs.pop("geographic_exposures", None),
            acquisition_history=legacy_kwargs.pop("acquisition_history", None),
            key_people_events=legacy_kwargs.pop("key_people_events", None),
            competitor_pressure=legacy_kwargs.pop("competitor_pressure", None),
            linked_refs=legacy_kwargs.pop("linked_refs", None),
            validate=validate,
        )
        save_company_structural_profile_payload(
            payload,
            base_dir=self.base_dir,
            validate=False,
        )
        return _build_legacy_aliases(payload)

    def save_profile(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_company_structural_profile(**kwargs)

    def load_company_structural_profile(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_company_structural_profile_payload(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_profile(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_company_structural_profile(
            company_ref,
            as_of_date,
            validate=validate,
        )

    def company_structural_profile_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(company_ref, as_of_date).exists()

    def structural_profile_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.company_structural_profile_exists(company_ref, as_of_date)

    def profile_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.company_structural_profile_exists(company_ref, as_of_date)

    def list_profiles(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))
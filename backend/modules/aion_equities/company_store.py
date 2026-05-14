from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.investing_ids import make_company_id
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


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "companies"


def _safe_ticker_filename(ticker: str) -> str:
    return str(ticker).strip().replace("/", "_")


def company_storage_path(ticker: str, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_ticker_filename(ticker)}.json"


def _slug_sector_name(value: str) -> str:
    s = str(value).strip().lower()
    s = s.replace("&", " and ")
    s = s.replace("/", "_").replace("\\", "_").replace(" ", "_").replace("-", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def _normalize_sector_ref(
    *,
    sector_ref: Optional[str] = None,
    sector: Optional[str] = None,
    sector_name: Optional[str] = None,
) -> str:
    """
    Accept any of:
      - sector_ref="sector/industrial_equipment_rental"
      - sector="sector/industrial_equipment_rental"
      - sector_name="Industrial Equipment Rental"

    Canonical storage always uses sector_ref.
    """
    value = sector_ref or sector
    if value:
        return str(value).strip()

    if sector_name:
        return f"sector/{_slug_sector_name(sector_name)}"

    raise ValueError("sector_ref (or sector / sector_name alias) is required")


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def build_company_payload(
    *,
    ticker: str,
    name: str,
    exchange: str,
    currency: str,
    sector_ref: Optional[str] = None,
    sector: Optional[str] = None,
    sector_name: Optional[str] = None,
    created_by: str = "aion_equities",
    status: str = "watchlist",
    country: Optional[str] = None,
    industry: Optional[str] = None,
    acs_band: str = "unknown",
    sector_confidence_tier: str = "tier_3",
    latest_assessment_ref: str = "",
    active_thesis_refs: Optional[list[str]] = None,
    quarter_event_refs: Optional[list[str]] = None,
    catalyst_event_refs: Optional[list[str]] = None,
    pattern_refs: Optional[list[str]] = None,
    description: Optional[str] = None,
    geographic_exposure_summary: Optional[str] = None,
    segment_summary: Optional[str] = None,
    moat_hypotheses: Optional[list[str]] = None,
    cost_base_structure_notes: Optional[str] = None,
    management_behavior_profile: Optional[str] = None,
    commodity_exposure_notes: Optional[str] = None,
    hedging_opacity_notes: Optional[str] = None,
    regulatory_complexity_notes: Optional[str] = None,
    updated_by: Optional[str] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s
    sector_ref_value = _normalize_sector_ref(
        sector_ref=sector_ref,
        sector=sector,
        sector_name=sector_name,
    )

    payload: Dict[str, Any] = {
        "company_id": make_company_id(ticker),
        "ticker": str(ticker).strip(),
        "name": name,
        "exchange": exchange,
        "currency": currency.upper(),
        "sector_ref": sector_ref_value,
        "status": status,
        "predictability_profile": {
            "acs_band": acs_band,
            "sector_confidence_tier": sector_confidence_tier,
        },
        "intelligence_state": {
            "latest_assessment_ref": latest_assessment_ref,
            "active_thesis_refs": active_thesis_refs or [],
            "quarter_event_refs": quarter_event_refs or [],
            "catalyst_event_refs": catalyst_event_refs or [],
            "pattern_refs": pattern_refs or [],
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": created_by,
        },
    }

    if updated_by:
        payload["audit"]["updated_by"] = updated_by
    if country:
        payload["country"] = country
    if industry:
        payload["industry"] = industry

    business_profile: Dict[str, Any] = {}
    if description:
        business_profile["description"] = description
    if geographic_exposure_summary:
        business_profile["geographic_exposure_summary"] = geographic_exposure_summary
    if segment_summary:
        business_profile["segment_summary"] = segment_summary
    if moat_hypotheses is not None:
        business_profile["moat_hypotheses"] = moat_hypotheses
    if cost_base_structure_notes:
        business_profile["cost_base_structure_notes"] = cost_base_structure_notes
    if management_behavior_profile:
        business_profile["management_behavior_profile"] = management_behavior_profile
    if business_profile:
        payload["business_profile"] = business_profile

    if commodity_exposure_notes:
        payload["predictability_profile"]["commodity_exposure_notes"] = commodity_exposure_notes
    if hedging_opacity_notes:
        payload["predictability_profile"]["hedging_opacity_notes"] = hedging_opacity_notes
    if regulatory_complexity_notes:
        payload["predictability_profile"]["regulatory_complexity_notes"] = regulatory_complexity_notes

    if validate:
        validate_payload("company", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_company_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("company", payload, version=SCHEMA_PACK_VERSION)

    ticker = payload["ticker"]
    path = company_storage_path(ticker, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_company_payload(
    ticker: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = company_storage_path(ticker, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Company payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("company", payload, version=SCHEMA_PACK_VERSION)
    return payload


def upsert_company(
    *,
    ticker: str,
    name: str,
    exchange: str,
    currency: str,
    sector_ref: Optional[str] = None,
    sector: Optional[str] = None,
    sector_name: Optional[str] = None,
    created_by: str = "aion_equities",
    updated_by: Optional[str] = None,
    company_payload_patch: Optional[Dict[str, Any]] = None,
    base_dir: Optional[Path] = None,
    validate: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    path = company_storage_path(ticker, base_dir=base_dir)

    existing: Optional[Dict[str, Any]] = None
    if path.exists():
        existing = load_company_payload(ticker, base_dir=base_dir, validate=False)

    generated_by = kwargs.pop("generated_by", None)
    kwargs.pop("create_write_event", None)
    kwargs.pop("company_payload_patch", None)
    kwargs.pop("created_by", None)

    effective_created_by = existing["audit"]["created_by"] if existing else (generated_by or created_by)
    effective_updated_by = updated_by or generated_by

    payload = build_company_payload(
        ticker=ticker,
        name=name,
        exchange=exchange,
        currency=currency,
        sector_ref=sector_ref,
        sector=sector,
        sector_name=sector_name,
        created_by=effective_created_by,
        created_at=existing["audit"]["created_at"] if existing else None,
        updated_by=effective_updated_by,
        updated_at=_utc_now_iso(),
        validate=False,
        **kwargs,
    )

    if existing:
        merged = deepcopy(existing)
        merged.update(
            {
                "company_id": payload["company_id"],
                "ticker": payload["ticker"],
                "name": payload["name"],
                "exchange": payload["exchange"],
                "currency": payload["currency"],
                "sector_ref": payload["sector_ref"],
                "status": payload["status"],
                "predictability_profile": payload["predictability_profile"],
                "intelligence_state": payload["intelligence_state"],
                "audit": {
                    **existing.get("audit", {}),
                    **payload["audit"],
                    "created_at": existing["audit"]["created_at"],
                    "created_by": existing["audit"]["created_by"],
                },
            }
        )

        for optional_key in ("country", "industry", "business_profile"):
            if optional_key in payload:
                merged[optional_key] = payload[optional_key]

        payload = merged

    if company_payload_patch:
        payload = _deep_merge(payload, company_payload_patch)

    if validate:
        validate_payload("company", payload, version=SCHEMA_PACK_VERSION)

    save_company_payload(payload, base_dir=base_dir, validate=False)
    return payload


class CompanyStore:
    """
    Small file-backed runtime store for company containers.
    This wraps the functional helpers above so the intelligence runtime can
    depend on a stable class API.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, ticker: str) -> Path:
        return company_storage_path(ticker, base_dir=self.base_dir)

    def build_company_payload(self, **kwargs: Any) -> Dict[str, Any]:
        return build_company_payload(**kwargs)

    def save_company_payload(self, payload: Dict[str, Any], *, validate: bool = True) -> Path:
        return save_company_payload(payload, base_dir=self.base_dir, validate=validate)

    def load_company_payload(self, ticker: str, *, validate: bool = True) -> Dict[str, Any]:
        return load_company_payload(ticker, base_dir=self.base_dir, validate=validate)

    def load_company(self, ticker: str, *, validate: bool = True) -> Dict[str, Any]:
        return load_company_payload(ticker, base_dir=self.base_dir, validate=validate)

    def upsert_company(self, *, validate: bool = True, **kwargs: Any) -> Dict[str, Any]:
        return upsert_company(base_dir=self.base_dir, validate=validate, **kwargs)

    def company_exists(self, ticker: str) -> bool:
        return self.storage_path(ticker).exists()
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_equities.aion_equities_kg_bridge import AIONEquitiesKGBridge
from backend.modules.aion_equities.aion_equities_sqi_container_writer import (
    AIONEquitiesSQIContainerWriter,
)
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _band_multiplier(acs_band: str) -> float:
    return {
        "very_high": 1.10,
        "high": 1.00,
        "medium": 0.87,
        "low": 0.70,
    }.get(str(acs_band or "medium").strip().lower(), 0.87)


def _first_non_empty(*values: Any, default: str) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _extract_predictability_context(company: Dict[str, Any]) -> Dict[str, str]:
    """
    Read predictability context from all seed shapes we may have in the repo.

    Supported shapes:
    - company["predictability_profile"]["acs_band"]
    - company["predictability_profile"]["sector_confidence_tier"]
    - company["acs_band"]
    - company["sector_confidence_tier"]
    - company["payload"]["predictability_profile"][...]
    - company["company_snapshot"]["predictability_profile"][...]
    - company["seed_data"]["predictability_profile"][...]
    """
    predictability_profile = deepcopy(company.get("predictability_profile") or {})

    payload = company.get("payload") or {}
    payload_predictability = deepcopy(payload.get("predictability_profile") or {})

    company_snapshot = company.get("company_snapshot") or {}
    snapshot_predictability = deepcopy(company_snapshot.get("predictability_profile") or {})

    seed_data = company.get("seed_data") or {}
    seed_predictability = deepcopy(seed_data.get("predictability_profile") or {})

    acs_band = _first_non_empty(
        predictability_profile.get("acs_band"),
        payload_predictability.get("acs_band"),
        snapshot_predictability.get("acs_band"),
        seed_predictability.get("acs_band"),
        company.get("acs_band"),
        payload.get("acs_band"),
        company_snapshot.get("acs_band"),
        seed_data.get("acs_band"),
        default="medium",
    ).lower()

    sector_confidence_tier = _first_non_empty(
        predictability_profile.get("sector_confidence_tier"),
        payload_predictability.get("sector_confidence_tier"),
        snapshot_predictability.get("sector_confidence_tier"),
        seed_predictability.get("sector_confidence_tier"),
        company.get("sector_confidence_tier"),
        payload.get("sector_confidence_tier"),
        company_snapshot.get("sector_confidence_tier"),
        seed_data.get("sector_confidence_tier"),
        default="tier_2",
    ).lower()

    return {
        "acs_band": acs_band,
        "sector_confidence_tier": sector_confidence_tier,
    }


class AssessmentRuntime:
    """
    Builds a first-pass assessment from:
    - pilot company seed
    - quarter event store payload

    Important:
    This runtime is aligned to the REAL quarter_event_store payload structure:
      - extraction.financials
      - extraction.narrative
      - analysis.*
      - source.*
      - period.*
    """

    def __init__(
        self,
        *,
        pilot_company_seed_store: PilotCompanySeedStore,
        quarter_event_store: QuarterEventStore,
        kg_bridge: Optional[AIONEquitiesKGBridge] = None,
        sqi_container_writer: Optional[AIONEquitiesSQIContainerWriter] = None,
    ):
        self.pilot_company_seed_store = pilot_company_seed_store
        self.quarter_event_store = quarter_event_store
        self.kg_bridge = kg_bridge or AIONEquitiesKGBridge()
        self.sqi_container_writer = sqi_container_writer or AIONEquitiesSQIContainerWriter()

    def build_assessment(
        self,
        *,
        company_ref: str,
        quarter_event_id: str,
        thesis_ref: Optional[str] = None,
        write_to_kg: bool = False,
        write_to_sqi_container: bool = False,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or _utc_now_iso()

        company = self.pilot_company_seed_store.load_company_seed(company_ref)
        quarter_event = self.quarter_event_store.load_quarter_event(
            quarter_event_id,
            validate=False,
        )

        predictability_context = _extract_predictability_context(company)
        acs_band = predictability_context["acs_band"]
        sector_confidence_tier = predictability_context["sector_confidence_tier"]

        company_snapshot = {
            "company_id": company.get("company_id"),
            "ticker": company.get("ticker"),
            "name": company.get("name"),
            "sector": company.get("sector"),
            "country": company.get("country"),
            "sector_template_ref": company.get("sector_template_ref"),
            "fingerprint_ref": company.get("fingerprint_ref"),
            "credit_profile_ref": company.get("credit_profile_ref"),
            "pair_context_ref": company.get("pair_context_ref"),
        }

        extraction = deepcopy(quarter_event.get("extraction") or {})
        source = deepcopy(quarter_event.get("source") or {})
        analysis = deepcopy(quarter_event.get("analysis") or {})
        period = deepcopy(quarter_event.get("period") or {})

        fin = deepcopy(extraction.get("financials") or {})
        narrative = deepcopy(extraction.get("narrative") or {})

        revenue = _safe_float(fin.get("revenue"), 0.0)
        ebit = _safe_float(fin.get("ebit"), 0.0)
        fcf = _safe_float(fin.get("free_cash_flow"), 0.0)
        net_debt = _safe_float(fin.get("net_debt"), 0.0)
        guidance_delta = _safe_float(fin.get("guidance_delta"), 0.0)

        margin = (ebit / revenue * 100.0) if revenue > 0 else 0.0
        balance_sheet_strength = _clamp_0_100(80.0 - max(0.0, net_debt / 1000.0))
        cash_generation_score = _clamp_0_100(55.0 + min(30.0, max(0.0, fcf / 100.0)))
        margin_score = _clamp_0_100(45.0 + min(35.0, max(0.0, margin * 2.0)))
        guidance_score = _clamp_0_100(50.0 + guidance_delta)

        business_quality_score = round(
            _clamp_0_100(
                (cash_generation_score * 0.30)
                + (margin_score * 0.30)
                + (balance_sheet_strength * 0.25)
                + (guidance_score * 0.15)
            ),
            2,
        )

        narrative_summary = str(narrative.get("summary") or "").strip()
        narrative_clarity_bonus = 8.0 if narrative_summary else 0.0
        reporting_clarity = 20.0 if fin else 0.0

        analytical_confidence_score = round(
            _clamp_0_100(
                (55.0 + reporting_clarity + narrative_clarity_bonus)
                * _band_multiplier(acs_band)
            ),
            2,
        )

        ai_benefit_score = 0.0
        if isinstance(analysis.get("flags"), list):
            flags = analysis.get("flags", [])
            if any("ai" in str(x).lower() for x in flags):
                ai_benefit_score = 10.0

        automation_opportunity_score = round(
            _clamp_0_100(40.0 + ai_benefit_score),
            2,
        )

        risk_flags = []
        if net_debt > 2500.0:
            risk_flags.append("elevated_net_debt")
        if revenue > 0 and margin < 8.0:
            risk_flags.append("thin_operating_margin")
        if guidance_delta < 0.0:
            risk_flags.append("negative_guidance_drift")

        fiscal_year = period.get("fiscal_year")
        fiscal_quarter = period.get("fiscal_quarter")
        fiscal_period_ref = (
            f"{fiscal_year}-Q{fiscal_quarter}"
            if fiscal_year is not None and fiscal_quarter is not None
            else "unknown-period"
        )

        assessment_id = f"assessment/{company_ref}/{fiscal_period_ref}"

        payload: Dict[str, Any] = {
            "assessment_id": assessment_id,
            "entity_id": company_ref,
            "as_of": as_of,
            "fiscal_period_ref": fiscal_period_ref,
            "company_snapshot": company_snapshot,
            "scores": {
                "business_quality_score": business_quality_score,
                "analytical_confidence_score": analytical_confidence_score,
                "automation_opportunity_score": automation_opportunity_score,
            },
            "dimensions": {
                "margin_score": round(margin_score, 2),
                "cash_generation_score": round(cash_generation_score, 2),
                "balance_sheet_strength": round(balance_sheet_strength, 2),
                "guidance_score": round(guidance_score, 2),
                "reporting_clarity": round(reporting_clarity, 2),
                "narrative_clarity_bonus": round(narrative_clarity_bonus, 2),
            },
            "predictability_context": {
                "acs_band": acs_band,
                "sector_confidence_tier": sector_confidence_tier,
            },
            "linked_refs": {
                "company_ref": company_ref,
                "quarter_event_ref": quarter_event.get("quarter_event_id"),
                "thesis_ref": thesis_ref,
                "source_document_refs": source.get("document_refs", []),
            },
            "source_snapshot": {
                "event_type": quarter_event.get("event_type"),
                "as_reported_date": quarter_event.get("as_reported_date"),
                "provider": source.get("provider"),
                "document_refs": source.get("document_refs", []),
                "source_hashes": source.get("source_hashes", []),
            },
            "risk_flags": risk_flags,
            "notes": {
                "narrative_summary_present": bool(narrative_summary),
                "assessment_refs_on_event": analysis.get("assessment_refs", []),
            },
        }

        if write_to_kg:
            self.kg_bridge.write_assessment(payload)

        if write_to_sqi_container:
            self.sqi_container_writer.write_assessment(
                payload,
                company_ref=company_ref,
                thesis_ref=thesis_ref,
            )

        return payload

    def run_first_pass_for_company(
        self,
        *,
        company_ref: str,
        quarter_event_id: str,
        thesis_ref: Optional[str] = None,
        write_to_kg: bool = True,
        write_to_sqi_container: bool = True,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.build_assessment(
            company_ref=company_ref,
            quarter_event_id=quarter_event_id,
            thesis_ref=thesis_ref,
            write_to_kg=write_to_kg,
            write_to_sqi_container=write_to_sqi_container,
            as_of=as_of,
        )


__all__ = [
    "AssessmentRuntime",
]
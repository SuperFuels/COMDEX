from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_equities.aion_equities_kg_bridge import AIONEquitiesKGBridge
from backend.modules.aion_equities.aion_equities_sqi_container_writer import (
    AIONEquitiesSQIContainerWriter,
)
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _ticker_from_company_ref(company_ref: str, fallback: str = "unknown") -> str:
    text = str(company_ref or "").strip()
    if not text:
        return fallback
    parts = text.split("/")
    return parts[-1] if parts else fallback


class ThesisRuntime:
    """
    Builds / refreshes thesis state from company seed + assessment.

    This stays domain-native:
    - no fake SQI math
    - no hard-coded coherence engine
    - produces thesis payloads that can then be written into KG / UCS / SQI containers
    """

    def __init__(
        self,
        *,
        pilot_company_seed_store: PilotCompanySeedStore,
        thesis_store: Optional[Any] = None,
        kg_bridge: Optional[AIONEquitiesKGBridge] = None,
        sqi_container_writer: Optional[AIONEquitiesSQIContainerWriter] = None,
    ):
        self.pilot_company_seed_store = pilot_company_seed_store
        self.thesis_store = thesis_store
        self.kg_bridge = kg_bridge or AIONEquitiesKGBridge()
        self.sqi_container_writer = sqi_container_writer or AIONEquitiesSQIContainerWriter()

    def _persist_thesis(self, payload: Dict[str, Any]) -> None:
        if self.thesis_store is None:
            return

        if hasattr(self.thesis_store, "save_thesis"):
            self.thesis_store.save_thesis(payload)
            return

        if hasattr(self.thesis_store, "save_thesis_state"):
            self.thesis_store.save_thesis_state(payload)
            return

        if hasattr(self.thesis_store, "upsert_thesis"):
            self.thesis_store.upsert_thesis(payload)
            return

        if hasattr(self.thesis_store, "upsert"):
            self.thesis_store.upsert(payload)
            return

        raise AttributeError(
            "thesis_store must expose one of: save_thesis, save_thesis_state, upsert_thesis, upsert"
        )

    def build_thesis(
        self,
        *,
        company_ref: str,
        assessment: Dict[str, Any],
        mode: str = "long",
        window: str = "medium_term",
        trigger_map_ref: Optional[str] = None,
        quarter_event_ref: Optional[str] = None,
        existing_thesis: Optional[Dict[str, Any]] = None,
        write_to_store: bool = False,
        write_to_kg: bool = False,
        write_to_sqi_container: bool = False,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or _utc_now_iso()

        company = self.pilot_company_seed_store.load_company_seed(company_ref)
        ticker = company.get("ticker") or _ticker_from_company_ref(company_ref)

        scores = deepcopy(assessment.get("scores") or {})
        risk_flags = list(assessment.get("risk_flags") or [])
        predictability_context = deepcopy(assessment.get("predictability_context") or {})

        bqs = _safe_float(scores.get("business_quality_score"), 0.0)
        acs = _safe_float(scores.get("analytical_confidence_score"), 0.0)
        aot = _safe_float(scores.get("automation_opportunity_score"), 0.0)

        risk_penalty = min(30.0, float(len(risk_flags)) * 8.0)
        conviction_score = _clamp_0_100((bqs * 0.45) + (acs * 0.40) + (aot * 0.15) - risk_penalty)

        net_support = (bqs + acs) / 2.0 - risk_penalty

        if mode == "long":
            if conviction_score >= 65.0 and net_support >= 55.0:
                status = "active"
            elif conviction_score >= 45.0:
                status = "watch"
            else:
                status = "inactive"
        elif mode in {"short", "swing_short"}:
            if risk_penalty >= 16.0 and bqs < 55.0 and acs >= 50.0:
                status = "active"
            elif risk_penalty >= 8.0:
                status = "watch"
            else:
                status = "inactive"
        else:
            status = "watch" if conviction_score >= 45.0 else "inactive"

        prior_state = deepcopy(existing_thesis or {})
        prior_status = str(prior_state.get("status") or "new").strip().lower()

        thesis_id = f"thesis/{ticker}/{mode}/{window}"

        payload: Dict[str, Any] = {
            "thesis_id": thesis_id,
            "ticker": ticker,
            "mode": str(mode),
            "window": str(window),
            "status": status,
            "as_of": as_of,
            "entity_ref": company_ref,
            "conviction": {
                "score": round(conviction_score, 2),
                "band": (
                    "high" if conviction_score >= 70.0
                    else "medium" if conviction_score >= 45.0
                    else "low"
                ),
            },
            "decision_context": {
                "prior_status": prior_status,
                "risk_penalty": round(risk_penalty, 2),
                "net_support": round(net_support, 2),
            },
            "linked_refs": {
                "company_ref": company_ref,
                "assessment_refs": [assessment.get("assessment_id")] if assessment.get("assessment_id") else [],
                "quarter_event_ref": quarter_event_ref,
                "trigger_map_ref": trigger_map_ref,
            },
            "predictability_context": {
                "acs_band": str(predictability_context.get("acs_band") or "medium"),
                "sector_confidence_tier": str(
                    predictability_context.get("sector_confidence_tier") or "tier_2"
                ),
            },
            "company_snapshot": {
                "company_id": company.get("company_id"),
                "ticker": company.get("ticker"),
                "name": company.get("name"),
                "sector": company.get("sector"),
                "country": company.get("country"),
                "sector_template_ref": company.get("sector_template_ref"),
                "fingerprint_ref": company.get("fingerprint_ref"),
                "credit_profile_ref": company.get("credit_profile_ref"),
                "pair_context_ref": company.get("pair_context_ref"),
            },
            "assessment_snapshot": {
                "assessment_id": assessment.get("assessment_id"),
                "business_quality_score": round(bqs, 2),
                "analytical_confidence_score": round(acs, 2),
                "automation_opportunity_score": round(aot, 2),
                "risk_flags": risk_flags,
            },
        }

        if write_to_store:
            self._persist_thesis(payload)

        if write_to_kg:
            self.kg_bridge.write_thesis(payload)

        if write_to_sqi_container:
            self.sqi_container_writer.write_thesis(
                payload,
                company_ref=company_ref,
                trigger_map_ref=trigger_map_ref,
            )

        return payload

    def run_first_pass_for_company(
        self,
        *,
        company_ref: str,
        assessment: Dict[str, Any],
        mode: str = "long",
        window: str = "medium_term",
        trigger_map_ref: Optional[str] = None,
        quarter_event_ref: Optional[str] = None,
        write_to_store: bool = True,
        write_to_kg: bool = True,
        write_to_sqi_container: bool = True,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.build_thesis(
            company_ref=company_ref,
            assessment=assessment,
            mode=mode,
            window=window,
            trigger_map_ref=trigger_map_ref,
            quarter_event_ref=quarter_event_ref,
            write_to_store=write_to_store,
            write_to_kg=write_to_kg,
            write_to_sqi_container=write_to_sqi_container,
            as_of=as_of,
        )


__all__ = [
    "ThesisRuntime",
]
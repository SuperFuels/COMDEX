from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.catalyst_event_store import CatalystEventStore
from backend.modules.aion_equities.company_store import CompanyStore
from backend.modules.aion_equities.kg_edge_store import KGEdgeStore
from backend.modules.aion_equities.macro_regime_store import MacroRegimeStore
from backend.modules.aion_equities.observer_decision_cycle_store import ObserverDecisionCycleStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.sqi_mapping import build_sqi_signal_inputs
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.top_down_levers_store import TopDownLeversStore
from backend.modules.aion_equities.top_down_rules import derive_top_down_implications


class IntelligenceRuntime:
    """
    First integrated AION Equities runtime loop.

    Core path:
      company -> assessment -> sqi signals -> thesis -> kg edges

    Extended path:
      macro_regime + top_down_snapshot -> rules engine -> helicopter view
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.company_store = CompanyStore(self.base_dir)
        self.assessment_store = AssessmentStore(self.base_dir)
        self.thesis_store = ThesisStore(self.base_dir)
        self.kg_edge_store = KGEdgeStore(self.base_dir)
        self.quarter_event_store = QuarterEventStore(self.base_dir)
        self.catalyst_event_store = CatalystEventStore(self.base_dir)
        self.observer_cycle_store = ObserverDecisionCycleStore(self.base_dir)
        self.macro_regime_store = MacroRegimeStore(self.base_dir)
        self.top_down_levers_store = TopDownLeversStore(self.base_dir)

    def build_daily_helicopter_view(
        self,
        *,
        macro_regime_id: str,
        top_down_snapshot_id: str,
    ) -> Dict[str, Any]:
        macro_regime = self.macro_regime_store.load_macro_regime_by_id(macro_regime_id)
        top_down_snapshot = self.top_down_levers_store.load_snapshot_by_id(top_down_snapshot_id)

        derived = derive_top_down_implications(
            macro_regime=macro_regime,
            top_down_snapshot=top_down_snapshot,
        )

        return {
            "macro_regime": macro_regime,
            "top_down_snapshot": top_down_snapshot,
            "derived": derived,
        }

    def bootstrap_company_intelligence(
        self,
        *,
        ticker: str,
        name: str,
        exchange: str,
        currency: str,
        sector_name: str,
        industry: str = "",
        country: str = "",
        company_status: str = "active",
        acs_band: str = "unknown",
        sector_confidence_tier: str = "tier_2",
        as_of: Any,
        generated_by: str = "aion_equities.intelligence_runtime",
        company_payload_patch: Optional[Dict[str, Any]] = None,
        assessment_payload_patch: Optional[Dict[str, Any]] = None,
        thesis_mode: str = "long",
        thesis_window: str = "bootstrap",
        thesis_status: str = "candidate",
        assessment_refs: Optional[List[str]] = None,
        create_write_events: bool = True,
        validate: bool = True,
        macro_regime_id: Optional[str] = None,
        top_down_snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        helicopter_view: Optional[Dict[str, Any]] = None
        if macro_regime_id and top_down_snapshot_id:
            helicopter_view = self.build_daily_helicopter_view(
                macro_regime_id=macro_regime_id,
                top_down_snapshot_id=top_down_snapshot_id,
            )

        company_payload = self.company_store.upsert_company(
            ticker=ticker,
            name=name,
            exchange=exchange,
            currency=currency,
            sector_name=sector_name,
            industry=industry,
            country=country,
            status=company_status,
            acs_band=acs_band,
            sector_confidence_tier=sector_confidence_tier,
            company_payload_patch=company_payload_patch or {},
            generated_by=generated_by,
            create_write_event=create_write_events,
            validate=validate,
        )
        company_id = company_payload["company_id"]

        assessment_payload = self.assessment_store.save_assessment(
            entity_id=company_id,
            entity_type="company",
            as_of=as_of,
            assessment_payload_patch=assessment_payload_patch or {},
            generated_by=generated_by,
            create_write_event=create_write_events,
            validate=validate,
        )
        assessment_id = assessment_payload["assessment_id"]

        kg_context = {
            "supports_count": 0,
            "contradicts_count": 0,
            "drift_score": 0.0,
            "confidence_modifier": 0.0,
            "pattern_match_score": 0.0,
        }
        pattern_context = {
            "aggregate_score": 0.0,
            "stability_modifier": 0.0,
        }
        observer_context = {
            "bias_penalty": 0.0,
        }

        if helicopter_view:
            derived = helicopter_view["derived"]
            conviction = derived.get("conviction_filter", {}).get("macro_signal_coherence", "medium")
            contradiction_count = derived.get("conviction_filter", {}).get("contradiction_count", 0)
            sector_posture = derived.get("sector_posture", {})

            if conviction == "high":
                kg_context["confidence_modifier"] = 0.10
            elif conviction == "low":
                kg_context["confidence_modifier"] = -0.10

            kg_context["contradicts_count"] = float(contradiction_count)

            company_sector = company_payload.get("sector_ref", "")
            if company_sector.endswith("energy") and sector_posture.get("energy") == "green":
                pattern_context["aggregate_score"] = 0.15

            if company_sector.endswith("industrial_equipment_rental") and sector_posture.get("cyclicals") == "red":
                observer_context["bias_penalty"] = 0.05

        sqi_signals = build_sqi_signal_inputs(
            assessment=assessment_payload,
            context={
                "kg": kg_context,
                "pattern": pattern_context,
                "observer": observer_context,
            },
        )

        linked_assessment_refs = list(assessment_refs or [])
        if assessment_id not in linked_assessment_refs:
            linked_assessment_refs.append(assessment_id)

        thesis_payload = self.thesis_store.save_thesis_state(
            ticker=ticker,
            mode=thesis_mode,
            window=thesis_window,
            as_of=as_of,
            assessment_refs=linked_assessment_refs,
            status=thesis_status,
            generated_by=generated_by,
            create_write_event=create_write_events,
            validate=validate,
        )
        thesis_id = thesis_payload["thesis_id"]

        company_payload = self.company_store.upsert_company(
            ticker=ticker,
            name=company_payload["name"],
            exchange=company_payload["exchange"],
            currency=company_payload["currency"],
            sector_ref=company_payload["sector_ref"],
            industry=company_payload.get("industry", ""),
            country=company_payload.get("country", ""),
            status=company_payload["status"],
            acs_band=company_payload["predictability_profile"]["acs_band"],
            sector_confidence_tier=company_payload["predictability_profile"]["sector_confidence_tier"],
            generated_by=generated_by,
            create_write_event=create_write_events,
            company_payload_patch={
                "intelligence_state": {
                    "latest_assessment_ref": assessment_id,
                    "active_thesis_refs": sorted(
                        list(
                            {
                                *company_payload.get("intelligence_state", {}).get("active_thesis_refs", []),
                                thesis_id,
                            }
                        )
                    ),
                    "quarter_event_refs": company_payload.get("intelligence_state", {}).get("quarter_event_refs", []),
                    "catalyst_event_refs": company_payload.get("intelligence_state", {}).get("catalyst_event_refs", []),
                    "pattern_refs": company_payload.get("intelligence_state", {}).get("pattern_refs", []),
                }
            },
            validate=validate,
        )

        edges: List[Dict[str, Any]] = []

        edges.append(
            self.kg_edge_store.save_edge(
                src=company_id,
                dst=company_payload["sector_ref"],
                link_type="exposure",
                created_at=as_of,
                confidence=85.0,
                active=True,
                source_event_ids=[assessment_id],
                edge_payload_patch={"payload": {"relation_note": "company sector classification"}},
                generated_by=generated_by,
                create_write_event=create_write_events,
                validate=validate,
            )
        )

        edges.append(
            self.kg_edge_store.save_edge(
                src=company_id,
                dst=thesis_id,
                link_type="supports_thesis",
                created_at=as_of,
                confidence=70.0,
                active=True,
                source_event_ids=[assessment_id],
                edge_payload_patch={"payload": {"relation_note": "bootstrap thesis linked to company"}},
                generated_by=generated_by,
                create_write_event=create_write_events,
                validate=validate,
            )
        )

        edges.append(
            self.kg_edge_store.save_edge(
                src=assessment_id,
                dst=thesis_id,
                link_type="evidence_source",
                created_at=as_of,
                confidence=90.0,
                active=True,
                source_event_ids=[assessment_id],
                edge_payload_patch={"payload": {"relation_note": "assessment used as thesis evidence"}},
                generated_by=generated_by,
                create_write_event=create_write_events,
                validate=validate,
            )
        )

        if helicopter_view:
            macro_regime = helicopter_view["macro_regime"]
            top_down_snapshot = helicopter_view["top_down_snapshot"]

            edges.append(
                self.kg_edge_store.save_edge(
                    src=macro_regime["macro_regime_id"],
                    dst=company_id,
                    link_type="confidence_modifier",
                    created_at=as_of,
                    confidence=75.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "macro regime applied as company-level confidence modifier"
                        }
                    },
                    generated_by=generated_by,
                    create_write_event=create_write_events,
                    validate=validate,
                )
            )

            edges.append(
                self.kg_edge_store.save_edge(
                    src=top_down_snapshot["snapshot_id"],
                    dst=thesis_id,
                    link_type="drift_signal",
                    created_at=as_of,
                    confidence=65.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "top-down lever snapshot informs thesis drift/context"
                        }
                    },
                    generated_by=generated_by,
                    create_write_event=create_write_events,
                    validate=validate,
                )
            )

        return {
            "company": company_payload,
            "assessment": assessment_payload,
            "sqi_signals": sqi_signals,
            "thesis": thesis_payload,
            "edges": edges,
            "helicopter_view": helicopter_view,
        }

    def load_company_intelligence_snapshot(self, *, ticker: str, mode: str, window: str) -> Dict[str, Any]:
        company = self.company_store.load_company(ticker)
        thesis = self.thesis_store.load_latest_thesis_state_by_parts(
            ticker=ticker,
            mode=mode,
            window=window,
        )

        latest_assessment_ref = company.get("intelligence_state", {}).get("latest_assessment_ref")
        assessment = None
        if latest_assessment_ref:
            assessment = self.assessment_store.load_assessment_by_id(latest_assessment_ref)

        return {
            "company": company,
            "assessment": assessment,
            "thesis": thesis,
        }
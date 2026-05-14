from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.catalyst_event_store import CatalystEventStore
from backend.modules.aion_equities.company_store import CompanyStore
from backend.modules.aion_equities.credit_trajectory_store import CreditTrajectoryStore
from backend.modules.aion_equities.kg_edge_store import KGEdgeStore
from backend.modules.aion_equities.macro_regime_store import MacroRegimeStore
from backend.modules.aion_equities.observer_decision_cycle_store import ObserverDecisionCycleStore
from backend.modules.aion_equities.pair_context_store import PairContextStore
from backend.modules.aion_equities.post_report_calibration_store import (
    PostReportCalibrationStore,
)
from backend.modules.aion_equities.pre_earnings_estimate_store import (
    PreEarningsEstimateStore,
)
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.runtime_confidence_modifiers import (
    build_runtime_confidence_modifiers,
)
from backend.modules.aion_equities.sqi_mapping import build_sqi_signal_inputs
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.top_down_levers_store import TopDownLeversStore
from backend.modules.aion_equities.top_down_rules import derive_top_down_implications


class IntelligenceRuntime:
    """
    First integrated AION Equities runtime loop.

    Base path:
      company -> assessment -> sqi signals -> thesis -> kg edges

    Extended path:
      macro_regime + top_down_snapshot + pair_context -> helicopter view
      -> confidence / contradiction / pair-aware SQI adjustment

    Runtime confidence path:
      pair_context + credit_trajectory + pre_earnings_estimate
      + post_report_calibration -> combined confidence modifiers
      -> SQI / thesis / catalyst-aware adjustment
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
        self.pair_context_store = PairContextStore(self.base_dir)
        self.credit_trajectory_store = CreditTrajectoryStore(self.base_dir)
        self.pre_earnings_estimate_store = PreEarningsEstimateStore(self.base_dir)
        self.post_report_calibration_store = PostReportCalibrationStore(self.base_dir)

    def build_daily_helicopter_view(
        self,
        *,
        macro_regime_id: str,
        top_down_snapshot_id: str,
        pair_context_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        macro_regime = self.macro_regime_store.load_macro_regime_by_id(macro_regime_id)
        top_down_snapshot = self.top_down_levers_store.load_snapshot_by_id(
            top_down_snapshot_id
        )

        derived = derive_top_down_implications(
            macro_regime=macro_regime,
            top_down_snapshot=top_down_snapshot,
        )

        pair_context = None
        if pair_context_id:
            pair_context = self.pair_context_store.load_pair_context_by_id(pair_context_id)

        return {
            "macro_regime": macro_regime,
            "top_down_snapshot": top_down_snapshot,
            "pair_context": pair_context,
            "derived": derived,
        }

    def build_runtime_confidence_modifiers(
        self,
        *,
        ticker: str,
        thesis_window: str,
        pair_context_id: Optional[str] = None,
        credit_trajectory_id: Optional[str] = None,
        pre_earnings_estimate_id: Optional[str] = None,
        post_report_calibration_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        pair_context = None
        if pair_context_id:
            pair_context = self.pair_context_store.load_pair_context_by_id(pair_context_id)

        credit_trajectory = None
        if credit_trajectory_id:
            credit_trajectory = (
                self.credit_trajectory_store.load_credit_trajectory_by_id(
                    credit_trajectory_id
                )
            )

        pre_earnings_estimate = None
        if pre_earnings_estimate_id:
            pre_earnings_estimate = (
                self.pre_earnings_estimate_store.load_pre_earnings_estimate_by_id(
                    pre_earnings_estimate_id
                )
            )

        post_report_calibration = None
        if post_report_calibration_id:
            post_report_calibration = (
                self.post_report_calibration_store.load_post_report_calibration_by_id(
                    post_report_calibration_id
                )
            )

        return build_runtime_confidence_modifiers(
            pair_context=pair_context,
            credit_trajectory=credit_trajectory,
            pre_earnings_estimate=pre_earnings_estimate,
            post_report_calibration=post_report_calibration,
        )

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
        pair_context_id: Optional[str] = None,
        credit_trajectory_id: Optional[str] = None,
        pre_earnings_estimate_id: Optional[str] = None,
        post_report_calibration_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        helicopter_view: Optional[Dict[str, Any]] = None
        if macro_regime_id and top_down_snapshot_id:
            helicopter_view = self.build_daily_helicopter_view(
                macro_regime_id=macro_regime_id,
                top_down_snapshot_id=top_down_snapshot_id,
                pair_context_id=pair_context_id,
            )

        runtime_confidence_modifiers = self.build_runtime_confidence_modifiers(
            ticker=ticker,
            thesis_window=thesis_window,
            pair_context_id=pair_context_id,
            credit_trajectory_id=credit_trajectory_id,
            pre_earnings_estimate_id=pre_earnings_estimate_id,
            post_report_calibration_id=post_report_calibration_id,
        )

        # 1) Company
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

        # 2) Assessment
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

        # 3) SQI bridge
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
            conviction = derived.get("conviction_filter", {}).get(
                "macro_signal_coherence", "medium"
            )
            contradiction_count = derived.get("conviction_filter", {}).get(
                "contradiction_count", 0
            )
            sector_posture = derived.get("sector_posture", {})

            if conviction == "high":
                kg_context["confidence_modifier"] += 0.10
            elif conviction == "low":
                kg_context["confidence_modifier"] -= 0.10

            kg_context["contradicts_count"] = float(contradiction_count)

            company_sector = company_payload.get("sector_ref", "")
            if (
                company_sector.endswith("energy")
                and sector_posture.get("energy") == "green"
            ):
                pattern_context["aggregate_score"] = 0.15

            if (
                company_sector.endswith("industrial_equipment_rental")
                and sector_posture.get("cyclicals") == "red"
            ):
                observer_context["bias_penalty"] = 0.05

            pair_context = helicopter_view.get("pair_context")
            if pair_context:
                pair_conviction = float(
                    pair_context.get("pair_score", {}).get("conviction", 0.0)
                )
                carry_state = pair_context.get("carry_signal", {}).get("state", "unknown")
                risk_state = pair_context.get("risk_appetite_signal", {}).get(
                    "state", "unknown"
                )

                if pair_conviction >= 75:
                    kg_context["confidence_modifier"] += 0.08
                elif pair_conviction <= 40:
                    kg_context["confidence_modifier"] -= 0.08

                if carry_state == "unwind_risk":
                    kg_context["contradicts_count"] += 1.0
                    observer_context["bias_penalty"] += 0.03

                if risk_state == "risk_off":
                    kg_context["confidence_modifier"] -= 0.05
                elif risk_state == "risk_on":
                    kg_context["confidence_modifier"] += 0.05

        combined_mods = runtime_confidence_modifiers["combined"]
        kg_context["confidence_modifier"] += combined_mods["thesis_confidence_modifier"]
        kg_context["drift_score"] += combined_mods["credit_drift_penalty"]
        pattern_context["aggregate_score"] += combined_mods[
            "catalyst_conviction_modifier"
        ]
        observer_context["bias_penalty"] += max(
            -combined_mods["calibration_modifier"], 0.0
        )

        sqi_signals = build_sqi_signal_inputs(
            assessment=assessment_payload,
            context={
                "kg": kg_context,
                "pattern": pattern_context,
                "observer": observer_context,
            },
        )

        # 4) Thesis
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

        # update company intelligence refs
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
            sector_confidence_tier=company_payload["predictability_profile"][
                "sector_confidence_tier"
            ],
            generated_by=generated_by,
            create_write_event=create_write_events,
            company_payload_patch={
                "intelligence_state": {
                    "latest_assessment_ref": assessment_id,
                    "active_thesis_refs": sorted(
                        list(
                            {
                                *company_payload.get("intelligence_state", {}).get(
                                    "active_thesis_refs", []
                                ),
                                thesis_id,
                            }
                        )
                    ),
                    "quarter_event_refs": company_payload.get(
                        "intelligence_state", {}
                    ).get("quarter_event_refs", []),
                    "catalyst_event_refs": company_payload.get(
                        "intelligence_state", {}
                    ).get("catalyst_event_refs", []),
                    "pattern_refs": company_payload.get("intelligence_state", {}).get(
                        "pattern_refs", []
                    ),
                }
            },
            validate=validate,
        )

        # 5) KG edges
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
                edge_payload_patch={
                    "payload": {"relation_note": "company sector classification"}
                },
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
                edge_payload_patch={
                    "payload": {"relation_note": "bootstrap thesis linked to company"}
                },
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
                edge_payload_patch={
                    "payload": {"relation_note": "assessment used as thesis evidence"}
                },
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

            pair_context = helicopter_view.get("pair_context")
            if pair_context:
                edges.append(
                    self.kg_edge_store.save_edge(
                        src=pair_context["pair_context_id"],
                        dst=thesis_id,
                        link_type="confidence_modifier",
                        created_at=as_of,
                        confidence=68.0,
                        active=True,
                        source_event_ids=[assessment_id],
                        edge_payload_patch={
                            "payload": {
                                "relation_note": "pair-context coherence modifies thesis confidence"
                            }
                        },
                        generated_by=generated_by,
                        create_write_event=create_write_events,
                        validate=validate,
                    )
                )

        pair_context_mod = runtime_confidence_modifiers.get("pair_context")
        if pair_context_mod:
            edges.append(
                self.kg_edge_store.save_edge(
                    src=pair_context_mod["pair_context_id"],
                    dst=thesis_id,
                    link_type="confidence_modifier",
                    created_at=as_of,
                    confidence=70.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "pair context runtime modifier applied to thesis confidence"
                        }
                    },
                    generated_by=generated_by,
                    create_write_event=create_write_events,
                    validate=validate,
                )
            )

        credit_mod = runtime_confidence_modifiers.get("credit_trajectory")
        if credit_mod:
            edges.append(
                self.kg_edge_store.save_edge(
                    src=credit_mod["credit_trajectory_id"],
                    dst=thesis_id,
                    link_type="drift_signal",
                    created_at=as_of,
                    confidence=72.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "credit trajectory applies downgrade / drift pressure to thesis"
                        }
                    },
                    generated_by=generated_by,
                    create_write_event=create_write_events,
                    validate=validate,
                )
            )

        pre_mod = runtime_confidence_modifiers.get("pre_earnings_estimate")
        if pre_mod:
            edges.append(
                self.kg_edge_store.save_edge(
                    src=pre_mod["pre_earnings_estimate_id"],
                    dst=thesis_id,
                    link_type="supports_thesis",
                    created_at=as_of,
                    confidence=74.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "pre-earnings divergence informs catalyst conviction"
                        }
                    },
                    generated_by=generated_by,
                    create_write_event=create_write_events,
                    validate=validate,
                )
            )

        calibration_mod = runtime_confidence_modifiers.get("post_report_calibration")
        if calibration_mod:
            edges.append(
                self.kg_edge_store.save_edge(
                    src=calibration_mod["post_report_calibration_id"],
                    dst=thesis_id,
                    link_type="confidence_modifier",
                    created_at=as_of,
                    confidence=66.0,
                    active=True,
                    source_event_ids=[assessment_id],
                    edge_payload_patch={
                        "payload": {
                            "relation_note": "post-report calibration adjusts model confidence"
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
            "runtime_confidence_modifiers": runtime_confidence_modifiers,
        }

    def load_company_intelligence_snapshot(
        self, *, ticker: str, mode: str, window: str
    ) -> Dict[str, Any]:
        company = self.company_store.load_company(ticker)
        thesis = self.thesis_store.load_latest_thesis_state_by_parts(
            ticker=ticker,
            mode=mode,
            window=window,
        )

        latest_assessment_ref = company.get("intelligence_state", {}).get(
            "latest_assessment_ref"
        )
        assessment = None
        if latest_assessment_ref:
            assessment = self.assessment_store.load_assessment_by_id(
                latest_assessment_ref
            )

        return {
            "company": company,
            "assessment": assessment,
            "thesis": thesis,
        }
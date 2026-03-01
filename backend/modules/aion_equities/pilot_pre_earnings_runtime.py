from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.aion_equities_kg_bridge import (
    AIONEquitiesKGBridge,
)
from backend.modules.aion_equities.aion_equities_sqi_container_writer import (
    AIONEquitiesSQIContainerWriter,
)
from backend.modules.aion_equities.company_trigger_map_store import (
    CompanyTriggerMapStore,
)
from backend.modules.aion_equities.live_variable_tracker import LiveVariableTracker
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


class PilotPreEarningsRuntime:
    """
    Builds a first real pre-earnings estimate from:

    - pilot company seed
    - latest trigger map
    - live variable history
    - optional thesis / assessment refs

    And can persist the result into:
    - KG bridge
    - UCS/SQI container writer

    Notes:
    - No fake "true SQI engine" is hard-coded here.
    - This runtime produces domain-level estimate fields that are then written
      into KG/UCS/SQI-ready containers.
    - The writer layer can attach sqi_context, but the estimate logic here stays
      domain-native and auditable.
    """

    def __init__(
        self,
        *,
        pilot_company_seed_store: PilotCompanySeedStore,
        trigger_map_store: CompanyTriggerMapStore,
        live_variable_tracker: LiveVariableTracker,
        kg_bridge: Optional[AIONEquitiesKGBridge] = None,
        sqi_container_writer: Optional[AIONEquitiesSQIContainerWriter] = None,
    ):
        self.pilot_company_seed_store = pilot_company_seed_store
        self.trigger_map_store = trigger_map_store
        self.live_variable_tracker = live_variable_tracker
        self.kg_bridge = kg_bridge or AIONEquitiesKGBridge()
        self.sqi_container_writer = sqi_container_writer or AIONEquitiesSQIContainerWriter()

    def build_pre_earnings_estimate(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        thesis_ref: Optional[str] = None,
        assessment_ref: Optional[str] = None,
        write_to_kg: bool = False,
        write_to_sqi_container: bool = False,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or _utc_now_iso()

        company = self.pilot_company_seed_store.load_company_seed(company_ref)
        trigger_map = self.trigger_map_store.load_trigger_map(
            company_ref,
            fiscal_period_ref,
            validate=False,
        )
        variable_history = self.live_variable_tracker.get_company_variable_history(company_ref)

        triggers = deepcopy(trigger_map.get("triggers") or trigger_map.get("trigger_entries") or [])

        confirmed_count = 0
        building_count = 0
        broken_count = 0
        inactive_count = 0

        positive_weight = 0.0
        negative_weight = 0.0
        broken_weight = 0.0
        total_weight = 0.0

        for trig in triggers:
            state = str(trig.get("current_state", "inactive")).strip().lower()
            weight = _safe_float(trig.get("impact_weight", 0.0), 0.0)
            direction = str(trig.get("impact_direction", "unknown")).strip().lower()

            total_weight += max(0.0, weight)

            if state == "confirmed":
                confirmed_count += 1
                if direction == "positive":
                    positive_weight += weight
                elif direction == "negative":
                    negative_weight += weight
            elif state == "building":
                building_count += 1
                if direction == "positive":
                    positive_weight += weight * 0.5
                elif direction == "negative":
                    negative_weight += weight * 0.5
            elif state == "broken":
                broken_count += 1
                broken_weight += weight
            else:
                inactive_count += 1

        predictability_profile = company.get("predictability_profile", {}) or {}
        acs_band = str(predictability_profile.get("acs_band", "medium")).strip().lower()
        band_multiplier = {
            "very_high": 1.15,
            "high": 1.00,
            "medium": 0.85,
            "low": 0.65,
        }.get(acs_band, 0.85)

        variable_count = len(variable_history)
        variable_depth_bonus = min(15.0, float(variable_count) * 2.5)

        net_signal = positive_weight - negative_weight - broken_weight
        base_divergence = max(0.0, net_signal * 100.0)
        divergence_score = min(100.0, base_divergence)

        raw_confidence = (
            35.0
            + (confirmed_count * 12.0)
            + (building_count * 6.0)
            - (broken_count * 10.0)
            + variable_depth_bonus
        ) * band_multiplier
        confidence = max(0.0, min(100.0, raw_confidence))

        catalyst_strength = max(
            0.0,
            min(
                100.0,
                (confirmed_count * 18.0) + (building_count * 8.0) - (broken_count * 10.0),
            ),
        )

        minimum_signal_confidence = 45.0

        long_candidate = (
            confirmed_count > 0
            and net_signal > 0
            and confidence >= minimum_signal_confidence
        )

        short_candidate = (
            confirmed_count > 0
            and net_signal < 0
            and confidence >= minimum_signal_confidence
        )

        estimate_id = f"{company_ref}/pre_earnings/{fiscal_period_ref}"

        payload: Dict[str, Any] = {
            "pre_earnings_estimate_id": estimate_id,
            "company_ref": company_ref,
            "fiscal_period_ref": fiscal_period_ref,
            "as_of": as_of,
            "company_snapshot": {
                "company_id": company.get("company_id"),
                "ticker": company.get("ticker"),
                "name": company.get("name"),
                "sector_template_ref": company.get("sector_template_ref"),
                "fingerprint_ref": company.get("fingerprint_ref"),
                "credit_profile_ref": company.get("credit_profile_ref"),
                "pair_context_ref": company.get("pair_context_ref"),
            },
            "trigger_summary": {
                "total_triggers": len(triggers),
                "confirmed_trigger_count": confirmed_count,
                "building_trigger_count": building_count,
                "broken_trigger_count": broken_count,
                "inactive_trigger_count": inactive_count,
                "positive_weight": round(positive_weight, 4),
                "negative_weight": round(negative_weight, 4),
                "broken_weight": round(broken_weight, 4),
                "net_signal": round(net_signal, 4),
            },
            "variable_tracking": {
                "history_points": variable_count,
                "latest_points": variable_history[-5:],
            },
            "divergence": {
                "divergence_score": round(divergence_score, 2),
                "confidence": round(confidence, 2),
            },
            "signal": {
                "catalyst_strength": round(catalyst_strength, 2),
                "long_candidate": bool(long_candidate),
                "short_candidate": bool(short_candidate),
            },
            "linked_refs": {
                "company_ref": company_ref,
                "trigger_map_ref": trigger_map.get("company_trigger_map_id"),
                "thesis_ref": thesis_ref,
                "assessment_ref": assessment_ref,
            },
            "runtime_notes": {
                "acs_band": acs_band,
                "band_multiplier": band_multiplier,
                "variable_depth_bonus": round(variable_depth_bonus, 2),
            },
        }

        if write_to_kg:
            self.kg_bridge.write_pre_earnings_estimate(payload)

        if write_to_sqi_container:
            self.sqi_container_writer.write_pre_earnings_estimate(
                payload,
                company_ref=company_ref,
                thesis_ref=thesis_ref,
                trigger_map_ref=trigger_map.get("company_trigger_map_id"),
            )

        return payload

    def run_first_pass_for_company(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        thesis_ref: Optional[str] = None,
        assessment_ref: Optional[str] = None,
        write_to_kg: bool = True,
        write_to_sqi_container: bool = True,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.build_pre_earnings_estimate(
            company_ref=company_ref,
            fiscal_period_ref=fiscal_period_ref,
            thesis_ref=thesis_ref,
            assessment_ref=assessment_ref,
            write_to_kg=write_to_kg,
            write_to_sqi_container=write_to_sqi_container,
            as_of=as_of,
        )


__all__ = [
    "PilotPreEarningsRuntime",
]
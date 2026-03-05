# /workspaces/COMDEX/backend/modules/aion_equities/company_intelligence_snapshot_loader.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def _dedupe_preserve(values: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for v in values:
        if not v:
            continue
        k = str(v)
        if k in seen:
            continue
        seen.add(k)
        out.append(v)
    return out


class CompanyIntelligenceSnapshotLoader:
    """
    One-pass loader for company intelligence packs used by:
      - OpenAI trade review context packets
      - runtime replay/audit tools
      - UI/debug tooling

    Loads:
      - company seed (with refs)
      - latest assessment (via latest_assessment_ref, fallback to latest snapshot)
      - theses:
          * prefers thesis_refs (ALL statuses: watch/active/closed/etc.)
          * also includes active_thesis_refs (for backward compatibility)
      - quarter events (via quarter_event_refs; fallback to empty)
      - latest trigger map (best-effort from trigger_map_refs)
      - latest variable watch (best-effort from variable_watch_refs)

    Notes:
      - This is intentionally tolerant (best-effort) to support bootstrap state.
      - It returns missing_* lists to help debugging.
    """

    def __init__(
        self,
        *,
        pilot_company_seed_store: PilotCompanySeedStore,
        assessment_store: AssessmentStore,
        thesis_store: ThesisStore,
        quarter_event_store: QuarterEventStore,
        trigger_map_store: CompanyTriggerMapStore,
        variable_watch_store: VariableWatchStore,
    ):
        self.pilot_company_seed_store = pilot_company_seed_store
        self.assessment_store = assessment_store
        self.thesis_store = thesis_store
        self.quarter_event_store = quarter_event_store
        self.trigger_map_store = trigger_map_store
        self.variable_watch_store = variable_watch_store

    def load_snapshot(
        self,
        *,
        company_ref: str,
        include_quarter_events: bool = True,
        max_quarter_events: int = 12,
    ) -> Dict[str, Any]:
        company = deepcopy(self.pilot_company_seed_store.load_company_seed(company_ref))

        missing: Dict[str, List[str]] = {
            "assessments": [],
            "theses": [],
            "quarter_events": [],
            "trigger_maps": [],
            "variable_watch": [],
        }

        # --- assessment ---
        assessment: Optional[Dict[str, Any]] = None
        latest_assessment_ref = company.get("latest_assessment_ref")
        if isinstance(latest_assessment_ref, str) and latest_assessment_ref:
            try:
                assessment = self.assessment_store.load_assessment_by_id(latest_assessment_ref)
            except Exception:
                missing["assessments"].append(latest_assessment_ref)

        if assessment is None:
            # fallback: try latest assessment snapshot for entity_id = company_ref
            try:
                assessment = self.assessment_store.load_latest_assessment(company_ref)
            except Exception:
                assessment = None

        # --- theses (ALL refs preferred; fallback to active refs) ---
        theses: List[Dict[str, Any]] = []

        thesis_refs = company.get("thesis_refs") or []
        active_thesis_refs = company.get("active_thesis_refs") or []

        all_refs: List[Any] = []
        if isinstance(thesis_refs, list):
            all_refs.extend(thesis_refs)
        if isinstance(active_thesis_refs, list):
            all_refs.extend(active_thesis_refs)

        for tid in _dedupe_preserve(all_refs):
            try:
                theses.append(self.thesis_store.load_latest_thesis_state(str(tid)))
            except Exception:
                missing["theses"].append(str(tid))

        # --- quarter events ---
        quarter_events: List[Dict[str, Any]] = []
        quarter_event_refs = company.get("quarter_event_refs") or []
        if include_quarter_events and isinstance(quarter_event_refs, list):
            refs = _dedupe_preserve(quarter_event_refs)[-max_quarter_events:]
            for qid in refs:
                try:
                    quarter_events.append(
                        self.quarter_event_store.load_quarter_event(str(qid), validate=False)
                    )
                except Exception:
                    missing["quarter_events"].append(str(qid))

        # --- trigger map (latest ref) ---
        trigger_map: Optional[Dict[str, Any]] = None
        trigger_map_ref: Optional[str] = None
        trigger_map_refs = company.get("trigger_map_refs") or []
        if isinstance(trigger_map_refs, list) and trigger_map_refs:
            trigger_map_ref = str(trigger_map_refs[-1])
            try:
                trigger_map = self.trigger_map_store.load_company_trigger_map_by_id(
                    trigger_map_ref, validate=False
                )
            except Exception:
                missing["trigger_maps"].append(trigger_map_ref)

        # --- variable watch (latest ref) ---
        variable_watch: Optional[Dict[str, Any]] = None
        variable_watch_ref: Optional[str] = None
        variable_watch_refs = company.get("variable_watch_refs") or []
        if isinstance(variable_watch_refs, list) and variable_watch_refs:
            variable_watch_ref = str(variable_watch_refs[-1])
            try:
                variable_watch = self.variable_watch_store.load_variable_watch_by_id(variable_watch_ref)
            except Exception:
                missing["variable_watch"].append(variable_watch_ref)

        return {
            "company_ref": company_ref,
            "company": company,
            "latest_assessment_ref": latest_assessment_ref,
            "assessment": assessment,
            # include both for callers/debug
            "active_thesis_refs": deepcopy(active_thesis_refs) if isinstance(active_thesis_refs, list) else [],
            "thesis_refs": deepcopy(thesis_refs) if isinstance(thesis_refs, list) else [],
            "theses": theses,
            "quarter_event_refs": deepcopy(quarter_event_refs) if isinstance(quarter_event_refs, list) else [],
            "quarter_events": quarter_events,
            "trigger_map_ref": trigger_map_ref,
            "trigger_map": trigger_map,
            "variable_watch_ref": variable_watch_ref,
            "variable_watch": variable_watch,
            "missing": missing,
        }


__all__ = ["CompanyIntelligenceSnapshotLoader"]
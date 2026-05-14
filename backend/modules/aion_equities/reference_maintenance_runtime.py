# backend/modules/aion_equities/reference_maintenance_runtime.py

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore


def _dedupe_preserve(values: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for value in values:
        key = str(value)
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _merge_existing(company: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(company)
    out.update(deepcopy(patch))
    return out


class ReferenceMaintenanceRuntime:
    """
    Keeps company-level reference pointers current.

    Scope:
    - latest_assessment_ref
    - active_thesis_refs (ACTIVE only)
    - thesis_refs (ALL statuses: watch/active/closed etc.)
    - quarter_event_refs
    - catalyst_event_refs
    - trigger_map_refs
    - variable_watch_refs
    """

    def __init__(self, *, pilot_company_seed_store: PilotCompanySeedStore):
        self.pilot_company_seed_store = pilot_company_seed_store

    def update_company_references(
        self,
        *,
        company_ref: str,
        latest_assessment_ref: Optional[str] = None,
        active_thesis_refs: Optional[List[str]] = None,
        thesis_refs: Optional[List[str]] = None,  # NEW
        quarter_event_ref: Optional[str] = None,
        catalyst_event_ref: Optional[str] = None,
        trigger_map_ref: Optional[str] = None,
        variable_watch_ref: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        company = self.pilot_company_seed_store.load_company_seed(company_ref)

        existing_active_thesis_refs = list(company.get("active_thesis_refs") or [])
        existing_thesis_refs = list(company.get("thesis_refs") or [])  # NEW

        existing_quarter_event_refs = list(company.get("quarter_event_refs") or [])
        existing_catalyst_event_refs = list(company.get("catalyst_event_refs") or [])
        existing_trigger_map_refs = list(company.get("trigger_map_refs") or [])
        existing_variable_watch_refs = list(company.get("variable_watch_refs") or [])

        new_active_thesis_refs = _dedupe_preserve(
            list(active_thesis_refs or []) + existing_active_thesis_refs
        )

        new_thesis_refs = _dedupe_preserve(  # NEW
            list(thesis_refs or []) + existing_thesis_refs
        )

        new_quarter_event_refs = _dedupe_preserve(
            ([quarter_event_ref] if quarter_event_ref else []) + existing_quarter_event_refs
        )
        new_catalyst_event_refs = _dedupe_preserve(
            ([catalyst_event_ref] if catalyst_event_ref else []) + existing_catalyst_event_refs
        )
        new_trigger_map_refs = _dedupe_preserve(
            ([trigger_map_ref] if trigger_map_ref else []) + existing_trigger_map_refs
        )
        new_variable_watch_refs = _dedupe_preserve(
            ([variable_watch_ref] if variable_watch_ref else []) + existing_variable_watch_refs
        )

        merged_patch: Dict[str, Any] = {
            "latest_assessment_ref": latest_assessment_ref or company.get("latest_assessment_ref"),
            "active_thesis_refs": new_active_thesis_refs,
            "thesis_refs": new_thesis_refs,  # NEW
            "quarter_event_refs": new_quarter_event_refs,
            "catalyst_event_refs": new_catalyst_event_refs,
            "trigger_map_refs": new_trigger_map_refs,
            "variable_watch_refs": new_variable_watch_refs,
        }

        if payload_patch:
            merged_patch.update(deepcopy(payload_patch))

        updated = self.pilot_company_seed_store.save_company_seed(
            company_ref=company_ref,
            company_id=company["company_id"],
            ticker=company["ticker"],
            name=company["name"],
            sector=company["sector"],
            country=company["country"],
            generated_by="aion_equities.reference_maintenance_runtime",
            payload_patch=_merge_existing(company, merged_patch),
        )
        return updated

    def refresh_from_runtime_objects(
        self,
        *,
        company_ref: str,
        assessment: Optional[Dict[str, Any]] = None,
        thesis: Optional[Dict[str, Any]] = None,
        quarter_event: Optional[Dict[str, Any]] = None,
        catalyst_event_ref: Optional[str] = None,
        trigger_map_ref: Optional[str] = None,
        variable_watch_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        latest_assessment_ref = assessment.get("assessment_id") if assessment else None

        thesis_id: Optional[str] = None
        thesis_refs: List[str] = []
        active_thesis_refs: List[str] = []

        if thesis:
            thesis_id = thesis.get("thesis_id")
            if thesis_id:
                thesis_refs.append(thesis_id)  # ALWAYS track it
                if str(thesis.get("status", "")).strip().lower() == "active":
                    active_thesis_refs.append(thesis_id)

        quarter_event_ref = quarter_event.get("quarter_event_id") if quarter_event else None

        return self.update_company_references(
            company_ref=company_ref,
            latest_assessment_ref=latest_assessment_ref,
            active_thesis_refs=active_thesis_refs,
            thesis_refs=thesis_refs,  # NEW
            quarter_event_ref=quarter_event_ref,
            catalyst_event_ref=catalyst_event_ref,
            trigger_map_ref=trigger_map_ref,
            variable_watch_ref=variable_watch_ref,
        )


__all__ = ["ReferenceMaintenanceRuntime"]
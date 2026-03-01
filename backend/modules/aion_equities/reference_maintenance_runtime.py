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


class ReferenceMaintenanceRuntime:
    """
    Keeps company-level reference pointers current.

    Current scope:
    - latest_assessment_ref
    - active_thesis_refs
    - quarter_event_refs
    - catalyst_event_refs

    Storage target:
    - pilot company seed / company object payload
    """

    def __init__(self, *, pilot_company_seed_store: PilotCompanySeedStore):
        self.pilot_company_seed_store = pilot_company_seed_store

    def update_company_references(
        self,
        *,
        company_ref: str,
        latest_assessment_ref: Optional[str] = None,
        active_thesis_refs: Optional[List[str]] = None,
        quarter_event_ref: Optional[str] = None,
        catalyst_event_ref: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        company = self.pilot_company_seed_store.load_company_seed(company_ref)

        existing_active_thesis_refs = list(company.get("active_thesis_refs") or [])
        existing_quarter_event_refs = list(company.get("quarter_event_refs") or [])
        existing_catalyst_event_refs = list(company.get("catalyst_event_refs") or [])

        new_active_thesis_refs = _dedupe_preserve(
            list(active_thesis_refs or []) + existing_active_thesis_refs
        )
        new_quarter_event_refs = _dedupe_preserve(
            ([quarter_event_ref] if quarter_event_ref else []) + existing_quarter_event_refs
        )
        new_catalyst_event_refs = _dedupe_preserve(
            ([catalyst_event_ref] if catalyst_event_ref else []) + existing_catalyst_event_refs
        )

        merged_patch: Dict[str, Any] = {
            "latest_assessment_ref": latest_assessment_ref or company.get("latest_assessment_ref"),
            "active_thesis_refs": new_active_thesis_refs,
            "quarter_event_refs": new_quarter_event_refs,
            "catalyst_event_refs": new_catalyst_event_refs,
        }

        if payload_patch:
            merged_patch.update(deepcopy(payload_patch))

        updated = self.pilot_company_seed_store.save_company_seed(
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
    ) -> Dict[str, Any]:
        latest_assessment_ref = assessment.get("assessment_id") if assessment else None

        active_thesis_refs: List[str] = []
        if thesis and str(thesis.get("status", "")).strip().lower() == "active":
            thesis_id = thesis.get("thesis_id")
            if thesis_id:
                active_thesis_refs.append(thesis_id)

        quarter_event_ref = None
        if quarter_event:
            quarter_event_ref = quarter_event.get("quarter_event_id")

        return self.update_company_references(
            company_ref=company_ref,
            latest_assessment_ref=latest_assessment_ref,
            active_thesis_refs=active_thesis_refs,
            quarter_event_ref=quarter_event_ref,
            catalyst_event_ref=catalyst_event_ref,
        )


def _merge_existing(company: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(company)
    out.update(deepcopy(patch))
    return out


__all__ = [
    "ReferenceMaintenanceRuntime",
]
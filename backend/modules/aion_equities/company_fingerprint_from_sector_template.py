from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_equities.company_fingerprint_store import CompanyFingerprintStore
from backend.modules.aion_equities.sector_template_store import SectorTemplateStore


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_company_fingerprint_from_sector_template(
    *,
    company_ref: str,
    sector_ref: str,
    as_of_date: Optional[Any],
    sector_template_store: SectorTemplateStore,
    fingerprint_store: CompanyFingerprintStore,
    generated_by: str = "aion_equities.company_fingerprint_from_sector_template",
    validate: bool = False,
) -> Dict[str, Any]:
    """
    Minimal v0: create a company fingerprint that starts from sector template priors.

    It does NOT pretend to be calibrated; it seeds:
      - driver_map from sector_template.variable_map.primary/secondary
      - fingerprint_summary.report_count = 0
      - fingerprint_summary.analytical_confidence = low-ish
      - linked_refs includes sector_template_id and sector_ref
    """
    as_of_date = as_of_date or _utc_today()

    tmpl = sector_template_store.load_sector_template(sector_ref, validate=False)

    vm = tmpl.get("variable_map", {}) if isinstance(tmpl.get("variable_map"), dict) else {}
    primary = vm.get("primary_variables", []) if isinstance(vm.get("primary_variables"), list) else []
    secondary = vm.get("secondary_variables", []) if isinstance(vm.get("secondary_variables"), list) else []

    # Convert variable map items into fingerprint drivers
    def to_driver(x: Any, importance: str) -> Dict[str, Any]:
        if isinstance(x, dict):
            return {
                "name": x.get("name") or x.get("variable_name") or "unknown",
                "importance": importance,
                "source_series": x.get("feed_id") or x.get("data_source") or x.get("source_series") or "unknown",
            }
        return {"name": str(x), "importance": importance, "source_series": "unknown"}

    primary_drivers = [to_driver(x, "primary") for x in primary]
    secondary_drivers = [to_driver(x, "secondary") for x in secondary]

    fp_defaults = tmpl.get("fingerprint_defaults", {}) if isinstance(tmpl.get("fingerprint_defaults"), dict) else {}
    base_predictability = fp_defaults.get("base_predictability", "medium")
    expected_reports = int(fp_defaults.get("expected_report_count_for_calibration", 20))

    payload = fingerprint_store.save_company_fingerprint(
        company_ref=company_ref,
        sector_template_ref=tmpl.get("sector_template_id") or tmpl.get("sector_ref"),
        as_of_date=as_of_date,
        generated_by=generated_by,
        primary_drivers=primary_drivers,
        secondary_drivers=secondary_drivers,
        fingerprint_summary_patch={
            "analytical_confidence": 10.0,
            "report_count": 0,
            "summary": f"Seeded from sector template priors (base_predictability={base_predictability}, expected_reports={expected_reports}).",
        },
        linked_refs_patch={
            "sector_ref": sector_ref,
            "sector_template_id": tmpl.get("sector_template_id"),
        },
        validate=validate,
    )
    return payload


__all__ = ["build_company_fingerprint_from_sector_template"]
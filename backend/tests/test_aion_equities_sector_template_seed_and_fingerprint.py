from __future__ import annotations

from backend.modules.aion_equities.company_fingerprint_from_sector_template import (
    build_company_fingerprint_from_sector_template,
)
from backend.modules.aion_equities.company_fingerprint_store import CompanyFingerprintStore
from backend.modules.aion_equities.sector_template_seed_runtime import SectorTemplateSeedRuntime
from backend.modules.aion_equities.sector_template_store import SectorTemplateStore


def test_sector_template_seed_runtime_writes_presets(tmp_path):
    store = SectorTemplateStore(tmp_path)
    seeder = SectorTemplateSeedRuntime(sector_template_store=store)

    out = seeder.seed_presets_v0(as_of_date="2026-03-05", validate=False)
    assert len(out) >= 5

    loaded = store.load_sector_template("sector/staffing", validate=False)
    assert loaded["sector_ref"] == "sector/staffing"
    assert "variable_map" in loaded
    assert isinstance(loaded["variable_map"]["primary_variables"], list)


def test_build_company_fingerprint_from_sector_template(tmp_path):
    sector_store = SectorTemplateStore(tmp_path)
    fp_store = CompanyFingerprintStore(tmp_path)

    seeder = SectorTemplateSeedRuntime(sector_template_store=sector_store)
    seeder.seed_presets_v0(as_of_date="2026-03-05", validate=False)

    fp = build_company_fingerprint_from_sector_template(
        company_ref="company/PAGE.L",
        sector_ref="sector/staffing",
        as_of_date="2026-03-05",
        sector_template_store=sector_store,
        fingerprint_store=fp_store,
        validate=False,
    )

    assert fp["company_ref"] == "company/PAGE.L"
    assert fp["sector_template_ref"].startswith("sector_template/")
    assert fp["fingerprint_summary"]["report_count"] == 0
    assert len(fp["driver_map"]["primary_drivers"]) > 0
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PILOT = (ROOT / "desktop/mac/src/aion_finance_pilot.js").read_text(encoding="utf-8")


def test_finance_model_finalisation_requires_canonical_container_receipt():
    assert "syncFinanceStateNow?.(latest)" in PILOT
    assert "Canonical Finance Business Container receipt was not returned" in PILOT
    assert "finance_model_receipt: sync.finance_model" in PILOT
    assert "latest.status = 'review'" in PILOT
    assert "status: 'failed'" in PILOT


def test_finance_model_handoff_does_not_duplicate_workbook_analysis_in_local_storage():
    assert "const sourceRecords = (state.source_records || []).map" in PILOT
    assert "source_records: sourceRecords" in PILOT
    assert "analysis_result: item.analysis_result" not in PILOT.split(
        "function buildBusinessFinancialModel", 1
    )[1].split("function refresh", 1)[0]
    assert "canonical Business Container remains authoritative" in PILOT


def test_finance_model_build_exposes_progress_and_actionable_failure_state():
    assert "Building Financial Model…" in PILOT
    assert "role=\"alert\"" in PILOT
    assert "Your discovery answers remain saved" in PILOT


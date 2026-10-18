from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_reconciliation_service import FinanceReconciliationService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _setup(monkeypatch, tmp_path: Path) -> BusinessContainerRepository:
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    repository = BusinessContainerRepository(root / "business_containers")
    workspace = "home-fixed"; period = {"from": "2025-01-01", "to": "2025-12-31"}; sync_id = "sync-1"
    repository.save_dict(workspace, "business_financial_model", {
        "id": f"{workspace}.business_financial_model", "workspace_id": workspace,
        "kind": "business_financial_model", "meta": {}, "currency": "EUR", "revision": 4,
        "integration_evidence": {"xero": {"period": period, "evidence_ref": {"sync_id": sync_id, "period": period, "verification_status": "provider_sourced"}}},
        "external_data": {"artifacts": {"accounts-xlsx": {
            "artifact_id": "accounts-xlsx", "verification_status": "accepted_from_source_document", "period": period,
            "facts": [{"source_column": "revenue", "value": 120000}, {"source_column": "gross_profit", "value": 70000}],
        }}},
    })
    repository.save_dict(workspace, "department_intelligence", {"id": f"{workspace}.department_intelligence", "workspace_id": workspace, "kind": "department_intelligence", "meta": {}, "departments": {}, "revision": 1})
    repository.save_dict(workspace, "boardroom_snapshot", {"id": f"{workspace}.boardroom_snapshot", "workspace_id": workspace, "kind": "boardroom_snapshot", "meta": {}, "topology": {}, "boardroom": {}})
    sync = AIONBusinessPaths.business_container_dir(workspace) / f"integrations/xero/syncs/{sync_id}"; sync.mkdir(parents=True)
    (sync / "profit_and_loss.json").write_text(json.dumps({"Reports": [{"Rows": [
        {"Cells": [{"Value": "Revenue"}, {"Value": "120000.00"}]},
        {"Cells": [{"Value": "Gross Profit"}, {"Value": "68000.00"}]},
    ]}]}))
    return repository


def test_reconciliation_matches_equivalent_periods_and_surfaces_conflicts(monkeypatch, tmp_path: Path) -> None:
    repository = _setup(monkeypatch, tmp_path); before = repository.load_dict("home-fixed", "business_financial_model")
    record = FinanceReconciliationService(repository).run("home-fixed", created_at="2026-07-20T12:00:00+00:00")
    rows = {item["metric"]: item for item in record["comparisons"]}
    assert rows["revenue"]["status"] == "match"
    assert rows["gross_profit"]["status"] == "conflict"
    assert rows["gross_profit"]["difference"] == -2000
    assert record["status"] == "review_required"
    assert record["external_writes_performed"] is False
    assert repository.load_dict("home-fixed", "business_financial_model") == before
    intelligence = repository.load_dict("home-fixed", "department_intelligence")
    assert intelligence["departments"]["finance"]["latest_reconciliation"]["counts"]["conflict"] == 1


def test_reconciliation_requires_period_and_review_does_not_silently_replace_truth(monkeypatch, tmp_path: Path) -> None:
    repository = _setup(monkeypatch, tmp_path); model = repository.load_dict("home-fixed", "business_financial_model")
    model["external_data"]["artifacts"]["accounts-xlsx"].pop("period"); repository.save_dict("home-fixed", "business_financial_model", model)
    service = FinanceReconciliationService(repository)
    record = service.run("home-fixed", created_at="2026-07-20T12:00:00+00:00")
    assert record["counts"]["period_missing"] == 2
    assert any("reporting period is required" in warning for warning in record["warnings"])
    before = repository.load_dict("home-fixed", "business_financial_model")
    reviewed = service.review("home-fixed", record["reconciliation_id"], decision="prefer_xero", reviewed_by="kevin")
    assert reviewed["status"] == "reviewed_requires_separate_canonical_update"
    assert reviewed["canonical_values_changed"] is False
    assert repository.load_dict("home-fixed", "business_financial_model") == before


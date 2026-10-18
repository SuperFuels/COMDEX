from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_director_service import FinanceDirectorService
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.finance_transaction_reconciliation_service import FinanceTransactionReconciliationService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


ROOT = Path(__file__).resolve().parents[3]


def configure(monkeypatch, tmp_path: Path) -> BusinessContainerRepository:
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")
    return BusinessContainerRepository(root / "business_containers")


def seed(monkeypatch, tmp_path: Path) -> BusinessContainerRepository:
    repository = configure(monkeypatch, tmp_path); workspace = "home-fixed"; sync_id = "xero_sync_test"
    repository.save_dict(workspace, "business_financial_model", {
        "id": f"{workspace}.business_financial_model", "workspace_id": workspace,
        "kind": "business_financial_model", "meta": {"workspace_id": workspace, "container_key": "business_financial_model"},
        "currency": "EUR", "period_basis": "annual", "revision": 2,
        "metrics": {"revenue": 120000, "direct_costs": 96000, "overheads": 30000, "ending_cash": 5000},
        "cashflow_model": {"minimum_cash_reserve": 3500},
        "integration_evidence": {"xero": {"evidence_ref": {"sync_id": sync_id}, "status": "connected"}},
        "evidence_refs": [{"provider": "xero", "sync_id": sync_id}],
    })
    repository.save_dict(workspace, "business_operating_model", {
        "id": f"{workspace}.business_operating_model", "workspace_id": workspace,
        "kind": "business_operating_model", "meta": {"workspace_id": workspace, "container_key": "business_operating_model"},
        "currency": "EUR", "offerings": [{"name": "Repair visit"}],
        "unit_economics": [{"offering": "Repair visit", "price": 100, "contribution_per_unit": 16}],
        "inventory_metrics": {"total_stock_value": 2000, "suggested_procurement_cash_required": 900},
        "procurement_queue": [{"status": "review_required"}],
    })
    repository.save_dict(workspace, "department_intelligence", {
        "id": f"{workspace}.department_intelligence", "workspace_id": workspace, "kind": "department_intelligence",
        "meta": {"workspace_id": workspace, "container_key": "department_intelligence"}, "departments": {}, "revision": 1,
    })
    repository.save_dict(workspace, "boardroom_snapshot", {
        "id": f"{workspace}.boardroom_snapshot", "workspace_id": workspace, "kind": "boardroom_snapshot",
        "meta": {"workspace_id": workspace, "container_key": "boardroom_snapshot"}, "boardroom": {},
    })
    sync_dir = AIONBusinessPaths.business_container_dir(workspace) / "integrations/xero/syncs" / sync_id
    sync_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).date(); overdue = (today - timedelta(days=30)).isoformat()
    payloads = {
        "accounts": {"Accounts": [{"AccountID": "bank-1", "Code": "090", "Name": "Current Account", "Type": "BANK", "Status": "ACTIVE"}]},
        "invoices": {"Invoices": [
            {"InvoiceID": "sales-1", "InvoiceNumber": "INV-001", "Type": "ACCREC", "Status": "AUTHORISED", "Date": overdue, "DueDate": overdue, "Total": 1000, "AmountPaid": 0, "AmountDue": 1000, "Contact": {"ContactID": "c1", "Name": "Customer One"}},
            {"InvoiceID": "bill-1", "InvoiceNumber": "BILL-001", "Type": "ACCPAY", "Status": "AUTHORISED", "Date": overdue, "DueDate": overdue, "Total": 400, "AmountPaid": 400, "AmountDue": 0, "Contact": {"ContactID": "s1", "Name": "Supplier One"}},
        ]},
        "payments": {"Payments": [{"PaymentID": "pay-1", "Date": overdue, "Amount": 400, "Status": "AUTHORISED", "Invoice": {"InvoiceID": "bill-1", "InvoiceNumber": "BILL-001"}, "Account": {"AccountID": "bank-1"}}]},
        "bank_transactions": {"BankTransactions": [
            {"BankTransactionID": "bank-tx-1", "Type": "RECEIVE", "Status": "AUTHORISED", "Date": overdue, "Total": 1000, "Reference": "INV-001", "IsReconciled": False, "Contact": {"ContactID": "c1", "Name": "Customer One"}, "BankAccount": {"AccountID": "bank-1"}},
            {"BankTransactionID": "bank-tx-2", "Type": "RECEIVE", "Status": "AUTHORISED", "Date": overdue, "Total": 1000, "Reference": "INV-001", "IsReconciled": False, "Contact": {"ContactID": "c1", "Name": "Customer One"}, "BankAccount": {"AccountID": "bank-1"}},
        ]},
        "manual_journals": {"ManualJournals": [{"ManualJournalID": "j1", "Date": overdue, "Status": "POSTED", "Narration": "Accrual", "JournalLines": [{"LineAmount": 100}, {"LineAmount": -100}]}]},
        "tracking_categories": {"TrackingCategories": [{"TrackingCategoryID": "t1", "Name": "Region", "Status": "ACTIVE", "Options": [{"TrackingOptionID": "o1", "Name": "Almeria", "Status": "ACTIVE"}]}]},
        "projects": {"items": [{"projectId": "p1", "name": "Villa repair", "status": "INPROGRESS", "estimateAmount": 5000}]},
    }
    for name, payload in payloads.items():
        (sync_dir / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    snapshot = {"schema_version": "aion.xero.read_only_sync.v1", "sync_id": sync_id, "business_id": workspace,
                "synced_at": datetime.now(UTC).isoformat(), "period": {"from": overdue, "to": today.isoformat()},
                "summary": {}, "source_paths": {}, "read_only": True, "external_writes_enabled": False}
    snapshot["snapshot_hash"] = FinanceLedgerService._hash(snapshot)
    (sync_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    return repository


def test_canonical_ledger_is_hash_bound_bounded_and_file_cabinet_indexed(monkeypatch, tmp_path: Path) -> None:
    repository = seed(monkeypatch, tmp_path); service = FinanceLedgerService(repository)
    ledger = service.build("home-fixed", created_at="2026-07-21T20:00:00+00:00")
    assert ledger["record_counts"]["invoices"] == 2
    assert ledger["record_counts"]["bank_transactions"] == 2
    assert ledger["record_counts"]["projects"] == 1
    assert ledger["summaries"]["accounts_receivable"] == 1000
    assert ledger["external_write_performed"] is False
    assert len(service.records("home-fixed", ledger["ledger_id"], "bank_transactions", limit=1)) == 1
    model = repository.load_dict("home-fixed", "business_financial_model")
    assert model["ledger"]["ledger_hash"] == ledger["ledger_hash"]
    cabinet = (AIONBusinessPaths.ROOT / "workflow_file_cabinets/home-fixed/tree.json").read_text(encoding="utf-8")
    assert "Ledgers" in cabinet and ledger["ledger_id"] in cabinet


def test_transaction_matching_scores_duplicates_and_never_posts_provider_write(monkeypatch, tmp_path: Path) -> None:
    repository = seed(monkeypatch, tmp_path); ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    service = FinanceTransactionReconciliationService(repository, ledger)
    result = service.run("home-fixed", created_at="2026-07-21T20:01:00+00:00")
    assert result["match_count"] >= 2
    assert any(item["confidence"] == "high" for item in result["matches"])
    assert any(item["kind"] == "possible_duplicate" for item in result["exceptions"])
    assert any(item["kind"] == "overdue_invoice" for item in result["exceptions"])
    reviewed = service.review("home-fixed", result["run_id"], result["matches"][0]["match_id"], decision="accept_match", reviewed_by="founder")
    assert reviewed["accepted_draft_match_count"] == 1
    assert reviewed["provider_reconciliations_posted"] == 0
    assert reviewed["external_write_performed"] is False


def test_finance_director_builds_living_model_signals_and_boardroom_proposals(monkeypatch, tmp_path: Path) -> None:
    repository = seed(monkeypatch, tmp_path); ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    record = FinanceDirectorService(repository, ledger).refresh("home-fixed", minimum_cash_reserve=3500,
                                                               created_at="2026-07-21T20:02:00+00:00")
    codes = {item["code"] for item in record["proactive_signals"]}
    proposal_kinds = {item["kind"] for item in record["boardroom_proposals"]}
    assert "overdue_receivables" in codes
    assert "gross_margin_low" in codes
    assert "invoice_chase" in proposal_kinds
    assert "pricing_review" in proposal_kinds
    assert all(item["status"] == "boardroom_review_required" for item in record["boardroom_proposals"])
    assert record["external_write_performed"] is False
    boardroom = repository.load_dict("home-fixed", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["finance_boardroom_proposals"]


def test_finance_director_desktop_surface_exposes_review_controls_and_read_only_boundary() -> None:
    source = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(encoding="utf-8")
    for marker in ["data-aion-finance-build-ledger", "data-aion-finance-refresh-director",
                   "data-aion-finance-run-transaction-reconciliation", "data-aion-transaction-match-review"]:
        assert marker in source
    assert "Accepting a match never posts a reconciliation" in source
    assert "provider not changed" in source

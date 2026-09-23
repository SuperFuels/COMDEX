from __future__ import annotations

from backend.modules.aion_business.runtime.finance_month_end_service import FinanceMonthEndService
from backend.tests.test_finance_bookkeeping_service import configure


def test_month_end_is_evidence_backed_and_never_closes_period(monkeypatch, tmp_path):
    repository, _ = configure(monkeypatch, tmp_path)
    repository.save_dict("acme", "business_financial_model", {
        "id": "acme.business_financial_model", "workspace_id": "acme",
        "kind": "business_financial_model",
        "meta": {"workspace_id": "acme", "container_key": "business_financial_model"},
        "integration_evidence": {"xero": {"evidence_ref": {"sync_id": "sync-1", "snapshot_hash": "sha256:x"},
                                                    "sync_summary": {"reports_received": ["profit_and_loss", "balance_sheet"]}}},
    })
    repository.save_dict("acme", "finance_inbox", {
        "id": "acme.finance_inbox", "workspace_id": "acme", "kind": "finance_inbox",
        "meta": {"workspace_id": "acme", "container_key": "finance_inbox"}, "documents": [],
    })
    service = FinanceMonthEndService(repository)
    service.ledger.latest = lambda *_args, **_kwargs: {
        "record_counts": {"bank_transactions": 3, "payments": 2},
        "summaries": {"accounts_receivable": 0, "accounts_payable": 0,
                      "overdue_receivables": 0, "overdue_payables": 0},
    }
    result = service.evaluate("acme", period_end="2026-08-31", prepared_by_person_id="person.owner")
    assert result["status"] == "ready_for_human_review"
    assert result["blocker_count"] == 0
    assert result["external_write_performed"] is False
    assert result["period_closed"] is False
    assert service.latest("acme")["readiness_hash"] == result["readiness_hash"]
    boardroom = repository.load_dict("acme", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["latest_finance_month_end_readiness"]["status"] == "ready_for_human_review"


def test_month_end_blocks_when_source_reports_are_missing(monkeypatch, tmp_path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = FinanceMonthEndService(repository)
    service.ledger.latest = lambda *_args, **_kwargs: {"record_counts": {}, "summaries": {}}
    result = service.evaluate("acme", period_end="2026-08-31", prepared_by_person_id="person.owner")
    assert result["status"] == "blocked"
    assert {row["check_id"] for row in result["checks"] if row["status"] == "block"} >= {
        "provider_sync", "profit_and_loss", "balance_sheet",
    }

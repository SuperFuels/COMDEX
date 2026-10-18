from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from backend.modules.aion_business.runtime.finance_counterparty_intelligence_service import FinanceCounterpartyIntelligenceService
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.finance_transaction_reconciliation_service import FinanceTransactionReconciliationService
from backend.modules.aion_business.runtime.finance_security_policy import get_finance_security_policy
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.xero_reconciliation_handoff_service import XeroReconciliationHandoffService
from backend.tests.workflow_capsules.test_aion_finance_director_transaction_vertical import ROOT, seed


class FakeClassifierRouter:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        assert kwargs["capability"] == "classification"
        assert kwargs["metadata"]["external_write_allowed"] is False
        assert "allowed_accounts" in kwargs["prompt"]
        return SimpleNamespace(ok=True, content=json.dumps({
            "account_code": "300", "category": "materials", "confidence": 0.88,
            "rationale": "The supplier and reference indicate repair materials.",
            "question_for_human": "Confirm that ABC Supplier provides repair materials.",
        }), provider="test-llm", model="classification-test", error_code=None)


def _add_unknown_supplier(repository) -> None:
    model = repository.load_dict("home-fixed", "business_financial_model")
    sync_id = model["integration_evidence"]["xero"]["evidence_ref"]["sync_id"]
    sync_dir = AIONBusinessPaths.business_container_dir("home-fixed") / "integrations/xero/syncs" / sync_id
    accounts_path = sync_dir / "accounts.json"
    accounts = json.loads(accounts_path.read_text(encoding="utf-8"))
    accounts["Accounts"].append({"AccountID": "materials-1", "Code": "300", "Name": "Materials", "Type": "DIRECTCOSTS", "Status": "ACTIVE"})
    accounts_path.write_text(json.dumps(accounts), encoding="utf-8")
    bank_path = sync_dir / "bank_transactions.json"
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    bank["BankTransactions"].append({
        "BankTransactionID": "bank-tx-unknown", "Type": "SPEND", "Status": "AUTHORISED",
        "Date": "2026-07-20", "Total": -125.50, "Reference": "building supplies 8844221100",
        "IsReconciled": False, "Contact": {"ContactID": "abc", "Name": "ABC Supplier"},
        "BankAccount": {"AccountID": "bank-1"},
    })
    bank_path.write_text(json.dumps(bank), encoding="utf-8")


def test_llm_suggests_new_counterparty_but_human_confirmation_creates_memory(monkeypatch, tmp_path) -> None:
    repository = seed(monkeypatch, tmp_path); _add_unknown_supplier(repository)
    ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    router = FakeClassifierRouter(); intelligence = FinanceCounterpartyIntelligenceService(router)
    service = FinanceTransactionReconciliationService(repository, ledger, intelligence)
    first = service.run("home-fixed")
    suggestion = next(item for item in first["classifications"] if item["counterparty"] == "ABC Supplier")
    assert suggestion["source"] == "llm_suggestion"
    assert suggestion["suggested_account"]["code"] == "300"
    assert suggestion["status"] == "human_confirmation_required"
    assert suggestion["external_write_performed"] is False
    reviewed = service.review_classification(
        "home-fixed", first["run_id"], suggestion["suggestion_id"], decision="accept_mapping",
        reviewed_by="founder", selected_account=suggestion["suggested_account"],
    )
    assert reviewed["reviewed_classification_count"] == 1
    second = service.run("home-fixed")
    remembered = next(item for item in second["classifications"] if item["counterparty"] == "ABC Supplier")
    assert remembered["source"] == "confirmed_mapping"
    assert remembered["confidence"] == 1.0
    assert router.calls == 1


def test_unknown_or_invalid_llm_account_is_escalated_not_invented(monkeypatch, tmp_path) -> None:
    repository = seed(monkeypatch, tmp_path); _add_unknown_supplier(repository)
    ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    class InvalidRouter(FakeClassifierRouter):
        def generate(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(ok=True, content='{"account_code":"DOES-NOT-EXIST","confidence":0.99}', provider="test", model="test", error_code=None)
    service = FinanceTransactionReconciliationService(repository, ledger, FinanceCounterpartyIntelligenceService(InvalidRouter()))
    result = service.run("home-fixed")
    suggestion = next(item for item in result["classifications"] if item["counterparty"] == "ABC Supplier")
    assert suggestion["suggested_account"] is None
    assert suggestion["status"] == "needs_human_input"
    assert suggestion["confidence"] == 0


def test_malformed_llm_confidence_is_safely_treated_as_untrusted(monkeypatch, tmp_path) -> None:
    repository = seed(monkeypatch, tmp_path); _add_unknown_supplier(repository)
    ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    class MalformedRouter(FakeClassifierRouter):
        def generate(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(ok=True, content='{"account_code":"300","confidence":"certain"}', provider="test", model="test", error_code=None)
    service = FinanceTransactionReconciliationService(repository, ledger, FinanceCounterpartyIntelligenceService(MalformedRouter()))
    result = service.run("home-fixed", classification_limit=1)
    suggestion = next(item for item in result["classifications"] if item["counterparty"] == "ABC Supplier")
    assert suggestion["confidence"] == 0
    assert suggestion["status"] == "needs_human_input"
    assert result["policy"]["classification_limit"] == 1


def test_xero_handoff_requires_exact_hash_and_returns_immutable_provider_limitation_receipt(monkeypatch, tmp_path) -> None:
    repository = seed(monkeypatch, tmp_path); ledger = FinanceLedgerService(repository); ledger.build("home-fixed")
    reconciliation_service = FinanceTransactionReconciliationService(repository, ledger)
    reconciliation = reconciliation_service.run("home-fixed", classify_unmatched=False)
    match = reconciliation["matches"][0]
    reconciliation = reconciliation_service.review("home-fixed", reconciliation["run_id"], match["match_id"], decision="accept_match", reviewed_by="founder")
    service = XeroReconciliationHandoffService()
    handoff = service.prepare("home-fixed", reconciliation, match["match_id"])
    with pytest.raises(ValueError, match="approved_payload_hash_mismatch"):
        service.decide("home-fixed", handoff["handoff_id"], approved=True, decided_by="founder", decided_payload_hash="sha256:wrong")
    approved = service.decide("home-fixed", handoff["handoff_id"], approved=True, decided_by="founder", decided_payload_hash=handoff["payload_hash"])
    receipt = service.execute("home-fixed", approved["handoff_id"], attempted_by="founder")
    assert receipt["code"] == "xero_bank_statement_reconciliation_api_not_supported"
    assert receipt["manual_handoff_required"] is True
    assert receipt["external_write_performed"] is False
    assert receipt["provider_reconciliations_posted"] == 0
    assert service.execute("home-fixed", approved["handoff_id"], attempted_by="founder")["receipt_hash"] == receipt["receipt_hash"]
    assert service.list("home-fixed")[0]["handoff_id"] == approved["handoff_id"]
    cabinet = (AIONBusinessPaths.ROOT / "workflow_file_cabinets/home-fixed/tree.json").read_text(encoding="utf-8")
    assert "Xero Reconciliation Handoffs" in cabinet and receipt["receipt_id"] in cabinet


def test_policy_and_ui_make_llm_and_xero_boundaries_explicit() -> None:
    policy = get_finance_security_policy()["capability_matrix"]
    assert policy["classify_unknown_counterparties"]["enabled"] is True
    assert policy["reconcile_xero_bank_statement_line"]["enabled"] is False
    assert policy["reconcile_xero_bank_statement_line"]["mode"] == "provider_unsupported"
    source = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(encoding="utf-8")
    assert "data-aion-counterparty-classification-review" in source
    assert "data-aion-xero-handoff-prepare" in source
    assert "Approve this exact handoff" in source
    assert "only a confirmed human review creates reusable mapping memory" in source

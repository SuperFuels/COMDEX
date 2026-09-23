from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def configure(monkeypatch, tmp_path: Path):
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")
    repository = BusinessContainerRepository(root / "business_containers")
    authority = OrganizationAuthorityService(repository)
    organisation = authority.empty("acme")
    organisation["people"] = [{
        "id": "person.owner", "name": "Owner", "email": "owner@example.test",
        "status": "active", "employment_type": "owner",
        "role_ids": ["role.owner_director"], "department_ids": [], "project_ids": [],
    }]
    authority.save("acme", organisation)
    repository.save_dict("acme", "department_intelligence", {
        "id": "acme.department_intelligence", "workspace_id": "acme", "kind": "department_intelligence",
        "meta": {"workspace_id": "acme", "container_key": "department_intelligence"},
        "departments": {}, "revision": 1,
    })
    repository.save_dict("acme", "boardroom_snapshot", {
        "id": "acme.boardroom_snapshot", "workspace_id": "acme", "kind": "boardroom_snapshot",
        "meta": {"workspace_id": "acme", "container_key": "boardroom_snapshot"}, "boardroom": {},
    })
    return repository, authority


def instruction_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return "sha256:" + sha256(raw.encode()).hexdigest()


def seed_document(repository, *, allocation=True):
    instruction = {
        "schema_version": "aion.finance.accounting_instruction.v1", "workspace_id": "acme",
        "source_document_id": "finance-document-1", "source_document_hash": "sha256:source",
        "destination": "expense", "document_type": "receipt",
        "fields": {"supplier": "Builder Store", "document_date": "2026-08-09", "currency": "EUR",
                   "net": 50, "tax": 10.5, "total": 60.5, "due_date": "2026-08-16",
                   "payment_method": "company card"},
        "ownership": {"submitted_by_person_id": "person.owner", "department_id": None,
                      "project_id": None, "card_asset_id": "card.1"},
        "allocation": {"account_code": "500", "account_name": "Materials", "tax_code": "INPUT21"}
                      if allocation else {},
        "approval": {"decided_by_person_id": "person.owner", "decided_at": "2026-08-09T09:00:00+00:00"},
        "external_write_permitted": False,
    }
    repository.save_dict("acme", "finance_inbox", {
        "id": "finance-inbox-acme", "workspace_id": "acme", "kind": "finance_inbox",
        "meta": {"workspace_id": "acme", "container_key": "finance_inbox"},
        "documents": [{
            "id": "finance-document-1", "status": "approved_for_accounting", "document_type": "receipt",
            "accounting": {"exact_payload": instruction, "payload_hash": instruction_hash(instruction)},
        }],
    })


def test_approved_receipt_becomes_balanced_separately_approved_internal_journal(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_document(repository)
    service = FinanceBookkeepingService(repository, authority)
    draft = service.prepare_document("acme", "finance-document-1", prepared_by_person_id="person.owner")
    assert draft["status"] == "exact_posting_approval_required"
    assert draft["debit_total"] == draft["credit_total"] == 60.5
    assert {row["account_code"] for row in draft["lines"]} == {"500", "control.input_tax", "control.company_card_clearing"}
    assert draft["external_write_performed"] is False

    with pytest.raises(ValueError, match="hash_mismatch"):
        service.approve("acme", draft["draft_id"], approved_by_person_id="person.owner", approved_draft_hash="wrong")
    approved = service.approve(
        "acme", draft["draft_id"], approved_by_person_id="person.owner",
        approved_draft_hash=draft["draft_hash"],
    )
    assert approved["status"] == "approved_for_internal_posting"
    posted = service.post_internal("acme", draft["draft_id"], posted_by_person_id="person.owner")
    assert posted["status"] == "posted_internal"
    assert posted["internal_posting"]["entry_hash"]
    assert service.post_internal("acme", draft["draft_id"], posted_by_person_id="person.owner") == posted
    journal = AIONBusinessPaths.business_container_dir("acme") / "finance/bookkeeping/internal_journal.jsonl"
    assert len(journal.read_text().splitlines()) == 1
    summary = service.ledger_summary("acme")
    assert summary["balanced"] is True
    assert summary["entry_count"] == 1
    assert summary["total_debits"] == summary["total_credits"] == 60.5
    assert summary["included_in_provider_actuals"] is False
    assert {row["account_type"] for row in summary["accounts"]} == {"expense", "asset", "liability"}
    boardroom = repository.load_dict("acme", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["latest_finance_bookkeeping_entry"]["debit_total"] == 60.5
    assert boardroom["boardroom"]["runtime"]["latest_finance_bookkeeping_entry"]["internal_ledger"]["balanced"] is True


def test_missing_account_or_tax_mapping_fails_closed(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_document(repository, allocation=False)
    service = FinanceBookkeepingService(repository, authority)
    draft = service.prepare_document("acme", "finance-document-1", prepared_by_person_id="person.owner")
    assert draft["status"] == "mapping_required"
    assert "expense_account_code" in draft["unresolved_controls"]
    assert "input_tax_code" in draft["unresolved_controls"]
    with pytest.raises(ValueError, match="mapping_required"):
        service.approve("acme", draft["draft_id"], approved_by_person_id="person.owner",
                        approved_draft_hash=draft["draft_hash"])


def test_provider_catalog_is_honest_about_implemented_connectors(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    repository.save_dict("acme", "business_financial_model", {
        "id": "acme.business_financial_model", "workspace_id": "acme", "kind": "business_financial_model",
        "meta": {"workspace_id": "acme", "container_key": "business_financial_model"},
        "integration_evidence": {"xero": {"status": "connected"}},
    })
    catalog = FinanceBookkeepingService(repository, authority).provider_catalog("acme")
    rows = {row["provider_id"]: row for row in catalog["providers"]}
    assert rows["xero"]["connected"] is True
    assert rows["xero"]["available_writes"] == []
    assert rows["sage_accounting"]["implemented_mode"] == "read_adapter_and_harness_ready"
    assert rows["quickbooks_online"]["connected"] is False
    assert catalog["external_writes_enabled"] is False

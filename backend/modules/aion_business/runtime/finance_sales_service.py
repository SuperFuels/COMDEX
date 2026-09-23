"""Provider-neutral sales invoicing and collections control.

Sales invoices are business instructions before they are provider resources.
This service validates customers and offerings, creates a balanced receivables
journal, requires exact approval, and projects only controlled summaries.
It never sends customer messages or writes to an accounting provider.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


class FinanceSalesService:
    """Own the provider-neutral customer invoice and collection lifecycle."""

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None,
                 bookkeeping: FinanceBookkeepingService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)
        self.bookkeeping = bookkeeping or FinanceBookkeepingService(self.repository, self.authority)

    def catalog(self, workspace_id: str) -> dict[str, Any]:
        operating = self.repository.load_optional_dict(workspace_id, "business_operating_model") or {}
        return {
            "workspace_id": workspace_id,
            "currency": operating.get("currency") or "EUR",
            "offerings": operating.get("offerings") or [],
            "customers": self.list_customers(workspace_id),
            "invoices": self.list_invoices(workspace_id),
            "summary": self.summary(workspace_id),
        }

    def create_customer(self, workspace_id: str, *, name: str, email: str | None,
                        tax_id: str | None = None, billing_address: str | None = None,
                        payment_terms_days: int = 14,
                        created_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, created_by_person_id, "finance.prepare")
        name = str(name or "").strip()
        email = str(email or "").strip().lower() or None
        if not name:
            raise ValueError("finance_customer_name_required")
        if payment_terms_days < 0 or payment_terms_days > 365:
            raise ValueError("finance_customer_payment_terms_invalid")
        key = canonical_contract_hash({"name": name.casefold(), "email": email}).removeprefix("sha256:")[:20]
        customer_id = f"customer-{key}"
        existing = self._customer_path(workspace_id, customer_id)
        if existing.exists():
            return self.load_customer(workspace_id, customer_id)
        record = {
            "schema_version": "aion.finance.customer.v1", "customer_id": customer_id,
            "workspace_id": workspace_id, "name": name, "email": email,
            "tax_id": str(tax_id or "").strip() or None,
            "billing_address": str(billing_address or "").strip() or None,
            "payment_terms_days": int(payment_terms_days), "status": "active",
            "provider_links": {}, "created_at": _now(),
            "created_by_person_id": created_by_person_id,
        }
        self._rehash(record, "customer_hash")
        self._write(existing, record)
        return record

    def link_customer_provider(self, workspace_id: str, customer_id: str, *, provider: str,
                               provider_contact_id: str, linked_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, linked_by_person_id, "finance.prepare")
        customer = self.load_customer(workspace_id, customer_id)
        if not str(provider_contact_id or "").strip():
            raise ValueError("finance_customer_provider_contact_required")
        customer.setdefault("provider_links", {})[provider] = {
            "contact_id": str(provider_contact_id).strip(), "linked_at": _now(),
            "linked_by_person_id": linked_by_person_id,
        }
        self._rehash(customer, "customer_hash")
        self._write(self._customer_path(workspace_id, customer_id), customer)
        return customer

    def prepare_invoice(self, workspace_id: str, *, customer_id: str, issue_date: str,
                        due_date: str | None, currency: str | None, reference: str | None,
                        lines: list[dict[str, Any]], prepared_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, prepared_by_person_id, "finance.prepare")
        customer = self.load_customer(workspace_id, customer_id)
        if customer.get("status") != "active":
            raise ValueError("active_finance_customer_required")
        issued = date.fromisoformat(str(issue_date)[:10])
        if due_date:
            due = date.fromisoformat(str(due_date)[:10])
        else:
            from datetime import timedelta
            due = issued + timedelta(days=int(customer.get("payment_terms_days") or 0))
        if due < issued:
            raise ValueError("sales_invoice_due_date_before_issue_date")
        if not lines:
            raise ValueError("sales_invoice_line_required")
        operating = self.repository.load_optional_dict(workspace_id, "business_operating_model") or {}
        offerings = {str(row.get("id")): row for row in operating.get("offerings") or []}
        clean_lines: list[dict[str, Any]] = []
        subtotal = tax_total = 0.0
        for index, raw in enumerate(lines[:100], start=1):
            offering_id = str(raw.get("offering_id") or "").strip() or None
            offering = offerings.get(offering_id or "")
            description = str(raw.get("description") or (offering or {}).get("name") or "").strip()
            quantity = _money(raw.get("quantity") or 1)
            unit_amount = _money(raw.get("unit_amount") if raw.get("unit_amount") not in (None, "")
                                 else (offering or {}).get("price"))
            tax_rate = _money(raw.get("tax_rate"))
            account_code = str(raw.get("account_code") or "200").strip()
            tax_type = str(raw.get("tax_type") or ("OUTPUT" if tax_rate else "NONE")).strip()
            if not description or quantity <= 0 or unit_amount < 0 or not account_code:
                raise ValueError(f"invalid_sales_invoice_line:{index}")
            net = round(quantity * unit_amount, 2)
            tax = round(net * tax_rate / 100, 2)
            clean_lines.append({
                "line_id": f"line-{index}", "offering_id": offering_id,
                "description": description, "quantity": quantity, "unit_amount": unit_amount,
                "net_amount": net, "tax_rate": tax_rate, "tax_amount": tax,
                "account_code": account_code, "account_name": str(raw.get("account_name") or "Sales"),
                "tax_type": tax_type,
                "offering_verification": (offering or {}).get("verification"),
            })
            subtotal = round(subtotal + net, 2); tax_total = round(tax_total + tax, 2)
        total = round(subtotal + tax_total, 2)
        if total <= 0:
            raise ValueError("positive_sales_invoice_total_required")
        identity = canonical_contract_hash({
            "workspace_id": workspace_id, "customer_id": customer_id, "issue_date": issued.isoformat(),
            "reference": str(reference or "").strip(), "lines": clean_lines,
        }).removeprefix("sha256:")[:20]
        invoice_id = f"sales-invoice-{identity}"
        path = self._invoice_path(workspace_id, invoice_id)
        if path.exists():
            return self.load_invoice(workspace_id, invoice_id)
        invoice_number = f"TESS-{issued.strftime('%Y%m%d')}-{identity[:8].upper()}"
        invoice = {
            "schema_version": "aion.finance.sales_invoice.v1", "invoice_id": invoice_id,
            "invoice_number": invoice_number, "workspace_id": workspace_id,
            "customer_id": customer_id,
            "customer": {key: customer.get(key) for key in ("name", "email", "tax_id", "billing_address")},
            "issue_date": issued.isoformat(), "due_date": due.isoformat(),
            "currency": str(currency or operating.get("currency") or "EUR").upper(),
            "reference": str(reference or "").strip() or None, "lines": clean_lines,
            "subtotal": subtotal, "tax_total": tax_total, "total": total,
            "amount_due": total, "amount_paid": 0.0,
            "status": "exact_internal_approval_required", "collection_status": "not_due",
            "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
            "approval": None, "internal_posting": None, "provider_exports": {},
            "reminders": [], "external_write_performed": False,
        }
        self._rehash(invoice, "invoice_hash")
        draft = self._bookkeeping_draft(invoice)
        invoice["bookkeeping_draft_id"] = draft["draft_id"]
        self._rehash(invoice, "invoice_hash")
        self.bookkeeping._save_draft(workspace_id, draft)
        self._write(path, invoice)
        self._project(workspace_id, invoice)
        return invoice

    def approve_invoice(self, workspace_id: str, invoice_id: str, *, approved_by_person_id: str,
                        approved_invoice_hash: str) -> dict[str, Any]:
        invoice = self.load_invoice(workspace_id, invoice_id)
        if invoice.get("status") not in {"exact_internal_approval_required", "approved_for_internal_posting"}:
            raise ValueError("sales_invoice_not_awaiting_internal_approval")
        access = self._require(workspace_id, approved_by_person_id, "finance.approve_posting")
        if approved_invoice_hash != invoice.get("invoice_hash"):
            raise ValueError("approved_sales_invoice_hash_mismatch")
        draft = self.bookkeeping.load(workspace_id, invoice["bookkeeping_draft_id"])
        draft = self.bookkeeping.approve(
            workspace_id, draft["draft_id"], approved_by_person_id=approved_by_person_id,
            approved_draft_hash=draft["draft_hash"],
        )
        invoice["approval"] = {"approved_by_person_id": approved_by_person_id, "approved_at": _now(),
                               "approved_invoice_hash": approved_invoice_hash, "authority_decision": access}
        invoice["status"] = "approved_for_internal_posting"
        self._rehash(invoice, "invoice_hash"); self._write(self._invoice_path(workspace_id, invoice_id), invoice)
        return invoice

    def post_internal(self, workspace_id: str, invoice_id: str, *, posted_by_person_id: str) -> dict[str, Any]:
        invoice = self.load_invoice(workspace_id, invoice_id)
        if invoice.get("status") in {"posted_internal", "verified_in_xero"}:
            return invoice
        if invoice.get("status") != "approved_for_internal_posting":
            raise PermissionError("exact_sales_invoice_approval_required")
        draft = self.bookkeeping.post_internal(
            workspace_id, invoice["bookkeeping_draft_id"], posted_by_person_id=posted_by_person_id,
        )
        invoice["internal_posting"] = draft.get("internal_posting")
        invoice["status"] = "posted_internal"
        self._rehash(invoice, "invoice_hash"); self._write(self._invoice_path(workspace_id, invoice_id), invoice)
        self._project(workspace_id, invoice)
        return invoice

    def prepare_reminder(self, workspace_id: str, invoice_id: str, *, tone: str,
                         prepared_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, prepared_by_person_id, "finance.prepare")
        invoice = self.load_invoice(workspace_id, invoice_id)
        if invoice.get("amount_due", 0) <= 0:
            raise ValueError("paid_invoice_does_not_need_reminder")
        customer = invoice.get("customer") or {}
        if not customer.get("email"):
            raise ValueError("customer_email_required_for_reminder")
        today = date.today(); due = date.fromisoformat(invoice["due_date"])
        days = (today - due).days
        tone = tone if tone in {"friendly", "firm", "final"} else "friendly"
        subject = f"Invoice {invoice['invoice_number']} — payment update"
        body = (
            f"Hello {customer.get('name')},\n\n"
            f"This is a {tone} reminder that invoice {invoice['invoice_number']} for "
            f"{invoice['currency']} {invoice['amount_due']:.2f} was due on {invoice['due_date']}. "
            f"Please confirm the payment status or let us know if anything needs resolving.\n\nThank you."
        )
        contract = {"to": customer["email"], "subject": subject, "body": body,
                    "invoice_id": invoice_id, "amount_due": invoice["amount_due"],
                    "days_overdue": max(0, days), "channel": "email"}
        reminder = {"reminder_id": f"reminder-{len(invoice.get('reminders') or []) + 1}",
                    "tone": tone, "payload": contract, "payload_hash": canonical_contract_hash(contract),
                    "status": "exact_message_approval_required", "prepared_at": _now(),
                    "prepared_by_person_id": prepared_by_person_id, "external_message_sent": False}
        invoice.setdefault("reminders", []).append(reminder)
        self._rehash(invoice, "invoice_hash"); self._write(self._invoice_path(workspace_id, invoice_id), invoice)
        return reminder

    def summary(self, workspace_id: str) -> dict[str, Any]:
        invoices = self.list_invoices(workspace_id)
        today = date.today()
        for row in invoices:
            if row.get("amount_due", 0) > 0 and row.get("due_date"):
                due = date.fromisoformat(row["due_date"])
                row["collection_status"] = "overdue" if due < today else "due_soon" if (due - today).days <= 7 else "not_due"
        return {
            "invoice_count": len(invoices),
            "draft_count": sum(row.get("status") not in {"verified_in_xero", "paid", "voided"} for row in invoices),
            "verified_count": sum(row.get("status") == "verified_in_xero" for row in invoices),
            "outstanding": round(sum(_money(row.get("amount_due")) for row in invoices), 2),
            "overdue": round(sum(_money(row.get("amount_due")) for row in invoices if row.get("collection_status") == "overdue"), 2),
            "reminder_drafts": sum(len(row.get("reminders") or []) for row in invoices),
            "external_messages_sent": 0,
        }

    def load_customer(self, workspace_id: str, customer_id: str) -> dict[str, Any]:
        return self._load(self._customer_path(workspace_id, customer_id), workspace_id, "customer_hash")

    def list_customers(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load_customer(workspace_id, path.stem) for path in sorted(
            self._customers_dir(workspace_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def load_invoice(self, workspace_id: str, invoice_id: str) -> dict[str, Any]:
        return self._load(self._invoice_path(workspace_id, invoice_id), workspace_id, "invoice_hash")

    def list_invoices(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load_invoice(workspace_id, path.stem) for path in sorted(
            self._invoices_dir(workspace_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def mark_verified_provider(self, workspace_id: str, invoice_id: str, *, provider: str,
                               export_summary: dict[str, Any]) -> dict[str, Any]:
        invoice = self.load_invoice(workspace_id, invoice_id)
        invoice.setdefault("provider_exports", {})[provider] = export_summary
        invoice["status"] = f"verified_in_{provider}"
        invoice["external_write_performed"] = True
        self._rehash(invoice, "invoice_hash"); self._write(self._invoice_path(workspace_id, invoice_id), invoice)
        self._project(workspace_id, invoice)
        return invoice

    def _bookkeeping_draft(self, invoice: dict[str, Any]) -> dict[str, Any]:
        lines = [{"account_code": "control.trade_receivables", "account_name": "Trade Receivables",
                  "account_type": "asset", "debit": invoice["total"], "credit": 0.0, "tax_code": None}]
        for row in invoice["lines"]:
            lines.append({"account_code": row["account_code"], "account_name": row["account_name"],
                          "account_type": "revenue", "debit": 0.0, "credit": row["net_amount"],
                          "tax_code": None})
            if row["tax_amount"]:
                lines.append({"account_code": "control.output_tax", "account_name": "Output tax",
                              "account_type": "liability", "debit": 0.0, "credit": row["tax_amount"],
                              "tax_code": row["tax_type"]})
        draft = {
            "schema_version": "aion.finance.bookkeeping_journal.v1",
            "draft_id": f"bookkeeping-{invoice['invoice_id']}", "workspace_id": invoice["workspace_id"],
            "source_document_id": invoice["invoice_id"], "source_document_hash": invoice["invoice_hash"],
            "instruction_hash": invoice["invoice_hash"], "journal_date": invoice["issue_date"],
            "currency": invoice["currency"], "description": f"Sales invoice {invoice['invoice_number']}",
            "counterparty": invoice["customer"]["name"], "document_type": "sales_invoice",
            "destination": "sales_invoice", "department_id": None, "project_id": None,
            "lines": lines, "debit_total": invoice["total"], "credit_total": invoice["total"],
            "unresolved_controls": [], "status": "exact_posting_approval_required",
            "prepared_by_person_id": invoice["prepared_by_person_id"], "prepared_at": invoice["prepared_at"],
            "posting_approval": None, "internal_posting": None, "external_write_performed": False,
        }
        draft["draft_hash"] = canonical_contract_hash(draft)
        return draft

    def _project(self, workspace_id: str, invoice: dict[str, Any]) -> None:
        summary = self.summary(workspace_id)
        latest = {key: invoice.get(key) for key in (
            "invoice_id", "invoice_number", "customer_id", "issue_date", "due_date", "currency",
            "total", "amount_due", "status", "collection_status", "invoice_hash")}
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            finance = intelligence.setdefault("departments", {}).setdefault("finance", {})
            finance["sales_invoicing"] = {"summary": summary, "latest_invoice": latest}
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["finance_sales_invoicing"] = {
                "summary": summary, "latest_invoice": latest,
                "boundary": "Customer messages and provider writes require separate exact approval.",
            }
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        decision = self.authority.access_decision(workspace_id, person_id=person_id, capability=capability)
        if not decision.get("allowed"):
            raise PermissionError(decision.get("reason") or f"{capability}_not_authorised")
        return decision

    def _root(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/sales"
        path.mkdir(parents=True, exist_ok=True); return path

    def _customers_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "customers"; path.mkdir(parents=True, exist_ok=True); return path

    def _invoices_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "invoices"; path.mkdir(parents=True, exist_ok=True); return path

    def _customer_path(self, workspace_id: str, customer_id: str) -> Path:
        return self._customers_dir(workspace_id) / f"{_safe(customer_id)}.json"

    def _invoice_path(self, workspace_id: str, invoice_id: str) -> Path:
        return self._invoices_dir(workspace_id) / f"{_safe(invoice_id)}.json"

    @staticmethod
    def _rehash(record: dict[str, Any], field: str) -> None:
        record.pop(field, None); record[field] = canonical_contract_hash(record)

    @staticmethod
    def _write(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _load(path: Path, workspace_id: str, hash_field: str) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path.stem)
        record = json.loads(path.read_text(encoding="utf-8"))
        expected = record.get(hash_field); payload = dict(record); payload.pop(hash_field, None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError(f"finance_sales_{hash_field}_mismatch")
        if record.get("workspace_id") != workspace_id:
            raise PermissionError("finance_sales_workspace_isolation_violation")
        return record

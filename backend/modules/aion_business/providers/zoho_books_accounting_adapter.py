"""Read-only Zoho Books adapter for the governed accountant harness."""

from __future__ import annotations

from typing import Any

import httpx

from .accounting_provider_contract import AccountingProviderCapabilities, empty_collections, number, source_ref


class ZohoBooksAccountingAdapter:
    provider_id = "zoho_books"
    BASE_URL = "https://www.zohoapis.com/books/v3"

    @staticmethod
    def _connection(company_id: str) -> tuple[str, str]:
        organization_id, separator, api_domain = str(company_id or "").partition("|")
        if not organization_id:
            raise ValueError("zoho_books_organization_required")
        domain = api_domain.rstrip("/") if separator and api_domain else "https://www.zohoapis.com"
        if not domain.startswith("https://"):
            raise ValueError("zoho_books_api_domain_must_be_https")
        return organization_id, f"{domain}/books/v3"

    def capabilities(self) -> AccountingProviderCapabilities:
        return AccountingProviderCapabilities(
            provider_id=self.provider_id, label="Zoho Books", oauth2=True,
            read_collections=("chartofaccounts", "invoices", "bills", "customerpayments", "vendorpayments", "banktransactions", "journals"),
            draft_writes=("contact", "invoice", "bill", "journal"),
            approved_writes=("contact", "invoice", "bill", "customer_payment", "vendor_payment", "bank_transaction", "journal"),
            bank_reconciliation_api=False,
        )

    async def read_snapshot(self, *, access_token: str, company_id: str,
                            sandbox: bool = False) -> dict[str, Any]:
        if not access_token or not company_id:
            raise ValueError("zoho_books_access_token_and_organization_required")
        organization_id, base_url = self._connection(company_id)
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}", "Accept": "application/json"}
        endpoints = {
            "chartofaccounts": "chartofaccounts", "invoices": "invoices", "bills": "bills",
            "customerpayments": "customerpayments", "vendorpayments": "vendorpayments",
            "banktransactions": "banktransactions", "journals": "journals",
        }
        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=45) as client:
            for key, path in endpoints.items():
                response = await client.get(f"{base_url}/{path}", headers=headers,
                                            params={"organization_id": organization_id, "per_page": 200})
                response.raise_for_status()
                result[key] = list(response.json().get(key) or [])
        return result

    def normalize_snapshot(self, raw: dict[str, Any], *, sync_id: str,
                           company_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_collections()
        for item in raw.get("chartofaccounts") or []:
            records["accounts"].append({
                "account_id": str(item.get("account_id") or ""), "code": item.get("account_code"),
                "name": item.get("account_name"), "type": item.get("account_type"), "subtype": item.get("account_sub_type"),
                "status": "active" if item.get("is_active", True) else "archived", "currency": item.get("currency_code"),
                "bank_account_type": item.get("account_type") if item.get("account_type") in ("bank", "credit_card") else None,
                "source_ref": source_ref(self.provider_id, sync_id, "chartofaccounts", item.get("account_id")),
            })
        for collection, invoice_type in (("invoices", "sales_invoice"), ("bills", "supplier_bill")):
            for item in raw.get(collection) or []:
                total = number(item.get("total")); due = number(item.get("balance"))
                contact_id = item.get("customer_id") or item.get("vendor_id")
                display_name = item.get("customer_name") or item.get("vendor_name")
                status = str(item.get("status") or "recorded").lower()
                records["invoices"].append({
                    "invoice_id": str(item.get("invoice_id") or item.get("bill_id") or ""),
                    "invoice_number": item.get("invoice_number") or item.get("bill_number"),
                    "invoice_type": invoice_type, "status": status,
                    "contact": {"contact_id": contact_id, "display_name": display_name},
                    "date": item.get("date"), "due_date": item.get("due_date"), "currency": item.get("currency_code"),
                    "total": total, "amount_paid": round(max(0, total - due), 4), "amount_due": due,
                    "reference": item.get("reference_number"), "is_overdue": status == "overdue",
                    "line_items": self._lines(item.get("line_items")),
                    "source_ref": source_ref(self.provider_id, sync_id, collection, item.get("invoice_id") or item.get("bill_id")),
                })
        for collection in ("customerpayments", "vendorpayments"):
            for item in raw.get(collection) or []:
                records["payments"].append({
                    "payment_id": str(item.get("payment_id") or ""), "date": item.get("date"),
                    "amount": number(item.get("amount")), "status": item.get("status") or "recorded",
                    "reference": item.get("reference_number"),
                    "invoice_id": self._linked_id(item, "invoice_id" if collection == "customerpayments" else "bill_id"),
                    "invoice_number": self._linked_id(item, "invoice_number" if collection == "customerpayments" else "bill_number"),
                    "account_id": item.get("account_id") or item.get("bank_account_id"),
                    "source_ref": source_ref(self.provider_id, sync_id, collection, item.get("payment_id")),
                })
        for item in raw.get("banktransactions") or []:
            txn_type = str(item.get("transaction_type") or "bank_transaction").lower()
            amount = number(item.get("amount") if item.get("amount") is not None else item.get("total"))
            if txn_type in ("withdrawal", "expense", "vendor_payment"):
                amount = -abs(amount)
            records["bank_transactions"].append({
                "bank_transaction_id": str(item.get("transaction_id") or item.get("bank_transaction_id") or ""),
                "transaction_type": txn_type, "status": item.get("status") or "recorded",
                "contact": {"contact_id": item.get("customer_id") or item.get("vendor_id"),
                            "display_name": item.get("customer_name") or item.get("vendor_name") or item.get("payee")},
                "date": item.get("date"), "reference": item.get("reference_number") or item.get("description"),
                "total": amount, "bank_account_id": item.get("to_account_id") or item.get("account_id"),
                "is_reconciled": str(item.get("reconcile_status") or item.get("status") or "").lower() in ("reconciled", "matched", "categorized"),
                "source_ref": source_ref(self.provider_id, sync_id, "banktransactions", item.get("transaction_id") or item.get("bank_transaction_id")),
            })
        for item in raw.get("journals") or []:
            lines = item.get("line_items") or item.get("journal_entries") or []
            records["manual_journals"].append({
                "manual_journal_id": str(item.get("journal_id") or ""), "date": item.get("journal_date") or item.get("date"),
                "status": item.get("status") or "posted", "narration": item.get("notes") or item.get("description"),
                "line_count": len(lines), "net_amount": round(sum(number(row.get("debit")) - number(row.get("credit")) for row in lines), 4),
                "source_ref": source_ref(self.provider_id, sync_id, "journals", item.get("journal_id")),
            })
        return records

    @staticmethod
    def _linked_id(item: dict[str, Any], key: str) -> Any:
        values = item.get("invoices") or item.get("bills") or []
        return values[0].get(key) if values else item.get(key)

    @staticmethod
    def _lines(lines: Any) -> list[dict[str, Any]]:
        return [{
            "description": row.get("description") or row.get("name"), "quantity": number(row.get("quantity")),
            "unit_amount": number(row.get("rate")), "line_amount": number(row.get("item_total") or row.get("amount")),
            "account_code": row.get("account_id"), "tax_type": row.get("tax_name") or row.get("tax_id"),
            "tracking": list(row.get("tags") or []),
        } for row in lines or []]

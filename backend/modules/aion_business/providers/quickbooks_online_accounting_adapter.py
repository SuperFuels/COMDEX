"""Read-only QuickBooks Online adapter for the accountant harness."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .accounting_provider_contract import (
    AccountingProviderCapabilities,
    empty_collections,
    number,
    source_ref,
)


class QuickBooksOnlineAccountingAdapter:
    provider_id = "quickbooks_online"
    PRODUCTION_BASE = "https://quickbooks.api.intuit.com"
    SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com"

    def capabilities(self) -> AccountingProviderCapabilities:
        return AccountingProviderCapabilities(
            provider_id=self.provider_id,
            label="QuickBooks Online",
            oauth2=True,
            read_collections=("accounts", "invoices", "bills", "payments", "purchases", "journal_entries"),
            draft_writes=("customer", "vendor", "invoice", "bill", "journal_entry"),
            approved_writes=("customer", "vendor", "invoice", "bill", "payment", "journal_entry", "attachment"),
            bank_reconciliation_api=False,
        )

    async def read_snapshot(self, *, access_token: str, company_id: str,
                            sandbox: bool = False) -> dict[str, Any]:
        if not access_token or not company_id:
            raise ValueError("quickbooks_access_token_and_realm_required")
        base = self.SANDBOX_BASE if sandbox else self.PRODUCTION_BASE
        url = f"{base}/v3/company/{quote(company_id, safe='')}/query"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        entities = {
            "accounts": "Account", "invoices": "Invoice", "bills": "Bill",
            "payments": "Payment", "purchases": "Purchase", "journal_entries": "JournalEntry",
        }
        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=45) as client:
            for key, entity in entities.items():
                response = await client.get(url, headers=headers, params={"query": f"select * from {entity} maxresults 1000", "minorversion": "75"})
                response.raise_for_status()
                payload = response.json()
                result[key] = list((payload.get("QueryResponse") or {}).get(entity) or [])
        return result

    def normalize_snapshot(self, raw: dict[str, Any], *, sync_id: str,
                           company_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_collections()
        for item in raw.get("accounts") or []:
            records["accounts"].append({
                "account_id": str(item.get("Id") or ""), "code": item.get("AcctNum"),
                "name": item.get("Name"), "type": item.get("AccountType"),
                "subtype": item.get("AccountSubType"), "status": "active" if item.get("Active", True) else "archived",
                "currency": (item.get("CurrencyRef") or {}).get("value"),
                "bank_account_type": item.get("AccountSubType") if item.get("AccountType") == "Bank" else None,
                "source_ref": source_ref(self.provider_id, sync_id, "accounts", item.get("Id")),
            })
        for collection, invoice_type in (("invoices", "sales_invoice"), ("bills", "supplier_bill")):
            for item in raw.get(collection) or []:
                contact_ref = item.get("CustomerRef") or item.get("VendorRef") or {}
                total, balance = number(item.get("TotalAmt")), number(item.get("Balance"))
                records["invoices"].append({
                    "invoice_id": str(item.get("Id") or ""), "invoice_number": item.get("DocNumber"),
                    "invoice_type": invoice_type, "status": "paid" if total and balance == 0 else "open",
                    "contact": {"contact_id": contact_ref.get("value"), "display_name": contact_ref.get("name")},
                    "date": item.get("TxnDate"), "due_date": item.get("DueDate"), "currency": (item.get("CurrencyRef") or {}).get("value"),
                    "total": total, "amount_paid": round(max(0, total - balance), 4), "amount_due": balance,
                    "reference": item.get("PrivateNote") or item.get("CustomerMemo", {}).get("value"),
                    "is_overdue": False, "line_items": self._lines(item.get("Line")),
                    "source_ref": source_ref(self.provider_id, sync_id, collection, item.get("Id")),
                })
        for item in raw.get("payments") or []:
            linked = next((row for line in item.get("Line") or [] for row in line.get("LinkedTxn") or [] if row.get("TxnType") == "Invoice"), {})
            records["payments"].append({
                "payment_id": str(item.get("Id") or ""), "date": item.get("TxnDate"),
                "amount": number(item.get("TotalAmt")), "status": "recorded", "reference": item.get("PaymentRefNum"),
                "invoice_id": linked.get("TxnId"), "invoice_number": None,
                "account_id": (item.get("DepositToAccountRef") or {}).get("value"),
                "source_ref": source_ref(self.provider_id, sync_id, "payments", item.get("Id")),
            })
        for item in raw.get("purchases") or []:
            entity = item.get("EntityRef") or {}
            records["bank_transactions"].append({
                "bank_transaction_id": str(item.get("Id") or ""), "transaction_type": "spend",
                "status": "recorded", "contact": {"contact_id": entity.get("value"), "display_name": entity.get("name")},
                "date": item.get("TxnDate"), "reference": item.get("DocNumber") or item.get("PrivateNote"),
                "total": -abs(number(item.get("TotalAmt"))), "bank_account_id": (item.get("AccountRef") or {}).get("value"),
                "is_reconciled": False, "source_ref": source_ref(self.provider_id, sync_id, "purchases", item.get("Id")),
            })
        for item in raw.get("journal_entries") or []:
            records["manual_journals"].append({
                "manual_journal_id": str(item.get("Id") or ""), "date": item.get("TxnDate"),
                "status": "posted", "narration": item.get("PrivateNote"),
                "line_count": len(item.get("Line") or []),
                "net_amount": round(sum(row.get("debit", 0) - row.get("credit", 0) for row in self._journal_lines(item.get("Line"))), 4),
                "source_ref": source_ref(self.provider_id, sync_id, "journal_entries", item.get("Id")),
            })
        return records

    @staticmethod
    def _lines(lines: Any) -> list[dict[str, Any]]:
        result = []
        for line in lines or []:
            detail = line.get("SalesItemLineDetail") or line.get("ItemBasedExpenseLineDetail") or line.get("AccountBasedExpenseLineDetail") or {}
            result.append({"description": line.get("Description"), "quantity": number(detail.get("Qty")),
                           "unit_amount": number(detail.get("UnitPrice")), "line_amount": number(line.get("Amount")),
                           "account_code": (detail.get("AccountRef") or {}).get("value"),
                           "tax_type": (detail.get("TaxCodeRef") or {}).get("value"), "tracking": []})
        return result

    @staticmethod
    def _journal_lines(lines: Any) -> list[dict[str, Any]]:
        result = []
        for line in lines or []:
            detail = line.get("JournalEntryLineDetail") or {}
            amount = number(line.get("Amount")); posting = str(detail.get("PostingType") or "").lower()
            result.append({"account_code": (detail.get("AccountRef") or {}).get("value"),
                           "description": line.get("Description"), "debit": amount if posting == "debit" else 0.0,
                           "credit": amount if posting == "credit" else 0.0})
        return result

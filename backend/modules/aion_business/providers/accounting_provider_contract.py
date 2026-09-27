"""Canonical contract for governed small-business accounting providers.

Provider adapters are intentionally narrow.  They may read provider facts and
translate them into Tessaris' canonical ledger, but they do not decide whether
an item is correctly accounted for and may not post an unapproved mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


CANONICAL_COLLECTIONS = (
    "accounts",
    "invoices",
    "bank_transactions",
    "payments",
    "manual_journals",
    "tracking_categories",
    "projects",
)


@dataclass(frozen=True)
class AccountingProviderCapabilities:
    provider_id: str
    label: str
    oauth2: bool
    read_collections: tuple[str, ...]
    draft_writes: tuple[str, ...]
    approved_writes: tuple[str, ...]
    bank_reconciliation_api: bool
    readback_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["read_collections"] = list(self.read_collections)
        value["draft_writes"] = list(self.draft_writes)
        value["approved_writes"] = list(self.approved_writes)
        return value


class AccountingProviderAdapter(Protocol):
    """Boundary implemented by Xero, QuickBooks, Sage and future adapters."""

    provider_id: str

    def capabilities(self) -> AccountingProviderCapabilities: ...

    async def read_snapshot(
        self, *, access_token: str, company_id: str, sandbox: bool = False
    ) -> dict[str, Any]: ...

    def normalize_snapshot(
        self, raw: dict[str, Any], *, sync_id: str, company_id: str
    ) -> dict[str, list[dict[str, Any]]]: ...


def empty_collections() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in CANONICAL_COLLECTIONS}


def number(value: Any) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def source_ref(provider: str, sync_id: str, collection: str, provider_id: Any) -> dict[str, Any]:
    return {
        "provider": provider,
        "sync_id": sync_id,
        "collection": collection,
        "provider_id": None if provider_id is None else str(provider_id),
        "verification_status": "provider_sourced",
    }

# backend/modules/photon_pay/photon_receipt.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Literal
import time
import uuid


ReceiptKind = Literal["PAYMENT", "REFUND"]


@dataclass
class PhotonPayReceipt:
    """
    Dev-only Photon Pay receipt model.

    NOT final on-chain or production API – just enough to:
      - track POS / P2P payments in memory,
      - let wallet/admin UIs show history,
      - support simple "refund" entries.
    """

    receipt_id: str
    invoice_id: str

    from_account: str
    to_account: str

    amount_pho: str
    memo: Optional[str]

    channel: str  # "mesh", "net", "radio", etc. (dev-only string)

    kind: ReceiptKind  # "PAYMENT" or "REFUND"
    refunded_receipt_id: Optional[str]  # set iff this is a REFUND

    paid_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ───────────────────────────────────────────────
# Dev-only in-memory store
# ───────────────────────────────────────────────

_DEV_RECEIPTS: List[PhotonPayReceipt] = []
_DEV_RECEIPTS_BY_ID: Dict[str, PhotonPayReceipt] = {}


def dev_add_receipt(rcpt: PhotonPayReceipt) -> None:
    """Append a receipt to the in-memory dev store."""
    _DEV_RECEIPTS.append(rcpt)
    _DEV_RECEIPTS_BY_ID[rcpt.receipt_id] = rcpt


def dev_all_receipts() -> List[PhotonPayReceipt]:
    """Return a shallow copy of all dev receipts (oldest → newest)."""
    return list(_DEV_RECEIPTS)


def dev_recent_receipts(limit: int = 50) -> List[PhotonPayReceipt]:
    """
    Return at most `limit` most recent receipts (newest → oldest).
    """
    if limit <= 0:
        return []
    tail = _DEV_RECEIPTS[-limit:]
    return list(reversed(tail))


def dev_get_receipt(receipt_id: str) -> Optional[PhotonPayReceipt]:
    return _DEV_RECEIPTS_BY_ID.get(receipt_id)


def dev_has_refund_for(receipt_id: str) -> bool:
    """
    True if any REFUND receipt points at `receipt_id`.
    """
    for r in _DEV_RECEIPTS:
        if r.kind == "REFUND" and r.refunded_receipt_id == receipt_id:
            return True
    return False


# ───────────────────────────────────────────────
# Constructors
# ───────────────────────────────────────────────

def new_dev_payment_receipt_from_invoice(
    *,
    invoice: Dict[str, Any],
    from_account: str,
    channel: str = "mesh",
) -> PhotonPayReceipt:
    """
    Build a PAYMENT receipt from a PhotonInvoice dict.
    """
    invoice_id = str(invoice.get("invoice_id") or "inv_unknown")
    to_account = str(invoice.get("seller_account") or invoice.get("to_account") or "")
    amount_pho = str(invoice.get("amount_pho") or invoice.get("amount") or "0")
    memo = invoice.get("memo")

    rcpt = PhotonPayReceipt(
        receipt_id=f"rcpt_{uuid.uuid4().hex}",
        invoice_id=invoice_id,
        from_account=from_account,
        to_account=to_account,
        amount_pho=amount_pho,
        memo=memo,
        channel=channel,
        kind="PAYMENT",
        refunded_receipt_id=None,
        paid_at_ms=int(time.time() * 1000),
    )
    return rcpt


def new_dev_refund_receipt(
    *,
    original: PhotonPayReceipt,
    from_account: str,
    channel: str = "mesh",
) -> PhotonPayReceipt:
    """
    Build a REFUND receipt that conceptually reverses `original`.

    For dev:
      - amount_pho is same as original
      - from_account is the refunder (usually merchant)
      - to_account is the original payer
    """
    rcpt = PhotonPayReceipt(
        receipt_id=f"rcpt_{uuid.uuid4().hex}",
        invoice_id=original.invoice_id,
        from_account=from_account,
        to_account=original.from_account,
        amount_pho=original.amount_pho,
        memo=f"Refund for {original.receipt_id}",
        channel=channel,
        kind="REFUND",
        refunded_receipt_id=original.receipt_id,
        paid_at_ms=int(time.time() * 1000),
    )
    return rcpt
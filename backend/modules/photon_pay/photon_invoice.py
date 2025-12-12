# backend/modules/photon_pay/photon_invoice.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Optional, Dict, Any
import time
import uuid


@dataclass
class PhotonInvoice:
    """
    Minimal Photon Pay invoice model used for POS + wallet flows.

    This is the runtime version of the LaTeX spec:
      - seller_account is the PHO account to be paid
      - amount_pho is a decimal string (e.g. "5.0")
      - fiat_* fields are optional and can be used for local pricing
      - expiry_ms can be None for "no explicit expiry"
    """
    invoice_id: str
    seller_account: str
    seller_wave_addr: Optional[str]
    amount_pho: str
    fiat_symbol: Optional[str]
    fiat_amount: Optional[str]
    memo: Optional[str]
    created_at_ms: int
    expiry_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serialisable view for REST / GlyphCode payloads."""
        return asdict(self)


def _now_ms() -> int:
    return int(time.time() * 1000)


def new_photon_invoice(
    *,
    seller_account: str,
    amount_pho: str,
    seller_wave_addr: Optional[str] = None,
    fiat_symbol: Optional[str] = None,
    fiat_amount: Optional[str] = None,
    memo: Optional[str] = None,
    ttl_ms: Optional[int] = 5 * 60 * 1000,  # default: 5 minutes POS invoice
) -> PhotonInvoice:
    """
    Convenience helper to create a new PhotonInvoice with a fresh id
    and timestamps.

    - Validates that amount_pho > 0
    - Encodes decimals as strings (consistent with mesh wallet state)
    """
    try:
        amt = Decimal(amount_pho)
    except Exception as e:
        raise ValueError(f"invalid amount_pho: {amount_pho}") from e

    if amt <= 0:
        raise ValueError("amount_pho must be positive")

    created = _now_ms()
    expiry = created + ttl_ms if ttl_ms is not None else None

    inv = PhotonInvoice(
        invoice_id=f"inv_{uuid.uuid4().hex}",
        seller_account=seller_account,
        seller_wave_addr=seller_wave_addr,
        amount_pho=str(amt),
        fiat_symbol=fiat_symbol,
        fiat_amount=str(Decimal(fiat_amount)) if fiat_amount is not None else None,
        memo=memo,
        created_at_ms=created,
        expiry_ms=expiry,
    )
    return inv


def glyph_payload_for_invoice(invoice: PhotonInvoice) -> Dict[str, Any]:
    """
    Build the minimal payload we would encode into a QR / GlyphCode.

    This mirrors PhotonPayPayload in the LaTeX spec:
      { version, kind, invoice }
    """
    return {
        "version": 1,
        "kind": "INVOICE_POS",
        "invoice": invoice.to_dict(),
    }
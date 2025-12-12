# backend/modules/photon_pay/photon_pay_routes.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List
import time
import uuid

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from backend.modules.photon_pay.photon_invoice import (
    new_photon_invoice,
    glyph_payload_for_invoice,
)

router = APIRouter(
    prefix="/photon_pay",
    tags=["photon-pay-dev"],
)

# -------------------------------------------------------------------
# Small time helper (shared by receipts + recurring)
# -------------------------------------------------------------------


def _now_ms() -> int:
    return int(time.time() * 1000)


# ───────────────────────────────────────────────
# Dev invoice endpoint (legacy demo QR)
# ───────────────────────────────────────────────


@router.get("/dev/demo_invoice")
async def photon_pay_demo_invoice(
    seller_account: str = Query("pho1-demo-merchant"),
    amount_pho: str = Query("5.0"),
    seller_wave_addr: Optional[str] = Query(None),
    memo: Optional[str] = Query("Coffee"),
    ttl_ms: Optional[int] = Query(5 * 60 * 1000, description="Invoice TTL in ms"),
):
    """
    Dev-only endpoint: returns a demo Photon Pay invoice payload suitable
    for encoding into a QR / GlyphCode.
    """
    try:
        amt = Decimal(amount_pho)
        if amt <= 0:
            raise ValueError("amount_pho must be positive")
    except Exception as e:
        raise ValueError(f"invalid amount_pho: {amount_pho}") from e

    inv = new_photon_invoice(
        seller_account=seller_account,
        amount_pho=str(amt),
        seller_wave_addr=seller_wave_addr,
        fiat_symbol=None,
        fiat_amount=None,
        memo=memo,
        ttl_ms=ttl_ms,
    )
    payload = glyph_payload_for_invoice(inv)
    return payload


# ───────────────────────────────────────────────
# Dev: make POS invoice (used by AdminDashboard)
# ───────────────────────────────────────────────


class DevMakeInvoiceRequest(BaseModel):
    seller_account: str
    amount_pho: str          # decimal string, e.g. "5.0"
    memo: Optional[str] = None
    channel: Optional[str] = "mesh"  # reserved for future use


@router.post("/dev/make_invoice")
async def photon_pay_dev_make_invoice(req: DevMakeInvoiceRequest) -> Dict[str, Any]:
    """
    Dev-only: generate a Photon Pay POS invoice.

    Returns an INVOICE_POS payload that AdminDashboard renders in the
    POS keypad card.
    """
    try:
        amt = Decimal(req.amount_pho)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    if amt <= 0:
        raise HTTPException(status_code=400, detail="amount_pho must be positive")

    now_ms = _now_ms()
    invoice_id = f"inv_{uuid.uuid4().hex}"

    invoice = {
        "invoice_id": invoice_id,
        "seller_account": req.seller_account,
        "seller_wave_addr": None,
        "amount_pho": str(amt),
        "fiat_symbol": None,
        "fiat_amount": None,
        "memo": req.memo or "",
        "created_at_ms": now_ms,
        # 15-minute expiry in this dev model
        "expiry_ms": now_ms + 15 * 60 * 1000,
    }

    return {
        "version": 1,
        "kind": "INVOICE_POS",
        "invoice": invoice,
    }


# ───────────────────────────────────────────────
# Dev receipts model (in-memory)
# ───────────────────────────────────────────────


@dataclass
class DevPhotonReceipt:
    receipt_id: str
    from_account: str
    to_account: str
    amount_pho: str
    memo: Optional[str]
    channel: str  # "mesh", "net", etc.
    invoice_id: Optional[str]
    created_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEV_PHOTON_RECEIPTS: List[DevPhotonReceipt] = []


class DevReceiptCreate(BaseModel):
    from_account: str
    channel: str  # "mesh" | "net" | etc
    invoice: Optional[Dict[str, Any]] = None

    # optional overrides
    to_account: Optional[str] = None
    amount_pho: Optional[str] = None
    memo: Optional[str] = None


def list_dev_receipts_for_account(account: str) -> List[Dict[str, Any]]:
    """
    Helper used by wallet routes: filter receipts where this account
    was either payer or payee.
    """
    out: List[Dict[str, Any]] = []
    for r in _DEV_PHOTON_RECEIPTS:
        if r.from_account == account or r.to_account == account:
            out.append(r.to_dict())
    return out


@router.post("/dev/receipts")
async def photon_pay_dev_log_receipt(body: DevReceiptCreate) -> Dict[str, Any]:
    """
    Dev-only: log a Photon Pay receipt.

    PhotonPayBuyerPanel sends:

      {
        "from_account": "pho1-demo-offline",
        "channel": "mesh",
        "invoice": { ...PhotonInvoice... }
      }
    """
    inv = body.invoice or {}

    to_account = body.to_account or inv.get("seller_account")
    amount_pho = body.amount_pho or inv.get("amount_pho")
    memo = body.memo if body.memo is not None else inv.get("memo")

    if not to_account:
        raise HTTPException(
            status_code=400, detail="missing to_account / seller_account"
        )
    if not amount_pho:
        raise HTTPException(status_code=400, detail="missing amount_pho")

    try:
        amt = Decimal(str(amount_pho))
        if amt <= 0:
            raise ValueError("amount_pho must be positive")
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    receipt = DevPhotonReceipt(
        receipt_id=f"rcpt_{uuid.uuid4().hex}",
        from_account=body.from_account,
        to_account=to_account,
        amount_pho=str(amt),
        memo=memo,
        channel=body.channel,
        invoice_id=inv.get("invoice_id"),
        created_at_ms=_now_ms(),
    )
    _DEV_PHOTON_RECEIPTS.append(receipt)

    return {"ok": True, "receipt": receipt.to_dict()}


@router.get("/dev/receipts")
async def photon_pay_dev_list_receipts(
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """
    Dev-only: list recent Photon Pay receipts (newest first).
    """
    recent = _DEV_PHOTON_RECEIPTS[-limit:][::-1]
    return {"receipts": [r.to_dict() for r in recent]}


# ───────────────────────────────────────────────
# Dev recurring payment instructions (in-memory)
# ───────────────────────────────────────────────


@dataclass
class DevRecurringInstruction:
    """
    Dev-only recurring payment config.

    This is a config-only object; no scheduler is executing it yet.
    """

    instr_id: str
    from_account: str
    to_account: str
    amount_pho: str
    memo: Optional[str]
    frequency: str  # e.g. "DAILY", "WEEKLY", "MONTHLY"
    next_due_ms: int
    created_at_ms: int
    last_run_at_ms: Optional[int]
    total_runs: int
    max_runs: Optional[int]
    active: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEV_RECURRING_INSTR: List[DevRecurringInstruction] = []


def _ensure_demo_recurring() -> None:
    """
    Seed a couple of demo recurring instructions once for dev UX.
    """
    global _DEV_RECURRING_INSTR
    if _DEV_RECURRING_INSTR:
        return

    now = _now_ms()
    _DEV_RECURRING_INSTR = [
        DevRecurringInstruction(
            instr_id=f"rec_{uuid.uuid4().hex}",
            from_account="pho1-demo-offline",
            to_account="pho1-demo-merchant",
            amount_pho="25.0",
            memo="Weekly café membership",
            frequency="WEEKLY",
            next_due_ms=now + 7 * 24 * 60 * 60 * 1000,
            created_at_ms=now,
            last_run_at_ms=None,
            total_runs=0,
            max_runs=None,
            active=True,
        ),
        DevRecurringInstruction(
            instr_id=f"rec_{uuid.uuid4().hex}",
            from_account="pho1-demo-offline",
            to_account="pho1receiver",
            amount_pho="100.0",
            memo="Monthly support",
            frequency="MONTHLY",
            next_due_ms=now + 30 * 24 * 60 * 60 * 1000,
            created_at_ms=now,
            last_run_at_ms=None,
            total_runs=0,
            max_runs=None,
            active=True,
        ),
    ]


class DevRecurringCreate(BaseModel):
    from_account: str
    to_account: str
    amount_pho: str
    memo: Optional[str] = None
    frequency: str  # "DAILY" | "WEEKLY" | "MONTHLY"
    max_runs: Optional[int] = None


@router.get("/dev/recurring")
async def photon_pay_dev_list_recurring(
    from_account: Optional[str] = Query(
        None, description="If set, filter instructions by from_account"
    )
) -> Dict[str, Any]:
    """
    Dev-only listing of all recurring payment instructions.
    """
    _ensure_demo_recurring()

    if from_account:
        filtered = [
            instr
            for instr in _DEV_RECURRING_INSTR
            if instr.from_account == from_account
        ]
    else:
        filtered = list(_DEV_RECURRING_INSTR)

    return {"recurring": [i.to_dict() for i in filtered]}


@router.post("/dev/recurring")
async def photon_pay_dev_create_recurring(body: DevRecurringCreate) -> Dict[str, Any]:
    """
    Dev-only creation of a recurring instruction.
    """
    try:
        amt = Decimal(body.amount_pho)
        if amt <= 0:
            raise ValueError("amount_pho must be positive")
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    _ensure_demo_recurring()

    now = _now_ms()
    instr = DevRecurringInstruction(
        instr_id=f"rec_{uuid.uuid4().hex}",
        from_account=body.from_account,
        to_account=body.to_account,
        amount_pho=str(amt),
        memo=body.memo,
        frequency=body.frequency.upper(),
        next_due_ms=now + 24 * 60 * 60 * 1000,
        created_at_ms=now,
        last_run_at_ms=None,
        total_runs=0,
        max_runs=body.max_runs,
        active=True,
    )
    _DEV_RECURRING_INSTR.append(instr)
    return instr.to_dict()


@router.post("/dev/recurring/{instr_id}/cancel")
async def photon_pay_dev_cancel_recurring(instr_id: str) -> Dict[str, Any]:
    """
    Dev-only cancel of a recurring instruction.
    """
    _ensure_demo_recurring()
    for instr in _DEV_RECURRING_INSTR:
        if instr.instr_id == instr_id:
            if not instr.active:
                return {"ok": True, "instruction": instr.to_dict()}
            instr.active = False
            return {"ok": True, "instruction": instr.to_dict()}

    raise HTTPException(status_code=404, detail="recurring instruction not found")
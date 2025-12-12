# backend/modules/escrow/escrow_routes.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional
import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(
    prefix="/escrow",
    tags=["escrow-dev"],
)


# -------------------------------------------------------------------
# Small time helper
# -------------------------------------------------------------------


def _now_ms() -> int:
    return int(time.time() * 1000)


# -------------------------------------------------------------------
# Dev Escrow model (in-memory)
# -------------------------------------------------------------------


@dataclass
class EscrowAgreement:
    escrow_id: str
    from_account: str
    to_account: str
    amount_pho: str
    kind: str               # "SERVICE" | "LIQUIDITY" | etc (dev free-form)
    label: str
    created_at_ms: int
    unlock_at_ms: Optional[int]
    released_at_ms: Optional[int]
    refunded_at_ms: Optional[int]
    status: str             # "OPEN" | "RELEASED" | "REFUNDED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEV_ESCROWS: List[EscrowAgreement] = []


# -------------------------------------------------------------------
# Request models
# -------------------------------------------------------------------


class DevEscrowCreate(BaseModel):
    from_account: str
    to_account: str
    amount_pho: str
    kind: str = "SERVICE"          # or "LIQUIDITY" later
    label: str
    unlock_at_ms: Optional[int] = None  # optional time lock


class DevEscrowAction(BaseModel):
    escrow_id: str


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _find_escrow(escrow_id: str) -> EscrowAgreement:
    for e in _DEV_ESCROWS:
        if e.escrow_id == escrow_id:
            return e
    raise HTTPException(status_code=404, detail="escrow not found")


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@router.post("/dev/create")
async def create_dev_escrow(body: DevEscrowCreate) -> Dict[str, Any]:
    """
    Dev-only: create an escrow agreement and logically 'lock' PHO.
    For now this only updates the in-memory model; real PHO transfers
    will be wired in later via GMA/wallet.
    """
    try:
        amt = Decimal(body.amount_pho)
        if amt <= 0:
            raise ValueError("amount_pho must be positive")
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    now = _now_ms()
    escrow = EscrowAgreement(
        escrow_id=f"escrow_{uuid.uuid4().hex}",
        from_account=body.from_account,
        to_account=body.to_account,
        amount_pho=str(amt),
        kind=body.kind,
        label=body.label,
        created_at_ms=now,
        unlock_at_ms=body.unlock_at_ms,
        released_at_ms=None,
        refunded_at_ms=None,
        status="OPEN",
    )
    _DEV_ESCROWS.append(escrow)

    # NOTE: A real implementation would:
    #   - debit from_account's PHO,
    #   - credit an internal escrow bucket.
    # For this dev slice we just track the agreement.

    return {"ok": True, "escrow": escrow.to_dict()}


@router.get("/dev/list")
async def list_dev_escrows(
    account: Optional[str] = Query(
        None,
        description="If set, returns escrows where this account is from_account or to_account",
    )
) -> Dict[str, Any]:
    """
    Dev-only: list escrow agreements.
    """
    if account:
        filtered = [
            e for e in _DEV_ESCROWS
            if e.from_account == account or e.to_account == account
        ]
    else:
        filtered = list(_DEV_ESCROWS)

    # Newest first (dev convenience)
    filtered.sort(key=lambda e: e.created_at_ms, reverse=True)

    return {"escrows": [e.to_dict() for e in filtered]}


@router.post("/dev/release")
async def release_dev_escrow(body: DevEscrowAction) -> Dict[str, Any]:
    """
    Dev-only: release an escrow to the beneficiary (to_account).
    This marks the escrow as RELEASED; moving PHO will be hooked up later.
    """
    now = _now_ms()
    escrow = _find_escrow(body.escrow_id)

    if escrow.status != "OPEN":
        raise HTTPException(status_code=400, detail="escrow is not open")

    if escrow.unlock_at_ms is not None and now < escrow.unlock_at_ms:
        raise HTTPException(status_code=400, detail="escrow is still time-locked")

    escrow.status = "RELEASED"
    escrow.released_at_ms = now

    # Real system: move amount_pho from escrow bucket → to_account.

    return {"ok": True, "escrow": escrow.to_dict()}


@router.post("/dev/refund")
async def refund_dev_escrow(body: DevEscrowAction) -> Dict[str, Any]:
    """
    Dev-only: refund an escrow back to the originator (from_account).
    Marks the escrow as REFUNDED; no real PHO moves yet.
    """
    now = _now_ms()
    escrow = _find_escrow(body.escrow_id)

    if escrow.status != "OPEN":
        raise HTTPException(status_code=400, detail="escrow is not open")

    escrow.status = "REFUNDED"
    escrow.refunded_at_ms = now

    # Real system: move amount_pho from escrow bucket → from_account.

    return {"ok": True, "escrow": escrow.to_dict()}
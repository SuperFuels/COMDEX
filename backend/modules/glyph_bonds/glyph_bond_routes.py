# backend/modules/glyph_bonds/glyph_bond_routes.py

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(
    prefix="/glyph_bonds",
    tags=["glyph-bonds-dev"],
)


def _now_ms() -> int:
    return int(time.time() * 1000)


# ───────────────────────────────────────────────
# Dev in-memory model
# ───────────────────────────────────────────────


@dataclass
class DevBondSeries:
    series_id: str
    label: str
    coupon_bps: int              # e.g. 500 = 5.00% (APY in basis points)
    maturity_ms: int             # unix ms when this series matures
    created_at_ms: int
    total_issued_pho: str        # decimal string
    total_outstanding_pho: str   # decimal string

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevBondPosition:
    position_id: str
    series_id: str
    account: str
    principal_pho: str           # decimal string
    coupon_bps: int              # fixed at issuance
    created_at_ms: int

    status: str                  # "OPEN" | "REDEEMED"
    closed_at_ms: Optional[int]

    last_coupon_at_ms: int       # last time coupons were accrued
    accrued_interest_pho: str    # decimal string
    maturity_ms: int             # normally series.maturity_ms at issuance

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEV_BOND_SERIES: List[DevBondSeries] = []
_DEV_BOND_POSITIONS: List[DevBondPosition] = []


# ───────────────────────────────────────────────
# Request models
# ───────────────────────────────────────────────


class DevSeriesCreate(BaseModel):
    label: str
    coupon_bps: int           # 500 = 5.00% APY
    term_days: int            # days from now until maturity


class DevIssueRequest(BaseModel):
    series_id: str
    account: str
    principal_pho: str        # decimal string


class DevRunCouponsRequest(BaseModel):
    # Optional filters: run coupons for one series and/or one account
    series_id: Optional[str] = None
    account: Optional[str] = None


class DevRedeemRequest(BaseModel):
    position_id: str


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────


def _find_series(series_id: str) -> DevBondSeries:
    for s in _DEV_BOND_SERIES:
        if s.series_id == series_id:
            return s
    raise HTTPException(status_code=404, detail="bond series not found")


def _find_position(position_id: str) -> DevBondPosition:
    for p in _DEV_BOND_POSITIONS:
        if p.position_id == position_id:
            return p
    raise HTTPException(status_code=404, detail="bond position not found")


# ───────────────────────────────────────────────
# Series endpoints
# ───────────────────────────────────────────────


@router.get("/dev/series")
async def glyph_bonds_dev_list_series() -> Dict[str, Any]:
    """
    Dev-only: list all GlyphBond series.
    """
    return {"series": [s.to_dict() for s in _DEV_BOND_SERIES]}


@router.post("/dev/series")
async def glyph_bonds_dev_create_series(body: DevSeriesCreate) -> Dict[str, Any]:
    """
    Dev-only: create a new GlyphBond series.

    - label: human-readable name
    - coupon_bps: integer basis points (e.g. 500 = 5.00% APY)
    - term_days: days from now until maturity
    """
    now = _now_ms()

    if body.term_days <= 0:
        raise HTTPException(status_code=400, detail="term_days must be positive")

    series_id = f"GBOND_{uuid.uuid4().hex[:8]}"
    maturity_ms = now + body.term_days * 24 * 60 * 60 * 1000

    series = DevBondSeries(
        series_id=series_id,
        label=body.label.strip() or series_id,
        coupon_bps=int(body.coupon_bps),
        maturity_ms=maturity_ms,
        created_at_ms=now,
        total_issued_pho="0",
        total_outstanding_pho="0",
    )
    _DEV_BOND_SERIES.append(series)
    return series.to_dict()


# ───────────────────────────────────────────────
# Position endpoints
# ───────────────────────────────────────────────


@router.get("/dev/positions")
async def glyph_bonds_dev_list_positions(
    account: Optional[str] = Query(
        None,
        description="If set, filter positions by PHO account",
    ),
) -> Dict[str, Any]:
    """
    Dev-only: list bond positions. If 'account' is provided, filter by account.
    """
    if account:
        positions = [
            p.to_dict() for p in _DEV_BOND_POSITIONS if p.account == account
        ]
    else:
        positions = [p.to_dict() for p in _DEV_BOND_POSITIONS]

    return {"positions": positions}


@router.post("/dev/issue")
async def glyph_bonds_dev_issue(body: DevIssueRequest) -> Dict[str, Any]:
    """
    Dev-only: issue bonds in a given series to an account.

    - Increments series.total_issued_pho and total_outstanding_pho
    - Creates a DevBondPosition for the account
    """
    series = _find_series(body.series_id)

    try:
        principal = Decimal(body.principal_pho)
        if principal <= 0:
            raise ValueError("principal_pho must be positive")
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid principal_pho")

    now = _now_ms()
    pos = DevBondPosition(
        position_id=f"BPOS_{uuid.uuid4().hex[:10]}",
        series_id=series.series_id,
        account=body.account,
        principal_pho=str(principal),
        coupon_bps=series.coupon_bps,
        created_at_ms=now,
        status="OPEN",
        closed_at_ms=None,
        last_coupon_at_ms=now,
        accrued_interest_pho="0",
        maturity_ms=series.maturity_ms,
    )
    _DEV_BOND_POSITIONS.append(pos)

    # update series totals
    issued = Decimal(series.total_issued_pho)
    outstanding = Decimal(series.total_outstanding_pho)
    series.total_issued_pho = str(issued + principal)
    series.total_outstanding_pho = str(outstanding + principal)

    return {
        "ok": True,
        "series": series.to_dict(),
        "position": pos.to_dict(),
    }


# ───────────────────────────────────────────────
# Dev coupon engine
# ───────────────────────────────────────────────


@router.post("/dev/run_coupons")
async def glyph_bonds_dev_run_coupons(
    body: DevRunCouponsRequest,
) -> Dict[str, Any]:
    """
    Dev-only coupon engine.

    For each OPEN position (optionally filtered by series_id/account):
      - compute simple interest since last_coupon_at_ms, using:
            interest = principal * (coupon_bps / 10_000) * (days / 365)
      - add to accrued_interest_pho
      - bump last_coupon_at_ms

    No real PHO is moved yet; this just updates in-memory positions and
    returns the total coupon amount that 'should' be paid.
    """
    now = _now_ms()
    updated: List[Dict[str, Any]] = []
    total_coupon = Decimal("0")

    for p in _DEV_BOND_POSITIONS:
        if p.status != "OPEN":
            continue
        if body.series_id and p.series_id != body.series_id:
            continue
        if body.account and p.account != body.account:
            continue

        try:
            principal = Decimal(p.principal_pho)
            rate = Decimal(p.coupon_bps) / Decimal(10_000)  # bps → fraction
        except (InvalidOperation, AttributeError):
            continue

        elapsed_ms = now - p.last_coupon_at_ms
        if elapsed_ms <= 0:
            continue

        # Simple day-count: Actual/365
        elapsed_days = Decimal(elapsed_ms) / Decimal(1000 * 60 * 60 * 24)
        year_fraction = elapsed_days / Decimal(365)

        coupon = (principal * rate * year_fraction).quantize(
            Decimal("0.00000001")
        )
        if coupon <= 0:
            continue

        # Update position
        p.last_coupon_at_ms = now
        p.accrued_interest_pho = str(
            Decimal(p.accrued_interest_pho) + coupon
        )

        total_coupon += coupon
        updated.append(p.to_dict())

    return {
        "ok": True,
        "total_coupon_pho": str(total_coupon),
        "updated_positions": updated,
        # Real system: we'd also emit PhotonReceipt(s) and actually transfer PHO.
    }


# ───────────────────────────────────────────────
# Dev redemption
# ───────────────────────────────────────────────


@router.post("/dev/redeem")
async def glyph_bonds_dev_redeem(
    body: DevRedeemRequest,
) -> Dict[str, Any]:
    """
    Dev-only redemption:

      - checks maturity_ms
      - marks position as REDEEMED
      - reduces series.total_outstanding_pho
      - returns principal + accrued interest that 'should' be paid.

    No real PHO moves yet; this is an accounting / UX stub.
    """
    now = _now_ms()
    pos = _find_position(body.position_id)

    if pos.status != "OPEN":
        raise HTTPException(status_code=400, detail="position is not OPEN")

    if pos.maturity_ms is not None and now < pos.maturity_ms:
        raise HTTPException(status_code=400, detail="bond has not matured yet")

    series = _find_series(pos.series_id)

    principal = Decimal(pos.principal_pho)
    interest = Decimal(pos.accrued_interest_pho)
    payout = principal + interest

    # Mark position closed
    pos.status = "REDEEMED"
    pos.closed_at_ms = now

    # Reduce outstanding principal for the series
    try:
        outstanding = Decimal(series.total_outstanding_pho)
        series.total_outstanding_pho = str(outstanding - principal)
    except (AttributeError, InvalidOperation):
        # If something is off, we don't crash the dev route; state can be inspected.
        pass

    # NOTE: in real system we would:
    #   - move PHO from GMA's bond bucket -> pos.account
    #   - log a PhotonReceipt
    # Here we just return the computed numbers.
    return {
        "ok": True,
        "position": pos.to_dict(),
        "series": series.to_dict(),
        "principal_pho": str(principal),
        "interest_pho": str(interest),
        "payout_pho": str(payout),
    }
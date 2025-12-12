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
    coupon_bps: int          # e.g. 500 = 5.00%
    maturity_ms: int
    created_at_ms: int
    total_issued_pho: str    # decimal string
    total_outstanding_pho: str  # decimal string

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevBondPosition:
    position_id: str
    series_id: str
    account: str
    principal_pho: str       # decimal string
    created_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_DEV_BOND_SERIES: List[DevBondSeries] = []
_DEV_BOND_POSITIONS: List[DevBondPosition] = []


# ───────────────────────────────────────────────
# Request models
# ───────────────────────────────────────────────


class DevSeriesCreate(BaseModel):
    label: str
    coupon_bps: int           # 500 = 5.00%
    term_days: int            # days from now until maturity


class DevIssueRequest(BaseModel):
    series_id: str
    account: str
    principal_pho: str        # decimal string


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
    - coupon_bps: integer basis points (e.g. 500 = 5.00%)
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


def _find_series(series_id: str) -> DevBondSeries:
    for s in _DEV_BOND_SERIES:
        if s.series_id == series_id:
            return s
    raise HTTPException(status_code=404, detail="bond series not found")


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
        created_at_ms=now,
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
# backend/modules/savings/photon_savings_routes.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional
import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(
    prefix="/photon_savings",
    tags=["photon-savings-dev"],
)

# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _now_ms() -> int:
    return int(time.time() * 1000)


def _days_between(start_ms: int, end_ms: int) -> Decimal:
    if end_ms <= start_ms:
        return Decimal("0")
    delta_ms = end_ms - start_ms
    # 86_400_000 = 1000 * 60 * 60 * 24
    return Decimal(delta_ms) / Decimal(86_400_000)


# ───────────────────────────────────────────────
# In-memory dev products + positions
# ───────────────────────────────────────────────

@dataclass
class DevSavingsProduct:
    product_id: str
    label: str
    rate_apy_bps: int          # e.g. 500 = 5% APY
    term_days: Optional[int]   # None or 0 = on-demand
    created_at_ms: int
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevSavingsPosition:
    position_id: str
    account: str
    product_id: str
    principal_pho: str         # stored as string
    rate_apy_bps: int
    term_days: Optional[int]   # snapshot from product
    opened_at_ms: int
    status: str                # "OPEN" | "CLOSED"
    closed_at_ms: Optional[int] = None
    interest_paid_pho: str = "0"

    def accrued_interest(self, now_ms: Optional[int] = None) -> Decimal:
        """
        Simple linear interest:
          principal * (rate_apy / 10000) * (elapsed_days / 365)
        capped at term_days (if any).
        """
        if self.status != "OPEN":
            # For closed positions we just report interest_paid_pho.
            try:
                return Decimal(self.interest_paid_pho)
            except InvalidOperation:
                return Decimal("0")

        now = now_ms or _now_ms()
        elapsed_days = _days_between(self.opened_at_ms, now)

        if self.term_days and self.term_days > 0:
            elapsed_days = min(elapsed_days, Decimal(self.term_days))

        try:
            principal = Decimal(self.principal_pho)
        except InvalidOperation:
            return Decimal("0")

        rate = Decimal(self.rate_apy_bps) / Decimal(10_000)  # bps → fraction
        interest = principal * rate * (elapsed_days / Decimal(365))
        return interest.quantize(Decimal("0.0001"))  # 4 dp dev rounding

    def maturity_ms(self) -> Optional[int]:
        if not self.term_days:
            return None
        return self.opened_at_ms + self.term_days * 86_400_000

    def to_dict(self, now_ms: Optional[int] = None) -> Dict[str, Any]:
        d = asdict(self)
        # Attach dev-only computed fields
        acc = self.accrued_interest(now_ms)
        d["accrued_interest_pho"] = str(acc)
        d["maturity_ms"] = self.maturity_ms()
        return d


_DEV_PRODUCTS: List[DevSavingsProduct] = []
_DEV_POSITIONS: List[DevSavingsPosition] = []


def _ensure_demo_products() -> None:
    global _DEV_PRODUCTS
    if _DEV_PRODUCTS:
        return

    now = _now_ms()
    _DEV_PRODUCTS = [
        DevSavingsProduct(
            product_id="sav_30d_3pc",
            label="Photon Savings 30-day (3% APY)",
            rate_apy_bps=300,
            term_days=30,
            created_at_ms=now,
        ),
        DevSavingsProduct(
            product_id="sav_90d_4pc",
            label="Photon Savings 90-day (4% APY)",
            rate_apy_bps=400,
            term_days=90,
            created_at_ms=now,
        ),
        DevSavingsProduct(
            product_id="sav_180d_5pc",
            label="Photon Savings 180-day (5% APY)",
            rate_apy_bps=500,
            term_days=180,
            created_at_ms=now,
        ),
    ]


def _find_product(product_id: str) -> DevSavingsProduct:
    for p in _DEV_PRODUCTS:
        if p.product_id == product_id and p.active:
            return p
    raise HTTPException(status_code=404, detail="savings product not found")


def _find_position(position_id: str) -> DevSavingsPosition:
    for pos in _DEV_POSITIONS:
        if pos.position_id == position_id:
            return pos
    raise HTTPException(status_code=404, detail="savings position not found")


# ───────────────────────────────────────────────
# Schemas
# ───────────────────────────────────────────────

class DevDepositCreate(BaseModel):
    account: str
    product_id: str
    amount_pho: str


class DevRedeemResponse(BaseModel):
    position: Dict[str, Any]
    payout_principal_pho: str
    payout_interest_pho: str
    total_payout_pho: str


# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────

@router.get("/dev/products")
async def list_savings_products() -> Dict[str, Any]:
    """
    Dev-only list of Photon Savings products.
    """
    _ensure_demo_products()
    return {"products": [p.to_dict() for p in _DEV_PRODUCTS if p.active]}


@router.get("/dev/positions")
async def list_savings_positions(
    account: Optional[str] = Query(None, description="Filter by PHO account"),
) -> Dict[str, Any]:
    """
    Dev-only list of savings positions (with computed accrued interest).
    """
    _ensure_demo_products()
    now = _now_ms()

    positions = _DEV_POSITIONS
    if account:
        positions = [p for p in positions if p.account == account]

    # Newest first
    positions = sorted(positions, key=lambda p: p.opened_at_ms, reverse=True)
    return {"positions": [p.to_dict(now_ms=now) for p in positions]}


@router.post("/dev/deposit")
async def create_savings_position(body: DevDepositCreate) -> Dict[str, Any]:
    """
    Dev-only: open a new Photon Savings position for an account.
    """
    _ensure_demo_products()

    try:
        amt = Decimal(body.amount_pho)
        if amt <= 0:
            raise ValueError("amount_pho must be positive")
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    product = _find_product(body.product_id)

    now = _now_ms()
    pos = DevSavingsPosition(
        position_id=f"savpos_{uuid.uuid4().hex}",
        account=body.account,
        product_id=product.product_id,
        principal_pho=str(amt),
        rate_apy_bps=product.rate_apy_bps,
        term_days=product.term_days,
        opened_at_ms=now,
        status="OPEN",
    )
    _DEV_POSITIONS.append(pos)

    # NOTE: in a real system, this would:
    #   • debit PHO from account
    #   • credit GMA reserves / savings facility
    return {"ok": True, "position": pos.to_dict(now_ms=now)}


@router.post("/dev/redeem/{position_id}")
async def redeem_savings_position(position_id: str) -> DevRedeemResponse:
    """
    Dev-only redeem endpoint:
      • marks position CLOSED
      • computes simple accrued interest
      • returns hypothetical payout.
    """
    pos = _find_position(position_id)
    if pos.status != "OPEN":
        raise HTTPException(status_code=400, detail="position already closed")

    now = _now_ms()
    accrued = pos.accrued_interest(now_ms=now)

    try:
        principal = Decimal(pos.principal_pho)
    except InvalidOperation:
        raise HTTPException(status_code=500, detail="invalid stored principal")

    total = (principal + accrued).quantize(Decimal("0.0001"))

    pos.status = "CLOSED"
    pos.closed_at_ms = now
    pos.interest_paid_pho = str(accrued)

    return DevRedeemResponse(
        position=pos.to_dict(now_ms=now),
        payout_principal_pho=str(principal),
        payout_interest_pho=str(accrued),
        total_payout_pho=str(total),
    )
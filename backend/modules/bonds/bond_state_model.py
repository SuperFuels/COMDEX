# backend/modules/bonds/bond_state_model.py

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
import time
import uuid

DecimalLike = Decimal | str | float | int


def _D(x: DecimalLike) -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"invalid decimal: {x!r}") from e


def _now_ms() -> int:
    return int(time.time() * 1000)


# ───────────────────────────────────────────────
# Core bond structs (dev model)
# ───────────────────────────────────────────────

@dataclass
class BondSeries:
    """
    Dev-only representation of a bond series.

    This is intentionally simple and chain-agnostic.
    """

    series_id: str
    name: str
    currency: str              # e.g. "PHO"
    coupon_rate_bps: int       # e.g. 500 -> 5% annual
    maturity_ms: int           # timestamp (ms since epoch)
    face_value_pho: Decimal    # principal per bond unit

    # book-keeping
    created_at_ms: int
    total_issued_pho: Decimal = field(default_factory=lambda: _D("0"))
    total_redeemed_pho: Decimal = field(default_factory=lambda: _D("0"))
    active: bool = True

    def __post_init__(self) -> None:
        self.face_value_pho = _D(self.face_value_pho)
        self.total_issued_pho = _D(self.total_issued_pho)
        self.total_redeemed_pho = _D(self.total_redeemed_pho)

    def to_dict(self) -> Dict:
        d = asdict(self)
        # normalise decimals as strings
        d["face_value_pho"] = str(self.face_value_pho)
        d["total_issued_pho"] = str(self.total_issued_pho)
        d["total_redeemed_pho"] = str(self.total_redeemed_pho)
        return d


@dataclass
class BondPosition:
    """
    Dev-only position: how many PHO-face-value of a series
    a given account holds.
    """

    series_id: str
    owner_account: str
    principal_pho: Decimal
    created_at_ms: int

    def __post_init__(self) -> None:
        self.principal_pho = _D(self.principal_pho)

    def to_dict(self) -> Dict:
        return {
            "series_id": self.series_id,
            "owner_account": self.owner_account,
            "principal_pho": str(self.principal_pho),
            "created_at_ms": self.created_at_ms,
        }


# ───────────────────────────────────────────────
# In-memory dev store (singleton style)
# ───────────────────────────────────────────────

class BondDevStore:
    """
    Tiny in-process store for bond series + positions for dev/test.
    Not persistent, not thread-safe; matches other dev_* modules.
    """

    def __init__(self) -> None:
        self.series: Dict[str, BondSeries] = {}
        self.positions: List[BondPosition] = []

    # --- series management -------------------------------------------------

    def create_series(
        self,
        name: str,
        currency: str,
        coupon_rate_bps: int,
        maturity_ms: int,
        face_value_pho: DecimalLike,
    ) -> BondSeries:
        sid = f"series_{uuid.uuid4().hex}"
        s = BondSeries(
            series_id=sid,
            name=name,
            currency=currency,
            coupon_rate_bps=int(coupon_rate_bps),
            maturity_ms=int(maturity_ms),
            face_value_pho=_D(face_value_pho),
            created_at_ms=_now_ms(),
        )
        self.series[sid] = s
        return s

    def list_series(self) -> List[BondSeries]:
        # newest first
        return sorted(
            self.series.values(),
            key=lambda s: s.created_at_ms,
            reverse=True,
        )

    def get_series(self, series_id: str) -> BondSeries:
        if series_id not in self.series:
            raise KeyError(f"unknown bond series: {series_id}")
        return self.series[series_id]

    # --- positions (very bare-bones, no coupons yet) -----------------------

    def issue_bonds(
        self,
        series_id: str,
        owner_account: str,
        principal_pho: DecimalLike,
    ) -> BondPosition:
        s = self.get_series(series_id)
        amt = _D(principal_pho)
        if amt <= 0:
            raise ValueError("principal_pho must be positive")

        pos = BondPosition(
            series_id=series_id,
            owner_account=owner_account,
            principal_pho=amt,
            created_at_ms=_now_ms(),
        )
        self.positions.append(pos)

        s.total_issued_pho = s.total_issued_pho + amt
        return pos

    def list_positions_for_account(self, account: str) -> List[BondPosition]:
        return [p for p in self.positions if p.owner_account == account]


# global dev singleton helper (like _DEV_GMA_STATE)
_BOND_DEV_STORE: Optional[BondDevStore] = None


def get_bond_dev_store() -> BondDevStore:
    global _BOND_DEV_STORE
    if _BOND_DEV_STORE is None:
        _BOND_DEV_STORE = BondDevStore()
    return _BOND_DEV_STORE
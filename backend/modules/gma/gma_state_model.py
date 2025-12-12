# backend/modules/gma/gma_state_model.py
"""
Tiny in-memory GMAState model for sims / notebooks.

Goal:
  - Represent the GMA balance sheet in one place.
  - Track PHO/TESS supply + reserves + offline credit exposure.
  - Provide small helpers for:
      * reserve revaluation
      * PHO mint/burn with invariants
      * checking how much offline credit is safe to extend

This is DEV-ONLY: not wired to the real chain state yet.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional

DecimalLike = Decimal | str | float | int


def _D(x: DecimalLike) -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"invalid decimal: {x!r}") from e


# ───────────────────────────────────────────────
# Reserve positions
# ───────────────────────────────────────────────


@dataclass
class ReservePosition:
    """
    A single reserve asset on the GMA balance sheet.

    Example: USD bank deposits, BTC holdings, T-bills, etc.
    """

    asset_id: str  # e.g. "USD_BANK_X", "BTC_CUSTODIAN_Y"
    quantity: Decimal  # how many units (e.g. 1_000_000 USD)
    price_pho: Decimal  # price per unit in PHO
    value_pho: Decimal = field(init=False)  # computed = quantity * price_pho

    def __post_init__(self) -> None:
        self.quantity = _D(self.quantity)
        self.price_pho = _D(self.price_pho)
        self.value_pho = self.quantity * self.price_pho

    def revalue(self, new_price_pho: DecimalLike) -> None:
        """
        Update the PHO mark-to-market value based on a new oracle price.
        """
        self.price_pho = _D(new_price_pho)
        self.value_pho = self.quantity * self.price_pho


# ───────────────────────────────────────────────
# GMAState (balance sheet)
# ───────────────────────────────────────────────


@dataclass
class GMAState:
    """
    Minimal GMA balance sheet model.

    Assets:
      - total_reserves_pho: sum of all ReservePosition.value_pho

    Liabilities:
      - photon_supply_pho: total circulating PHO
      - tesseract_supply: TESS governance token (tracked but not valued here)
      - offline_credit_exposure_pho: outstanding offline credit promises

    Equity:
      - equity_pho = assets_pho - liabilities_pho
    """

    # token supply (liability side)
    photon_supply_pho: Decimal
    tesseract_supply: Decimal

    # reserve book (asset side)
    reserves: Dict[str, ReservePosition] = field(default_factory=dict)

    # offline credit exposure and budget knobs
    offline_credit_exposure_pho: Decimal = field(default_factory=lambda: _D("0"))
    offline_credit_soft_cap_ratio: Decimal = field(
        default_factory=lambda: _D("0.3")
    )
    # e.g. 0.3 → we try to keep offline_exposure <= 30% of reserves

    # Dev-only: log of all PHO mint/burn events for debugging
    mint_burn_log: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.photon_supply_pho = _D(self.photon_supply_pho)
        self.tesseract_supply = _D(self.tesseract_supply)
        self.offline_credit_exposure_pho = _D(self.offline_credit_exposure_pho)
        self.offline_credit_soft_cap_ratio = _D(self.offline_credit_soft_cap_ratio)

    # ───────────────────────────────────────────
    # Derived quantities
    # ───────────────────────────────────────────

    @property
    def total_reserves_pho(self) -> Decimal:
        return sum((r.value_pho for r in self.reserves.values()), _D("0"))

    @property
    def liabilities_pho(self) -> Decimal:
        # We only value PHO + offline exposure here.
        # TESS liabilities are tracked in supply but not marked in PHO yet.
        return self.photon_supply_pho + self.offline_credit_exposure_pho

    @property
    def equity_pho(self) -> Decimal:
        return self.total_reserves_pho - self.liabilities_pho

    @property
    def max_offline_credit_soft_cap(self) -> Decimal:
        """
        Soft cap for offline credit, as a fraction of reserves.

        This does NOT enforce anything by itself; it's used by helpers
        to answer "is it sane to extend another X PHO of offline credit?".
        """
        return self.total_reserves_pho * self.offline_credit_soft_cap_ratio

    # ───────────────────────────────────────────
    # Internal helpers
    # ───────────────────────────────────────────

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _recompute_equity(self) -> None:
        """
        Placeholder hook: equity is derived from reserves + liabilities,
        so there's nothing to store, but we keep this for future caching.
        """
        _ = self.equity_pho

    # ───────────────────────────────────────────
    # Reserve plumbing
    # ───────────────────────────────────────────

    def set_reserve_position(
        self,
        asset_id: str,
        quantity: DecimalLike,
        price_pho: DecimalLike,
    ) -> None:
        """
        Create or replace a reserve position, then recompute its PHO value.
        """
        self.reserves[asset_id] = ReservePosition(
            asset_id=asset_id,
            quantity=_D(quantity),
            price_pho=_D(price_pho),
        )

    def revalue_reserve(self, asset_id: str, new_price_pho: DecimalLike) -> None:
        if asset_id not in self.reserves:
            raise KeyError(f"unknown reserve asset_id={asset_id!r}")
        self.reserves[asset_id].revalue(new_price_pho)

    def record_reserve_deposit(self, asset_id: str, amount_pho: DecimalLike) -> None:
        """
        Dev model for a reserve-backed PHO mint:

          - A custodian (bank, fund, etc.) increases our off-chain reserves
            in asset_id by 'amount_pho' worth of value.
          - We mint the same amount of PHO (1:1) on the liability side.

        Equity is derived:
          equity = total_reserves_pho - photon_supply_pho - offline_credit_exposure_pho
        """
        amt = _D(amount_pho)
        if amt <= 0:
            raise ValueError("reserve deposit amount_pho must be positive")

        if asset_id not in self.reserves:
            raise ValueError(f"unknown reserve asset_id: {asset_id}")

        rp = self.reserves[asset_id]

        # Convert PHO value into underlying units using current price.
        qty_delta = amt / rp.price_pho
        rp.quantity = rp.quantity + qty_delta
        # keep value_pho in sync
        rp.value_pho = rp.quantity * rp.price_pho

        # Centralised mint (logs + sanity checks)
        self.gma_mint_photon(amt, reason=f"reserve_deposit:{asset_id}")

    def record_reserve_redemption(self, asset_id: str, amount_pho: DecimalLike) -> None:
        """
        Dev model for a reserve redemption:

          - A holder gives 'amount_pho' PHO back to the GMA.
          - We burn that PHO and release underlying reserves.
          - Must NOT exceed the available reserves in asset_id.

        If invariants would be violated (e.g. not enough reserves),
        we raise.
        """
        amt = _D(amount_pho)
        if amt <= 0:
            raise ValueError("reserve redemption amount_pho must be positive")

        if asset_id not in self.reserves:
            raise ValueError(f"unknown reserve asset_id: {asset_id}")

        rp = self.reserves[asset_id]
        qty_delta = amt / rp.price_pho

        if qty_delta > rp.quantity:
            raise ValueError(
                f"insufficient reserves in {asset_id}: have {rp.quantity}, need {qty_delta}"
            )

        # Adjust reserves first
        rp.quantity = rp.quantity - qty_delta
        rp.value_pho = rp.quantity * rp.price_pho

        # Centralised burn (logs + sanity checks)
        self.gma_burn_photon(amt, reason=f"reserve_redemption:{asset_id}")

    # ───────────────────────────────────────────
    # Mint / burn guard rails (P3_2 sketch)
    # ───────────────────────────────────────────

    def gma_mint_photon(self, amount_pho: DecimalLike, reason: str = "dev_mint") -> None:
        """
        Centralised PHO mint path for dev model.

        For now we just bump supply, log the event, and rely on the caller to ensure:
          - this corresponds to a reserve inflow or P&L,
          - invariants remain sane (equity >= 0).
        """
        amt = _D(amount_pho)
        if amt <= 0:
            raise ValueError("gma_mint_photon: amount must be positive")

        # Adjust supply
        self.photon_supply_pho += amt

        # Log event
        self.mint_burn_log.append(
            {
                "kind": "MINT",
                "amount_pho": str(amt),
                "reason": reason,
                "created_at_ms": self._now_ms(),
            }
        )

        # Sanity: shout loudly if we break solvency in dev mode
        if self.equity_pho < 0:
            raise RuntimeError(
                f"gma_mint_photon would make equity negative: equity={self.equity_pho}"
            )

        self._recompute_equity()

    def gma_burn_photon(self, amount_pho: DecimalLike, reason: str = "dev_burn") -> None:
        """
        Centralised PHO burn path for dev model.

        Used when:
          - redeeming reserves,
          - shrinking supply after losses, etc.
        """
        amt = _D(amount_pho)
        if amt <= 0:
            raise ValueError("gma_burn_photon: amount must be positive")
        if amt > self.photon_supply_pho:
            raise ValueError("gma_burn_photon: cannot burn more than supply")

        self.photon_supply_pho -= amt

        self.mint_burn_log.append(
            {
                "kind": "BURN",
                "amount_pho": str(amt),
                "reason": reason,
                "created_at_ms": self._now_ms(),
            }
        )

        # Burning reduces liabilities → equity only improves,
        # so we don't expect negative equity here, but we keep
        # the hook symmetric with mint.
        self._recompute_equity()

    # ───────────────────────────────────────────
    # Offline credit vs reserves
    # ───────────────────────────────────────────

    def can_extend_offline_credit(self, extra_pho: DecimalLike) -> bool:
        """
        Check whether extending `extra_pho` of offline credit keeps us
        within the soft cap based on reserves.

          offline_credit_exposure_pho + extra <= soft_cap

        This does NOT mutate state.
        """
        extra = _D(extra_pho)
        if extra < 0:
            raise ValueError("extra_pho must be non-negative")

        new_exposure = self.offline_credit_exposure_pho + extra
        return new_exposure <= self.max_offline_credit_soft_cap

    def extend_offline_credit(self, extra_pho: DecimalLike) -> None:
        """
        Increase the tracked offline credit exposure, enforcing the soft cap.
        This is the hook a future OfflineCreditPolicy would call when
        raising system-wide limits or granting large merchant limits.
        """
        extra = _D(extra_pho)
        if extra <= 0:
            raise ValueError("extra_pho must be positive")

        if not self.can_extend_offline_credit(extra):
            raise RuntimeError(
                f"offline credit soft cap exceeded: "
                f"current={self.offline_credit_exposure_pho}, "
                f"extra={extra}, "
                f"cap={self.max_offline_credit_soft_cap}"
            )

        self.offline_credit_exposure_pho += extra

    def realise_offline_losses(self, loss_pho: DecimalLike) -> None:
        """
        Apply realised losses from offline credit (e.g. bad mesh debt).

        In a full model this would:
          - reduce reserves or equity explicitly,
          - maybe feed into seigniorage / recap rules.

        Here we simply reduce `offline_credit_exposure_pho`.
        """
        loss = _D(loss_pho)
        if loss < 0:
            raise ValueError("loss_pho must be non-negative")

        self.offline_credit_exposure_pho = max(
            _D("0"), self.offline_credit_exposure_pho - loss
        )

    # ───────────────────────────────────────────
    # Small helper for debug / JSON-ish view
    # ───────────────────────────────────────────

    def snapshot_dict(self) -> Dict[str, Any]:
        return {
            "photon_supply_pho": str(self.photon_supply_pho),
            "tesseract_supply": str(self.tesseract_supply),
            "total_reserves_pho": str(self.total_reserves_pho),
            "offline_credit_exposure_pho": str(self.offline_credit_exposure_pho),
            "offline_credit_soft_cap_ratio": str(self.offline_credit_soft_cap_ratio),
            "max_offline_credit_soft_cap": str(self.max_offline_credit_soft_cap),
            "equity_pho": str(self.equity_pho),
            "reserves": {
                k: {
                    "asset_id": v.asset_id,
                    "quantity": str(v.quantity),
                    "price_pho": str(v.price_pho),
                    "value_pho": str(v.value_pho),
                }
                for k, v in self.reserves.items()
            },
            "mint_burn_log": list(self.mint_burn_log),
        }


# ───────────────────────────────────────────────
# Demo constructors
# ───────────────────────────────────────────────


def new_dev_gma_state() -> GMAState:
    """
    Convenience constructor for local sims / notebooks.

    Starts with:
      - 10_000 PHO supply
      - 1_000 TESS supply
      - a single USD reserve worth 20_000 PHO
      - zero offline credit exposure
      - 30% soft cap for offline credit vs reserves
    """
    state = GMAState(
        photon_supply_pho=_D("10000"),
        tesseract_supply=_D("1000"),
    )
    state.set_reserve_position(
        asset_id="USD_BANK_X",
        quantity=_D("20000"),
        price_pho=_D("1.0"),  # 1 USD ≈ 1 PHO in this toy model
    )
    return state


# --- Demo factory for dev routes / smoketests -----------------------------


def make_demo_gma_state() -> GMAState:
    """
    Construct the same initial demo state used by dev_gma_state_smoketest:

      - reserves: 20,000 PHO worth at USD_BANK_X
      - photon_supply_pho: 10,000
      - tesseract_supply: 1,000
      - offline_credit_soft_cap_ratio: 0.3
      - offline_credit_exposure_pho: 0

    This should yield (via snapshot_dict):
      total_reserves_pho = 20,000
      equity_pho         = 10,000
      max_offline_credit_soft_cap = 6,000
    """
    usd_reserve = ReservePosition(
        asset_id="USD_BANK_X",
        quantity=Decimal("20000"),
        price_pho=Decimal("1.0"),
    )

    return GMAState(
        photon_supply_pho=Decimal("10000"),
        tesseract_supply=Decimal("1000"),
        reserves={"USD_BANK_X": usd_reserve},
        offline_credit_exposure_pho=Decimal("0"),
        offline_credit_soft_cap_ratio=Decimal("0.3"),
    )


# Backwards-compat alias if anything still calls make_demo_state()
def make_demo_state() -> GMAState:
    return make_demo_gma_state()
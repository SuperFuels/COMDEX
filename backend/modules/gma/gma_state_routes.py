# backend/modules/gma/gma_state_routes.py

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.gma import gma_state_model as gma_state_model
from backend.modules.gma.gma_state_model import GMAState
from backend.modules.gma.gma_state_dev import (
    record_mint_burn,
    record_reserve_move,
    get_mint_burn_log,
    get_reserve_moves_log,
)

# Router lives under /gma/state so final paths are /api/gma/state/...
router = APIRouter(
    prefix="/gma/state",
    tags=["gma-dev"],
)

# In-process singleton for the dev GMA state model.
_DEV_GMA_STATE: GMAState | None = None


def _new_demo_state() -> GMAState:
    """
    Construct the same demo state used by dev_gma_state_smoketest.

    We support either:
      - make_demo_gma_state()
      - make_demo_state()
    depending on what exists in gma_state_model.
    """
    factory = getattr(gma_state_model, "make_demo_gma_state", None)
    if factory is None:
        factory = getattr(gma_state_model, "make_demo_state", None)

    if factory is None:
        raise RuntimeError(
            "No demo factory found in gma_state_model "
            "(expected make_demo_gma_state() or make_demo_state())."
        )

    return factory()


def _get_dev_gma_state() -> GMAState:
    global _DEV_GMA_STATE
    if _DEV_GMA_STATE is None:
        _DEV_GMA_STATE = _new_demo_state()
    return _DEV_GMA_STATE


# Optional alias mirroring the “dev store” idea
def get_dev_gma_state() -> GMAState:
    return _get_dev_gma_state()


# ───────────────────────────────────────────────
# Snapshot
# ───────────────────────────────────────────────


@router.get("/dev_snapshot")
async def gma_state_dev_snapshot():
    """
    Dev-only: expose the current GMAState snapshot in PHO terms.

    Mirrors the model that dev_gma_state_smoketest.py exercises.
    Not a stable public API and not the final on-chain representation.
    """
    state = get_dev_gma_state()
    snap = state.snapshot_dict()

    # Attach dev event logs so Admin dashboard / GMADashboardDevPanel
    # can render a single unified view.
    snap["mint_burn_log"] = get_mint_burn_log()
    snap["reserve_moves_log"] = get_reserve_moves_log()

    return snap


# ───────────────────────────────────────────────
# Dev reserve deposit / redemption endpoints
# ───────────────────────────────────────────────


class ReserveOpRequest(BaseModel):
    asset_id: str
    amount_pho: str  # decimal string, e.g. "2000"


@router.post("/dev_reserve_deposit")
async def gma_state_dev_reserve_deposit(req: ReserveOpRequest):
    """
    Dev-only: simulate a reserve-backed PHO mint.

    - Increases reserves[asset_id] by amount_pho (using current price_pho)
    - Mints amount_pho PHO supply (via gma_mint_photon)
    - Returns updated snapshot_dict()
    """
    state = get_dev_gma_state()

    try:
        amt = Decimal(req.amount_pho)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    try:
        state.record_reserve_deposit(req.asset_id, amt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Log as a reserve move in PHO-equivalent terms
    record_reserve_move(
        kind="ADD",
        amount_pho_eq=str(amt),
        reason=f"reserve_deposit:{req.asset_id}",
    )

    return state.snapshot_dict()


@router.post("/dev_reserve_redemption")
async def gma_state_dev_reserve_redemption(req: ReserveOpRequest):
    """
    Dev-only: simulate a reserve redemption.

    - Holder gives amount_pho PHO back to GMA
    - We burn that PHO and release underlying reserves
    - Enforces: cannot exceed reserves
    """
    state = get_dev_gma_state()

    try:
        amt = Decimal(req.amount_pho)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    try:
        state.record_reserve_redemption(req.asset_id, amt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    record_reserve_move(
        kind="REMOVE",
        amount_pho_eq=str(amt),
        reason=f"reserve_redemption:{req.asset_id}",
    )

    return state.snapshot_dict()


# ───────────────────────────────────────────────
# Dev mint / burn endpoints (direct)
# ───────────────────────────────────────────────


class DevMintBurnRequest(BaseModel):
    amount_pho: str
    reason: str | None = None


@router.post("/dev_mint")
async def dev_gma_mint(req: DevMintBurnRequest):
    """
    Dev-only: direct PHO mint via GMAState.gma_mint_photon.
    """
    state = get_dev_gma_state()

    try:
        amt = Decimal(req.amount_pho)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount_pho")

    if amt <= 0:
        raise HTTPException(status_code=400, detail="amount_pho must be positive")

    reason = req.reason or "dev_mint"

    try:
        state.gma_mint_photon(amt, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Log mint in dev event store
    record_mint_burn(
        kind="MINT",
        amount_pho=str(amt),
        reason=reason,
    )

    return {"ok": True, "snapshot": state.snapshot_dict()}


@router.post("/dev_burn")
async def dev_gma_burn(req: DevMintBurnRequest):
    """
    Dev-only: direct PHO burn via GMAState.gma_burn_photon.
    """
    state = get_dev_gma_state()

    try:
        amt = Decimal(req.amount_pho)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount_pho")

    if amt <= 0:
        raise HTTPException(status_code=400, detail="amount_pho must be positive")

    reason = req.reason or "dev_burn"

    try:
        state.gma_burn_photon(amt, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record_mint_burn(
        kind="BURN",
        amount_pho=str(amt),
        reason=reason,
    )

    return {"ok": True, "snapshot": state.snapshot_dict()}
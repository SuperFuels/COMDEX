# backend/modules/mesh/mesh_reconcile_routes.py

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.mesh.mesh_types import AccountId
from backend.modules.wallet.mesh_wallet_state import (
    get_or_init_local_state_for_api,
    record_local_send_for_api,
)

router = APIRouter(
    prefix="/mesh",
    tags=["mesh"],
)


class LocalSendRequest(BaseModel):
    from_account: AccountId
    to_account: AccountId
    amount_pho: str


@router.get("/local_state/{account}")
async def get_local_state(account: str):
    """
    Returns local mesh state for a given PHO account.

    Used by:
      - Wallet 'Mesh Pending' card
      - future mesh debug tools
    """
    local_balance, local_log = get_or_init_local_state_for_api(account)

    # mesh_pending_pho = max(0, -local_net_delta_pho)
    try:
        delta = Decimal(local_balance["local_net_delta_pho"])
        pending = max(Decimal("0"), -delta)
    except Exception:
        pending = Decimal("0")

    return {
        "account": account,
        "local_balance": local_balance,
        "tx_log": local_log,
        "mesh_pending_pho": str(pending),
    }


@router.post("/local_send")
async def post_local_send(req: LocalSendRequest):
    """
    Records an offline mesh send and returns updated state.

    This does NOT touch the main chain – it's just the local mesh ledger
    living in memory for dev/demo.
    """
    try:
        local_balance, local_log, tx = record_local_send_for_api(
            from_account=req.from_account,
            to_account=req.to_account,
            amount_pho=req.amount_pho,
        )
    except ValueError as e:
        # e.g. insufficient credit, non-positive amount
        raise HTTPException(status_code=400, detail=str(e))

    # mesh_pending_pho = max(0, -local_net_delta_pho)
    try:
        delta = Decimal(local_balance["local_net_delta_pho"])
        pending = max(Decimal("0"), -delta)
    except Exception:
        pending = Decimal("0")

    return {
        "status": "ok",
        "mesh_tx": tx,
        "local_balance": local_balance,
        "tx_log": local_log,
        "mesh_pending_pho": str(pending),
    }
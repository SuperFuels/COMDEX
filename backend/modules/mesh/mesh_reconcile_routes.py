# backend/modules/mesh/mesh_reconcile_routes.py

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.mesh.mesh_types import AccountId
from backend.modules.wallet.mesh_wallet_state import (
    get_or_init_local_state_for_api,
    record_local_send_for_api,
    record_incoming_tx,
)
from backend.modules.mesh.mesh_reconcile_service import (
    ReconcileRequest,
    ReconcileResult,
    reconcile_mesh_for_account,
)
from backend.modules.gma.gma_mesh_policy import (
    get_offline_limit_pho,
    get_policy_snapshot,
)

router = APIRouter(prefix="/mesh", tags=["mesh"])


# ───────────────────────────────────────────────
# Reconcile + policy
# ───────────────────────────────────────────────


@router.post("/reconcile", response_model=ReconcileResult)
def mesh_reconcile(req: ReconcileRequest) -> ReconcileResult:
    """
    Wallets call this when they come back online with local mesh history.
    """
    try:
        # Let the service pull the limit from GMA policy by default.
        result = reconcile_mesh_for_account(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"reconcile failed: {e}")


@router.get("/limits/{account}")
def mesh_get_limit(account: str):
    """
    Wallets call this to learn their offline_credit_limit_pho from GMA policy.
    """
    try:
        limit = get_offline_limit_pho(account)
        return {
            "account": account,
            "offline_credit_limit_pho": str(limit),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"failed to fetch limit: {e}")


@router.get("/policy/snapshot")
def mesh_policy_snapshot():
    """
    Debug/admin: inspect current offline credit policy snapshot.
    """
    return get_policy_snapshot()


# ───────────────────────────────────────────────
# Mesh local state + local send (demo)
# ───────────────────────────────────────────────


class LocalSendRequest(BaseModel):
    from_account: AccountId
    to_account: AccountId
    amount_pho: str


class LocalReceiveRequest(BaseModel):
    """
    Dev-only: apply a MeshTx as an *incoming* tx for the to_account.

    In a real BLE flow, the receiver device would:
      - receive a MeshTx blob over radio
      - POST it here to update its LocalBalance + LocalTxLog
    """
    mesh_tx: dict


@router.get("/local_state/{account}")
async def get_local_state(account: str):
    """
    Returns local mesh state for a given PHO account.

    Used by:
      - Wallet 'Mesh Pending' card
      - mesh activity log
      - dev local_state inspector
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
    Records an offline mesh *send* for the given from_account and
    returns updated state for that account.

    This does NOT touch the main chain – it's just the local mesh ledger.
    """
    try:
        local_balance, local_log, tx = record_local_send_for_api(
            from_account=req.from_account,
            to_account=req.to_account,
            amount_pho=req.amount_pho,
        )
    except ValueError as e:
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


@router.post("/local_receive")
async def post_local_receive(req: LocalReceiveRequest):
    """
    Dev-only endpoint: apply an incoming MeshTx for the *receiver* account.

    For now we:
      - look at mesh_tx.to_account
      - ensure that account has a LocalBalance + LocalTxLog
      - apply record_incoming_tx(...)
      - recompute mesh_pending_pho for that account

    This mirrors what a real receiver wallet would do after getting the tx
    over BLE / radio.
    """
    tx = req.mesh_tx or {}

    to_acct = tx.get("to_account")
    if not to_acct:
        raise HTTPException(status_code=400, detail="mesh_tx missing to_account")

    # Ensure receiver has local state
    local_balance, local_log = get_or_init_local_state_for_api(to_acct)

    # Apply as incoming tx
    local_balance, local_log = record_incoming_tx(local_balance, local_log, tx)

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
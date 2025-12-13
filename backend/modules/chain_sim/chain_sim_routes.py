# backend/modules/chain_sim/chain_sim_routes.py

from __future__ import annotations

from typing import Any, Dict, Optional, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.modules.chain_sim import chain_sim_model as bank
from backend.modules.chain_sim import chain_sim_engine as engine
from backend.modules.chain_sim.chain_sim_ledger import (
    list_blocks,
    get_block,
    list_txs,
    get_tx,
)

router = APIRouter(prefix="/chain_sim", tags=["chain-sim-dev"])


# ───────────────────────────────────────────────
# Request models
# ───────────────────────────────────────────────

class DevMintRequest(BaseModel):
    denom: str
    to: str
    amount: str


class DevTransferRequest(BaseModel):
    denom: str
    from_addr: str
    to: str
    amount: str


class DevBurnRequest(BaseModel):
    denom: str
    from_addr: str
    amount: str


class DevSubmitTx(BaseModel):
    """
    Canonical dev tx envelope (P1_3).
    Engine validates nonce + applies BANK_* ops.
    Engine also records into chain_sim_ledger (blocks/tx explorer).
    """
    tx_id: Optional[str] = None
    from_addr: str
    nonce: int
    tx_type: Literal["BANK_MINT", "BANK_SEND", "BANK_BURN"]
    payload: Dict[str, Any]


# ───────────────────────────────────────────────
# Canonical entrypoint: submit_tx (P1_3)
# ───────────────────────────────────────────────

@router.post("/dev/submit_tx")
async def chain_sim_submit_tx(body: DevSubmitTx) -> Dict[str, Any]:
    """
    Single tx entrypoint.
    Calls engine.submit_tx(), which:
      - validates nonce
      - applies bank ops
      - records to chain_sim_ledger (blocks + txs)
    """
    try:
        return engine.submit_tx(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"submit_tx failed: {e}")


# ───────────────────────────────────────────────
# Explorer / ledger endpoints
# ───────────────────────────────────────────────

@router.get("/dev/blocks")
async def chain_sim_dev_blocks(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return {"ok": True, "blocks": list_blocks(limit=limit, offset=offset)}


@router.get("/dev/block/{height}")
async def chain_sim_dev_block(height: int) -> Dict[str, Any]:
    blk = get_block(height)
    if not blk:
        raise HTTPException(status_code=404, detail="block not found")
    return {"ok": True, "block": blk}


@router.get("/dev/tx/{tx_id}")
async def chain_sim_dev_tx(tx_id: str) -> Dict[str, Any]:
    tx = get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return {"ok": True, "tx": tx}


@router.get("/dev/txs")
async def chain_sim_dev_txs(
    address: Optional[str] = Query(
        None,
        description="Optional address filter (from_addr or payload.to)",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return {"ok": True, "txs": list_txs(address=address, limit=limit, offset=offset)}


# Back-compat alias (older callers might still use /dev/tx?tx_id=...)
@router.get("/dev/tx")
async def chain_sim_get_tx(tx_id: str = Query(...)) -> Dict[str, Any]:
    tx = get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return {"ok": True, "tx": tx}


# ───────────────────────────────────────────────
# Back-compat: mint / transfer / burn wrappers
# These call engine.submit_tx (which records to ledger)
# ───────────────────────────────────────────────

@router.post("/dev/mint")
async def chain_sim_dev_mint(body: DevMintRequest) -> Dict[str, Any]:
    signer = engine.DEV_MINT_AUTHORITY
    nonce = bank.get_or_create_account(signer).nonce

    tx = {
        "from_addr": signer,
        "nonce": nonce,
        "tx_type": "BANK_MINT",
        "payload": {"denom": body.denom, "to": body.to, "amount": body.amount},
    }

    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"mint failed: {e}")

    return receipt.get("result") or {"ok": False}


@router.post("/dev/transfer")
async def chain_sim_dev_transfer(body: DevTransferRequest) -> Dict[str, Any]:
    nonce = bank.get_or_create_account(body.from_addr).nonce

    tx = {
        "from_addr": body.from_addr,
        "nonce": nonce,
        "tx_type": "BANK_SEND",
        "payload": {"denom": body.denom, "to": body.to, "amount": body.amount},
    }

    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"transfer failed: {e}")

    return receipt.get("result") or {"ok": False}


@router.post("/dev/burn")
async def chain_sim_dev_burn(body: DevBurnRequest) -> Dict[str, Any]:
    nonce = bank.get_or_create_account(body.from_addr).nonce

    tx = {
        "from_addr": body.from_addr,
        "nonce": nonce,
        "tx_type": "BANK_BURN",
        "payload": {"denom": body.denom, "amount": body.amount},
    }

    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"burn failed: {e}")

    return receipt.get("result") or {"ok": False}


# ───────────────────────────────────────────────
# Queries
# ───────────────────────────────────────────────

@router.get("/dev/account")
async def chain_sim_dev_get_account(address: str = Query(...)) -> Dict[str, Any]:
    return bank.get_account_view(address)


@router.get("/dev/supply")
async def chain_sim_dev_get_supply() -> Dict[str, str]:
    return bank.get_supply_view()
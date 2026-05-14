# backend/routes/chain_sim/dev_tx_routes.py
from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException

from backend.modules.chain_sim.canonical_codec import canonical_hash_hex
from backend.modules.chain_sim.tx_models import TxEnvelope, TxRecord, BlockHeader, Block
from backend.modules.chain_sim.dev_singletons import DEV_LEDGER
from backend.modules.chain_sim.tx_executor import apply_tx
from backend.modules.chain_sim.state_root import compute_state_root

router = APIRouter()

DEV_FEE_PHO = 1  # keep trivial for now; can be config-driven later

@router.post("/api/chain_sim/dev/submit_tx")
async def submit_tx(envelope: TxEnvelope):
    # 1) canonical tx hash based ONLY on envelope
    tx_hash = canonical_hash_hex(envelope.model_dump())
    tx_id = tx_hash  # simplest: use full hash for id

    # 2) apply tx
    ok, err, receipt = apply_tx(envelope)

    height = DEV_LEDGER.next_height()
    created_at_ms = int(time.time() * 1000)

    tx_record = TxRecord(
        tx_id=tx_id,
        tx_hash=tx_hash,
        height=height,
        created_at_ms=created_at_ms,
        fee_pho=DEV_FEE_PHO,
        status="accepted" if ok else "rejected",
        error=None if ok else err,
        envelope=envelope,
    )

    # 3) compute state_root after apply (even on reject you can choose policy;
    #    dev-simple: only commit block if accepted)
    if not ok:
        DEV_LEDGER.add_tx(tx_record)
        return {"status": "rejected", "tx": tx_record.model_dump(), "receipt": receipt}

    state_root = compute_state_root()

    header = BlockHeader(
        height=height,
        created_at_ms=created_at_ms,
        state_root=state_root,
        trace_root=None,
        transport_attestation_hash=None,
        tx_count=1,
    )

    block = Block(header=header, tx_ids=[tx_id])

    DEV_LEDGER.add_tx(tx_record)
    DEV_LEDGER.add_block(block)

    return {
        "status": "accepted",
        "tx": tx_record.model_dump(),
        "block": block.model_dump(),
        "receipt": receipt,
    }


@router.get("/api/chain_sim/dev/blocks")
async def dev_blocks(limit: int = 50):
    return {"blocks": [b.model_dump() for b in DEV_LEDGER.list_blocks(limit=limit)]}


@router.get("/api/chain_sim/dev/block/{height}")
async def dev_block(height: int):
    b = DEV_LEDGER.get_block(height)
    if not b:
        raise HTTPException(status_code=404, detail="block not found")
    return b.model_dump()


@router.get("/api/chain_sim/dev/tx/{tx_id}")
async def dev_tx(tx_id: str):
    tx = DEV_LEDGER.get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return tx.model_dump()


@router.get("/api/chain_sim/dev/txs")
async def dev_txs(address: str, limit: int = 50):
    txs = DEV_LEDGER.list_txs_for_address(address, limit=limit)
    return {"txs": [t.model_dump() for t in txs]}
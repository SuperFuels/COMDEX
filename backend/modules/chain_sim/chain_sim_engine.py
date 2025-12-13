# backend/modules/chain_sim/chain_sim_engine.py

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, Optional

from backend.modules.chain_sim import chain_sim_model as bank
from backend.modules.chain_sim.chain_sim_ledger import (
    record_applied_tx,
    get_tx as ledger_get_tx,
    list_txs as ledger_list_txs,
)

DEV_MINT_AUTHORITY = "pho1-dev-gma-authority"

# Legacy in-process log (kept for back-compat / debugging)
_TX_LOG: Dict[str, Dict[str, Any]] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _new_tx_id() -> str:
    return f"TX_{uuid.uuid4().hex[:16]}"


def get_tx(tx_id: str) -> Optional[Dict[str, Any]]:
    """
    Prefer ledger-backed txs; fallback to legacy _TX_LOG.
    """
    tx = ledger_get_tx(tx_id)
    if tx:
        return tx
    return _TX_LOG.get(tx_id)


def list_txs_for_address(address: str, limit: int = 50) -> Dict[str, Any]:
    """
    Back-compat wrapper (old shape: {"txs": [...]})
    """
    return {"txs": ledger_list_txs(address=address, limit=limit, offset=0)}


def submit_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    tx shape:
      {
        "tx_id": optional str,
        "from_addr": str,
        "nonce": int,
        "tx_type": "BANK_MINT"|"BANK_SEND"|"BANK_BURN",
        "payload": {...}
      }
    """
    tx_id = tx.get("tx_id") or _new_tx_id()
    from_addr = tx.get("from_addr")
    nonce = tx.get("nonce")
    tx_type = tx.get("tx_type")
    payload = tx.get("payload") or {}

    if not isinstance(from_addr, str) or not from_addr:
        raise ValueError("from_addr required")
    if not isinstance(nonce, int) or nonce < 0:
        raise ValueError("nonce must be int >= 0")
    if tx_type not in ("BANK_MINT", "BANK_SEND", "BANK_BURN"):
        raise ValueError("invalid tx_type")

    signer_acc = bank.get_or_create_account(from_addr)
    if nonce != signer_acc.nonce:
        raise ValueError(f"bad nonce: expected {signer_acc.nonce}, got {nonce}")

    signing_obj = {
        "from_addr": from_addr,
        "nonce": nonce,
        "tx_type": tx_type,
        "payload": payload,
    }
    preimage_hash = _sha256_hex(_canonical_bytes(signing_obj))

    applied = False
    result: Dict[str, Any] = {}
    accounts_touched = [from_addr]

    if tx_type == "BANK_MINT":
        denom = payload.get("denom")
        to_addr = payload.get("to")
        amount = payload.get("amount")

        if from_addr != DEV_MINT_AUTHORITY:
            raise ValueError("mint requires dev authority signer")
        if not isinstance(to_addr, str) or not to_addr:
            raise ValueError("payload.to required")

        accounts_touched.append(to_addr)
        result = bank.mint(
            denom=denom,
            signer=from_addr,
            to_addr=to_addr,
            amount=amount,
        )
        applied = True

    elif tx_type == "BANK_SEND":
        denom = payload.get("denom")
        to_addr = payload.get("to")
        amount = payload.get("amount")

        if not isinstance(to_addr, str) or not to_addr:
            raise ValueError("payload.to required")

        accounts_touched.append(to_addr)
        result = bank.transfer(
            denom=denom,
            signer=from_addr,
            to_addr=to_addr,
            amount=amount,
        )
        applied = True

    elif tx_type == "BANK_BURN":
        denom = payload.get("denom")
        amount = payload.get("amount")

        result = bank.burn(
            denom=denom,
            signer=from_addr,
            from_addr=from_addr,
            amount=amount,
        )
        applied = True

    receipt: Dict[str, Any] = {
        "ok": True,
        "tx_id": tx_id,
        "tx_hash": preimage_hash,  # will be overwritten by ledger hash below
        "tx_type": tx_type,
        "from_addr": from_addr,
        "nonce": nonce,
        "applied": applied,
        "created_at_ms": _now_ms(),
        "accounts_touched": list(dict.fromkeys(accounts_touched)),
        "result": result,
    }

    # ✅ NEW: record to dev ledger (this powers /dev/blocks and /dev/txs)
    rec = record_applied_tx(
        from_addr=from_addr,
        nonce=nonce,
        tx_type=tx_type,
        payload=payload,     # store just the op payload (recommended)
        applied=applied,
        result=result,
    )

    # ✅ NEW: enrich receipt for UI + debugging
    receipt["tx_id"] = rec.tx_id
    receipt["tx_hash"] = rec.tx_hash
    receipt["block_height"] = rec.block_height
    receipt["tx_index"] = rec.tx_index

    # Keep legacy log keyed by the ledger tx_id
    _TX_LOG[rec.tx_id] = receipt

    return receipt
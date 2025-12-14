# backend/modules/chain_sim/chain_sim_ledger.py

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict, field
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _normalize_payload(payload: Any) -> Dict[str, Any]:
    """
    Call sites sometimes pass:
      - inner payload: {"denom": ..., "to": ..., "amount": ...}
      - outer tx envelope: {"from_addr":..., "nonce":..., "tx_type":..., "payload": {...}}

    Normalize to the inner payload dict so:
      - identity hashing is stable
      - address filter (payload.to) works
    """
    if isinstance(payload, dict):
        maybe_inner = payload.get("payload")
        if isinstance(maybe_inner, dict) and (
            "tx_type" in payload or "from_addr" in payload or "nonce" in payload
        ):
            return maybe_inner
        return payload
    return {"value": payload}


@dataclass
class DevTxRecord:
    tx_id: str
    tx_hash: str
    from_addr: str
    nonce: int
    tx_type: str
    payload: Dict[str, Any]
    applied: bool
    result: Dict[str, Any]
    created_at_ms: int
    block_height: int
    tx_index: int

    # ✅ new (fee plumbing)
    fee: Optional[Dict[str, Any]] = None
    accounts_touched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        # asdict() already handles default_factory lists correctly
        return asdict(self)


@dataclass
class DevBlock:
    height: int
    created_at_ms: int
    txs: List[DevTxRecord]
    txs_root: str

    # ✅ new: header commitments (e.g., state_root)
    header: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "created_at_ms": self.created_at_ms,
            "txs_root": self.txs_root,
            "header": dict(self.header or {}),
            "txs": [t.to_dict() for t in self.txs],
        }


# ───────────────────────────────────────────────
# In-memory ledger
# ───────────────────────────────────────────────

_LOCK = Lock()

_BLOCKS: List[DevBlock] = []
_TXS: List[DevTxRecord] = []

_TX_BY_ID: Dict[str, DevTxRecord] = {}
_TX_BY_HASH: Dict[str, DevTxRecord] = {}
# Strong idempotency key: nonce is unique per signer (for applied txs)
_TX_BY_KEY: Dict[Tuple[str, int, str], DevTxRecord] = {}


def reset_ledger() -> None:
    """Dev/test helper."""
    with _LOCK:
        _BLOCKS.clear()
        _TXS.clear()
        _TX_BY_ID.clear()
        _TX_BY_HASH.clear()
        _TX_BY_KEY.clear()


def _next_height_locked() -> int:
    # Caller must hold _LOCK.
    return len(_BLOCKS) + 1


def compute_tx_identity(
    from_addr: str,
    nonce: int,
    tx_type: str,
    payload: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Returns: (tx_id, tx_hash)

    tx_hash: sha256 over stable envelope JSON
    tx_id: short human-friendly id derived from tx_hash
    """
    norm_payload = _normalize_payload(payload)
    envelope = {
        "from_addr": from_addr,
        "nonce": int(nonce),
        "tx_type": tx_type,
        "payload": norm_payload,
    }
    h = _sha256_hex(_stable_json(envelope))
    tx_id = f"tx_{h[:12]}"
    return tx_id, h


def _append_block_with_single_tx_locked(
    tx: DevTxRecord,
    *,
    header: Optional[Dict[str, Any]] = None,
) -> DevBlock:
    """
    Dev rule: 1 applied tx == 1 block.
    Caller must hold _LOCK.
    """
    h = _next_height_locked()
    tx.block_height = h
    tx.tx_index = 0

    txs_root = _sha256_hex(_stable_json([tx.tx_hash]))
    blk = DevBlock(
        height=h,
        # ✅ keep block time aligned with tx time if provided
        created_at_ms=int(tx.created_at_ms or _now_ms()),
        txs=[tx],
        txs_root=txs_root,
        header=dict(header or {}),
    )
    _BLOCKS.append(blk)
    return blk


def record_applied_tx(
    *,
    from_addr: str,
    nonce: int,
    tx_type: str,
    payload: Any,
    applied: bool,
    result: Dict[str, Any],
    fee: Optional[Dict[str, Any]] = None,
    accounts_touched: Optional[List[str]] = None,
    created_at_ms: Optional[int] = None,
    # ✅ new: block header commitments (e.g., {"state_root": ...})
    block_header: Optional[Dict[str, Any]] = None,
) -> DevTxRecord:
    """
    Idempotent recorder:
      - If the same (from_addr, nonce, tx_type) is recorded twice, return the original record.
      - Also de-dupes by tx_hash / tx_id.
    """
    norm_payload = _normalize_payload(payload)
    key = (from_addr, int(nonce), tx_type)

    # If caller didn't pass a header explicitly, allow "result.header" to carry it.
    hdr: Dict[str, Any] = {}
    if isinstance(block_header, dict):
        hdr = dict(block_header)
    else:
        try:
            maybe = (result or {}).get("header")  # type: ignore[union-attr]
            if isinstance(maybe, dict):
                hdr = dict(maybe)
        except Exception:
            hdr = {}

    with _LOCK:
        # 1) Strong guard: (signer, nonce, type) should be unique for applied txs
        existing = _TX_BY_KEY.get(key)
        if existing:
            return existing

        # 2) Hash/id guard: covers other duplicate call paths
        tx_id, tx_hash = compute_tx_identity(from_addr, nonce, tx_type, norm_payload)
        existing = _TX_BY_HASH.get(tx_hash) or _TX_BY_ID.get(tx_id)
        if existing:
            _TX_BY_KEY[key] = existing
            return existing

        rec = DevTxRecord(
            tx_id=tx_id,
            tx_hash=tx_hash,
            from_addr=from_addr,
            nonce=int(nonce),
            tx_type=tx_type,
            payload=norm_payload,
            applied=bool(applied),
            result=result or {},
            created_at_ms=int(created_at_ms) if created_at_ms is not None else _now_ms(),
            block_height=0,  # filled by block append
            tx_index=0,      # filled by block append
            fee=fee,
            accounts_touched=list(accounts_touched or []),
        )

        _TXS.append(rec)
        _TX_BY_ID[tx_id] = rec
        _TX_BY_HASH[tx_hash] = rec
        _TX_BY_KEY[key] = rec

        _append_block_with_single_tx_locked(rec, header=hdr)
        return rec


def list_blocks(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    with _LOCK:
        items = _BLOCKS[::-1]  # newest first
        slice_ = items[offset : offset + limit]
        return [b.to_dict() for b in slice_]


def get_block(height: int) -> Optional[Dict[str, Any]]:
    with _LOCK:
        if height <= 0 or height > len(_BLOCKS):
            return None
        return _BLOCKS[height - 1].to_dict()


def get_tx(tx_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        rec = _TX_BY_ID.get(tx_id)
        return rec.to_dict() if rec else None


def list_txs(
    *,
    address: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    address filter matches:
      - from_addr
      - payload.to (when present)
    """
    with _LOCK:
        items = _TXS[::-1]  # newest first

        if address:
            addr = address

            def _match(r: DevTxRecord) -> bool:
                if r.from_addr == addr:
                    return True
                to = (r.payload or {}).get("to")
                return isinstance(to, str) and to == addr

            items = [r for r in items if _match(r)]

        slice_ = items[offset : offset + limit]
        return [r.to_dict() for r in slice_]
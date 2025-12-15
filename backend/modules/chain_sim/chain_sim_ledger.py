# backend/modules/chain_sim/chain_sim_ledger.py

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
import hashlib
import json
import time
from dataclasses import dataclass, asdict, field
import threading
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root

_CHAIN_SIM_DB_PATH = os.getenv("CHAIN_SIM_DB_PATH", "").strip()
_CHAIN_SIM_PERSIST = (os.getenv("CHAIN_SIM_PERSIST", "1").strip() not in ("0", "false", "off", ""))

_DB_LOCK = threading.Lock()
_DB_CONN: Optional[sqlite3.Connection] = None

def _db_path() -> Optional[Path]:
    if not _CHAIN_SIM_PERSIST:
        return None
    if _CHAIN_SIM_DB_PATH:
        return Path(_CHAIN_SIM_DB_PATH)
    # default: backend/data/chain_sim.sqlite3
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "chain_sim.sqlite3"

def _db() -> Optional[sqlite3.Connection]:
    global _DB_CONN
    p = _db_path()
    if p is None:
        return None

    with _DB_LOCK:
        if _DB_CONN is not None:
            return _DB_CONN

        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _DB_CONN = conn
        _db_init(conn)
        return conn

def _db_init(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA user_version;")
    v = int(cur.fetchone()[0] or 0)

    if v < 1:
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blocks (
          height INTEGER PRIMARY KEY,
          created_at_ms INTEGER NOT NULL,
          header_json TEXT NOT NULL,
          state_root TEXT,
          txs_root TEXT
        );

        CREATE TABLE IF NOT EXISTS txs (
          tx_id TEXT PRIMARY KEY,
          tx_hash TEXT NOT NULL,
          block_height INTEGER NOT NULL,
          tx_index INTEGER NOT NULL,
          from_addr TEXT NOT NULL,
          nonce INTEGER NOT NULL,
          tx_type TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          applied INTEGER NOT NULL,
          result_json TEXT NOT NULL,
          fee_json TEXT,
          FOREIGN KEY(block_height) REFERENCES blocks(height) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_txs_block ON txs(block_height, tx_index);
        CREATE INDEX IF NOT EXISTS idx_txs_from ON txs(from_addr);
        CREATE INDEX IF NOT EXISTS idx_txs_hash ON txs(tx_hash);

        PRAGMA user_version=1;
        """)
        conn.commit()

def persist_clear_all() -> None:
    conn = _db()
    if conn is None:
        return
    with _DB_LOCK:
        cur = conn.cursor()
        cur.executescript("""
        DELETE FROM txs;
        DELETE FROM blocks;
        DELETE FROM meta;
        """)
        conn.commit()

def persist_set_genesis_state(state_obj: Dict[str, Any]) -> None:
    """
    Persist genesis snapshot as JSON (config+bank+staking).
    Replay imports this, then reapplies txs from DB.
    """
    conn = _db()
    if conn is None:
        return
    payload = json.dumps(state_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("genesis_state_json", payload))
        conn.commit()

def persist_begin_block(height: int, created_at_ms: int, header: Dict[str, Any]) -> None:
    conn = _db()
    if conn is None:
        return
    header_json = json.dumps(header or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO blocks(height, created_at_ms, header_json, state_root, txs_root) VALUES(?,?,?,?,?)",
            (int(height), int(created_at_ms), header_json, None, None),
        )
        conn.commit()

def persist_commit_block(height: int, header_patch: Dict[str, Any]) -> None:
    """
    Update block header commitments (state_root/txs_root) and header_json merge is optional.
    """
    conn = _db()
    if conn is None:
        return

    state_root = (header_patch or {}).get("state_root")
    txs_root = (header_patch or {}).get("txs_root")

    with _DB_LOCK:
        cur = conn.cursor()

        # best-effort merge header_json
        cur.execute("SELECT header_json FROM blocks WHERE height=?", (int(height),))
        row = cur.fetchone()
        header = {}
        if row and row["header_json"]:
            try:
                header = json.loads(row["header_json"]) or {}
            except Exception:
                header = {}
        header.update(header_patch or {})
        header_json = json.dumps(header, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

        cur.execute(
            "UPDATE blocks SET header_json=?, state_root=?, txs_root=? WHERE height=?",
            (header_json, state_root, txs_root, int(height)),
        )
        conn.commit()

def persist_tx_row(tx: Dict[str, Any]) -> None:
    conn = _db()
    if conn is None:
        return

    fee = tx.get("fee")
    fee_json = None
    if isinstance(fee, dict):
        fee_json = json.dumps(fee, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    payload_json = json.dumps(tx.get("payload") or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    result_json = json.dumps(tx.get("result") or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO txs(
              tx_id, tx_hash, block_height, tx_index,
              from_addr, nonce, tx_type, payload_json,
              applied, result_json, fee_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(tx["tx_id"]),
                str(tx["tx_hash"]),
                int(tx["block_height"]),
                int(tx["tx_index"]),
                str(tx["from_addr"]),
                int(tx["nonce"]),
                str(tx["tx_type"]),
                payload_json,
                1 if bool(tx.get("applied")) else 0,
                result_json,
                fee_json,
            ),
        )
        conn.commit()

def load_genesis_state_json() -> Optional[Dict[str, Any]]:
    conn = _db()
    if conn is None:
        return None
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key=?", ("genesis_state_json",))
        row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        return None


def load_all_txs() -> List[Dict[str, Any]]:
    conn = _db()
    if conn is None:
        return []
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT * FROM txs ORDER BY block_height ASC, tx_index ASC")
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "tx_id": r["tx_id"],
                "tx_hash": r["tx_hash"],
                "block_height": int(r["block_height"]),
                "tx_index": int(r["tx_index"]),
                "from_addr": r["from_addr"],
                "nonce": int(r["nonce"]),
                "tx_type": r["tx_type"],
                "payload": json.loads(r["payload_json"] or "{}"),
            }
        )
    return out

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

    fee: Optional[Dict[str, Any]] = None
    accounts_touched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevBlock:
    height: int
    created_at_ms: int
    txs: List[DevTxRecord]
    txs_root: str

    header: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        hdr = dict(self.header or {})
        hdr.setdefault("txs_root", self.txs_root)

        return {
            "height": self.height,
            "created_at_ms": self.created_at_ms,
            "txs_root": self.txs_root,  # back-compat
            "header": hdr,
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
_TX_BY_KEY: Dict[Tuple[str, int, str], DevTxRecord] = {}  # (from_addr, nonce, tx_type)


# ───────────────────────────────────────────────
# Ledger batching (open block)
# ───────────────────────────────────────────────

_OPEN_BLOCK: Optional[DevBlock] = None


def _merge_header(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    if not isinstance(dst, dict) or not isinstance(src, dict):
        return
    for k, v in src.items():
        if v is None:
            continue
        dst[str(k)] = v


def _next_height_locked() -> int:
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


def _compute_txs_root_hex(tx_hashes: List[str]) -> str:
    leaves: List[bytes] = []
    for h in tx_hashes:
        try:
            raw = bytes.fromhex(str(h))
        except Exception:
            raw = str(h).encode("utf-8")
        leaves.append(hash_leaf(raw))
    return merkle_root(leaves).hex()


def abort_open_block() -> None:
    """
    Abort the currently open block.
    If an empty shell block was appended, remove it.
    """
    global _OPEN_BLOCK
    with _LOCK:
        if _OPEN_BLOCK is not None:
            if _BLOCKS and _BLOCKS[-1] is _OPEN_BLOCK and not (_OPEN_BLOCK.txs or []):
                _BLOCKS.pop()
        _OPEN_BLOCK = None


def begin_block(*, created_at_ms: Optional[int] = None) -> int:
    """
    Start a batched block. Pre-creates a shell block so height is reserved.
    record_applied_tx() will append into it.
    """
    global _OPEN_BLOCK
    with _LOCK:
        if _OPEN_BLOCK is not None:
            abort_open_block()

        h = _next_height_locked()
        cam = int(created_at_ms) if created_at_ms is not None else _now_ms()

        blk = DevBlock(
            height=h,
            created_at_ms=cam,
            txs=[],
            txs_root="",
            header={},
        )
        _BLOCKS.append(blk)
        _OPEN_BLOCK = blk

        # ✅ persist the shell block reservation
        try:
            persist_begin_block(h, cam, header={})
        except Exception:
            pass

        return h


def commit_block(*, header_patch: Optional[Dict[str, Any]] = None) -> Optional[DevBlock]:
    """
    Finalize the open block:
      - if no txs were appended -> remove shell block and return None
      - else compute txs_root and merge header_patch
      - persist header commitments (state_root / txs_root) for replay
    """
    global _OPEN_BLOCK
    with _LOCK:
        blk = _OPEN_BLOCK
        if blk is None:
            return None

        if not blk.txs:
            if _BLOCKS and _BLOCKS[-1] is blk:
                _BLOCKS.pop()
            _OPEN_BLOCK = None
            # (optional) we don't persist empty blocks; DB row is harmless if it exists
            return None

        txs_root = _compute_txs_root_hex([t.tx_hash for t in blk.txs])
        blk.txs_root = txs_root
        if blk.header is None:
            blk.header = {}
        blk.header["txs_root"] = txs_root

        if isinstance(header_patch, dict):
            _merge_header(blk.header, header_patch)
            # keep struct consistent if caller patched txs_root explicitly
            if blk.header.get("txs_root"):
                blk.txs_root = str(blk.header["txs_root"])

        for i, t in enumerate(blk.txs):
            t.block_height = blk.height
            t.tx_index = i

        # ✅ persist committed header (include computed txs_root even if caller didn't pass it)
        try:
            patch = dict(header_patch or {})
            patch.setdefault("txs_root", blk.txs_root)
            persist_commit_block(blk.height, patch)
        except Exception:
            pass

        _OPEN_BLOCK = None
        return blk


def reset_ledger() -> None:
    global _OPEN_BLOCK
    with _LOCK:
        _BLOCKS.clear()
        _TXS.clear()
        _TX_BY_ID.clear()
        _TX_BY_HASH.clear()
        _TX_BY_KEY.clear()
        _OPEN_BLOCK = None

    # ✅ best-effort persistence wipe (outside _LOCK to avoid lock-order issues)
    try:
        persist_clear_all()
    except Exception:
        pass

def _append_block_with_single_tx_locked(
    tx: DevTxRecord,
    *,
    header: Optional[Dict[str, Any]] = None,
) -> DevBlock:
    """
    Legacy rule: 1 applied tx == 1 block (when batching not active).
    Caller must hold _LOCK.
    """
    h = _next_height_locked()
    tx.block_height = h
    tx.tx_index = 0

    txs_root = _compute_txs_root_hex([tx.tx_hash])

    hdr = dict(header or {})
    hdr.setdefault("txs_root", txs_root)

    blk = DevBlock(
        height=h,
        created_at_ms=int(tx.created_at_ms or _now_ms()),
        txs=[tx],
        txs_root=txs_root,
        header=hdr,
    )
    _BLOCKS.append(blk)
    return blk


def patch_block_header(height: int, header_patch: Dict[str, Any]) -> None:
    """
    Update an existing block's header in-place (merge semantics).
    Safe if called multiple times.

    Rules:
      - shallow-merge keys into block.header
      - if "txs_root" is patched, keep DevBlock.txs_root consistent too
      - ignore None values
    """
    if not isinstance(header_patch, dict):
        raise ValueError("header_patch must be a dict")

    with _LOCK:
        if height <= 0 or height > len(_BLOCKS):
            raise ValueError(f"block not found: height={height}")

        blk = _BLOCKS[height - 1]
        if blk.header is None:
            blk.header = {}

        for k, v in header_patch.items():
            if v is None:
                continue
            if k == "txs_root":
                blk.txs_root = str(v)
                blk.header["txs_root"] = str(v)
            else:
                blk.header[str(k)] = v


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
    block_header: Optional[Dict[str, Any]] = None,
) -> DevTxRecord:
    norm_payload = _normalize_payload(payload)
    key = (from_addr, int(nonce), tx_type)

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
        existing = _TX_BY_KEY.get(key)
        if existing:
            return existing

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
            block_height=0,
            tx_index=0,
            fee=fee,
            accounts_touched=list(accounts_touched or []),
        )

        _TXS.append(rec)
        _TX_BY_ID[tx_id] = rec
        _TX_BY_HASH[tx_hash] = rec
        _TX_BY_KEY[key] = rec

        global _OPEN_BLOCK
        if _OPEN_BLOCK is not None:
            if _OPEN_BLOCK.header is None:
                _OPEN_BLOCK.header = {}
            _merge_header(_OPEN_BLOCK.header, hdr)

            rec.block_height = _OPEN_BLOCK.height
            rec.tx_index = len(_OPEN_BLOCK.txs)
            _OPEN_BLOCK.txs.append(rec)

            # ✅ persist tx row now that block_height/tx_index are known
            try:
                persist_tx_row(
                    {
                        "tx_id": rec.tx_id,
                        "tx_hash": rec.tx_hash,
                        "block_height": rec.block_height,
                        "tx_index": rec.tx_index,
                        "from_addr": from_addr,
                        "nonce": int(nonce),
                        "tx_type": tx_type,
                        "payload": norm_payload,  # normalized
                        "applied": True,
                        "result": result or {},
                        "fee": fee,
                    }
                )
            except Exception:
                pass

            return rec

        # legacy behavior (1 tx == 1 block)
        _append_block_with_single_tx_locked(rec, header=hdr)

        # ✅ persist tx row now that block_height/tx_index are known
        try:
            persist_tx_row(
                {
                    "tx_id": rec.tx_id,
                    "tx_hash": rec.tx_hash,
                    "block_height": rec.block_height,
                    "tx_index": rec.tx_index,
                    "from_addr": from_addr,
                    "nonce": int(nonce),
                    "tx_type": tx_type,
                    "payload": norm_payload,  # normalized
                    "applied": True,
                    "result": result or {},
                    "fee": fee,
                }
            )
        except Exception:
            pass

        return rec


def list_blocks(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    with _LOCK:
        items = _BLOCKS[::-1]
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
    with _LOCK:
        items = _TXS[::-1]

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


def _compute_txs_root_hex(tx_hashes: List[str]) -> str:
    """
    Commitment over tx hashes using chain_sim_merkle:
      leaf_i = hash_leaf(raw_tx_hash_bytes)
      root = merkle_root([leaf_i...])
    tx_hashes are hex strings (sha256 hexdigest).
    """
    leaves: List[bytes] = []
    for h in tx_hashes:
        try:
            raw = bytes.fromhex(str(h))
        except Exception:
            raw = str(h).encode("utf-8")
        leaves.append(hash_leaf(raw))
    return merkle_root(leaves).hex()


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

    txs_root = _compute_txs_root_hex([tx.tx_hash])

    # Optional cleanup: ensure header contains txs_root too
    hdr = dict(header or {})
    hdr.setdefault("txs_root", txs_root)

    blk = DevBlock(
        height=h,
        # ✅ keep block time aligned with tx time if provided
        created_at_ms=int(tx.created_at_ms or _now_ms()),
        txs=[tx],
        txs_root=txs_root,
        header=hdr,
    )
    _BLOCKS.append(blk)
    return blk

def patch_block_header(height: int, header_patch: Dict[str, Any]) -> None:
    """
    Update a block header in-place (merge semantics).
    - If the block is currently open, patch the open block.
    - Otherwise patch a committed block in _BLOCKS.
    """
    if not isinstance(header_patch, dict):
        raise ValueError("header_patch must be a dict")

    with _LOCK:
        # patch open block if it matches
        if _OPEN_BLOCK is not None and _OPEN_BLOCK.height == height:
            if _OPEN_BLOCK.header is None:
                _OPEN_BLOCK.header = {}
            for k, v in header_patch.items():
                if v is None:
                    continue
                if k == "txs_root":
                    _OPEN_BLOCK.txs_root = str(v)
                    _OPEN_BLOCK.header["txs_root"] = str(v)
                else:
                    _OPEN_BLOCK.header[str(k)] = v
            return

        # otherwise patch committed blocks
        if height <= 0 or height > len(_BLOCKS):
            raise ValueError(f"block not found: height={height}")

        blk = _BLOCKS[height - 1]
        if blk.header is None:
            blk.header = {}

        for k, v in header_patch.items():
            if v is None:
                continue
            if k == "txs_root":
                blk.txs_root = str(v)
                blk.header["txs_root"] = str(v)
            else:
                blk.header[str(k)] = v

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
    block_header: Optional[Dict[str, Any]] = None,
) -> DevTxRecord:
    norm_payload = _normalize_payload(payload)
    key = (from_addr, int(nonce), tx_type)

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
        existing = _TX_BY_KEY.get(key)
        if existing:
            return existing

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
            block_height=0,
            tx_index=0,
            fee=fee,
            accounts_touched=list(accounts_touched or []),
        )

        _TXS.append(rec)
        _TX_BY_ID[tx_id] = rec
        _TX_BY_HASH[tx_hash] = rec
        _TX_BY_KEY[key] = rec

        # If a block is open (worker batching), append into it.
        global _OPEN_BLOCK
        if _OPEN_BLOCK is not None:
            if _OPEN_BLOCK.header is None:
                _OPEN_BLOCK.header = {}
            _merge_header(_OPEN_BLOCK.header, hdr)

            rec.block_height = _OPEN_BLOCK.height
            rec.tx_index = len(_OPEN_BLOCK.txs)
            _OPEN_BLOCK.txs.append(rec)
            return rec

        # Otherwise: legacy behavior (1 tx == 1 block)
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
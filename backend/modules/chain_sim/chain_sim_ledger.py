# backend/modules/chain_sim/chain_sim_ledger.py

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple, Literal
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root

# ───────────────────────────────────────────────
# Persistence env (DO NOT freeze at import-time)
# ───────────────────────────────────────────────

def _refresh_persist_env() -> None:
    """
    Tests (and some dev setups) mutate env vars after import.
    Do NOT freeze CHAIN_SIM_DB_PATH / CHAIN_SIM_PERSIST at import-time.
    """
    global _CHAIN_SIM_DB_PATH, _CHAIN_SIM_PERSIST
    _CHAIN_SIM_DB_PATH = os.getenv("CHAIN_SIM_DB_PATH", "").strip()
    _CHAIN_SIM_PERSIST = (
        os.getenv("CHAIN_SIM_PERSIST", "1").strip().lower()
        not in ("0", "false", "off", "")
    )


# defaults (may be overridden by _refresh_persist_env() at runtime)
_CHAIN_SIM_DB_PATH = os.getenv("CHAIN_SIM_DB_PATH", "").strip()
_CHAIN_SIM_PERSIST = (
    os.getenv("CHAIN_SIM_PERSIST", "1").strip().lower()
    not in ("0", "false", "off", "")
)

_DB_LOCK = threading.Lock()
_DB_CONN: Optional[sqlite3.Connection] = None
_DB_CONN_PATH: Optional[str] = None

def _db_path() -> Optional[Path]:
    _refresh_persist_env()

    if not _CHAIN_SIM_PERSIST:
        return None
    if _CHAIN_SIM_DB_PATH:
        return Path(_CHAIN_SIM_DB_PATH)

    # default: repo-root/data/chain_sim.sqlite3
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "chain_sim.sqlite3"

def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")

def _db() -> Optional[sqlite3.Connection]:
    global _DB_CONN, _DB_CONN_PATH
    p = _db_path()
    if p is None:
        return None

    with _DB_LOCK:
        # if env changed DB path, close old conn and reopen
        if _DB_CONN is not None and _DB_CONN_PATH and str(p) != _DB_CONN_PATH:
            try:
                _DB_CONN.close()
            except Exception:
                pass
            _DB_CONN = None
            _DB_CONN_PATH = None

        if _DB_CONN is not None:
            return _DB_CONN

        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _DB_CONN = conn
        _DB_CONN_PATH = str(p)
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
        cur.executescript(
            """
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
            """
        )
        conn.commit()

# --- meta helpers (key/value table) ---

def persist_meta_set_json(key: str, obj: Any) -> None:
    con = _db()
    if con is None:
        return

    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    with _DB_LOCK:
        cur = con.cursor()
        # meta exists in _db_init, but keep this harmless guard
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            INSERT INTO meta(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (str(key), payload),
        )
        con.commit()

def persist_meta_get_json(key: str) -> Optional[Any]:
    con = _db()
    if con is None:
        return None

    with _DB_LOCK:
        cur = con.cursor()
        try:
            cur.execute("SELECT value FROM meta WHERE key = ?", (str(key),))
        except Exception:
            return None
        row = cur.fetchone()

    if not row:
        return None

    raw = row["value"] if isinstance(row, sqlite3.Row) else row[0]
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None

def persist_list_applied_txs_for_block(height: int) -> List[Dict[str, Any]]:
    """
    Returns applied tx hashes for a given block height in deterministic order.

    Ordering is stable:
      ORDER BY tx_index ASC, tx_id ASC

    Used by REPLAY_STRICT to recompute txs_root.
    Safe no-op if persistence is disabled.
    """
    conn = _db()
    if conn is None:
        return []

    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tx_hash, tx_index, tx_id
            FROM txs
            WHERE block_height = ? AND applied = 1
            ORDER BY tx_index ASC, tx_id ASC
            """,
            (int(height),),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        # r is sqlite3.Row (row_factory set in _db())
        tx_hash = r["tx_hash"] if isinstance(r, sqlite3.Row) else r[0]
        tx_index = r["tx_index"] if isinstance(r, sqlite3.Row) else r[1]
        out.append({"tx_hash": str(tx_hash), "tx_index": int(tx_index or 0)})
    return out


def persist_patch_block_roots_and_txs(
    height: int, *, state_root: Optional[str], txs_root: Optional[str]
) -> None:
    """
    Patch txs.result_json for all applied txs in a block with committed roots.

    NOTE: This does NOT write the replay checkpoint.
    Checkpointing is centralized in persist_commit_block().
    """
    con = _db()
    if con is None:
        return

    h = int(height)
    st = str(state_root or "")
    tr = str(txs_root or "")
    if not st and not tr:
        return

    with _DB_LOCK:
        cur = con.cursor()
        try:
            cur.execute(
                """
                SELECT tx_id, result_json
                FROM txs
                WHERE block_height = ? AND applied = 1
                ORDER BY tx_index ASC, tx_id ASC
                """,
                (h,),
            )
            rows = cur.fetchall()

            for row in rows:
                tx_id = row["tx_id"] if isinstance(row, sqlite3.Row) else row[0]
                result_json = row["result_json"] if isinstance(row, sqlite3.Row) else row[1]

                try:
                    rec = json.loads(result_json) if result_json else {}
                except Exception:
                    rec = {}
                if not isinstance(rec, dict):
                    rec = {}

                if st:
                    rec["state_root"] = st
                    rec["state_root_committed"] = True
                if tr:
                    rec["txs_root"] = tr

                cur.execute(
                    "UPDATE txs SET result_json=? WHERE tx_id=?",
                    (
                        json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                        str(tx_id),
                    ),
                )

            con.commit()
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise

# --- checkpoint helpers (meta table) ---
_CHECKPOINT_KEY = "checkpoint_json"

def persist_set_checkpoint(last_height: int, last_state_root: str, last_txs_root: str) -> None:
    """
    Best-effort: store latest committed block checkpoint into meta.
    Uses the same meta JSON helpers as genesis.
    """
    try:
        ck = {
            "last_height": int(last_height or 0),
            "last_state_root": str(last_state_root or ""),
            "last_txs_root": str(last_txs_root or ""),
            "updated_at_ms": int(time.time() * 1000),
        }
        persist_meta_set_json(_CHECKPOINT_KEY, ck)
    except Exception:
        # best-effort by design
        return

def persist_get_checkpoint() -> Optional[Dict[str, Any]]:
    try:
        ck = persist_meta_get_json(_CHECKPOINT_KEY)
        return ck if isinstance(ck, dict) else None
    except Exception:
        return None

def replay_ledger_only_from_db() -> bool:
    """
    Rebuild ONLY the in-memory ledger (_BLOCKS/_TXS) from sqlite.
    Does NOT apply tx execution / state transitions.
    Used as a fallback when genesis_state_json is missing.
    """
    conn = _db()
    if conn is None:
        return False

    # reset in-memory ledger, keep sqlite
    reset_ledger(clear_persist=False)

    # pull blocks + txs
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT * FROM blocks ORDER BY height ASC")
        block_rows = cur.fetchall()

        cur.execute(
            """
            SELECT *
            FROM txs
            ORDER BY block_height ASC, tx_index ASC, tx_id ASC
            """
        )
        tx_rows = cur.fetchall()

    # group txs by height
    txs_by_h: Dict[int, List[sqlite3.Row]] = {}
    for r in tx_rows:
        bh = int((r["block_height"] if isinstance(r, sqlite3.Row) else r[2]) or 0)
        if bh <= 0:
            continue
        txs_by_h.setdefault(bh, []).append(r)

    with _LOCK:
        for br in block_rows:
            h = int(br["height"] if isinstance(br, sqlite3.Row) else br[0])
            created_at_ms = int(br["created_at_ms"] if isinstance(br, sqlite3.Row) else br[1])
            raw_hdr = (br["header_json"] if isinstance(br, sqlite3.Row) else br[2]) or "{}"
            try:
                header = json.loads(raw_hdr) if isinstance(raw_hdr, str) else {}
            except Exception:
                header = {}
            if not isinstance(header, dict):
                header = {}

            state_root = str((br["state_root"] if isinstance(br, sqlite3.Row) else br[3]) or "")
            txs_root   = str((br["txs_root"]   if isinstance(br, sqlite3.Row) else br[4]) or "")

            tx_recs: List[DevTxRecord] = []
            for tr in txs_by_h.get(h, []):
                tx_id = str((tr["tx_id"] if isinstance(tr, sqlite3.Row) else tr[0]) or "")
                tx_hash = str((tr["tx_hash"] if isinstance(tr, sqlite3.Row) else tr[1]) or "")
                from_addr = str((tr["from_addr"] if isinstance(tr, sqlite3.Row) else tr[4]) or "")
                nonce = int((tr["nonce"] if isinstance(tr, sqlite3.Row) else tr[5]) or 0)
                tx_type = str((tr["tx_type"] if isinstance(tr, sqlite3.Row) else tr[6]) or "")
                payload_json = (tr["payload_json"] if isinstance(tr, sqlite3.Row) else tr[7]) or "{}"
                result_json  = (tr["result_json"]  if isinstance(tr, sqlite3.Row) else tr[9]) or "{}"
                fee_json     = (tr["fee_json"]     if isinstance(tr, sqlite3.Row) else tr[10]) or None
                applied_i    = int((tr["applied"]  if isinstance(tr, sqlite3.Row) else tr[8]) or 0)
                tx_index     = int((tr["tx_index"] if isinstance(tr, sqlite3.Row) else tr[3]) or 0)

                try:
                    payload = json.loads(payload_json) if isinstance(payload_json, str) else {}
                except Exception:
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}

                try:
                    result = json.loads(result_json) if isinstance(result_json, str) else {}
                except Exception:
                    result = {}
                if not isinstance(result, dict):
                    result = {}

                fee = None
                if isinstance(fee_json, str) and fee_json:
                    try:
                        fee = json.loads(fee_json)
                    except Exception:
                        fee = None
                if not isinstance(fee, dict):
                    fee = None

                rec = DevTxRecord(
                    tx_id=tx_id,
                    tx_hash=tx_hash,
                    from_addr=from_addr,
                    nonce=nonce,
                    tx_type=tx_type,
                    payload=payload,
                    applied=bool(applied_i),
                    result=result,
                    created_at_ms=created_at_ms,
                    block_height=h,
                    tx_index=tx_index,
                    fee=fee,
                )

                _TXS.append(rec)
                _TX_BY_ID[rec.tx_id] = rec
                if rec.tx_hash:
                    _TX_BY_HASH[rec.tx_hash] = rec
                _TX_BY_KEY[(rec.from_addr, int(rec.nonce), rec.tx_type)] = rec
                tx_recs.append(rec)

            blk = DevBlock(
                height=h,
                created_at_ms=created_at_ms,
                txs=tx_recs,
                txs_root=txs_root or (header.get("txs_root") or ""),
                header=header,
            )
            if state_root:
                blk.header.setdefault("state_root", state_root)
            if blk.txs_root:
                blk.header.setdefault("txs_root", blk.txs_root)

            _BLOCKS.append(blk)

    return True

def replay_strict_verify_or_raise() -> None:
    """
    Loud-mode verification:
      - checkpoint exists
      - checkpoint last_height matches a blocks row
      - checkpoint roots match the persisted block roots
      - persisted block txs_root matches recomputed txs_root from applied tx hashes
    """
    cp = persist_get_checkpoint()
    if not isinstance(cp, dict):
        raise RuntimeError("REPLAY_STRICT: missing checkpoint")

    try:
        h = int(cp.get("last_height") or 0)
        cp_st = str(cp.get("last_state_root") or "")
        cp_tr = str(cp.get("last_txs_root") or "")
    except Exception:
        raise RuntimeError("REPLAY_STRICT: invalid checkpoint payload")

    if h <= 0:
        raise RuntimeError(f"REPLAY_STRICT: invalid checkpoint height={h}")

    con = _db()
    if con is None:
        raise RuntimeError("REPLAY_STRICT: persistence disabled (no db)")

    # Load block roots for last_height
    with _DB_LOCK:
        cur = con.cursor()
        cur.execute("SELECT state_root, txs_root FROM blocks WHERE height=?", (h,))
        row = cur.fetchone()

    if not row:
        raise RuntimeError(f"REPLAY_STRICT: checkpoint height {h} not found in blocks")

    db_st = str((row["state_root"] if isinstance(row, sqlite3.Row) else row[0]) or "")
    db_tr = str((row["txs_root"] if isinstance(row, sqlite3.Row) else row[1]) or "")

    # Checkpoint must match block row (this catches your tamper test)
    if cp_st != db_st:
        raise RuntimeError(
            f"REPLAY_STRICT: checkpoint state_root mismatch at height {h}"
        )
    if cp_tr != db_tr:
        raise RuntimeError(
            f"REPLAY_STRICT: checkpoint txs_root mismatch at height {h}"
        )

    # Recompute txs_root from applied tx hashes and ensure the block row matches too
    applied = persist_list_applied_txs_for_block(h)
    recomputed_tr = _compute_txs_root_hex([t["tx_hash"] for t in applied])

    if recomputed_tr != db_tr:
        raise RuntimeError(
            f"REPLAY_STRICT: block txs_root mismatch vs recomputed at height {h}"
        )

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

def _persist_db_path() -> str:
    return os.getenv("CHAIN_SIM_DB_PATH", "") or ""

def persist_get_genesis_state() -> Optional[Dict[str, Any]]:
    """
    Best-effort loader for whatever table persist_set_genesis_state() writes.
    Tries a few common table/column names to avoid schema coupling.
    """
    db_path = _persist_db_path()
    if not db_path:
        return None

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()

        # Find candidate tables containing 'genesis'
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%genesis%';")
        tables = [r[0] for r in cur.fetchall() if r and r[0]]

        # Common fallbacks if table name doesn't include genesis
        tables += ["genesis", "genesis_state", "chain_sim_genesis", "chain_sim_genesis_state"]

        tried = set()
        for t in tables:
            if t in tried:
                continue
            tried.add(t)

            try:
                cur.execute(f"PRAGMA table_info({t});")
                cols = [r[1] for r in cur.fetchall() if r and len(r) > 1]
            except Exception:
                continue

            # pick likely json column
            for col in ("state_json", "genesis_json", "json", "state", "genesis"):
                if col in cols:
                    try:
                        cur.execute(f"SELECT {col} FROM {t} ORDER BY rowid DESC LIMIT 1;")
                        row = cur.fetchone()
                        if not row or row[0] is None:
                            continue
                        val = row[0]
                        if isinstance(val, (bytes, bytearray)):
                            val = val.decode("utf-8")
                        obj = json.loads(val) if isinstance(val, str) else None
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        continue

        return None
    finally:
        con.close()

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

def persist_commit_block(height: int, header_patch: Optional[Dict[str, Any]] = None) -> None:
    """
    Commit an open block:
      - merge header_patch into header_json
      - write state_root/txs_root onto blocks row
      - patch tx rows for this height (INLINE; avoids _DB_LOCK re-entry deadlock)
      - con.commit()
      - AFTER releasing _DB_LOCK, best-effort persist_set_checkpoint(...)
    """
    h = int(height or 0)
    if h <= 0:
        return

    con = _db()  # cached global connection
    if con is None:
        return

    hp = header_patch or {}

    # capture for checkpoint write AFTER db lock is released
    ck_height = 0
    ck_state_root = ""
    ck_txs_root = ""

    with _DB_LOCK:
        cur = con.cursor()
        try:
            # --- load existing header_json ---
            cur.execute("SELECT header_json FROM blocks WHERE height=?", (h,))
            row = cur.fetchone()

            prev: Dict[str, Any] = {}
            if row:
                raw = row["header_json"] if isinstance(row, sqlite3.Row) else row[0]
                if raw:
                    try:
                        obj = json.loads(raw) if isinstance(raw, str) else (raw or {})
                        prev = obj if isinstance(obj, dict) else {}
                    except Exception:
                        prev = {}

            merged = dict(prev)
            if isinstance(hp, dict):
                merged.update(hp)

            # roots (prefer explicit patch keys)
            state_root = str(merged.get("state_root") or hp.get("state_root") or "")
            txs_root   = str(merged.get("txs_root")   or hp.get("txs_root")   or "")

            # --- write block header_json ---
            cur.execute(
                "UPDATE blocks SET header_json=? WHERE height=?",
                (json.dumps(merged, sort_keys=True, separators=(",", ":"), ensure_ascii=False), h),
            )

            # keep dedicated columns in sync (these cols exist per _db_init)
            cur.execute(
                "UPDATE blocks SET state_root=?, txs_root=? WHERE height=?",
                (state_root or None, txs_root or None, h),
            )

            # --- patch tx rows centrally (INLINE; do NOT call helper that grabs _DB_LOCK again) ---
            if state_root or txs_root:
                cur.execute(
                    """
                    SELECT tx_id, result_json
                    FROM txs
                    WHERE block_height = ? AND applied = 1
                    ORDER BY tx_index ASC, tx_id ASC
                    """,
                    (h,),
                )
                rows = cur.fetchall()

                for r in rows:
                    tx_id = r["tx_id"] if isinstance(r, sqlite3.Row) else r[0]
                    result_json = r["result_json"] if isinstance(r, sqlite3.Row) else r[1]

                    try:
                        rec = json.loads(result_json) if result_json else {}
                    except Exception:
                        rec = {}
                    if not isinstance(rec, dict):
                        rec = {}

                    if state_root:
                        rec["state_root"] = state_root
                        rec["state_root_committed"] = True
                    if txs_root:
                        rec["txs_root"] = txs_root

                    cur.execute(
                        "UPDATE txs SET result_json=? WHERE tx_id=?",
                        (
                            json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                            str(tx_id),
                        ),
                    )

            con.commit()

            # checkpoint payload to write OUTSIDE lock
            if state_root and txs_root:
                ck_height = h
                ck_state_root = state_root
                ck_txs_root = txs_root

        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise

    # AFTER releasing _DB_LOCK (best-effort; never break startup on this)
    if ck_height > 0 and ck_state_root and ck_txs_root:
        try:
            persist_set_checkpoint(ck_height, ck_state_root, ck_txs_root)
        except Exception:
            pass

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

# --- SQLite loaders + replay ---------------------------------

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


def load_all_blocks() -> List[Dict[str, Any]]:
    conn = _db()
    if conn is None:
        return []
    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT * FROM blocks ORDER BY height ASC")
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        header = {}
        try:
            header = json.loads(r["header_json"] or "{}") or {}
        except Exception:
            header = {}
        out.append(
            {
                "height": int(r["height"]),
                "created_at_ms": int(r["created_at_ms"]),
                "header": header,
                "state_root": r["state_root"],
                "txs_root": r["txs_root"],
            }
        )
    return out


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
        payload = {}
        try:
            payload = json.loads(r["payload_json"] or "{}") or {}
        except Exception:
            payload = {}
        out.append(
            {
                "tx_id": r["tx_id"],
                "tx_hash": r["tx_hash"],
                "block_height": int(r["block_height"]),
                "tx_index": int(r["tx_index"]),
                "from_addr": r["from_addr"],
                "nonce": int(r["nonce"]),
                "tx_type": r["tx_type"],
                "payload": payload,
                "applied": bool(int(r["applied"])),
            }
        )
    return out


def replay_state_from_db() -> bool:
    """
    Rebuild in-memory state + in-memory ledger deterministically from SQLite:
      1) load genesis snapshot from meta.genesis_state_json
      2) reset bank+staking+config and ledger (WITHOUT wiping sqlite)
      3) restore genesis (config/bank/staking) best-effort
      4) replay txs in (block_height, tx_index) order, rebuilding blocks/txs
    """
    genesis = load_genesis_state_json()
    if not isinstance(genesis, dict):
        # PR4.2: allow “ledger-only” replay so get_block(h) works after import
        return replay_ledger_only_from_db()

    # local imports to avoid import cycles
    from backend.modules.chain_sim import chain_sim_config as cfg
    from backend.modules.chain_sim import chain_sim_model as bank
    from backend.modules.staking import staking_model as staking
    from backend.modules.chain_sim import chain_sim_engine as engine
    from backend.modules.chain_sim.tx_executor import apply_tx_receipt as apply_tx_executor

    # reset in-memory state
    cfg.reset_config()
    try:
        staking.reset_state()
    except Exception:
        pass
    if hasattr(bank, "reset_state") and callable(getattr(bank, "reset_state")):
        bank.reset_state()

    # IMPORTANT: do NOT wipe sqlite during replay
    reset_ledger(clear_persist=False)

    try:
        reset_ledger(clear_persist=False)  # preferred (if you added this arg)
    except TypeError:
        # fallback if reset_ledger() has no args
        global _OPEN_BLOCK
        with _LOCK:
            _BLOCKS.clear()
            _TXS.clear()
            _TX_BY_ID.clear()
            _TX_BY_HASH.clear()
            _TX_BY_KEY.clear()
            _OPEN_BLOCK = None

    # restore config
    cfg_in = genesis.get("config") or {}
    try:
        cfg.set_config(chain_id=cfg_in.get("chain_id"), network_id=cfg_in.get("network_id"))
    except Exception:
        pass

    # restore bank+staking snapshot if helpers exist (preferred)
    fn = getattr(engine, "import_chain_state", None)
    if callable(fn):
        try:
            fn(genesis)
            imported = True
        except Exception:
            imported = False
    else:
        imported = False

    # minimal fallback (only what we can safely infer)
    if not imported:
        # try restore validators if present
        try:
            st = genesis.get("staking") or {}
            vals = st.get("validators") or []
            if vals and hasattr(staking, "apply_genesis_validators"):
                staking.apply_genesis_validators(vals)
        except Exception:
            pass

        # try restore accounts if snapshot contains them
        try:
            b = genesis.get("bank") or {}
            accounts = b.get("accounts") or b.get("accounts_by_address") or []
            if isinstance(accounts, dict):
                accounts = [{"address": k, **(v or {})} for k, v in accounts.items()]

            for a in accounts if isinstance(accounts, list) else []:
                addr = a.get("address")
                if not isinstance(addr, str) or not addr:
                    continue
                acc = bank.get_or_create_account(addr)
                bals = a.get("balances") or {}
                if isinstance(bals, dict):
                    setattr(acc, "balances", dict(bals))
                if "nonce" in a:
                    try:
                        setattr(acc, "nonce", int(a["nonce"]))
                    except Exception:
                        pass

            if hasattr(bank, "recompute_supply") and callable(getattr(bank, "recompute_supply")):
                bank.recompute_supply()
        except Exception:
            pass

    # replay txs grouped by block height
    blocks = {b["height"]: b for b in load_all_blocks()}
    txs = load_all_txs()

    class _AttrDict(dict):
        def __getattr__(self, k):
            return self[k]

    cur_h: Optional[int] = None
    for tx in txs:
        h = int(tx["block_height"])

        if cur_h != h:
            if cur_h is not None:
                # commit previous
                try:
                    header_patch = dict(blocks.get(cur_h, {}).get("header") or {})
                    if blocks.get(cur_h, {}).get("state_root"):
                        header_patch["state_root"] = blocks[cur_h]["state_root"]
                    if blocks.get(cur_h, {}).get("txs_root"):
                        header_patch["txs_root"] = blocks[cur_h]["txs_root"]
                    commit_block(header_patch=header_patch)
                except Exception:
                    commit_block()

            # begin next
            bmeta = blocks.get(h) or {}
            begin_block(created_at_ms=bmeta.get("created_at_ms"))
            cur_h = h

        # IMPORTANT: replay must follow the SAME execution path as /dev/submit_tx
        # (apply_tx_executor includes the dev fee behavior; engine.submit_tx may not)
        tx_type = str(tx["tx_type"] or "")
        if tx_type == "BANK_TRANSFER":
            tx_type = "BANK_SEND"

        tx_obj = _AttrDict(
            {
                "from_addr": tx["from_addr"],
                "nonce": int(tx["nonce"]),
                "tx_type": tx_type,
                "payload": tx["payload"],
            }
        )

        receipt = apply_tx_executor(tx_obj)

        # normalize receipt like routes._submit_tx_core
        if not isinstance(receipt, dict):
            receipt = {"ok": True, "result": receipt}
        result = receipt.get("result") or {}

        applied = receipt.get("applied", None)
        if applied is None:
            if isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], bool):
                applied = bool(result[0])
            elif isinstance(result, dict) and "ok" in result:
                applied = bool(result.get("ok"))
            else:
                applied = True
        applied = bool(applied)

        if applied:
            fee = None
            if isinstance(result, dict):
                maybe_fee = result.get("fee")
                fee = maybe_fee if isinstance(maybe_fee, dict) else None

            record_applied_tx(
                from_addr=tx["from_addr"],
                nonce=int(tx["nonce"]),
                tx_type=tx_type,
                payload=tx["payload"],
                applied=True,
                result=result if isinstance(result, dict) else {},
                fee=fee,
            )

    # commit final open block
    if cur_h is not None:
        try:
            header_patch = dict(blocks.get(cur_h, {}).get("header") or {})
            if blocks.get(cur_h, {}).get("state_root"):
                header_patch["state_root"] = blocks[cur_h]["state_root"]
            if blocks.get(cur_h, {}).get("txs_root"):
                header_patch["txs_root"] = blocks[cur_h]["txs_root"]
            commit_block(header_patch=header_patch)
        except Exception:
            commit_block()

    return True

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

_LOCK = RLock()

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
      - patch in-memory tx results so /dev/tx reflects them immediately in the running process

    Note: DB tx-row patching + checkpoint is handled by persist_commit_block().
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
            return None

        # compute txs_root from in-block tx ordering
        txs_root = _compute_txs_root_hex([t.tx_hash for t in blk.txs])
        blk.txs_root = txs_root
        if blk.header is None:
            blk.header = {}
        blk.header["txs_root"] = txs_root

        # merge caller patch (state_root, etc.)
        if isinstance(header_patch, dict):
            _merge_header(blk.header, header_patch)
            if blk.header.get("txs_root"):
                blk.txs_root = str(blk.header["txs_root"])

        # ensure tx indexes are consistent
        for i, t in enumerate(blk.txs):
            t.block_height = blk.height
            t.tx_index = i

        # persist committed header (include computed txs_root even if caller didn't pass it)
        patch = dict(header_patch or {})
        patch.setdefault("txs_root", blk.txs_root)

        try:
            persist_commit_block(blk.height, patch)
        except Exception:
            pass

        # ✅ patch in-memory tx results so /dev/tx/{tx_id} shows roots immediately
        sr = patch.get("state_root")
        tr = patch.get("txs_root")
        if sr or tr:
            for t in blk.txs:
                if not isinstance(t.result, dict) or t.result is None:
                    t.result = {}
                if sr:
                    t.result["state_root"] = str(sr)
                    t.result["state_root_committed"] = True
                if tr:
                    t.result["txs_root"] = str(tr)

        _OPEN_BLOCK = None
        return blk


def reset_ledger(*, clear_persist: bool = True) -> None:
    global _OPEN_BLOCK
    with _LOCK:
        _BLOCKS.clear()
        _TXS.clear()
        _TX_BY_ID.clear()
        _TX_BY_HASH.clear()
        _TX_BY_KEY.clear()
        _OPEN_BLOCK = None

    # ✅ persistence wipe is optional
    if clear_persist:
        try:
            persist_clear_all()
        except Exception:
            pass

def _append_block_with_single_tx_locked(tx: DevTxRecord, *, header: Optional[Dict[str, Any]] = None) -> DevBlock:
    h = _next_height_locked()
    tx.block_height = h
    tx.tx_index = 0

    txs_root = _compute_txs_root_hex([tx.tx_hash])
    hdr = dict(header or {})
    hdr.setdefault("txs_root", txs_root)

    # ✅ persist shell block BEFORE any tx rows reference it
    try:
        persist_begin_block(h, int(tx.created_at_ms or _now_ms()), header=hdr)
    except Exception:
        pass

    blk = DevBlock(
        height=h,
        created_at_ms=int(tx.created_at_ms or _now_ms()),
        txs=[tx],
        txs_root=txs_root,
        header=hdr,
    )
    _BLOCKS.append(blk)

    # ✅ persist commitments now that we know txs_root (and any state_root you patch later)
    try:
        persist_commit_block(h, {"txs_root": txs_root, **hdr})
    except Exception:
        pass

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
                persist_tx_row({
                    "tx_id": rec.tx_id,
                    "tx_hash": rec.tx_hash,
                    "block_height": rec.block_height,
                    "tx_index": rec.tx_index,
                    "from_addr": rec.from_addr,
                    "nonce": rec.nonce,
                    "tx_type": rec.tx_type,
                    "payload": rec.payload,
                    "applied": bool(rec.applied),
                    "result": rec.result or {},
                    "fee": fee,
                })
            except Exception as e:
                # THIS is where your "persist_tx_row failed" print goes
                if os.getenv("CHAIN_SIM_PERSIST_DEBUG", "0") == "1":
                    print("persist_tx_row failed:", repr(e))

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


BlockOrder = Literal["asc", "desc"]

def list_headers(limit: int = 20, offset: int = 0, order: BlockOrder = "desc") -> List[Dict[str, Any]]:
    """
    Headers-only view (no tx bodies).
    Backed directly by the blocks table to keep this lightweight.
    """
    lim = max(1, int(limit))
    off = max(0, int(offset))
    ord_sql = "DESC" if (order or "desc") == "desc" else "ASC"

    with _DB_LOCK:
        con = _db_connect()
        try:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                f"""
                SELECT height, created_at_ms, header_json, state_root, txs_root
                FROM blocks
                ORDER BY height {ord_sql}
                LIMIT ? OFFSET ?
                """,
                (lim, off),
            )
            rows = cur.fetchall()
        finally:
            try:
                con.close()
            except Exception:
                pass

    out: List[Dict[str, Any]] = []
    for r in rows:
        # sqlite3.Row supports dict-style
        raw_hdr = (r["header_json"] or "{}") if isinstance(r, sqlite3.Row) else (r[2] or "{}")
        try:
            hdr = json.loads(raw_hdr) or {}
        except Exception:
            hdr = {}

        out.append(
            {
                "height": int(r["height"] if isinstance(r, sqlite3.Row) else r[0]),
                "created_at_ms": int(r["created_at_ms"] if isinstance(r, sqlite3.Row) else r[1]),
                "header": hdr,
                "state_root": (r["state_root"] if isinstance(r, sqlite3.Row) else r[3]),
                "txs_root": (r["txs_root"] if isinstance(r, sqlite3.Row) else r[4]),
            }
        )
    return out

def list_headers(limit: int = 20, offset: int = 0, order: BlockOrder = "desc") -> List[Dict[str, Any]]:
    """
    Header-only view, sourced from the in-memory blocks list to stay consistent with list_blocks().
    """
    blocks = list_blocks(limit=limit, offset=offset, order=order)

    out: List[Dict[str, Any]] = []
    for b in blocks:
        hdr = b.get("header") or {}
        if not isinstance(hdr, dict):
            hdr = {}

        out.append(
            {
                "height": int(b.get("height") or 0),
                "created_at_ms": b.get("created_at_ms"),
                "state_root": b.get("state_root") or hdr.get("state_root"),
                "txs_root": b.get("txs_root") or hdr.get("txs_root"),
                "header": hdr,
            }
        )

    return out

def list_blocks(limit: int = 20, offset: int = 0, order: BlockOrder = "desc") -> List[Dict[str, Any]]:
    """
    Deterministic ordering:
      - desc (default): newest-first (highest height first)
      - asc: oldest-first
    """
    with _LOCK:
        # _BLOCKS is assumed to be append-increasing by height
        if order == "asc":
            items = _BLOCKS[:]          # oldest-first
        else:
            items = _BLOCKS[::-1]       # newest-first

        slice_ = items[offset : offset + limit]
        return [b.to_dict() for b in slice_]


def get_block(height: int) -> Optional[Dict[str, Any]]:
    h = int(height or 0)
    if h <= 0:
        return None

    with _LOCK:
        # fast path if list happens to be perfectly aligned
        if h <= len(_BLOCKS):
            b = _BLOCKS[h - 1]
            if b and int(getattr(b, "height", 0)) == h:
                return b.to_dict()

        # fallback: search by actual height
        for b in reversed(_BLOCKS):
            if int(getattr(b, "height", 0)) == h:
                return b.to_dict()

    return None


def get_tx(tx_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        rec = _TX_BY_ID.get(tx_id)
        return rec.to_dict() if rec else None

def _json_load_if_str(x: Any) -> Any:
    if isinstance(x, (dict, list)) or x is None:
        return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except Exception:
            return {}
    return {}

def persist_list_applied_txs_ordered(*, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Canonical replay order:
      ORDER BY block_height ASC, tx_index ASC, tx_id ASC

    Returns payload as dict (decoded from payload_json).
    """
    conn = _db()
    if conn is None:
        return []

    with _DB_LOCK:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              tx_id,
              from_addr,
              nonce,
              tx_type,
              payload_json,
              applied,
              block_height,
              tx_index
            FROM txs
            WHERE applied = 1
            ORDER BY block_height ASC, tx_index ASC, tx_id ASC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        )
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        # r is sqlite3.Row (row_factory set in _db())
        payload = {}
        try:
            payload = json.loads(r["payload_json"] or "{}") or {}
        except Exception:
            payload = {}

        out.append(
            {
                "tx_id": str(r["tx_id"]),
                "from_addr": str(r["from_addr"] or ""),
                "nonce": int(r["nonce"] or 0),
                "tx_type": str(r["tx_type"] or ""),
                "payload": payload,
                "applied": bool(int(r["applied"] or 0)),
                "block_height": int(r["block_height"] or 0),
                "tx_index": int(r["tx_index"] or 0),
            }
        )

    return out

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

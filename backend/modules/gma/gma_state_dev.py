# backend/modules/gma/gma_state_dev.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import json
import threading
import time

# Simple dev JSON persistence under repo-root/data/
_DATA_PATH = Path("data") / "gma_dev_events.json"
_LOCK = threading.Lock()
_LOADED = False


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class MintBurnRow:
    kind: Literal["MINT", "BURN"]
    amount_pho: str
    reason: Optional[str]
    created_at_ms: int


@dataclass
class ReserveMoveRow:
    kind: Literal["ADD", "REMOVE"]
    amount_pho_eq: str
    reason: Optional[str]
    created_at_ms: int


_MINT_BURN_LOG: List[MintBurnRow] = []
_RESERVE_MOVES_LOG: List[ReserveMoveRow] = []


def _ensure_loaded() -> None:
    """
    Lazy-load logs from disk once per process.
    """
    global _LOADED, _MINT_BURN_LOG, _RESERVE_MOVES_LOG
    if _LOADED:
        return

    with _LOCK:
        if _LOADED:
            return

        if _DATA_PATH.exists():
            try:
                with _DATA_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
        else:
            data = {}

        mb_raw = data.get("mint_burn_log", []) or []
        rm_raw = data.get("reserve_moves_log", []) or []

        _MINT_BURN_LOG = [
            MintBurnRow(
                kind=row.get("kind", "MINT"),
                amount_pho=str(row.get("amount_pho", "0")),
                reason=row.get("reason"),
                created_at_ms=int(row.get("created_at_ms", _now_ms())),
            )
            for row in mb_raw
        ]

        _RESERVE_MOVES_LOG = [
            ReserveMoveRow(
                kind=row.get("kind", "ADD"),
                amount_pho_eq=str(row.get("amount_pho_eq", "0")),
                reason=row.get("reason"),
                created_at_ms=int(row.get("created_at_ms", _now_ms())),
            )
            for row in rm_raw
        ]

        _LOADED = True


def _save() -> None:
    """
    Persist current in-memory logs to JSON.
    """
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mint_burn_log": [asdict(row) for row in _MINT_BURN_LOG],
        "reserve_moves_log": [asdict(row) for row in _RESERVE_MOVES_LOG],
    }
    with _DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def record_mint_burn(
    *,
    kind: Literal["MINT", "BURN"],
    amount_pho: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append a mint/burn event to the dev log and persist.
    """
    if kind not in ("MINT", "BURN"):
        raise ValueError(f"invalid mint/burn kind: {kind}")

    _ensure_loaded()

    row = MintBurnRow(
        kind=kind,
        amount_pho=str(amount_pho),
        reason=reason,
        created_at_ms=_now_ms(),
    )

    with _LOCK:
        _MINT_BURN_LOG.append(row)
        _save()

    return asdict(row)


def record_reserve_move(
    *,
    kind: Literal["ADD", "REMOVE"],
    amount_pho_eq: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append a reserve move (PHO-equivalent) to the dev log and persist.
    """
    if kind not in ("ADD", "REMOVE"):
        raise ValueError(f"invalid reserve move kind: {kind}")

    _ensure_loaded()

    row = ReserveMoveRow(
        kind=kind,
        amount_pho_eq=str(amount_pho_eq),
        reason=reason,
        created_at_ms=_now_ms(),
    )

    with _LOCK:
        _RESERVE_MOVES_LOG.append(row)
        _save()

    return asdict(row)


def get_mint_burn_log(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return mint/burn events as plain dicts (oldest → newest).
    """
    _ensure_loaded()
    rows = [asdict(r) for r in sorted(_MINT_BURN_LOG, key=lambda r: r.created_at_ms)]
    if limit is not None and limit > 0:
        rows = rows[-limit:]
    return rows


def get_reserve_moves_log(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return reserve move events as plain dicts (oldest → newest).
    """
    _ensure_loaded()
    rows = [asdict(r) for r in sorted(_RESERVE_MOVES_LOG, key=lambda r: r.created_at_ms)]
    if limit is not None and limit > 0:
        rows = rows[-limit:]
    return rows
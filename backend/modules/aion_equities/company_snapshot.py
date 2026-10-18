# backend/modules/aion_equities/company_snapshot.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _company_folder_name(company_ref_or_ticker: str) -> str:
    """
    Accepts "company/ULVR.L" OR "ULVR.L" OR "company_ULVR.L"
    Returns "company_ULVR.L"
    """
    s = str(company_ref_or_ticker or "").strip()
    if s.startswith("company_"):
        return s
    if s.startswith("company/"):
        s = s.split("/", 1)[1]
    return f"company_{s}" if s else "company_unknown"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl_last(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        # efficient tail: read last ~64KB
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 65536)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="ignore")
        lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def _read_jsonl_tail(path: Path, n: int) -> List[Dict[str, Any]]:
    if not path.exists() or n <= 0:
        return []
    try:
        # simple + safe: ok for small files; upgrade later if needed
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        out: List[Dict[str, Any]] = []
        for ln in reversed(lines):
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
            if len(out) >= n:
                break
        return list(reversed(out))
    except Exception:
        return []


def _parse_period(p: str) -> Tuple[int, int]:
    """
    "2026-Q4" -> (2026, 4)
    Unknown sorts low.
    """
    s = str(p or "").strip().upper()
    try:
        year, q = s.split("-Q", 1)
        return (int(year), int(q))
    except Exception:
        return (0, 0)


def _latest_period_from_trigger_maps(base_dir: Path, folder: str) -> Optional[str]:
    d = base_dir / "company_trigger_maps" / folder
    if not d.exists():
        return None
    periods: List[str] = []
    for p in d.glob("*.json"):
        periods.append(p.stem)
    if not periods:
        return None
    periods.sort(key=_parse_period)
    return periods[-1]


def build_company_snapshot(
    *,
    base_dir: str | Path,
    ticker: str,
    latest_period: Optional[str] = None,
    acs_rows: int = 10,
    include_trigger_map: bool = True,
) -> Dict[str, Any]:
    base = Path(base_dir)
    folder = _company_folder_name(ticker)  # company_ULVR.L
    company_ref = f"company/{ticker}"

    # decide period
    period = (latest_period or "").strip()
    if not period:
        period = _latest_period_from_trigger_maps(base, folder) or "unknown"

    tm_path = base / "company_trigger_maps" / folder / f"{period}.json"
    bqs_path = base / "bqs_history" / f"{folder}.jsonl"
    acs_path = base / "acs_history" / f"{folder}.jsonl"

    trigger_map = _read_json(tm_path) if tm_path.exists() else None

    bqs_last = _read_jsonl_last(bqs_path)
    acs_last = _read_jsonl_last(acs_path)
    acs_recent = _read_jsonl_tail(acs_path, acs_rows)

    # health (deterministic)
    trigger_entries = []
    if isinstance(trigger_map, dict):
        te = trigger_map.get("trigger_entries")
        if not isinstance(te, list):
            te = trigger_map.get("triggers")
        if isinstance(te, list):
            trigger_entries = [t for t in te if isinstance(t, dict)]

    variables_total = len(trigger_entries)
    variables_with_value = sum(1 for t in trigger_entries if t.get("latest_value") is not None)
    variables_confirmed = sum(1 for t in trigger_entries if str(t.get("current_state") or "").strip() == "confirmed")

    # easiest reports_ingested: count of trigger_map period files
    tm_dir = base / "company_trigger_maps" / folder
    reports_ingested = len(list(tm_dir.glob("*.json"))) if tm_dir.exists() else 0

    if reports_ingested < 2:
        maturity = "EARLY_STAGE"
    elif reports_ingested >= 2 and variables_confirmed < 3:
        maturity = "CALIBRATING"
    else:
        maturity = "READY" if (reports_ingested >= 4 and variables_confirmed >= 5) else "CALIBRATING"

    # last_updated_at: max(trigger last_updated_at, last history as_of)
    last_ts = None
    def _pick(ts: Optional[str]) -> None:
        nonlocal last_ts
        if not ts:
            return
        if last_ts is None or str(ts) > str(last_ts):
            last_ts = str(ts)

    for t in trigger_entries:
        _pick(t.get("last_updated_at"))
    if isinstance(bqs_last, dict):
        _pick(bqs_last.get("as_of"))
    if isinstance(acs_last, dict):
        _pick(acs_last.get("as_of"))

    snap: Dict[str, Any] = {
        "company_ref": company_ref,
        "latest_period": period,
        "paths": {
            "trigger_map": str(tm_path),
            "bqs_history": str(bqs_path),
            "acs_history": str(acs_path),
        },
        "bqs_latest": bqs_last,
        "acs_latest": acs_last,
        "acs_recent": acs_recent,
        "health": {
            "reports_ingested": reports_ingested,
            "variables_total": variables_total,
            "variables_with_value": variables_with_value,
            "variables_confirmed": variables_confirmed,
            "maturity": maturity,
            "last_updated_at": last_ts,
        },
    }

    if include_trigger_map:
        # keep it light: don’t dump huge blobs unless you want
        snap["trigger_map"] = trigger_map

    return snap
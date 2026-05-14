from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _ticker_from_company_ref(company_ref: str) -> str:
    # company/ULVR.L -> ULVR.L
    parts = str(company_ref or "").split("/")
    return parts[-1].strip() if parts else ""


def _company_safe(company_ref: str) -> str:
    # company/ULVR.L -> company_ULVR.L
    t = _ticker_from_company_ref(company_ref)
    return f"company_{t}" if t else _safe_segment(company_ref)


def _read_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_manual_overrides(base_dir: Path) -> Dict[str, Any]:
    """
    base_dir/company_events/manual_overrides.json

    Example:
    {
      "company/ULVR.L": {
        "next_reporting_date": "2026-04-24",
        "notes": "Manual override..."
      }
    }
    """
    p = base_dir / "company_events" / "manual_overrides.json"
    obj = _read_json(p)
    return obj if isinstance(obj, dict) else {}


def _yfinance_next_earnings_date(symbol: str) -> Tuple[Optional[str], str]:
    """
    Returns (YYYY-MM-DD or None, source_string)
    Never throws.
    """
    sym = str(symbol or "").strip()
    if not sym:
        return None, "yfinance:missing_symbol"

    try:
        import yfinance as yf
    except Exception:
        return None, "yfinance:not_installed"

    try:
        tkr = yf.Ticker(sym)

        # Try calendar first
        try:
            cal = getattr(tkr, "calendar", None)
            if cal is not None:
                # calendar might be DataFrame-like or dict-like depending on yfinance version
                # We attempt a few common shapes.
                # DataFrame-like: index might include "Earnings Date"
                # Dict-like: keys might include "Earnings Date"
                if hasattr(cal, "to_dict"):
                    # try dataframe path
                    try:
                        # cal can be DF with rows keyed by event name
                        # Best effort: scan stringified keys
                        d = cal.to_dict()
                        # We don't rely on exact shape; fallback to history/fast_info next.
                    except Exception:
                        pass
                if isinstance(cal, dict):
                    for k in ("Earnings Date", "EarningsDate", "earningsDate"):
                        if k in cal:
                            v = cal.get(k)
                            # v can be list/tuple of timestamps
                            if isinstance(v, (list, tuple)) and v:
                                vv = v[0]
                            else:
                                vv = v
                            # normalize
                            s = str(vv)
                            if len(s) >= 10:
                                return s[:10], "yfinance:calendar"
        except Exception:
            pass

        # Try fast_info / info fallbacks
        for attr, src in (("fast_info", "yfinance:fast_info"), ("info", "yfinance:info")):
            try:
                info = getattr(tkr, attr, None) or {}
                if not isinstance(info, dict):
                    continue
                for k in ("earningsDate", "nextEarningsDate", "next_earnings_date"):
                    v = info.get(k)
                    if not v:
                        continue
                    s = str(v)
                    if len(s) >= 10:
                        return s[:10], src
            except Exception:
                continue

        return None, "yfinance:not_found"
    except Exception:
        return None, "yfinance:error"


def refresh_company_events(*, base_dir: Path, company_ref: str) -> Tuple[Path, Dict[str, Any]]:
    """
    Writes:
      base_dir/company_events/<company_safe>.json

    Payload:
      {
        company_ref,
        yahoo_symbol,
        event_type: "earnings",
        next_reporting_date,
        window_start,
        window_end,
        source,
        fetched_at,
        notes
      }

    Merge rule:
      - If manual_overrides has an entry for company_ref, override wins.
    """
    base_dir = Path(base_dir).resolve()
    company_safe = _company_safe(company_ref)
    ticker = _ticker_from_company_ref(company_ref)
    yahoo_symbol = ticker  # for LSE symbols we keep ".L" (e.g., ULVR.L)

    # 1) fetch from yfinance (best-effort)
    yf_date, yf_source = _yfinance_next_earnings_date(yahoo_symbol)

    obj: Dict[str, Any] = {
        "company_ref": str(company_ref),
        "yahoo_symbol": str(yahoo_symbol),
        "event_type": "earnings",
        "next_reporting_date": yf_date,
        "window_start": None,
        "window_end": None,
        "source": yf_source,
        "fetched_at": _utc_now_iso(),
        "notes": "No earnings date found via yfinance for this symbol." if yf_date is None else "",
    }

    # 2) apply manual override if present
    overrides = _load_manual_overrides(base_dir)
    ov = overrides.get(str(company_ref))
    if isinstance(ov, dict):
        # Only override known keys; keep everything else
        obj2 = deepcopy(obj)
        if ov.get("next_reporting_date"):
            obj2["next_reporting_date"] = str(ov["next_reporting_date"])[:10]
            obj2["source"] = "manual_override"
            # if the override set a date, clear the "not found" note unless user supplied notes
            if not ov.get("notes"):
                obj2["notes"] = ""
        if ov.get("window_start"):
            obj2["window_start"] = str(ov["window_start"])[:10]
        if ov.get("window_end"):
            obj2["window_end"] = str(ov["window_end"])[:10]
        if ov.get("notes"):
            obj2["notes"] = str(ov["notes"])
        obj = obj2

    out_path = base_dir / "company_events" / f"{company_safe}.json"
    _write_json(out_path, obj)
    return out_path, obj


__all__ = ["refresh_company_events"]

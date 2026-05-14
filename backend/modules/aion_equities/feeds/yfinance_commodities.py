# /workspaces/COMDEX/backend/modules/aion_equities/feeds/yfinance_commodities.py
from __future__ import annotations

import contextlib
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _squelch_yfinance_noise(fn, *args, **kwargs):
    """
    yfinance can emit noisy stdout/stderr (and sometimes raises after printing).
    We redirect stdout+stderr so tick runner stays jq-clean.
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            return fn(*args, **kwargs)
    except Exception:
        return None


def _yfinance_close(ticker: str, *, period: str = "10d") -> Optional[Dict[str, Any]]:
    """
    Returns:
      {"ticker","as_of_date","close","currency"} or None
    Silences yfinance/yahoo noise so scripts stay jq-clean.
    """
    try:
        import yfinance as yf
    except Exception:
        return None

    def _do() -> Optional[Dict[str, Any]]:
        tkr = yf.Ticker(ticker)
        hist = tkr.history(period=period)

        if hist is None or getattr(hist, "empty", True):
            return None

        latest = hist.iloc[-1]
        close = _safe_float(latest.get("Close"))
        if close is None:
            return None

        dt = hist.index[-1]
        as_of_date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]

        # Best-effort currency discovery
        ccy = None
        try:
            finfo = getattr(tkr, "fast_info", None) or {}
            ccy = finfo.get("currency") or None
        except Exception:
            ccy = None

        if not ccy:
            try:
                info = tkr.info or {}
                ccy = info.get("currency") or None
            except Exception:
                ccy = None

        ccy = str(ccy).upper().strip() if ccy else None

        return {
            "ticker": ticker,
            "as_of_date": as_of_date,
            "close": float(close),
            "currency": ccy,
        }

    return _squelch_yfinance_noise(_do)


def _normalize_ticker_list(candidates: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        c = str(c or "").strip()
        if not c:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _select_first_working_close(
    *,
    candidates: list[str],
    period: str = "10d",
) -> Tuple[Optional[Dict[str, Any]], list[str], Optional[str]]:
    attempted: list[str] = []
    last_error: Optional[str] = None

    for t in candidates:
        attempted.append(t)
        got = _yfinance_close(t, period=period)
        if got:
            return got, attempted, None

    last_error = "no_yahoo_symbol_worked"
    return None, attempted, last_error


def commodity_update_for_feed(feed_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns (success):
      {
        "feed_id": ...,
        "current_value": <float>,
        "current_value_as_of": "YYYY-MM-DD",
        "unit": "tonne"|"barrel"|...,
        "currency": "USD"/"MYR"/... (best-effort from Yahoo),
        "target_currency": "USD" (if we want to convert later),
        "source": "yfinance/<TICKER_USED>",
        "attempted": [tickers...],
        "fetched_at": ISO8601
      }

    Returns (failure but still structured, so caller can log/debug if desired):
      {
        "feed_id": ...,
        "error": "...",
        "attempted": [...],
        "fetched_at": ISO8601
      }
    """
    fid = str(feed_id or "").strip()

    # Allow overrides without code changes.
    # Example:
    #   YF_PALM_OIL_TICKER=CPO=F
    #   YF_BRENT_TICKER=BZ=F
    palm_override = str(os.environ.get("YF_PALM_OIL_TICKER", "")).strip()
    brent_override = str(os.environ.get("YF_BRENT_TICKER", "")).strip()

    # -------------------------
    # PALM OIL (FCPO proxy)
    # -------------------------
    if fid == "palm_oil_fcpo_price":
        # NOTE:
        # - KO=F is unreliable/404 for many accounts/regions.
        # - Your run proved CPO=F works (and returned USD), so we prefer it first.
        # - Keep fallbacks because Yahoo symbols can vary by region.
        candidates: list[str] = []
        if palm_override:
            candidates.append(palm_override)

        candidates += [
            "CPO=F",   # ✅ preferred (worked for you)
            "KPO=F",
            "FCPO=F",
            "FCPO.MY",
            "FCPO.KL",
            # last resort: some users only get generic palm oil series (rare)
            "PALM-OIL",
        ]
        candidates = _normalize_ticker_list(candidates)

        got, attempted, err = _select_first_working_close(candidates=candidates, period="10d")
        if got:
            return {
                "feed_id": fid,
                "current_value": got["close"],
                "current_value_as_of": got["as_of_date"],
                "unit": "tonne",
                "currency": got.get("currency"),
                # keep your thresholds USD-based (runner converts if needed)
                "target_currency": "USD",
                "source": f"yfinance/{got['ticker']}",
                "attempted": attempted,
                "fetched_at": _utc_now_iso(),
            }

        return {
            "feed_id": fid,
            "error": err or "no_yahoo_symbol_worked",
            "attempted": attempted,
            "fetched_at": _utc_now_iso(),
        }

    # -------------------------
    # BRENT CRUDE
    # -------------------------
    if fid in {"brent_crude_daily", "brent_crude_price"}:
        candidates: list[str] = []
        if brent_override:
            candidates.append(brent_override)

        # Common Yahoo proxies:
        candidates += [
            "BZ=F",    # Brent crude oil futures (most common)
            "BRN=F",   # alternative brent futures symbol seen on some regions
            "BZZ=F",   # occasional alt
            # last resort: WTI (not brent) — keep as final fallback only
            "CL=F",
        ]
        candidates = _normalize_ticker_list(candidates)

        got, attempted, err = _select_first_working_close(candidates=candidates, period="10d")
        if got:
            return {
                "feed_id": "brent_crude_daily",
                "current_value": got["close"],
                "current_value_as_of": got["as_of_date"],
                "unit": "barrel",
                "currency": got.get("currency"),
                "target_currency": "USD",
                "source": f"yfinance/{got['ticker']}",
                "attempted": attempted,
                "fetched_at": _utc_now_iso(),
            }

        return {
            "feed_id": "brent_crude_daily",
            "error": err or "no_yahoo_symbol_worked",
            "attempted": attempted,
            "fetched_at": _utc_now_iso(),
        }

    return None


__all__ = ["commodity_update_for_feed"]
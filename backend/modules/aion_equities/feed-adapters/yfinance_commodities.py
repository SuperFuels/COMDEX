from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


@dataclass(frozen=True)
class YFResult:
    symbol: str
    as_of_date: str          # YYYY-MM-DD (market date)
    close: float
    currency: str            # e.g. USD, MYR
    fetched_at: str          # ISO8601 Z


def _fetch_latest_close(symbol: str, *, period: str = "10d") -> Optional[YFResult]:
    """
    Best-effort fetch latest daily close via yfinance.

    Notes:
    - Yahoo can rate-limit; caller should tolerate {}.
    - currency may not be USD (important for palm oil).
    """
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        raise RuntimeError("yfinance not installed. Run: pip install yfinance --break-system-packages")

    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=period, interval="1d", auto_adjust=False)

        if hist is None or getattr(hist, "empty", True):
            return None

        latest = hist.iloc[-1]
        close = _safe_float(latest.get("Close"))
        if close is None:
            return None

        idx = hist.index[-1]
        # idx can be tz-aware; normalize to date
        as_of_date = idx.strftime("%Y-%m-%d")

        # currency can be missing; try info
        currency = ""
        try:
            info = getattr(t, "info", {}) or {}
            currency = str(info.get("currency") or "").strip()
        except Exception:
            currency = ""

        if not currency:
            currency = "UNKNOWN"

        return YFResult(
            symbol=symbol,
            as_of_date=as_of_date,
            close=float(close),
            currency=currency,
            fetched_at=_utc_now_iso(),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------
# Public adapters (return dicts the live monitor can turn into FeedTicks)
# ---------------------------------------------------------------------

def fetch_palm_oil_yahoo() -> Dict[str, Any]:
    """
    Palm oil proxy via Yahoo.

    Default symbol:
      - KO=F is commonly used as a palm oil proxy on Yahoo via yfinance.
    IMPORTANT:
      - The returned currency may be MYR (common) not USD.
      - We emit currency in current_value_unit so you can see it immediately.
      - If you want USD/tonne consistency later, we’ll add FX conversion.
    """
    symbol = "KO=F"
    r = _fetch_latest_close(symbol)
    if not r:
        return {}

    return {
        "feed_id": "palm_oil_fcpo_price",
        "current_value": round(r.close, 4),
        "current_value_unit": f"{r.currency}/tonne",
        "current_value_as_of": r.as_of_date,
        "source": f"yfinance/{r.symbol}",
        "fetched_at": r.fetched_at,
        "metadata": {
            "symbol": r.symbol,
            "currency": r.currency,
        },
    }


def fetch_brent_yahoo() -> Dict[str, Any]:
    """
    Brent crude futures via Yahoo.

    Symbol:
      - BZ=F (Brent Crude Oil Last Day Financial Futures)
    """
    symbol = "BZ=F"
    r = _fetch_latest_close(symbol)
    if not r:
        return {}

    return {
        "feed_id": "brent_crude_daily",
        "current_value": round(r.close, 4),
        "current_value_unit": f"{r.currency}/barrel",
        "current_value_as_of": r.as_of_date,
        "source": f"yfinance/{r.symbol}",
        "fetched_at": r.fetched_at,
        "metadata": {
            "symbol": r.symbol,
            "currency": r.currency,
        },
    }
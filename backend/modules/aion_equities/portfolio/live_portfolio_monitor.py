# /workspaces/COMDEX/backend/modules/aion_equities/portfolio/live_portfolio_monitor.py
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_equities.portfolio.portfolio_state_store import PortfolioStateStore

# Optional helper module (if present). We keep our own fallback logic too.
try:
    from backend.modules.aion_equities.portfolio.drawdown import (  # type: ignore
        drawdown_pct as _dd_pct,  # expected signature: (peak: float, current: float) -> float
        update_peak as _update_peak,  # expected signature: (peak: float|None, current: float) -> float
    )
except Exception:  # pragma: no cover
    _dd_pct = None
    _update_peak = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None


def _update_peak_fallback(peak: Optional[float], current: float) -> float:
    if peak is None:
        return float(current)
    return float(max(float(peak), float(current)))


def _drawdown_pct_fallback(peak: Optional[float], current: float) -> float:
    if peak is None:
        return 0.0
    p = float(peak)
    c = float(current)
    if p <= 0:
        return 0.0
    return (p - c) / p  # 0.0 .. 1.0


def _update_peak(peak: Optional[float], current: float) -> float:
    if callable(_update_peak):
        try:
            return float(_update_peak(peak, current))
        except Exception:
            return _update_peak_fallback(peak, current)
    return _update_peak_fallback(peak, current)


def _drawdown_pct(peak: Optional[float], current: float) -> float:
    if callable(_dd_pct):
        try:
            return float(_dd_pct(peak, current))
        except Exception:
            return _drawdown_pct_fallback(peak, current)
    return _drawdown_pct_fallback(peak, current)


class LivePortfolioMonitor:
    """
    LivePortfolioMonitor (separate from LiveVariableTracker).

    Purpose:
      - ingest market price updates per instrument
      - update per-position drawdown metrics
      - update portfolio NAV series + portfolio-level drawdown
      - emit alert events when drawdown breaches configured thresholds

    Storage:
      - uses PortfolioStateStore (simple JSON store)
      - optionally writes alerts JSONL to <alerts_dir>/<safe_portfolio_id>.jsonl

    Expected state shape (but we are tolerant of missing fields):
      {
        "portfolio_id": "portfolio/default",
        "as_of": "ISO8601Z",
        "cash": 10000.0,
        "positions": [
          {
            "instrument_id": "ULVR.L",
            "quantity": 10.0,
            "avg_cost": 46.20,
            "last_price": 48.10,
            "peak_price": 49.00,
            "max_drawdown_pct": 0.031,
            "thesis_break_drawdown_pct": 0.12,   # optional per-position
          }
        ],
        "nav": {
          "current": 12345.67,
          "peak": 13000.00,
          "drawdown_pct": 0.0502,
          "max_drawdown_pct": 0.0810
        },
        "nav_history": [
          {"as_of":"...", "nav":123.4}
        ],
        "alerts": [
          {"as_of":"...", "type":"position_drawdown_breach", ...}
        ]
      }
    """

    def __init__(
        self,
        *,
        state_store: PortfolioStateStore,
        portfolio_id: str = "portfolio/default",
        max_nav_history: int = 3650,
        alerts_dir: Optional[str | Path] = None,
        default_position_break_dd_pct: float = 0.15,  # 15% drawdown default thesis-break if not specified
        default_portfolio_break_dd_pct: float = 0.12,  # 12% portfolio drawdown default
    ):
        self.state_store = state_store
        self.portfolio_id = str(portfolio_id)
        self.max_nav_history = int(max_nav_history)
        self.default_position_break_dd_pct = float(default_position_break_dd_pct)
        self.default_portfolio_break_dd_pct = float(default_portfolio_break_dd_pct)

        self.alerts_dir = Path(alerts_dir) if alerts_dir else None
        if self.alerts_dir:
            self.alerts_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # state helpers
    # -----------------------------
    def _load_state(self) -> Dict[str, Any]:
        try:
            state = self.state_store.load_state(self.portfolio_id)
            if isinstance(state, dict):
                return state
        except Exception:
            pass

        # minimal default
        return {
            "portfolio_id": self.portfolio_id,
            "as_of": _utc_now_iso(),
            "cash": 0.0,
            "positions": [],
            "nav": {
                "current": 0.0,
                "peak": None,
                "drawdown_pct": 0.0,
                "max_drawdown_pct": 0.0,
            },
            "nav_history": [],
            "alerts": [],
        }

    def _save_state(self, state: Dict[str, Any]) -> None:
        self.state_store.save_state(self.portfolio_id, state)

    def _emit_alert(self, state: Dict[str, Any], alert: Dict[str, Any]) -> None:
        # store in-state (bounded)
        alerts = state.get("alerts")
        if not isinstance(alerts, list):
            alerts = []
        alerts.append(deepcopy(alert))
        # keep last N alerts
        if len(alerts) > 5000:
            alerts = alerts[-5000:]
        state["alerts"] = alerts

        # optionally write JSONL for external tailing
        if self.alerts_dir:
            safe_id = self.portfolio_id.replace("/", "_").replace("\\", "_").replace(":", "-")
            p = self.alerts_dir / f"{safe_id}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            line = (str(alert).replace("'", '"'))  # not perfect JSON; keep simple
            try:
                with p.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

    # -----------------------------
    # public API
    # -----------------------------
    def update_price(
        self,
        *,
        instrument_id: str,
        price: float,
        as_of: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update a single instrument price, recompute NAV, recompute drawdowns, emit alerts.
        """
        as_of = as_of or _utc_now_iso()
        metadata = deepcopy(metadata or {})

        state = self._load_state()
        state["as_of"] = as_of

        positions = state.get("positions")
        if not isinstance(positions, list):
            positions = []
            state["positions"] = positions

        # find position
        pos: Optional[Dict[str, Any]] = None
        for p in positions:
            if isinstance(p, dict) and str(p.get("instrument_id") or "").strip() == str(instrument_id).strip():
                pos = p
                break

        if pos is None:
            # Allow “watch-only” price updates: keep a shadow position entry with qty=0
            pos = {
                "instrument_id": str(instrument_id),
                "quantity": 0.0,
                "avg_cost": None,
            }
            positions.append(pos)

        # update position price and drawdown
        px = float(price)
        prev_px = _safe_float(pos.get("last_price"))
        peak_px = _safe_float(pos.get("peak_price"))
        peak_px_new = _update_peak(peak_px, px)
        dd = _drawdown_pct(peak_px_new, px)

        max_dd = _safe_float(pos.get("max_drawdown_pct")) or 0.0
        max_dd_new = max(float(max_dd), float(dd))

        pos["last_price"] = px
        pos["last_price_as_of"] = as_of
        pos["peak_price"] = peak_px_new
        pos["drawdown_pct"] = float(dd)
        pos["max_drawdown_pct"] = float(max_dd_new)

        # PnL fields if we have qty and avg_cost
        qty = _safe_float(pos.get("quantity")) or 0.0
        avg_cost = _safe_float(pos.get("avg_cost"))
        if avg_cost is not None and qty != 0.0:
            pos["market_value"] = float(qty * px)
            pos["cost_value"] = float(qty * avg_cost)
            pos["unrealized_pnl"] = float(qty * (px - avg_cost))
            if avg_cost != 0:
                pos["unrealized_pnl_pct"] = float((px - avg_cost) / avg_cost)

        # alert on drawdown breach (position)
        break_dd = _safe_float(pos.get("thesis_break_drawdown_pct"))
        if break_dd is None:
            break_dd = self.default_position_break_dd_pct

        prev_dd = _safe_float(pos.get("prev_drawdown_pct")) or _safe_float(pos.get("drawdown_pct")) or 0.0
        pos["prev_drawdown_pct"] = float(prev_dd)

        # “cross above” the breach level (dd increases past threshold)
        if float(prev_dd) < float(break_dd) <= float(dd):
            self._emit_alert(
                state,
                {
                    "as_of": as_of,
                    "type": "position_drawdown_breach",
                    "portfolio_id": self.portfolio_id,
                    "instrument_id": str(instrument_id),
                    "drawdown_pct": float(dd),
                    "breach_level_pct": float(break_dd),
                    "peak_price": float(peak_px_new),
                    "last_price": float(px),
                    "metadata": metadata,
                },
            )

        # update NAV and portfolio drawdown
        nav_out = self._recompute_nav_and_drawdown(state=state, as_of=as_of, metadata=metadata)

        self._save_state(state)

        return {
            "ok": True,
            "portfolio_id": self.portfolio_id,
            "instrument_id": str(instrument_id),
            "as_of": as_of,
            "price": float(px),
            "position": deepcopy(pos),
            "nav": deepcopy(nav_out),
        }

    def update_nav(
        self,
        *,
        nav: float,
        as_of: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optional: if you already compute NAV elsewhere (broker feed),
        call this to update portfolio-level drawdown directly.
        """
        as_of = as_of or _utc_now_iso()
        metadata = deepcopy(metadata or {})

        state = self._load_state()
        state["as_of"] = as_of

        nav_obj = state.get("nav")
        if not isinstance(nav_obj, dict):
            nav_obj = {}
        current = float(nav)
        peak = _safe_float(nav_obj.get("peak"))
        peak_new = _update_peak(peak, current)
        dd = _drawdown_pct(peak_new, current)

        max_dd = _safe_float(nav_obj.get("max_drawdown_pct")) or 0.0
        max_dd_new = max(float(max_dd), float(dd))

        nav_obj["current"] = current
        nav_obj["peak"] = peak_new
        nav_obj["drawdown_pct"] = float(dd)
        nav_obj["max_drawdown_pct"] = float(max_dd_new)
        state["nav"] = nav_obj

        self._append_nav_history(state=state, as_of=as_of, nav=current)

        # portfolio breach alert
        prev_dd = _safe_float(nav_obj.get("prev_drawdown_pct")) or float(dd)
        nav_obj["prev_drawdown_pct"] = float(prev_dd)

        if float(prev_dd) < self.default_portfolio_break_dd_pct <= float(dd):
            self._emit_alert(
                state,
                {
                    "as_of": as_of,
                    "type": "portfolio_drawdown_breach",
                    "portfolio_id": self.portfolio_id,
                    "drawdown_pct": float(dd),
                    "breach_level_pct": float(self.default_portfolio_break_dd_pct),
                    "peak_nav": float(peak_new),
                    "nav": float(current),
                    "metadata": metadata,
                },
            )

        self._save_state(state)

        return {
            "ok": True,
            "portfolio_id": self.portfolio_id,
            "as_of": as_of,
            "nav": deepcopy(nav_obj),
        }

    # -----------------------------
    # internals
    # -----------------------------
    def _append_nav_history(self, *, state: Dict[str, Any], as_of: str, nav: float) -> None:
        hist = state.get("nav_history")
        if not isinstance(hist, list):
            hist = []
        hist.append({"as_of": as_of, "nav": float(nav)})
        if self.max_nav_history > 0 and len(hist) > self.max_nav_history:
            hist = hist[-self.max_nav_history :]
        state["nav_history"] = hist

    def _recompute_nav_and_drawdown(
        self,
        *,
        state: Dict[str, Any],
        as_of: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        cash = _safe_float(state.get("cash")) or 0.0
        positions = state.get("positions")
        if not isinstance(positions, list):
            positions = []

        mv_total = 0.0
        for p in positions:
            if not isinstance(p, dict):
                continue
            qty = _safe_float(p.get("quantity")) or 0.0
            px = _safe_float(p.get("last_price"))
            if px is None:
                continue
            mv_total += float(qty * px)

        nav_current = float(cash + mv_total)

        nav_obj = state.get("nav")
        if not isinstance(nav_obj, dict):
            nav_obj = {}

        peak = _safe_float(nav_obj.get("peak"))
        peak_new = _update_peak(peak, nav_current)
        dd = _drawdown_pct(peak_new, nav_current)

        max_dd = _safe_float(nav_obj.get("max_drawdown_pct")) or 0.0
        max_dd_new = max(float(max_dd), float(dd))

        prev_dd = _safe_float(nav_obj.get("prev_drawdown_pct")) or float(dd)
        nav_obj["prev_drawdown_pct"] = float(prev_dd)

        nav_obj["current"] = nav_current
        nav_obj["peak"] = peak_new
        nav_obj["drawdown_pct"] = float(dd)
        nav_obj["max_drawdown_pct"] = float(max_dd_new)

        state["nav"] = nav_obj
        self._append_nav_history(state=state, as_of=as_of, nav=nav_current)

        # portfolio breach alert
        if float(prev_dd) < self.default_portfolio_break_dd_pct <= float(dd):
            self._emit_alert(
                state,
                {
                    "as_of": as_of,
                    "type": "portfolio_drawdown_breach",
                    "portfolio_id": self.portfolio_id,
                    "drawdown_pct": float(dd),
                    "breach_level_pct": float(self.default_portfolio_break_dd_pct),
                    "peak_nav": float(peak_new),
                    "nav": float(nav_current),
                    "metadata": metadata,
                },
            )

        return deepcopy(nav_obj)


__all__ = ["LivePortfolioMonitor"]
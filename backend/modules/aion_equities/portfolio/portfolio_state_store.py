# /workspaces/COMDEX/backend/modules/aion_equities/portfolio/portfolio_state_store.py
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


class PortfolioStateStore:
    """
    Simple JSON store for:
      - portfolio state (NAV, cash, positions summary)
      - per-position drawdown states
      - portfolio drawdown state
      - lightweight alerts list (optional)

    Layout:
      <base_dir>/portfolio_state/
        portfolio_default.json
        portfolio_main.json
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.store_dir = self.base_dir / "portfolio_state"
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, portfolio_id: str = "portfolio_default") -> Path:
        return self.store_dir / f"{_safe_segment(portfolio_id)}.json"

    def load(self, portfolio_id: str = "portfolio_default") -> Dict[str, Any]:
        path = self.storage_path(portfolio_id)
        if not path.exists():
            # minimal default shape
            return {
                "portfolio_id": portfolio_id,
                "as_of": None,
                "nav": None,
                "cash": None,
                "positions": {},  # { "company/ULVR.L": { ... } }
                "drawdowns": {
                    "portfolio": None,
                    "positions": {},
                },
                "alerts": [],
                "updated_at": None,
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, payload: Dict[str, Any], portfolio_id: str = "portfolio_default") -> Dict[str, Any]:
        out = deepcopy(payload or {})
        out["portfolio_id"] = portfolio_id
        out["updated_at"] = _utc_now_iso()
        path = self.storage_path(portfolio_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    # -----------------------------
    # convenience helpers
    # -----------------------------
    def upsert_position(
        self,
        *,
        portfolio_id: str = "portfolio_default",
        company_ref: str,
        position: Dict[str, Any],
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        st = self.load(portfolio_id)
        st.setdefault("positions", {})
        st["positions"][str(company_ref)] = deepcopy(position or {})
        if as_of is not None:
            st["as_of"] = as_of
        return self.save(st, portfolio_id)

    def append_alert(
        self,
        *,
        portfolio_id: str = "portfolio_default",
        alert: Dict[str, Any],
        max_alerts: int = 200,
    ) -> Dict[str, Any]:
        st = self.load(portfolio_id)
        st.setdefault("alerts", [])
        st["alerts"].append(deepcopy(alert or {}))
        if max_alerts > 0 and len(st["alerts"]) > max_alerts:
            st["alerts"] = st["alerts"][-max_alerts:]
        return self.save(st, portfolio_id)

    def list_portfolios(self) -> List[str]:
        out: List[str] = []
        for p in sorted(self.store_dir.glob("*.json")):
            out.append(p.stem.replace("_", "/"))
        return out


__all__ = ["PortfolioStateStore"]
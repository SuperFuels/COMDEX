from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        return _iso_z(value)[:10]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 10:
            return s[:10]
    raise ValueError(f"Unsupported date value: {value!r}")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "global_capital_markets"


def global_capital_markets_storage_path(as_of_date: Any, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    ds = _date_str(as_of_date)
    return root / f"{_safe_segment(ds)}.json"


def build_global_capital_markets_payload(
    *,
    as_of_date: Any,
    generated_by: str = "aion_equities.global_capital_markets_store",
    liquidity_regime_patch: Optional[Dict[str, Any]] = None,
    dollar_funding_patch: Optional[Dict[str, Any]] = None,
    yield_curves: Optional[List[Dict[str, Any]]] = None,
    real_yields: Optional[List[Dict[str, Any]]] = None,
    credit_spreads: Optional[List[Dict[str, Any]]] = None,
    yield_differential_matrix: Optional[List[Dict[str, Any]]] = None,
    foreign_ownership_vulnerability: Optional[List[Dict[str, Any]]] = None,
    market_structure_patch: Optional[Dict[str, Any]] = None,
    cross_market_signals_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "global_capital_markets_id": f"global_capital_markets/{as_of_date_s}",
        "as_of_date": as_of_date_s,
        "liquidity_regime": {
            "state": "neutral",
            "confidence": 50.0,
            "summary": "Neutral global liquidity backdrop",
        },
        "dollar_funding": {
            "regime": "normal",
            "dxy_direction": "unknown",
            "cross_currency_basis_regime": "unknown",
            "notes": "",
        },
        "yield_curves": yield_curves or [
            {
                "country_code": "US",
                "yield_2y": 0.0,
                "yield_10y": 0.0,
                "yield_30y": 0.0,
                "curve_regime": "unknown",
            }
        ],
        "real_yields": real_yields or [
            {
                "country_code": "US",
                "real_yield_10y": 0.0,
                "real_yield_2y": 0.0,
                "real_rate_regime": "unknown",
            }
        ],
        "credit_spreads": credit_spreads or [
            {
                "country_code": "US",
                "ig_oas_bps": 0.0,
                "hy_oas_bps": 0.0,
                "spread_regime": "unknown",
                "direction": "unknown",
            }
        ],
        "yield_differential_matrix": yield_differential_matrix or [],
        "foreign_ownership_vulnerability": foreign_ownership_vulnerability or [],
        "market_structure": {
            "vix_regime": "unknown",
            "gamma_regime": "unknown",
            "liquidity_depth_regime": "unknown",
            "algo_pressure_regime": "unknown",
            "notes": "",
        },
        "cross_market_signals": {
            "risk_appetite_regime": "unknown",
            "carry_regime": "unknown",
            "equity_bond_correlation_regime": "unknown",
            "stress_notes": [],
        },
        "linked_refs": {
            "macro_regime_refs": [],
            "top_down_snapshot_refs": [],
            "country_ambassador_refs": [],
            "country_relationship_refs": [],
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if liquidity_regime_patch:
        payload["liquidity_regime"] = _deep_merge(payload["liquidity_regime"], liquidity_regime_patch)
    if dollar_funding_patch:
        payload["dollar_funding"] = _deep_merge(payload["dollar_funding"], dollar_funding_patch)
    if market_structure_patch:
        payload["market_structure"] = _deep_merge(payload["market_structure"], market_structure_patch)
    if cross_market_signals_patch:
        payload["cross_market_signals"] = _deep_merge(payload["cross_market_signals"], cross_market_signals_patch)
    if linked_refs_patch:
        payload["linked_refs"] = _deep_merge(payload["linked_refs"], linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("global_capital_markets", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_global_capital_markets_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("global_capital_markets", payload, version=SCHEMA_PACK_VERSION)

    path = global_capital_markets_storage_path(payload["as_of_date"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_global_capital_markets_payload(
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = global_capital_markets_storage_path(as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Global capital markets payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("global_capital_markets", payload, version=SCHEMA_PACK_VERSION)
    return payload


class GlobalCapitalMarketsStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "global_capital_markets"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, as_of_date: Any) -> Path:
        return global_capital_markets_storage_path(as_of_date, base_dir=self.base_dir)

    def save_global_capital_markets(
        self,
        *,
        as_of_date: Any,
        generated_by: str = "aion_equities.global_capital_markets_store",
        liquidity_regime_patch: Optional[Dict[str, Any]] = None,
        dollar_funding_patch: Optional[Dict[str, Any]] = None,
        yield_curves: Optional[List[Dict[str, Any]]] = None,
        real_yields: Optional[List[Dict[str, Any]]] = None,
        credit_spreads: Optional[List[Dict[str, Any]]] = None,
        yield_differential_matrix: Optional[List[Dict[str, Any]]] = None,
        foreign_ownership_vulnerability: Optional[List[Dict[str, Any]]] = None,
        market_structure_patch: Optional[Dict[str, Any]] = None,
        cross_market_signals_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_global_capital_markets_payload(
            as_of_date=as_of_date,
            generated_by=generated_by,
            liquidity_regime_patch=liquidity_regime_patch,
            dollar_funding_patch=dollar_funding_patch,
            yield_curves=yield_curves,
            real_yields=real_yields,
            credit_spreads=credit_spreads,
            yield_differential_matrix=yield_differential_matrix,
            foreign_ownership_vulnerability=foreign_ownership_vulnerability,
            market_structure_patch=market_structure_patch,
            cross_market_signals_patch=cross_market_signals_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_global_capital_markets_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def save_snapshot(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_global_capital_markets(**kwargs)

    def load_global_capital_markets(self, as_of_date: Any, *, validate: bool = True) -> Dict[str, Any]:
        return load_global_capital_markets_payload(as_of_date, base_dir=self.base_dir, validate=validate)

    def load_snapshot(self, as_of_date: Any, *, validate: bool = True) -> Dict[str, Any]:
        return self.load_global_capital_markets(as_of_date, validate=validate)

    def global_capital_markets_exists(self, as_of_date: Any) -> bool:
        return self.storage_path(as_of_date).exists()

    def snapshot_exists(self, as_of_date: Any) -> bool:
        return self.global_capital_markets_exists(as_of_date)

    def list_snapshots(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
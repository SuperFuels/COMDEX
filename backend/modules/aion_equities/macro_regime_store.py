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
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        s = value.strip()
        if len(s) == 10:
            return f"{s}T00:00:00Z"
        return s
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
    return Path(__file__).resolve().parent / "data" / "macro_regime"


def macro_regime_storage_path(as_of_date: Any, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    ds = _date_str(as_of_date)
    return root / f"{_safe_segment(ds)}.json"


def _normalize_regime_state(value: Optional[str]) -> str:
    if not value:
        return "transition"

    v = str(value).strip().lower()
    mapping = {
        "transition": "transition",
        "transitioning": "transition",
        "active": "risk_off",
        "risk_on": "risk_on",
        "risk_off": "risk_off",
        "rotating": "rotating",
    }
    return mapping.get(v, v)


def build_macro_regime_payload(
    *,
    as_of_date: Any,
    regime_state: str = "transition",
    summary: str = "Macro regime snapshot",
    generated_by: str = "aion_equities.macro_regime_store",
    signals_patch: Optional[Dict[str, Any]] = None,
    sector_flows_patch: Optional[Dict[str, Any]] = None,
    market_style_patch: Optional[Dict[str, Any]] = None,
    regime_multipliers_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    risk_flags: Optional[List[str]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "macro_regime_id": f"macro/regime/{as_of_date_s}",
        "as_of_date": as_of_date_s,
        "regime_state": _normalize_regime_state(regime_state),
        "summary": summary,
        "signals": {
            "usd_direction": "unknown",
            "usd_jpy_signal": "unknown",
            "rates_direction": "unknown",
            "real_yields_direction": "unknown",
            "gold_direction": "unknown",
            "credit_spread_regime": "unknown",
        },
        "sector_flows": {
            "leaders": [],
            "laggards": [],
        },
        "market_style": {
            "mag7_state": "unknown",
            "breadth_state": "unknown",
            "ai_trade_state": "unknown",
        },
        "risk_flags": risk_flags or [],
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if signals_patch:
        payload["signals"] = _deep_merge(payload["signals"], signals_patch)
    if sector_flows_patch:
        payload["sector_flows"] = _deep_merge(payload["sector_flows"], sector_flows_patch)
    if market_style_patch:
        payload["market_style"] = _deep_merge(payload["market_style"], market_style_patch)
    if regime_multipliers_patch:
        payload["regime_multipliers"] = deepcopy(regime_multipliers_patch)
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("macro_regime", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_macro_regime_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("macro_regime", payload, version=SCHEMA_PACK_VERSION)

    path = macro_regime_storage_path(payload["as_of_date"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_macro_regime_payload(
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = macro_regime_storage_path(as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Macro regime payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("macro_regime", payload, version=SCHEMA_PACK_VERSION)
    return payload


class MacroRegimeStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "macro_regime"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, as_of_date: Any) -> Path:
        return macro_regime_storage_path(as_of_date, base_dir=self.base_dir)

    def save_macro_regime(
        self,
        *,
        as_of_date: Any = None,
        as_of: Any = None,
        regime_name: Optional[str] = None,
        regime_confidence: Optional[float] = None,
        regime_state: str = "transition",
        summary: str = "Macro regime snapshot",
        generated_by: str = "aion_equities.macro_regime_store",
        signals_patch: Optional[Dict[str, Any]] = None,
        sector_flows_patch: Optional[Dict[str, Any]] = None,
        market_style_patch: Optional[Dict[str, Any]] = None,
        regime_multipliers_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        risk_flags: Optional[List[str]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        effective_as_of = as_of_date if as_of_date is not None else as_of
        if effective_as_of is None:
            raise ValueError("save_macro_regime() requires as_of_date (or alias as_of)")

        effective_summary = regime_name if regime_name else summary

        effective_payload_patch = deepcopy(payload_patch or {})
        if regime_confidence is not None:
            multipliers = deepcopy(effective_payload_patch.get("regime_multipliers", {}))
            multipliers["regime_confidence"] = regime_confidence
            effective_payload_patch["regime_multipliers"] = multipliers

        payload = build_macro_regime_payload(
            as_of_date=effective_as_of,
            regime_state=regime_state,
            summary=effective_summary,
            generated_by=generated_by,
            signals_patch=signals_patch,
            sector_flows_patch=sector_flows_patch,
            market_style_patch=market_style_patch,
            regime_multipliers_patch=regime_multipliers_patch,
            linked_refs_patch=linked_refs_patch,
            risk_flags=risk_flags,
            payload_patch=effective_payload_patch,
            validate=validate,
        )
        save_macro_regime_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def load_macro_regime(self, as_of_date: Any, *, validate: bool = True) -> Dict[str, Any]:
        return load_macro_regime_payload(as_of_date, base_dir=self.base_dir, validate=validate)

    def load_macro_regime_by_id(self, macro_regime_id: str, *, validate: bool = True) -> Dict[str, Any]:
        parts = str(macro_regime_id).split("/")
        if len(parts) < 3:
            raise ValueError(f"Invalid macro_regime_id: {macro_regime_id!r}")
        as_of_date = parts[-1]
        return self.load_macro_regime(as_of_date, validate=validate)

    def macro_regime_exists(self, as_of_date: Any) -> bool:
        return self.storage_path(as_of_date).exists()

    def macro_regime_exists_by_id(self, macro_regime_id: str) -> bool:
        try:
            parts = str(macro_regime_id).split("/")
            if len(parts) < 3:
                return False
            return self.macro_regime_exists(parts[-1])
        except Exception:
            return False

    def list_macro_regimes(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
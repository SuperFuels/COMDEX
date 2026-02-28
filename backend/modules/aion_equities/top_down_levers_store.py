from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


# -------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        s = value.strip()
        if len(s) == 10:
            return f"{s}T00:00:00Z"
        return s
    raise ValueError(f"Unsupported datetime value: {value!r}")


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
    return Path(__file__).resolve().parent / "data" / "top_down_levers"


def _snapshot_id_from_timestamp(timestamp: str) -> str:
    return f"top_down/{timestamp}"


def top_down_snapshot_storage_path(snapshot_id: str, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(snapshot_id)}.json"


# -------------------------------------------------------------------
# legacy payload_patch -> schema conversion
# -------------------------------------------------------------------
_LEVER_MAP = {
    "usd_broad": "dollar",
    "usd_jpy": "yen",
    "gold": "gold",
    "oil": "oil",
    "real_yields": "real_yields",
    "spreads": "credit_spreads",
}

_SECTOR_REF_MAP = {
    "defensives": "sector/defensives",
    "energy": "sector/energy",
    "ai_infrastructure": "sector/ai_infrastructure",
    "cyclicals": "sector/cyclicals",
    "high_beta": "sector/high_beta",
    "long_duration_growth": "sector/long_duration_growth",
    "high_debt": "sector/high_debt",
    "credit_sensitive": "sector/credit_sensitive",
}


def _direction_to_schema(direction: str) -> str:
    d = str(direction).strip().lower()
    mapping = {
        "up": "up",
        "down": "down",
        "tightening": "tightening",
        "easing": "easing",
        "risk_on": "risk_on",
        "risk_off": "risk_off",
        "mixed": "mixed",
        "shock": "shock",
        "widening": "risk_off",
        "into": "risk_on",
        "out_of": "risk_off",
    }
    return mapping.get(d, "mixed")


def _materiality_for(direction: str) -> float:
    d = str(direction).strip().lower()
    if d in {"widening", "shock"}:
        return 85.0
    if d in {"up", "down", "into", "out_of"}:
        return 70.0
    return 50.0


def _legacy_patch_to_schema_fields(
    *,
    payload_patch: Dict[str, Any],
    regime_ref: str,
    regime_state: str,
) -> Dict[str, Any]:
    active_levers: List[Dict[str, Any]] = []
    sector_posture: List[Dict[str, Any]] = []
    cascade_implications: List[Dict[str, Any]] = []

    # FX
    fx = payload_patch.get("fx", {})
    if isinstance(fx, dict):
        for key in ("usd_broad", "usd_jpy"):
            node = fx.get(key, {})
            if isinstance(node, dict) and node.get("direction"):
                active_levers.append(
                    {
                        "lever": _LEVER_MAP[key],
                        "direction": _direction_to_schema(node["direction"]),
                        "materiality": _materiality_for(node["direction"]),
                        "note": f"Derived from legacy fx.{key}",
                    }
                )

    # Rates
    rates = payload_patch.get("rates", {})
    if isinstance(rates, dict):
        node = rates.get("real_yields", {})
        if isinstance(node, dict) and node.get("direction"):
            active_levers.append(
                {
                    "lever": "real_yields",
                    "direction": _direction_to_schema(node["direction"]),
                    "materiality": _materiality_for(node["direction"]),
                    "note": "Derived from legacy rates.real_yields",
                }
            )

    # Credit
    credit = payload_patch.get("credit", {})
    if isinstance(credit, dict):
        node = credit.get("spreads", {})
        if isinstance(node, dict) and node.get("direction"):
            active_levers.append(
                {
                    "lever": "credit_spreads",
                    "direction": _direction_to_schema(node["direction"]),
                    "materiality": _materiality_for(node["direction"]),
                    "note": "Derived from legacy credit.spreads",
                }
            )

    # Commodities
    commodities = payload_patch.get("commodities", {})
    if isinstance(commodities, dict):
        for key in ("gold", "oil"):
            node = commodities.get(key, {})
            if isinstance(node, dict) and node.get("direction"):
                active_levers.append(
                    {
                        "lever": _LEVER_MAP[key],
                        "direction": _direction_to_schema(node["direction"]),
                        "materiality": _materiality_for(node["direction"]),
                        "note": f"Derived from legacy commodities.{key}",
                    }
                )

    # Sector flows -> sector posture
    flows = payload_patch.get("sector_flows", {})
    if isinstance(flows, dict):
        for key, node in flows.items():
            if not isinstance(node, dict):
                continue
            direction = str(node.get("direction", "")).strip().lower()
            if not direction:
                continue

            if direction == "into":
                posture = "green"
                tailwind = 75.0
                headwind = 20.0
            elif direction == "out_of":
                posture = "red"
                tailwind = 20.0
                headwind = 75.0
            else:
                posture = "amber"
                tailwind = 50.0
                headwind = 50.0

            sector_posture.append(
                {
                    "sector_ref": _SECTOR_REF_MAP.get(key, f"sector/{key}"),
                    "posture": posture,
                    "tailwind_score": tailwind,
                    "headwind_score": headwind,
                    "note": f"Derived from legacy sector_flows.{key}",
                }
            )

    # lightweight implications from obvious signals
    if any(x["lever"] == "credit_spreads" and x["direction"] == "risk_off" for x in active_levers):
        cascade_implications.append(
            {
                "rule_id": "credit_spreads_widening",
                "summary": "Credit stress rising; high-debt and cyclical names face headwinds.",
                "affected_scope": "sector",
                "effect_direction": "headwind",
                "confidence": 88.0,
                "target_refs": ["sector/high_debt", "sector/cyclicals"],
            }
        )

    if any(x["lever"] == "yen" and x["direction"] == "down" for x in active_levers):
        cascade_implications.append(
            {
                "rule_id": "yen_strength_carry_unwind",
                "summary": "Yen strength implies carry unwind / risk-off signal.",
                "affected_scope": "cross_asset",
                "effect_direction": "de_risk",
                "confidence": 85.0,
                "target_refs": ["sector/high_beta", "sector/defensives"],
            }
        )

    contradictions = 0
    has_gold_up = any(x["lever"] == "gold" and x["direction"] == "up" for x in active_levers)
    has_dollar_up = any(x["lever"] == "dollar" and x["direction"] == "up" for x in active_levers)
    has_rates_up = any(x["lever"] == "real_yields" and x["direction"] == "up" for x in active_levers)
    has_credit_risk_off = any(x["lever"] == "credit_spreads" and x["direction"] == "risk_off" for x in active_levers)
    has_ai_green = any(x["sector_ref"] == "sector/ai_infrastructure" and x["posture"] == "green" for x in sector_posture)

    if has_gold_up and has_dollar_up:
        contradictions += 1
    if has_rates_up and has_ai_green:
        contradictions += 1
    if has_credit_risk_off and has_ai_green:
        contradictions += 1

    conviction_state = {
        "signal_coherence": 85.0 if contradictions == 0 else 65.0 if contradictions == 1 else 40.0,
        "uncertainty_score": 15.0 if contradictions == 0 else 35.0 if contradictions == 1 else 65.0,
        "summary": "Derived from legacy top-down payload patch.",
    }

    return {
        "regime_ref": regime_ref,
        "regime_state": regime_state,
        "active_levers": active_levers or [
            {
                "lever": "global_event",
                "direction": "mixed",
                "materiality": 1.0,
                "note": "Fallback placeholder",
            }
        ],
        "cascade_implications": cascade_implications,
        "sector_posture": sector_posture,
        "conviction_state": conviction_state,
    }


# -------------------------------------------------------------------
# payload builder
# -------------------------------------------------------------------
def build_top_down_snapshot_payload(
    *,
    snapshot_id: Optional[str] = None,
    timestamp: Any,
    regime_ref: str = "macro/regime/unknown",
    regime_state: str = "transitioning",
    active_levers: Optional[List[Dict[str, Any]]] = None,
    cascade_implications: Optional[List[Dict[str, Any]]] = None,
    sector_posture: Optional[List[Dict[str, Any]]] = None,
    conviction_state: Optional[Dict[str, Any]] = None,
    watchlist_impacts: Optional[List[Dict[str, Any]]] = None,
    created_by: Optional[str] = None,
    generated_by: Optional[str] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    timestamp_s = _iso_z(timestamp)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s
    actor = created_by or generated_by or "aion_equities.top_down_levers_store"

    payload: Dict[str, Any] = {
        "snapshot_id": snapshot_id or _snapshot_id_from_timestamp(timestamp_s),
        "timestamp": timestamp_s,
        "regime_ref": regime_ref,
        "regime_state": regime_state,
        "active_levers": active_levers or [
            {
                "lever": "global_event",
                "direction": "mixed",
                "materiality": 1.0,
                "note": "Default placeholder",
            }
        ],
        "cascade_implications": cascade_implications or [],
        "sector_posture": sector_posture or [],
        "conviction_state": conviction_state or {
            "signal_coherence": 50.0,
            "uncertainty_score": 50.0,
            "summary": "Default placeholder conviction state",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": actor,
        },
    }

    if watchlist_impacts is not None:
        payload["watchlist_impacts"] = watchlist_impacts

    if payload_patch:
        # Support legacy shape from macro runtime integration
        legacy_keys = {"fx", "rates", "credit", "commodities", "sector_flows", "geopolitical", "market_structure", "policy_signals"}
        if any(k in payload_patch for k in legacy_keys):
            normalized = _legacy_patch_to_schema_fields(
                payload_patch=payload_patch,
                regime_ref=payload["regime_ref"],
                regime_state=payload["regime_state"],
            )
            payload = _deep_merge(payload, normalized)
        else:
            payload = _deep_merge(payload, payload_patch)

    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)

    return payload


# -------------------------------------------------------------------
# io
# -------------------------------------------------------------------
def save_top_down_snapshot_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)

    path = top_down_snapshot_storage_path(payload["snapshot_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_top_down_snapshot_payload_by_id(
    snapshot_id: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = top_down_snapshot_storage_path(snapshot_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Top-down snapshot payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("top_down_levers_snapshot", payload, version=SCHEMA_PACK_VERSION)
    return payload


# -------------------------------------------------------------------
# store
# -------------------------------------------------------------------
class TopDownLeversStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "top_down_levers"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, snapshot_id: str) -> Path:
        return top_down_snapshot_storage_path(snapshot_id, base_dir=self.base_dir)

    def save_snapshot(
        self,
        *,
        snapshot_id: Optional[str] = None,
        timestamp: Any,
        regime_ref: str = "macro/regime/unknown",
        regime_state: str = "transitioning",
        active_levers: Optional[List[Dict[str, Any]]] = None,
        cascade_implications: Optional[List[Dict[str, Any]]] = None,
        sector_posture: Optional[List[Dict[str, Any]]] = None,
        conviction_state: Optional[Dict[str, Any]] = None,
        watchlist_impacts: Optional[List[Dict[str, Any]]] = None,
        created_by: Optional[str] = None,
        generated_by: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_top_down_snapshot_payload(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            regime_ref=regime_ref,
            regime_state=regime_state,
            active_levers=active_levers,
            cascade_implications=cascade_implications,
            sector_posture=sector_posture,
            conviction_state=conviction_state,
            watchlist_impacts=watchlist_impacts,
            created_by=created_by,
            generated_by=generated_by,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_top_down_snapshot_payload(payload, base_dir=self.base_dir, validate=False)
        return payload

    def save_top_down_snapshot(
        self,
        *,
        snapshot_date: Any,
        generated_by: str = "aion_equities.top_down_levers_store",
        regime_ref: str = "macro/regime/unknown",
        regime_state: str = "transitioning",
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # legacy wrapper used by macro runtime integration
        kwargs.pop("created_by", None)
        return self.save_snapshot(
            timestamp=snapshot_date,
            regime_ref=regime_ref,
            regime_state=regime_state,
            generated_by=generated_by,
            payload_patch=payload_patch,
            validate=validate,
            **kwargs,
        )

    def load_snapshot(self, snapshot_id: str, *, validate: bool = True) -> Dict[str, Any]:
        return load_top_down_snapshot_payload_by_id(snapshot_id, base_dir=self.base_dir, validate=validate)

    def load_snapshot_by_id(self, snapshot_id: str, *, validate: bool = True) -> Dict[str, Any]:
        return self.load_snapshot(snapshot_id, validate=validate)

    def snapshot_exists(self, snapshot_id: str) -> bool:
        return self.storage_path(snapshot_id).exists()

    def list_snapshots(self) -> List[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
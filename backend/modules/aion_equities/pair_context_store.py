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
    return Path(__file__).resolve().parent / "data" / "pair_contexts"


def pair_context_storage_path(
    pair: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(str(pair).upper()) / f"{_safe_segment(_date_str(as_of_date))}.json"


def _normalize_macro_coherence_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    out = deepcopy(patch)
    return out


def _normalize_carry_signal_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    out = deepcopy(patch)

    state_map = {
        "active": "unwind_risk",
        "inactive": "neutral",
        "favour_base": "favour_base",
        "favour_quote": "favour_quote",
        "neutral": "neutral",
        "unwind_risk": "unwind_risk",
        "unknown": "unknown",
    }

    if "state" in out:
        out["state"] = state_map.get(str(out["state"]), "unknown")

    return out


def _normalize_risk_appetite_signal_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    out = deepcopy(patch)

    if isinstance(out.get("state"), str):
        state = out["state"]
        if state not in {"risk_on", "risk_off", "transition", "unknown"}:
            out["state"] = "unknown"

    return out


def _normalize_pair_score_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    out = deepcopy(patch)

    direction_map = {
        "usd_strength": "quote_outperform",
        "usd_weakness": "base_outperform",
        "gbp_strength": "base_outperform",
        "gbp_weakness": "quote_outperform",
        "base_outperform": "base_outperform",
        "quote_outperform": "quote_outperform",
        "range_bound": "range_bound",
        "unknown": "unknown",
    }

    if "direction_bias" in out:
        out["direction_bias"] = direction_map.get(str(out["direction_bias"]), "unknown")

    return out


def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _normalize_payload_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    # Legacy shape:
    # {
    #   "pair_outlook": {...},
    #   "signals": {...},
    #   "linked_refs": {...}
    # }
    pair_outlook = out.pop("pair_outlook", None)
    if isinstance(pair_outlook, dict):
        macro_patch = out.setdefault("macro_coherence", {})
        pair_score_patch = out.setdefault("pair_score", {})

        if "coherence_score" in pair_outlook:
            macro_patch.setdefault("score", pair_outlook["coherence_score"])
        if "confidence" in pair_outlook:
            pair_score_patch.setdefault("conviction", pair_outlook["confidence"])
        if "summary" in pair_outlook:
            pair_score_patch.setdefault("summary", pair_outlook["summary"])

        direction_bias = pair_outlook.get("direction_bias")
        if direction_bias is not None:
            pair_score_patch.setdefault("direction_bias", direction_bias)

    signals = out.pop("signals", None)
    if isinstance(signals, dict):
        carry_patch = out.setdefault("carry_signal", {})
        risk_patch = out.setdefault("risk_appetite_signal", {})
        macro_patch = out.setdefault("macro_coherence", {})

        carry_unwind_signal = signals.get("carry_unwind_signal")
        if carry_unwind_signal == "active":
            carry_patch.setdefault("state", "unwind_risk")
            carry_patch.setdefault("strength", 75.0)
        elif carry_unwind_signal == "inactive":
            carry_patch.setdefault("state", "neutral")
            carry_patch.setdefault("strength", 25.0)

        risk_state = signals.get("risk_appetite_signal")
        if risk_state is not None:
            risk_patch.setdefault("state", risk_state)
            risk_patch.setdefault("confidence", 70.0)

        yds = signals.get("yield_differential_signal")
        if yds == "usd_supportive":
            macro_patch.setdefault("regime_alignment", "supportive")
            carry_patch.setdefault("state", "favour_quote")
            carry_patch.setdefault("strength", max(float(carry_patch.get("strength", 0.0)), 70.0))
        elif yds == "gbp_supportive":
            macro_patch.setdefault("regime_alignment", "supportive")
            carry_patch.setdefault("state", "favour_base")
            carry_patch.setdefault("strength", max(float(carry_patch.get("strength", 0.0)), 70.0))
        elif yds == "mixed":
            macro_patch.setdefault("regime_alignment", "mixed")

    if isinstance(out.get("macro_coherence"), dict):
        out["macro_coherence"] = _normalize_macro_coherence_patch(out["macro_coherence"])

    if isinstance(out.get("carry_signal"), dict):
        out["carry_signal"] = _normalize_carry_signal_patch(out["carry_signal"])

    if isinstance(out.get("risk_appetite_signal"), dict):
        out["risk_appetite_signal"] = _normalize_risk_appetite_signal_patch(out["risk_appetite_signal"])

    if isinstance(out.get("pair_score"), dict):
        out["pair_score"] = _normalize_pair_score_patch(out["pair_score"])

    if isinstance(out.get("linked_refs"), dict):
        out["linked_refs"] = _normalize_linked_refs_patch(out["linked_refs"])

    return out


def _build_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    out["pair_outlook"] = {
        "coherence_score": out.get("macro_coherence", {}).get("score", 0.0),
        "direction_bias": out.get("pair_score", {}).get("direction_bias", "unknown"),
        "confidence": out.get("pair_score", {}).get("conviction", 0.0),
        "summary": out.get("pair_score", {}).get("summary", ""),
    }

    carry_state = out.get("carry_signal", {}).get("state", "unknown")
    if carry_state == "unwind_risk":
        carry_unwind_signal = "active"
    elif carry_state == "neutral":
        carry_unwind_signal = "inactive"
    else:
        carry_unwind_signal = "unknown"

    yield_signal = "unknown"
    if carry_state == "favour_quote":
        yield_signal = "usd_supportive"
    elif carry_state == "favour_base":
        yield_signal = "gbp_supportive"

    out["signals"] = {
        "carry_unwind_signal": carry_unwind_signal,
        "risk_appetite_signal": out.get("risk_appetite_signal", {}).get("state", "unknown"),
        "yield_differential_signal": yield_signal,
    }

    return out


def build_pair_context_payload(
    *,
    pair: str,
    base_country_ref: str,
    quote_country_ref: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.pair_context_store",
    macro_coherence_patch: Optional[Dict[str, Any]] = None,
    carry_signal_patch: Optional[Dict[str, Any]] = None,
    risk_appetite_signal_patch: Optional[Dict[str, Any]] = None,
    pair_score_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    pair_s = str(pair).upper().strip()
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    macro_coherence_patch = _normalize_macro_coherence_patch(macro_coherence_patch)
    carry_signal_patch = _normalize_carry_signal_patch(carry_signal_patch)
    risk_appetite_signal_patch = _normalize_risk_appetite_signal_patch(risk_appetite_signal_patch)
    pair_score_patch = _normalize_pair_score_patch(pair_score_patch)
    linked_refs_patch = _normalize_linked_refs_patch(linked_refs_patch)
    payload_patch = _normalize_payload_patch(payload_patch)

    payload: Dict[str, Any] = {
        "pair_context_id": f"pair/{pair_s}/context/{as_of_date_s}",
        "pair": pair_s,
        "base_country_ref": base_country_ref,
        "quote_country_ref": quote_country_ref,
        "as_of_date": as_of_date_s,
        "macro_coherence": {
            "score": 0.0,
            "regime_alignment": "unknown",
            "notes": "",
        },
        "carry_signal": {
            "state": "unknown",
            "strength": 0.0,
            "notes": "",
        },
        "risk_appetite_signal": {
            "state": "unknown",
            "confidence": 0.0,
            "notes": "",
        },
        "pair_score": {
            "direction_bias": "unknown",
            "conviction": 0.0,
            "summary": "",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if macro_coherence_patch:
        payload["macro_coherence"] = _deep_merge(payload["macro_coherence"], macro_coherence_patch)
    if carry_signal_patch:
        payload["carry_signal"] = _deep_merge(payload["carry_signal"], carry_signal_patch)
    if risk_appetite_signal_patch:
        payload["risk_appetite_signal"] = _deep_merge(
            payload["risk_appetite_signal"],
            risk_appetite_signal_patch,
        )
    if pair_score_patch:
        payload["pair_score"] = _deep_merge(payload["pair_score"], pair_score_patch)
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if isinstance(payload.get("macro_coherence"), dict):
        payload["macro_coherence"] = _normalize_macro_coherence_patch(payload["macro_coherence"])
    if isinstance(payload.get("carry_signal"), dict):
        payload["carry_signal"] = _normalize_carry_signal_patch(payload["carry_signal"])
    if isinstance(payload.get("risk_appetite_signal"), dict):
        payload["risk_appetite_signal"] = _normalize_risk_appetite_signal_patch(payload["risk_appetite_signal"])
    if isinstance(payload.get("pair_score"), dict):
        payload["pair_score"] = _normalize_pair_score_patch(payload["pair_score"])
    if isinstance(payload.get("linked_refs"), dict):
        payload["linked_refs"] = _normalize_linked_refs_patch(payload["linked_refs"])

    if validate:
        validate_payload("pair_context", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_pair_context_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    canonical_payload = deepcopy(payload)
    canonical_payload.pop("pair_outlook", None)
    canonical_payload.pop("signals", None)

    if validate:
        validate_payload("pair_context", canonical_payload, version=SCHEMA_PACK_VERSION)

    path = pair_context_storage_path(
        canonical_payload["pair"],
        canonical_payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_pair_context_payload(
    pair: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = pair_context_storage_path(pair, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Pair context not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("pair_context", payload, version=SCHEMA_PACK_VERSION)
    return _build_legacy_aliases(payload)


class PairContextStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "pair_contexts"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, pair: str, as_of_date: Any) -> Path:
        return pair_context_storage_path(pair, as_of_date, base_dir=self.base_dir)

    def save_pair_context(
        self,
        *,
        pair: str,
        base_country_ref: str,
        quote_country_ref: str,
        as_of_date: Any,
        generated_by: str = "aion_equities.pair_context_store",
        macro_coherence_patch: Optional[Dict[str, Any]] = None,
        carry_signal_patch: Optional[Dict[str, Any]] = None,
        risk_appetite_signal_patch: Optional[Dict[str, Any]] = None,
        pair_score_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        payload = build_pair_context_payload(
            pair=pair,
            base_country_ref=base_country_ref,
            quote_country_ref=quote_country_ref,
            as_of_date=as_of_date,
            generated_by=generated_by,
            macro_coherence_patch=macro_coherence_patch,
            carry_signal_patch=carry_signal_patch,
            risk_appetite_signal_patch=risk_appetite_signal_patch,
            pair_score_patch=pair_score_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_pair_context_payload(payload, base_dir=self.base_dir, validate=False)
        return _build_legacy_aliases(payload)

    def save_context(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_pair_context(**kwargs)

    def load_pair_context(
        self,
        pair: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_pair_context_payload(
            pair,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_context(
        self,
        pair: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_pair_context(pair, as_of_date, validate=validate)

    def load_pair_context_by_id(
        self,
        pair_context_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        parts = str(pair_context_id).split("/")
        if len(parts) != 4 or parts[0] != "pair" or parts[2] != "context":
            raise ValueError(f"Invalid pair_context_id: {pair_context_id!r}")

        pair = parts[1]
        as_of_date = parts[3]
        return self.load_pair_context(pair, as_of_date, validate=validate)

    def load_context_by_id(
        self,
        pair_context_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_pair_context_by_id(pair_context_id, validate=validate)

    def pair_context_exists(self, pair: str, as_of_date: Any) -> bool:
        return self.storage_path(pair, as_of_date).exists()

    def context_exists(self, pair: str, as_of_date: Any) -> bool:
        return self.pair_context_exists(pair, as_of_date)

    def list_pair_contexts(self, pair: str) -> List[str]:
        pair_dir = self.base_dir / _safe_segment(str(pair).upper())
        if not pair_dir.exists():
            return []
        return sorted(p.stem for p in pair_dir.glob("*.json"))


__all__ = [
    "build_pair_context_payload",
    "save_pair_context_payload",
    "load_pair_context_payload",
    "PairContextStore",
]
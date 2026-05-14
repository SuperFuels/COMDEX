from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


_ESTIMATE_META_PREFIX = "__estimate_meta__:"
_CONSENSUS_META_PREFIX = "__consensus_meta__:"
_SIGNAL_META_PREFIX = "__signal_meta__:"


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
    return Path(__file__).resolve().parent / "data" / "pre_earnings_estimates"


def pre_earnings_estimate_storage_path(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


def _normalize_window_label(days_to_report: int) -> str:
    if days_to_report >= 60:
        return "far"
    if days_to_report >= 21:
        return "building"
    if days_to_report >= 7:
        return "decision_window"
    return "imminent"


def _normalize_driver_impact_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, str):
        return {
            "driver": item,
            "impact_direction": "neutral",
            "magnitude": 0.0,
        }

    if not isinstance(item, dict):
        return {
            "driver": str(item),
            "impact_direction": "neutral",
            "magnitude": 0.0,
        }

    out: Dict[str, Any] = {
        "driver": item.get("driver", item.get("name", "unknown")),
        "impact_direction": item.get("impact_direction", item.get("direction", "neutral")),
        "magnitude": float(item.get("magnitude", item.get("impact_score", 0.0))),
    }

    if "target_metric" in item:
        out["target_metric"] = item["target_metric"]
    elif "metric" in item:
        out["target_metric"] = item["metric"]

    if "notes" in item:
        out["notes"] = item["notes"]
    elif "summary" in item:
        out["notes"] = item["summary"]

    return out


def _normalize_driver_impacts(items: Optional[List[Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    return [_normalize_driver_impact_item(x) for x in items]


def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    out = deepcopy(patch)

    if "structural_profile_refs" in out and "company_profile_refs" not in out:
        out["company_profile_refs"] = deepcopy(out.pop("structural_profile_refs"))
    else:
        out.pop("structural_profile_refs", None)

    if "fingerprint_refs" in out and "company_fingerprint_refs" not in out:
        out["company_fingerprint_refs"] = deepcopy(out.pop("fingerprint_refs"))
    else:
        out.pop("fingerprint_refs", None)

    return out


def _append_meta(base_text: str, prefix: str, payload: Optional[Dict[str, Any]]) -> str:
    text = str(base_text or "").strip()
    if not payload:
        return text

    clean = {k: v for k, v in payload.items() if v is not None}
    if not clean:
        return text

    meta = prefix + json.dumps(clean, ensure_ascii=False, sort_keys=True)
    if not text:
        return meta
    return f"{text}\n{meta}"


def _extract_meta(text: Any, prefix: str) -> Optional[Dict[str, Any]]:
    if not isinstance(text, str) or prefix not in text:
        return None

    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            raw = line[len(prefix):].strip()
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except Exception:
                return None
    return None


def _clean_meta_lines(text: Any, prefixes: List[str]) -> str:
    if not isinstance(text, str):
        return ""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if any(s.startswith(p) for p in prefixes):
            continue
        if s:
            lines.append(line)
    return "\n".join(lines).strip()


def _allowed_signal_flags_from_patch(signal_patch: Optional[Dict[str, Any]]) -> List[str]:
    if not signal_patch:
        return []

    flags: List[str] = []

    if signal_patch.get("long_candidate"):
        flags.append("consensus_gap_long")
    if signal_patch.get("short_candidate"):
        flags.append("consensus_gap_short")

    strength = signal_patch.get("catalyst_strength")
    try:
        s = float(strength)
        if s < 40 and "low_confidence" not in flags:
            flags.append("low_confidence")
    except Exception:
        pass

    return flags


def _clean_signal_flags(signal_flags: Any) -> List[str]:
    if not isinstance(signal_flags, list):
        return []
    return [str(item) for item in signal_flags]


def _direction_from_number(value: Any) -> str:
    try:
        x = float(value)
    except Exception:
        return "unknown"
    if x > 0:
        return "up"
    if x < 0:
        return "down"
    return "flat"


def _quality_from_eps(value: Any) -> str:
    try:
        x = float(value)
    except Exception:
        return "unknown"
    if x > 0:
        return "beat"
    if x < 0:
        return "miss"
    return "in_line"


def _build_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    out["estimate_id"] = out["pre_earnings_estimate_id"]

    summary = out.get("estimate_summary", {})
    if isinstance(summary, dict):
        out["estimate_direction"] = {
            "revenue": summary.get("revenue_direction", "unknown"),
            "margin": summary.get("margin_direction", "unknown"),
            "quality": summary.get("expected_quality", "unknown"),
        }

    consensus = out.get("consensus_comparison", {})
    if isinstance(consensus, dict):
        out["consensus_state"] = consensus.get("consensus_state", "unknown")
        out["divergence_score"] = consensus.get("divergence_score", 0.0)

    linked = out.get("linked_refs", {})
    if isinstance(linked, dict):
        if "company_profile_refs" in linked:
            linked["structural_profile_refs"] = deepcopy(linked["company_profile_refs"])
        if "company_fingerprint_refs" in linked:
            linked["fingerprint_refs"] = deepcopy(linked["company_fingerprint_refs"])

    estimate_summary = out.get("estimate_summary", {})
    consensus_comparison = out.get("consensus_comparison", {})

    estimate_meta = _extract_meta(estimate_summary.get("summary", ""), _ESTIMATE_META_PREFIX) or {}
    consensus_meta = _extract_meta(consensus_comparison.get("consensus_notes", ""), _CONSENSUS_META_PREFIX) or {}
    signal_meta = _extract_meta(estimate_summary.get("summary", ""), _SIGNAL_META_PREFIX) or {}

    out["fiscal_period_ref"] = out.get("estimate_window", {}).get("quarter_label", "")

    out["estimate"] = {
        "revenue_impact_pct": estimate_meta.get("revenue_impact_pct", 0.0),
        "margin_impact_bps": estimate_meta.get("margin_impact_bps", 0.0),
        "eps_impact_pct": estimate_meta.get("eps_impact_pct", 0.0),
    }

    out["consensus"] = {
        "street_revenue_impact_pct": consensus_meta.get("street_revenue_impact_pct", 0.0),
        "street_margin_impact_bps": consensus_meta.get("street_margin_impact_bps", 0.0),
        "street_eps_impact_pct": consensus_meta.get("street_eps_impact_pct", 0.0),
    }

    out["divergence"] = {
        "divergence_score": consensus_comparison.get("divergence_score", 0.0),
        "direction": consensus_meta.get("direction", consensus_comparison.get("consensus_state", "unknown")),
        "confidence": consensus_meta.get(
            "confidence",
            estimate_summary.get("analytical_confidence", 0.0),
        ),
    }

    flags = set(out.get("signal_flags", []))
    out["signal"] = {
        "long_candidate": bool(signal_meta.get("long_candidate", "consensus_gap_long" in flags)),
        "short_candidate": bool(signal_meta.get("short_candidate", "consensus_gap_short" in flags)),
        "catalyst_strength": float(signal_meta.get("catalyst_strength", 0.0)),
    }

    if isinstance(out.get("estimate_summary"), dict):
        out["estimate_summary"]["summary"] = _clean_meta_lines(
            out["estimate_summary"].get("summary", ""),
            [_ESTIMATE_META_PREFIX, _SIGNAL_META_PREFIX],
        )

    if isinstance(out.get("consensus_comparison"), dict):
        out["consensus_comparison"]["consensus_notes"] = _clean_meta_lines(
            out["consensus_comparison"].get("consensus_notes", ""),
            [_CONSENSUS_META_PREFIX],
        )

    out["signal_flags"] = _clean_signal_flags(out.get("signal_flags", []))

    return out


def build_pre_earnings_estimate_payload(
    *,
    company_ref: str,
    as_of_date: Any,
    next_report_date: Optional[Any] = None,
    fiscal_period_ref: Optional[str] = None,
    generated_by: str = "aion_equities.pre_earnings_estimate_store",
    estimate_window_patch: Optional[Dict[str, Any]] = None,
    estimate_summary_patch: Optional[Dict[str, Any]] = None,
    consensus_comparison_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    driver_impacts: Optional[List[Any]] = None,
    signal_flags: Optional[List[str]] = None,
    estimate_patch: Optional[Dict[str, Any]] = None,
    consensus_patch: Optional[Dict[str, Any]] = None,
    divergence_patch: Optional[Dict[str, Any]] = None,
    signal_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    next_report_date_s = _date_str(next_report_date if next_report_date is not None else as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    as_of_d = date.fromisoformat(as_of_date_s)
    next_report_d = date.fromisoformat(next_report_date_s)
    days_to_report = max((next_report_d - as_of_d).days, 0)

    linked_refs_patch = _normalize_linked_refs_patch(linked_refs_patch)

    payload: Dict[str, Any] = {
        "pre_earnings_estimate_id": f"{company_ref}/pre_earnings/{as_of_date_s}",
        "company_ref": company_ref,
        "as_of_date": as_of_date_s,
        "next_report_date": next_report_date_s,
        "estimate_window": {
            "window_label": _normalize_window_label(days_to_report),
            "days_to_report": days_to_report,
            "quarter_label": fiscal_period_ref or "",
        },
        "estimate_summary": {
            "revenue_direction": "unknown",
            "margin_direction": "unknown",
            "expected_quality": "unknown",
            "analytical_confidence": 0.0,
            "summary": "",
        },
        "consensus_comparison": {
            "consensus_state": "unknown",
            "divergence_score": 0.0,
            "consensus_notes": "",
        },
        "driver_impacts": [],
        "signal_flags": [],
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if estimate_window_patch:
        payload["estimate_window"] = _deep_merge(payload["estimate_window"], estimate_window_patch)

    if estimate_summary_patch:
        payload["estimate_summary"] = _deep_merge(payload["estimate_summary"], estimate_summary_patch)

    if consensus_comparison_patch:
        payload["consensus_comparison"] = _deep_merge(
            payload["consensus_comparison"],
            consensus_comparison_patch,
        )

    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)

    if driver_impacts:
        payload["driver_impacts"] = _normalize_driver_impacts(driver_impacts)

    if signal_flags:
        payload["signal_flags"] = list(signal_flags)

    if estimate_patch:
        payload["estimate_summary"] = _deep_merge(
            payload["estimate_summary"],
            {
                "revenue_direction": _direction_from_number(estimate_patch.get("revenue_impact_pct")),
                "margin_direction": _direction_from_number(estimate_patch.get("margin_impact_bps")),
                "expected_quality": _quality_from_eps(estimate_patch.get("eps_impact_pct")),
            },
        )
        payload["estimate_summary"]["summary"] = _append_meta(
            payload["estimate_summary"].get("summary", ""),
            _ESTIMATE_META_PREFIX,
            estimate_patch,
        )

    if divergence_patch:
        divergence_score = float(divergence_patch.get("divergence_score", 0.0))
        direction = str(divergence_patch.get("direction", "unknown"))
        payload["consensus_comparison"] = _deep_merge(
            payload["consensus_comparison"],
            {
                "divergence_score": divergence_score,
                "consensus_state": direction,
            },
        )

    consensus_meta: Dict[str, Any] = {}
    if consensus_patch:
        consensus_meta.update(consensus_patch)
    if divergence_patch:
        consensus_meta.update(
            {
                "direction": divergence_patch.get("direction", "unknown"),
                "confidence": divergence_patch.get("confidence", 0.0),
            }
        )
        payload["estimate_summary"]["analytical_confidence"] = float(
            divergence_patch.get("confidence", payload["estimate_summary"].get("analytical_confidence", 0.0))
        )

    if consensus_meta:
        payload["consensus_comparison"]["consensus_notes"] = _append_meta(
            payload["consensus_comparison"].get("consensus_notes", ""),
            _CONSENSUS_META_PREFIX,
            consensus_meta,
        )

    if signal_patch:
        payload["signal_flags"] = list(
            {
                *payload.get("signal_flags", []),
                *_allowed_signal_flags_from_patch(signal_patch),
            }
        )
        payload["estimate_summary"]["summary"] = _append_meta(
            payload["estimate_summary"].get("summary", ""),
            _SIGNAL_META_PREFIX,
            signal_patch,
        )

    if payload_patch:
        payload = _deep_merge(payload, deepcopy(payload_patch))

    if isinstance(payload.get("linked_refs"), dict):
        payload["linked_refs"] = _normalize_linked_refs_patch(payload["linked_refs"])

    if isinstance(payload.get("driver_impacts"), list):
        payload["driver_impacts"] = _normalize_driver_impacts(payload["driver_impacts"])

    if estimate_patch:
        payload["estimate_summary"]["summary"] = _append_meta(
            _clean_meta_lines(
                payload["estimate_summary"].get("summary", ""),
                [_ESTIMATE_META_PREFIX, _SIGNAL_META_PREFIX],
            ),
            _ESTIMATE_META_PREFIX,
            estimate_patch,
        )

    if signal_patch:
        payload["estimate_summary"]["summary"] = _append_meta(
            payload["estimate_summary"].get("summary", ""),
            _SIGNAL_META_PREFIX,
            signal_patch,
        )

    if consensus_meta:
        payload["consensus_comparison"]["consensus_notes"] = _append_meta(
            _clean_meta_lines(payload["consensus_comparison"].get("consensus_notes", ""), [_CONSENSUS_META_PREFIX]),
            _CONSENSUS_META_PREFIX,
            consensus_meta,
        )

    if validate:
        validate_payload("pre_earnings_estimate", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_pre_earnings_estimate_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    canonical_payload = deepcopy(payload)

    canonical_payload.pop("estimate_id", None)
    canonical_payload.pop("estimate_direction", None)
    canonical_payload.pop("consensus_state", None)
    canonical_payload.pop("divergence_score", None)
    canonical_payload.pop("fiscal_period_ref", None)
    canonical_payload.pop("estimate", None)
    canonical_payload.pop("consensus", None)
    canonical_payload.pop("divergence", None)
    canonical_payload.pop("signal", None)

    if isinstance(canonical_payload.get("linked_refs"), dict):
        canonical_payload["linked_refs"].pop("structural_profile_refs", None)
        canonical_payload["linked_refs"].pop("fingerprint_refs", None)

    if validate:
        validate_payload("pre_earnings_estimate", canonical_payload, version=SCHEMA_PACK_VERSION)

    path = pre_earnings_estimate_storage_path(
        canonical_payload["company_ref"],
        canonical_payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_pre_earnings_estimate_payload(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = pre_earnings_estimate_storage_path(company_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Pre earnings estimate not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("pre_earnings_estimate", payload, version=SCHEMA_PACK_VERSION)

    return _build_legacy_aliases(payload)


class PreEarningsEstimateStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "pre_earnings_estimates"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, as_of_date: Any) -> Path:
        return pre_earnings_estimate_storage_path(
            company_ref=company_ref,
            as_of_date=as_of_date,
            base_dir=self.base_dir,
        )

    def load_pre_earnings_estimate_by_id(
        self,
        pre_earnings_estimate_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        parts = str(pre_earnings_estimate_id).split("/pre_earnings/")
        if len(parts) != 2:
            raise ValueError(f"Invalid pre_earnings_estimate_id: {pre_earnings_estimate_id!r}")
        company_ref, as_of_date = parts
        return self.load_pre_earnings_estimate(company_ref, as_of_date, validate=validate)

    def save_pre_earnings_estimate(
        self,
        *,
        company_ref: str,
        as_of_date: Any,
        fiscal_period_ref: Optional[str] = None,
        next_report_date: Optional[Any] = None,
        generated_by: str = "aion_equities.pre_earnings_estimate_store",
        estimate_window_patch: Optional[Dict[str, Any]] = None,
        estimate_summary_patch: Optional[Dict[str, Any]] = None,
        consensus_comparison_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        driver_impacts: Optional[List[Any]] = None,
        signal_flags: Optional[List[str]] = None,
        estimate_patch: Optional[Dict[str, Any]] = None,
        consensus_patch: Optional[Dict[str, Any]] = None,
        divergence_patch: Optional[Dict[str, Any]] = None,
        signal_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        period_ref = legacy_kwargs.pop("period_ref", None)
        window_ref = legacy_kwargs.pop("window_ref", None)

        if fiscal_period_ref is None:
            fiscal_period_ref = period_ref or window_ref

        if next_report_date is None:
            next_report_date = legacy_kwargs.pop("report_date", None)

        if next_report_date is None:
            next_report_date = as_of_date

        payload = build_pre_earnings_estimate_payload(
            company_ref=company_ref,
            as_of_date=as_of_date,
            next_report_date=next_report_date,
            fiscal_period_ref=fiscal_period_ref,
            generated_by=generated_by,
            estimate_window_patch=estimate_window_patch,
            estimate_summary_patch=estimate_summary_patch,
            consensus_comparison_patch=consensus_comparison_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            driver_impacts=driver_impacts,
            signal_flags=signal_flags,
            estimate_patch=estimate_patch,
            consensus_patch=consensus_patch,
            divergence_patch=divergence_patch,
            signal_patch=signal_patch,
            validate=validate,
        )
        save_pre_earnings_estimate_payload(
            payload,
            base_dir=self.base_dir,
            validate=False,
        )
        return _build_legacy_aliases(payload)

    def save_estimate(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_pre_earnings_estimate(**kwargs)

    def load_pre_earnings_estimate(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_pre_earnings_estimate_payload(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_estimate(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_pre_earnings_estimate(
            company_ref,
            as_of_date,
            validate=validate,
        )

    def pre_earnings_estimate_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(company_ref, as_of_date).exists()

    def estimate_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.pre_earnings_estimate_exists(company_ref, as_of_date)

    def list_estimates(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))


__all__ = [
    "build_pre_earnings_estimate_payload",
    "save_pre_earnings_estimate_payload",
    "load_pre_earnings_estimate_payload",
    "PreEarningsEstimateStore",
]
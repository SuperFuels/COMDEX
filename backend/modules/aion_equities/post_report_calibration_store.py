from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


_PREDICTION_QUALITY_META_PREFIX = "__prediction_quality_meta__:"
_ADJUSTMENT_META_PREFIX = "__adjustment_meta__:"
_LEARNING_META_PREFIX = "__learning_meta__:"


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
    return Path(__file__).resolve().parent / "data" / "post_report_calibrations"


def post_report_calibration_storage_path(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


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
        s = line.strip()
        if s.startswith(prefix):
            raw = s[len(prefix):].strip()
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
    lines: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if any(s.startswith(p) for p in prefixes):
            continue
        if s:
            lines.append(line)
    return "\n".join(lines).strip()


def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _prediction_quality_from_patch(patch: Optional[Dict[str, Any]]) -> Optional[str]:
    if not patch:
        return None

    if "prediction_quality" in patch:
        return str(patch["prediction_quality"])

    direction_correct = patch.get("direction_correct")
    magnitude_error_pct = patch.get("magnitude_error_pct")
    calibration_score = patch.get("confidence_calibration_score")

    try:
        err = float(magnitude_error_pct) if magnitude_error_pct is not None else None
    except Exception:
        err = None

    try:
        cscore = float(calibration_score) if calibration_score is not None else None
    except Exception:
        cscore = None

    if direction_correct is True and err is not None and err <= 5 and (cscore is None or cscore >= 80):
        return "strong"
    if direction_correct is True and err is not None and err <= 15:
        return "acceptable"
    if direction_correct is False and err is not None and err >= 25:
        return "failed"
    if direction_correct is False:
        return "weak"
    return "acceptable"


def _build_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    out["fiscal_period_ref"] = out.get("report_ref", "")
    out["prediction_quality"] = out.get("prediction_comparison", {}).get("prediction_quality", "acceptable")

    pred = out.get("prediction_comparison", {})
    calib = out.get("calibration_actions", {})
    drift = out.get("confidence_drift", {})

    pred_meta = _extract_meta(pred.get("summary", ""), _PREDICTION_QUALITY_META_PREFIX) or {}
    adjust_meta = _extract_meta(calib.get("guidance_notes", ""), _ADJUSTMENT_META_PREFIX) or {}
    learning_meta = _extract_meta(drift.get("drift_reason", ""), _LEARNING_META_PREFIX) or {}

    out["prediction_quality_patch"] = pred_meta
    out["adjustment_patch"] = adjust_meta
    out["learning_patch"] = learning_meta

    if isinstance(out.get("prediction_comparison"), dict):
        out["prediction_comparison"]["summary"] = _clean_meta_lines(
            out["prediction_comparison"].get("summary", ""),
            [_PREDICTION_QUALITY_META_PREFIX],
        )

    if isinstance(out.get("calibration_actions"), dict):
        out["calibration_actions"]["guidance_notes"] = _clean_meta_lines(
            out["calibration_actions"].get("guidance_notes", ""),
            [_ADJUSTMENT_META_PREFIX],
        )

    if isinstance(out.get("confidence_drift"), dict):
        out["confidence_drift"]["drift_reason"] = _clean_meta_lines(
            out["confidence_drift"].get("drift_reason", ""),
            [_LEARNING_META_PREFIX],
        )

    return out


def build_post_report_calibration_payload(
    *,
    company_ref: str,
    as_of_date: Any,
    report_ref: str,
    prediction_ref: str,
    generated_by: str = "aion_equities.post_report_calibration_store",
    actuals_patch: Optional[Dict[str, Any]] = None,
    prediction_comparison_patch: Optional[Dict[str, Any]] = None,
    calibration_actions_patch: Optional[Dict[str, Any]] = None,
    confidence_drift_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    prediction_quality_patch: Optional[Dict[str, Any]] = None,
    adjustment_patch: Optional[Dict[str, Any]] = None,
    learning_patch: Optional[Dict[str, Any]] = None,
    validate: bool = True,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "post_report_calibration_id": f"{company_ref}/calibration/{as_of_date_s}",
        "company_ref": company_ref,
        "as_of_date": as_of_date_s,
        "report_ref": report_ref,
        "prediction_ref": prediction_ref,
        "actuals": {
            "reported_revenue": 0.0,
            "reported_operating_margin": 0.0,
            "reported_eps": 0.0,
            "reported_free_cash_flow": 0.0,
            "notes": "",
        },
        "prediction_comparison": {
            "revenue_error_pct": 0.0,
            "margin_error_bps": 0.0,
            "eps_error_pct": 0.0,
            "fcf_error_pct": 0.0,
            "prediction_quality": "acceptable",
            "summary": "",
        },
        "calibration_actions": {
            "sensitivity_update_required": False,
            "lag_update_required": False,
            "guidance_bias_update_required": False,
            "sensitivity_notes": "",
            "lag_notes": "",
            "guidance_notes": "",
        },
        "confidence_drift": {
            "previous_confidence": 0.0,
            "new_confidence": 0.0,
            "drift_reason": "",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if actuals_patch:
        payload["actuals"] = _deep_merge(payload["actuals"], actuals_patch)

    if prediction_comparison_patch:
        payload["prediction_comparison"] = _deep_merge(
            payload["prediction_comparison"],
            prediction_comparison_patch,
        )

    if calibration_actions_patch:
        payload["calibration_actions"] = _deep_merge(
            payload["calibration_actions"],
            calibration_actions_patch,
        )

    if confidence_drift_patch:
        payload["confidence_drift"] = _deep_merge(
            payload["confidence_drift"],
            confidence_drift_patch,
        )

    if linked_refs_patch:
        payload["linked_refs"] = _normalize_linked_refs_patch(linked_refs_patch)

    if prediction_quality_patch:
        pq = _prediction_quality_from_patch(prediction_quality_patch)
        if pq is not None:
            payload["prediction_comparison"]["prediction_quality"] = pq
        payload["prediction_comparison"]["summary"] = _append_meta(
            payload["prediction_comparison"].get("summary", ""),
            _PREDICTION_QUALITY_META_PREFIX,
            prediction_quality_patch,
        )

    if adjustment_patch:
        sensitivity_update_strength = adjustment_patch.get("sensitivity_update_strength")
        lag_update_days = adjustment_patch.get("lag_update_days")
        guidance_bias_shift = adjustment_patch.get("guidance_bias_shift")

        if sensitivity_update_strength is not None:
            try:
                payload["calibration_actions"]["sensitivity_update_required"] = float(sensitivity_update_strength) != 0.0
            except Exception:
                pass

        if lag_update_days is not None:
            try:
                payload["calibration_actions"]["lag_update_required"] = int(lag_update_days) != 0
            except Exception:
                pass

        if guidance_bias_shift is not None:
            payload["calibration_actions"]["guidance_bias_update_required"] = str(guidance_bias_shift) not in {"stable", "none", "unknown", ""}

        payload["calibration_actions"]["guidance_notes"] = _append_meta(
            payload["calibration_actions"].get("guidance_notes", ""),
            _ADJUSTMENT_META_PREFIX,
            adjustment_patch,
        )

    if learning_patch:
        prev_conf = payload["confidence_drift"].get("previous_confidence", 0.0)
        try:
            prev_conf = float(prev_conf)
        except Exception:
            prev_conf = 0.0

        penalty = float(learning_patch.get("confidence_penalty_bps", 0.0) or 0.0) / 100.0
        boost = float(learning_patch.get("confidence_boost_bps", 0.0) or 0.0) / 100.0
        new_conf = max(0.0, min(100.0, prev_conf - penalty + boost))

        payload["confidence_drift"] = _deep_merge(
            payload["confidence_drift"],
            {
                "new_confidence": new_conf,
            },
        )

        payload["confidence_drift"]["drift_reason"] = _append_meta(
            payload["confidence_drift"].get("drift_reason", ""),
            _LEARNING_META_PREFIX,
            learning_patch,
        )

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    if prediction_quality_patch:
        payload["prediction_comparison"]["summary"] = _append_meta(
            _clean_meta_lines(payload["prediction_comparison"].get("summary", ""), [_PREDICTION_QUALITY_META_PREFIX]),
            _PREDICTION_QUALITY_META_PREFIX,
            prediction_quality_patch,
        )

    if adjustment_patch:
        payload["calibration_actions"]["guidance_notes"] = _append_meta(
            _clean_meta_lines(payload["calibration_actions"].get("guidance_notes", ""), [_ADJUSTMENT_META_PREFIX]),
            _ADJUSTMENT_META_PREFIX,
            adjustment_patch,
        )

    if learning_patch:
        payload["confidence_drift"]["drift_reason"] = _append_meta(
            _clean_meta_lines(payload["confidence_drift"].get("drift_reason", ""), [_LEARNING_META_PREFIX]),
            _LEARNING_META_PREFIX,
            learning_patch,
        )

    if validate:
        validate_payload("post_report_calibration", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_post_report_calibration_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("post_report_calibration", payload, version=SCHEMA_PACK_VERSION)

    path = post_report_calibration_storage_path(
        payload["company_ref"],
        payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_post_report_calibration_payload(
    company_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = post_report_calibration_storage_path(company_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Post report calibration not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("post_report_calibration", payload, version=SCHEMA_PACK_VERSION)
    return _build_legacy_aliases(payload)


class PostReportCalibrationStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "post_report_calibrations"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, as_of_date: Any) -> Path:
        return post_report_calibration_storage_path(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
        )

    def load_post_report_calibration_by_id(
        self,
        post_report_calibration_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        parts = str(post_report_calibration_id).split("/calibration/")
        if len(parts) != 2:
            raise ValueError(f"Invalid post_report_calibration_id: {post_report_calibration_id!r}")
        company_ref, as_of_date = parts
        return self.load_post_report_calibration(company_ref, as_of_date, validate=validate)

    def save_post_report_calibration(
        self,
        *,
        company_ref: str,
        as_of_date: Any,
        report_ref: Optional[str] = None,
        prediction_ref: Optional[str] = None,
        fiscal_period_ref: Optional[str] = None,
        generated_by: str = "aion_equities.post_report_calibration_store",
        actuals_patch: Optional[Dict[str, Any]] = None,
        prediction_comparison_patch: Optional[Dict[str, Any]] = None,
        calibration_actions_patch: Optional[Dict[str, Any]] = None,
        confidence_drift_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        prediction_quality_patch: Optional[Dict[str, Any]] = None,
        adjustment_patch: Optional[Dict[str, Any]] = None,
        learning_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        period_ref = legacy_kwargs.pop("period_ref", None)
        if fiscal_period_ref is None:
            fiscal_period_ref = period_ref

        if report_ref is None:
            if fiscal_period_ref:
                report_ref = f"{company_ref}/quarter/{fiscal_period_ref}"
            else:
                report_ref = f"{company_ref}/quarter/{_date_str(as_of_date)}"

        if prediction_ref is None:
            pre_refs: List[str] = []
            if isinstance(linked_refs_patch, dict):
                pre_refs = list(linked_refs_patch.get("pre_earnings_refs", []) or [])
            if pre_refs:
                prediction_ref = str(pre_refs[0])
            elif fiscal_period_ref:
                prediction_ref = f"{company_ref}/pre_earnings/{_date_str(as_of_date)}"
            else:
                prediction_ref = f"{company_ref}/pre_earnings/{_date_str(as_of_date)}"

        payload = build_post_report_calibration_payload(
            company_ref=company_ref,
            as_of_date=as_of_date,
            report_ref=report_ref,
            prediction_ref=prediction_ref,
            generated_by=generated_by,
            actuals_patch=actuals_patch,
            prediction_comparison_patch=prediction_comparison_patch,
            calibration_actions_patch=calibration_actions_patch,
            confidence_drift_patch=confidence_drift_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            prediction_quality_patch=prediction_quality_patch,
            adjustment_patch=adjustment_patch,
            learning_patch=learning_patch,
            validate=validate,
        )
        save_post_report_calibration_payload(payload, base_dir=self.base_dir, validate=False)
        return _build_legacy_aliases(payload)

    def save_calibration(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_post_report_calibration(**kwargs)

    def load_post_report_calibration(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_post_report_calibration_payload(
            company_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_calibration(
        self,
        company_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_post_report_calibration(company_ref, as_of_date, validate=validate)

    def post_report_calibration_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(company_ref, as_of_date).exists()

    def calibration_exists(self, company_ref: str, as_of_date: Any) -> bool:
        return self.post_report_calibration_exists(company_ref, as_of_date)

    def list_calibrations(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))


__all__ = [
    "build_post_report_calibration_payload",
    "save_post_report_calibration_payload",
    "load_post_report_calibration_payload",
    "PostReportCalibrationStore",
]
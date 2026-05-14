from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.modules.aion_equities.aion_equities_container_adapter import (
    AIONEquitiesContainerAdapter,
)
from backend.modules.aion_equities.sqi_mapping import build_sqi_signal_inputs


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _neutral_context() -> Dict[str, Any]:
    return {
        "kg": {
            "supports_count": 0,
            "contradicts_count": 0,
            "drift_score": 0.0,
            "confidence_modifier": 0.0,
            "pattern_match_score": 0.0,
        },
        "pattern": {
            "aggregate_score": 0.0,
            "stability_modifier": 0.0,
        },
        "observer": {
            "bias_penalty": 0.0,
        },
    }


def _status_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def _derive_company_coherence(company: Dict[str, Any]) -> float:
    profile = company.get("predictability_profile", {}) or {}
    acs_band = str(profile.get("acs_band", "")).strip().lower()
    sector_tier = str(profile.get("sector_confidence_tier", "")).strip().lower()

    score = 0.45
    if acs_band == "high":
        score += 0.25
    elif acs_band == "medium":
        score += 0.12

    if sector_tier == "tier_1":
        score += 0.15
    elif sector_tier == "tier_2":
        score += 0.08

    return _clamp01(score)


def _derive_trigger_map_coherence(trigger_map: Dict[str, Any]) -> float:
    summary = trigger_map.get("summary", {}) or {}
    confirmed = float(summary.get("confirmed_trigger_count", 0) or 0)
    active = float(summary.get("active_trigger_count", 0) or 0)
    broken = float(summary.get("broken_trigger_count", 0) or 0)

    triggers = trigger_map.get("triggers")
    if triggers is None:
        triggers = trigger_map.get("trigger_entries", [])
    triggers = triggers or []

    total = max(float(len(triggers)), active, confirmed + broken, 1.0)
    score = 0.50 + 0.25 * (confirmed / total) - 0.20 * (broken / total)
    return _clamp01(score)


def _derive_pre_earnings_coherence(estimate: Dict[str, Any]) -> float:
    divergence = estimate.get("divergence", {}) or {}
    signal = estimate.get("signal", {}) or {}

    divergence_score = float(divergence.get("divergence_score", 0.0) or 0.0)
    confidence = float(divergence.get("confidence", 0.0) or 0.0)
    catalyst_strength = float(signal.get("catalyst_strength", 0.0) or 0.0)
    directional_bonus = 0.08 if signal.get("long_candidate") or signal.get("short_candidate") else 0.0

    score = (
        0.20
        + 0.30 * min(divergence_score / 100.0, 1.0)
        + 0.30 * min(confidence / 100.0, 1.0)
        + 0.20 * min(catalyst_strength / 100.0, 1.0)
        + directional_bonus
    )
    return _clamp01(score)


def _extract_assessment_score(assessment: Dict[str, Any]) -> float:
    scores = assessment.get("scores", {}) or {}
    bqs = float(scores.get("business_quality_score", 0.0) or 0.0)
    acs = float(scores.get("analytical_confidence_score", 0.0) or 0.0)
    aot = float(scores.get("automation_opportunity_score", 0.0) or 0.0)
    return _clamp01((0.45 * bqs + 0.45 * acs + 0.10 * aot) / 100.0)


def _build_sqi_payload(
    *,
    assessment: Optional[Dict[str, Any]],
    context: Optional[Dict[str, Any]],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_context = deepcopy(context or _neutral_context())
    signals = (
        build_sqi_signal_inputs(assessment=assessment, context=resolved_context)
        if assessment is not None
        else {}
    )
    payload: Dict[str, Any] = {
        "method": "build_sqi_signal_inputs",
        "context": resolved_context,
        "signals": signals,
    }
    if extra:
        payload["extra"] = deepcopy(extra)
    return payload


class AIONEquitiesSQIContainerWriter:
    """
    Real writer for equities objects into UCS/SQI-ready containers.

    Notes:
    - Does not hard-code SQI/coherence values as constants.
    - Derives coherence from the object payload and, when available,
      routes assessment objects through build_sqi_signal_inputs(...).
    - Stamps the fields the runtime/tests expect:
      * meta.sqi_ready
      * runtime_context
      * sqi_context
      * sqi_payload
    """

    def __init__(
        self,
        *,
        container_adapter: Optional[AIONEquitiesContainerAdapter] = None,
    ) -> None:
        self.container_adapter = container_adapter or AIONEquitiesContainerAdapter()

    def _finalize_container(
        self,
        container: Dict[str, Any],
        *,
        object_type: str,
        source_ref: str,
        kg_node_ref: str,
        coherence_score: float,
        runtime_refs: Optional[Dict[str, Any]] = None,
        sqi_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        out = deepcopy(container)
        out.setdefault("meta", {})
        out["meta"]["sqi_ready"] = True

        out["runtime_context"] = {
            "source_ref": source_ref,
            "kg_node_ref": kg_node_ref,
        }

        out["sqi_context"] = {
            "object_type": object_type,
            "coherence": {
                "score": coherence_score,
                "status": _status_from_score(coherence_score),
            },
            "runtime_refs": deepcopy(runtime_refs or {}),
        }

        out["sqi_payload"] = deepcopy(sqi_payload or {})
        return out

    def write_company(
        self,
        company: Dict[str, Any],
        *,
        assessment_ref: Optional[str] = None,
        thesis_refs: Optional[list[str]] = None,
        trigger_map_ref: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        assessment: Optional[Dict[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        payload = deepcopy(company)
        if assessment_ref is not None:
            payload["assessment_ref"] = assessment_ref
        if thesis_refs is not None:
            payload["thesis_refs"] = list(thesis_refs)
        if trigger_map_ref is not None:
            payload["trigger_map_ref"] = trigger_map_ref
        if extra_kwargs:
            payload = _deep_merge(payload, extra_kwargs)

        base = self.container_adapter.company_container(payload)

        coherence_score = _derive_company_coherence(payload)
        sqi_payload = _build_sqi_payload(
            assessment=assessment,
            context=context,
            extra={
                "source_type": "company",
                "company_id": payload.get("company_id"),
                "ticker": payload.get("ticker"),
            },
        )

        return self._finalize_container(
            base,
            object_type="company",
            source_ref=payload["company_id"],
            kg_node_ref=payload["company_id"],
            coherence_score=coherence_score,
            runtime_refs={
                "assessment_ref": assessment_ref,
                "thesis_refs": list(thesis_refs or []),
                "trigger_map_ref": trigger_map_ref,
            },
            sqi_payload=sqi_payload,
        )

    def write_assessment(
        self,
        assessment: Dict[str, Any],
        *,
        company_ref: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        payload = deepcopy(assessment)
        if company_ref is not None:
            payload["company_ref"] = company_ref
        if thesis_ref is not None:
            payload["thesis_ref"] = thesis_ref
        if extra_kwargs:
            payload = _deep_merge(payload, extra_kwargs)

        sqi_payload = _build_sqi_payload(
            assessment=payload,
            context=context,
            extra={
                "source_type": "assessment",
                "assessment_id": payload.get("assessment_id"),
                "entity_id": payload.get("entity_id"),
            },
        )

        base = self.container_adapter.assessment_container(
            payload,
            sqi_payload=sqi_payload,
        )

        coherence_score = _extract_assessment_score(payload)

        return self._finalize_container(
            base,
            object_type="assessment",
            source_ref=payload["assessment_id"],
            kg_node_ref=payload["assessment_id"],
            coherence_score=coherence_score,
            runtime_refs={
                "company_ref": company_ref,
                "thesis_ref": thesis_ref,
            },
            sqi_payload=sqi_payload,
        )

    def write_thesis(
        self,
        thesis: Dict[str, Any],
        *,
        company_ref: Optional[str] = None,
        trigger_map_ref: Optional[str] = None,
        assessment: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        payload = deepcopy(thesis)
        if company_ref is not None:
            payload["company_ref"] = company_ref
        if trigger_map_ref is not None:
            payload["trigger_map_ref"] = trigger_map_ref
        if extra_kwargs:
            payload = _deep_merge(payload, extra_kwargs)

        sqi_payload = _build_sqi_payload(
            assessment=assessment,
            context=context,
            extra={
                "source_type": "thesis",
                "thesis_id": payload.get("thesis_id"),
                "ticker": payload.get("ticker"),
                "mode": payload.get("mode"),
                "status": payload.get("status"),
            },
        )

        base = self.container_adapter.thesis_container(
            payload,
            sqi_payload=sqi_payload,
        )

        if assessment is not None:
            coherence_score = _extract_assessment_score(assessment)
        else:
            has_assessment_refs = bool(payload.get("assessment_refs"))
            is_active = str(payload.get("status", "")).lower() == "active"
            mode = str(payload.get("mode", "")).lower()

            score = 0.45
            if has_assessment_refs:
                score += 0.15
            if is_active:
                score += 0.10
            if mode in {"long", "catalyst_long"}:
                score += 0.08
            coherence_score = _clamp01(score)

        return self._finalize_container(
            base,
            object_type="thesis",
            source_ref=payload["thesis_id"],
            kg_node_ref=payload["thesis_id"],
            coherence_score=coherence_score,
            runtime_refs={
                "company_ref": company_ref,
                "trigger_map_ref": trigger_map_ref,
            },
            sqi_payload=sqi_payload,
        )

    def write_trigger_map(
        self,
        trigger_map: Dict[str, Any],
        *,
        company_ref: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        assessment: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        payload = deepcopy(trigger_map)
        if company_ref is not None:
            payload["company_ref"] = company_ref
        if thesis_ref is not None:
            payload["thesis_ref"] = thesis_ref
        if extra_kwargs:
            payload = _deep_merge(payload, extra_kwargs)

        sqi_payload = _build_sqi_payload(
            assessment=assessment,
            context=context,
            extra={
                "source_type": "trigger_map",
                "company_trigger_map_id": payload.get("company_trigger_map_id"),
                "company_ref": payload.get("company_ref"),
            },
        )

        base = self.container_adapter.trigger_map_container(
            payload,
            sqi_payload=sqi_payload,
        )

        coherence_score = _derive_trigger_map_coherence(payload)

        return self._finalize_container(
            base,
            object_type="trigger_map",
            source_ref=payload["company_trigger_map_id"],
            kg_node_ref=payload["company_trigger_map_id"],
            coherence_score=coherence_score,
            runtime_refs={
                "company_ref": company_ref or payload.get("company_ref"),
                "thesis_ref": thesis_ref,
            },
            sqi_payload=sqi_payload,
        )

    def write_pre_earnings_estimate(
        self,
        estimate: Dict[str, Any],
        *,
        company_ref: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        trigger_map_ref: Optional[str] = None,
        assessment: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        payload = deepcopy(estimate)
        if company_ref is not None:
            payload["company_ref"] = company_ref
        if thesis_ref is not None:
            payload["thesis_ref"] = thesis_ref
        if trigger_map_ref is not None:
            payload["trigger_map_ref"] = trigger_map_ref
        if extra_kwargs:
            payload = _deep_merge(payload, extra_kwargs)

        sqi_payload = _build_sqi_payload(
            assessment=assessment,
            context=context,
            extra={
                "source_type": "pre_earnings_estimate",
                "pre_earnings_estimate_id": payload.get("pre_earnings_estimate_id"),
                "company_ref": payload.get("company_ref"),
            },
        )

        base = self.container_adapter.pre_earnings_estimate_container(
            payload,
            sqi_payload=sqi_payload,
        )

        coherence_score = _derive_pre_earnings_coherence(payload)

        return self._finalize_container(
            base,
            object_type="pre_earnings_estimate",
            source_ref=payload["pre_earnings_estimate_id"],
            kg_node_ref=payload["pre_earnings_estimate_id"],
            coherence_score=coherence_score,
            runtime_refs={
                "company_ref": company_ref or payload.get("company_ref"),
                "thesis_ref": thesis_ref,
                "trigger_map_ref": trigger_map_ref,
            },
            sqi_payload=sqi_payload,
        )
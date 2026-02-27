from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

log = logging.getLogger("aion_equities.sqi_mapping")


@dataclass(frozen=True)
class MappingRule:
    source: str   # dotted path in assessment/thesis context
    target: str   # sqi signal name / policy field
    note: str = ""


# ---------------------------------------------------------------------
# v0.1 Bridge Contract: assessment/thesis/context -> SQI/policy inputs
# ---------------------------------------------------------------------
V0_1_MAPPING_RULES: Tuple[MappingRule, ...] = (
    # BQS
    MappingRule("assessment.bqs.score", "sqi.business_strength_signal"),
    MappingRule("assessment.bqs.components", "sqi.evidence_component_signals", "component values extracted"),
    MappingRule("assessment.bqs.components", "sqi.evidence_confidence_weights", "component confidences extracted"),

    # ACS
    MappingRule("assessment.acs.score", "sqi.predictability_signal"),
    MappingRule("assessment.acs.components.narrative_coherence.value", "sqi.narrative_coherence_signal"),
    MappingRule("assessment.acs.components.historical_model_error_stability.value", "sqi.model_stability_signal"),
    MappingRule("assessment.acs.components", "sqi.uncertainty_penalty_signals", "opacity/complexity components extracted"),

    # AOT
    MappingRule("assessment.aot.automation_beneficiary_score", "sqi.forward_margin_expansion_signal"),
    MappingRule("assessment.aot.automation_threat_score", "sqi.disruption_threat_signal"),
    MappingRule("assessment.aot.signals.management_execution_credibility.value", "sqi.execution_credibility_signal"),
    MappingRule("assessment.aot.signals.debt_blocks_transition.value", "sqi.transition_blocker_penalty"),

    # Risk / policy gate
    MappingRule("assessment.risk.analytical_confidence_gate_pass", "policy_gate.acs_pass"),
    MappingRule("assessment.risk.borrow_cost_estimate_annualized_pct", "sqi.short_net_return_penalty"),
    MappingRule("assessment.risk.position_risk_flags", "sqi.contradiction_pressure_inputs", "gate reasons and penalties"),

    # Catalyst
    MappingRule("assessment.catalyst.has_active_catalyst", "sqi.catalyst_alignment_signal"),
    MappingRule("assessment.catalyst.next_catalyst_date", "sqi.timing_alignment_input"),
    MappingRule("assessment.catalyst.timing_confidence", "sqi.catalyst_timing_confidence"),
    MappingRule("assessment.catalyst.catalyst_types", "sqi.catalyst_type_routing"),

    # KG / patterns (fed separately in many flows; included as bridge names)
    MappingRule("context.kg.supports_count", "sqi.kg_supports_signal"),
    MappingRule("context.kg.contradicts_count", "sqi.kg_contradiction_signal"),
    MappingRule("context.kg.drift_score", "sqi.drift_score"),
    MappingRule("context.kg.confidence_modifier", "sqi.coherence_weighting_modifier"),
    MappingRule("context.kg.pattern_match_score", "sqi.pattern_support_signal"),

    MappingRule("context.pattern.aggregate_score", "sqi.pattern_support_signal"),
    MappingRule("context.pattern.stability_modifier", "sqi.pattern_stability_modifier"),

    # Observer bias (phase 2 use; wire field now)
    MappingRule("context.observer.bias_penalty", "sqi.bias_penalty"),
)


def _get_path(obj: Any, dotted_path: str, default: Any = None) -> Any:
    cur = obj
    for part in dotted_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def _extract_component_values(components: Any) -> Dict[str, Any]:
    """
    Extract component values from:
      {"revenue_quality":{"value":0.8,"confidence":0.9}, ...}
    """
    out: Dict[str, Any] = {}
    if not isinstance(components, dict):
        return out
    for name, payload in components.items():
        if isinstance(payload, dict) and "value" in payload:
            out[name] = payload.get("value")
    return out


def _extract_component_confidences(components: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(components, dict):
        return out
    for name, payload in components.items():
        if isinstance(payload, dict) and "confidence" in payload:
            out[name] = payload.get("confidence")
    return out


def _extract_uncertainty_penalties(acs_components: Any) -> Dict[str, Any]:
    """
    Pulls opacity/complexity style ACS components into penalty signals.
    This stays heuristic in v1 and can be tightened after schema settles.
    """
    out: Dict[str, Any] = {}
    if not isinstance(acs_components, dict):
        return out

    penalty_like_names = (
        "commodity_input_opacity",
        "commodity_opacity",
        "hedging_book_opacity",
        "regulatory_complexity",
        "segment_complexity",
        "reporting_complexity",
    )
    for name, payload in acs_components.items():
        if name in penalty_like_names and isinstance(payload, dict):
            out[name] = payload.get("value")
    return out


def build_sqi_signal_inputs(
    *,
    assessment: Optional[dict] = None,
    thesis_state: Optional[dict] = None,
    context: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Build a flat SQI/policy signal input dict from assessment/thesis/context payloads.

    Returns a dict like:
      {
        "sqi.business_strength_signal": 0.72,
        "sqi.predictability_signal": 0.81,
        "policy_gate.acs_pass": True,
        ...
      }
    """
    root = {
        "assessment": assessment or {},
        "thesis": thesis_state or {},
        "context": context or {},
    }

    out: Dict[str, Any] = {}

    for rule in V0_1_MAPPING_RULES:
        src_val = _get_path(root, rule.source, default=None)

        # Special extraction handlers
        if rule.target == "sqi.evidence_component_signals":
            out[rule.target] = _extract_component_values(src_val)
            continue
        if rule.target == "sqi.evidence_confidence_weights":
            out[rule.target] = _extract_component_confidences(src_val)
            continue
        if rule.target == "sqi.uncertainty_penalty_signals":
            out[rule.target] = _extract_uncertainty_penalties(src_val)
            continue

        # Normal direct mapping
        if src_val is not None:
            out[rule.target] = src_val

    # Optional convenience derivations (v1, no scoring math)
    # Keep these lightweight and transparent.
    try:
        supports = float(out.get("sqi.kg_supports_signal", 0) or 0)
        contradicts = float(out.get("sqi.kg_contradiction_signal", 0) or 0)
        out.setdefault("sqi.kg_net_support_signal", supports - contradicts)
    except Exception:
        pass

    # Borrow cost can be interpreted as a penalty magnitude for short theses
    try:
        borrow = out.get("sqi.short_net_return_penalty")
        if borrow is not None:
            out["sqi.short_net_return_penalty"] = float(borrow)
    except Exception:
        log.warning("Could not normalize borrow cost estimate: %r", out.get("sqi.short_net_return_penalty"))

    return out


def get_v0_1_mapping_table() -> List[Dict[str, str]]:
    """Useful for debug UIs / docs export / inspection."""
    return [{"source": r.source, "target": r.target, "note": r.note} for r in V0_1_MAPPING_RULES]
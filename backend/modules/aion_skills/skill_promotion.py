from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PromotionDecision:
    ok: bool
    skill_id: str
    current_stage: str
    target_stage: Optional[str]
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "skill_id": self.skill_id,
            "current_stage": self.current_stage,
            "target_stage": self.target_stage,
            "reason": self.reason,
            "evidence": dict(self.evidence or {}),
        }


def evaluate_skill_for_promotion(*, registry, telemetry, skill_id: str) -> PromotionDecision:
    """
    registry: SkillRegistry-like (get_metadata, promote)
    telemetry: telemetry collector with summary_by_skill(skill_id) or aggregate summary
    """
    meta = registry.get_metadata(skill_id)
    if meta is None:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage="unknown",
            target_stage=None,
            reason="skill_not_found",
        )

    current = meta.stage
    policy = meta.validation_policy

    # adapt to your telemetry API
    stats = {}
    if hasattr(telemetry, "summary_for_skill"):
        stats = telemetry.summary_for_skill(skill_id) or {}
    elif hasattr(telemetry, "summary"):
        all_stats = telemetry.summary() or {}
        stats = ((all_stats.get("by_skill") or {}).get(skill_id) or {})
    else:
        stats = {}

    count = int(stats.get("count", 0) or 0)
    ok_count = int(stats.get("ok", 0) or 0)
    avg_latency_ms = int(stats.get("avg_latency_ms", stats.get("latency_ms_avg", 0)) or 0)
    success_rate = (ok_count / count) if count > 0 else 0.0

    evidence = {
        "count": count,
        "ok_count": ok_count,
        "success_rate": success_rate,
        "avg_latency_ms": avg_latency_ms,
        "policy": policy.to_dict(),
    }

    if count < policy.min_sample_size:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage=current,
            target_stage=None,
            reason="insufficient_sample_size",
            evidence=evidence,
        )

    if success_rate < policy.min_success_rate:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage=current,
            target_stage=None,
            reason="success_rate_below_threshold",
            evidence=evidence,
        )

    if avg_latency_ms > policy.max_avg_latency_ms:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage=current,
            target_stage=None,
            reason="latency_above_threshold",
            evidence=evidence,
        )

    next_stage = None
    if current == "experimental":
        next_stage = "verified"
    elif current == "verified":
        next_stage = "core"
    else:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage=current,
            target_stage=None,
            reason="already_core",
            evidence=evidence,
        )

    promoted = registry.promote(skill_id, next_stage)
    if not promoted:
        return PromotionDecision(
            ok=False,
            skill_id=skill_id,
            current_stage=current,
            target_stage=next_stage,
            reason="promotion_rejected_by_registry",
            evidence=evidence,
        )

    return PromotionDecision(
        ok=True,
        skill_id=skill_id,
        current_stage=current,
        target_stage=next_stage,
        reason="promotion_approved",
        evidence=evidence,
    )
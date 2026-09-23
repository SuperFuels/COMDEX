from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any


SUB_GOAL_SCHEMA_VERSION = "aion.goal_engine.sub_goal.v1"
GOAL_DECOMPOSITION_SCHEMA_VERSION = "aion.goal_engine.goal_decomposition.v1"

SUPPORTED_DECOMPOSITION_STRATEGIES = {
    "sequential",
    "parallel",
    "review_gated",
}

MAX_DEFAULT_DEPTH = 3
MAX_DEFAULT_SUB_GOALS = 8


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(getattr(value, "__dict__", {}) or {})
    return {}


@dataclass(frozen=True)
class SubGoalContract:
    sub_goal_id: str
    parent_goal_id: str
    title: str
    objective: str
    confidence: float = 0.0
    glyph_code: str | None = None
    needs_human_review: bool = False
    risk_tier: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.sub_goal_id or "").strip():
            errors.append("sub_goal_id_required")

        if not str(self.parent_goal_id or "").strip():
            errors.append("parent_goal_id_required")

        if not str(self.title or "").strip():
            errors.append("sub_goal_title_required")

        if not str(self.objective or "").strip():
            errors.append("sub_goal_objective_required")

        if not 0 <= float(self.confidence or 0) <= 1:
            errors.append("sub_goal_confidence_out_of_range")

        return errors


@dataclass(frozen=True)
class GoalDecompositionContract:
    decomposition_id: str
    parent_goal_id: str
    parent_goal_title: str
    decomposition_strategy: str = "sequential"
    max_depth: int = MAX_DEFAULT_DEPTH
    max_sub_goals: int = MAX_DEFAULT_SUB_GOALS
    current_depth: int = 0
    sub_goals: list[SubGoalContract] = field(default_factory=list)
    approval_required_before_expansion: bool = False
    risk_tier: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.decomposition_id or "").strip():
            errors.append("decomposition_id_required")

        if not str(self.parent_goal_id or "").strip():
            errors.append("parent_goal_id_required")

        if not str(self.parent_goal_title or "").strip():
            errors.append("parent_goal_title_required")

        if str(self.decomposition_strategy or "").strip() not in SUPPORTED_DECOMPOSITION_STRATEGIES:
            errors.append("unsupported_decomposition_strategy")

        if int(self.max_depth or 0) <= 0:
            errors.append("max_depth_required")

        if int(self.max_sub_goals or 0) <= 0:
            errors.append("max_sub_goals_required")

        if int(self.current_depth or 0) > int(self.max_depth or 0):
            errors.append("max_depth_exceeded")

        if len(self.sub_goals or []) > int(self.max_sub_goals or 0):
            errors.append("max_sub_goals_exceeded")

        if str(self.risk_tier or "").lower() in {"high", "critical"} and not self.approval_required_before_expansion:
            errors.append("high_risk_expansion_requires_approval")

        for sub_goal in self.sub_goals or []:
            errors.extend(sub_goal.validate())

        return errors


def build_sub_goal_preview(sub_goal: SubGoalContract | dict[str, Any]) -> dict[str, Any]:
    if not isinstance(sub_goal, SubGoalContract):
        row = _as_dict(sub_goal)
        sub_goal = SubGoalContract(
            sub_goal_id=str(row.get("sub_goal_id") or row.get("id") or ""),
            parent_goal_id=str(row.get("parent_goal_id") or ""),
            title=str(row.get("title") or ""),
            objective=str(row.get("objective") or ""),
            confidence=float(row.get("confidence") or 0),
            glyph_code=row.get("glyph_code"),
            needs_human_review=bool(row.get("needs_human_review") is True),
            risk_tier=str(row.get("risk_tier") or "low"),
            metadata=dict(row.get("metadata") or {}) if isinstance(row.get("metadata"), dict) else {},
        )

    validation_errors = sub_goal.validate()

    return {
        "schema_version": SUB_GOAL_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "sub_goal_preview",
        "sub_goal_id": sub_goal.sub_goal_id,
        "parent_goal_id": sub_goal.parent_goal_id,
        "title": sub_goal.title,
        "objective": sub_goal.objective,
        "confidence": float(sub_goal.confidence or 0),
        "glyph_code": sub_goal.glyph_code,
        "needs_human_review": bool(sub_goal.needs_human_review),
        "risk_tier": sub_goal.risk_tier,
        "valid": not bool(validation_errors),
        "validation_errors": validation_errors,
        "blocked_reasons": validation_errors,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def build_goal_decomposition_preview(contract: GoalDecompositionContract) -> dict[str, Any]:
    validation_errors = contract.validate()
    blocked_reasons = list(validation_errors)

    sub_goal_previews = [build_sub_goal_preview(item) for item in contract.sub_goals or []]

    bounded = (
        not validation_errors
        and len(sub_goal_previews) <= int(contract.max_sub_goals or 0)
        and int(contract.current_depth or 0) <= int(contract.max_depth or 0)
        and int(contract.max_depth or 0) > 0
        and int(contract.max_sub_goals or 0) > 0
    )

    if not bounded and "unbounded_decomposition_blocked" not in blocked_reasons:
        blocked_reasons.append("unbounded_decomposition_blocked")

    needs_human_review = bool(
        contract.approval_required_before_expansion
        or any(item.get("needs_human_review") is True for item in sub_goal_previews)
        or "high_risk_expansion_requires_approval" in blocked_reasons
    )

    return {
        "schema_version": GOAL_DECOMPOSITION_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "goal_decomposition_preview",
        "decomposition_id": contract.decomposition_id,
        "parent_goal_id": contract.parent_goal_id,
        "parent_goal_title": contract.parent_goal_title,
        "decomposition_strategy": contract.decomposition_strategy,
        "max_depth": int(contract.max_depth or 0),
        "max_sub_goals": int(contract.max_sub_goals or 0),
        "current_depth": int(contract.current_depth or 0),
        "sub_goal_count": len(sub_goal_previews),
        "sub_goals": [item["sub_goal_id"] for item in sub_goal_previews],
        "sub_goal_previews": sub_goal_previews,
        "approval_required_before_expansion": bool(contract.approval_required_before_expansion),
        "needs_human_review": needs_human_review,
        "risk_tier": contract.risk_tier,
        "bounded": bounded,
        "valid": not bool(validation_errors),
        "validation_errors": validation_errors,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

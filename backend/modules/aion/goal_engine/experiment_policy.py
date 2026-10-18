from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EXPERIMENT_POLICY_SCHEMA_VERSION = "aion.goal_engine.experiment_policy.v1"


@dataclass(frozen=True)
class ExperimentPolicyContract:
    experiment_id: str
    goal_id: str
    variants: list[str] = field(default_factory=list)
    metric: str = ""
    max_iterations: int = 0
    max_runtime_minutes: int = 0
    max_parallel_variants: int = 1
    exploration_factor: float = 0.2
    exploration_decay: float = 0.98
    min_exploration_floor: float = 0.05
    confidence_threshold: float = 0.95
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.experiment_id or "").strip():
            errors.append("experiment_id_required")

        if not str(self.goal_id or "").strip():
            errors.append("goal_id_required")

        variants = [str(item or "").strip() for item in self.variants or [] if str(item or "").strip()]
        if not variants:
            errors.append("variants_required")
        elif len(variants) < 2:
            errors.append("at_least_two_variants_required")

        if not str(self.metric or "").strip():
            errors.append("metric_required")

        if int(self.max_iterations or 0) <= 0:
            errors.append("max_iterations_required")

        if int(self.max_runtime_minutes or 0) <= 0:
            errors.append("max_runtime_minutes_required")

        if not 0 <= float(self.exploration_factor or 0) <= 1:
            errors.append("exploration_factor_out_of_range")

        if not 0 < float(self.exploration_decay or 0) <= 1:
            errors.append("exploration_decay_out_of_range")

        if not 0 <= float(self.min_exploration_floor or 0) <= 1:
            errors.append("min_exploration_floor_out_of_range")

        if not 0 <= float(self.confidence_threshold or 0) <= 1:
            errors.append("confidence_threshold_out_of_range")

        if int(self.max_parallel_variants or 0) <= 0:
            errors.append("max_parallel_variants_required")

        return errors


def build_experiment_policy_preview(contract: ExperimentPolicyContract) -> dict[str, Any]:
    validation_errors = contract.validate()
    blocked_reasons = list(validation_errors)

    has_required_bounds = (
        int(contract.max_iterations or 0) > 0
        and int(contract.max_runtime_minutes or 0) > 0
    )

    if not has_required_bounds and "unbounded_experiment_plan_blocked" not in blocked_reasons:
        blocked_reasons.append("unbounded_experiment_plan_blocked")

    variants = [str(item or "").strip() for item in contract.variants or [] if str(item or "").strip()]
    bounded = bool(has_required_bounds and not validation_errors)

    return {
        "schema_version": EXPERIMENT_POLICY_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "experiment_policy_preview",
        "experiment_id": contract.experiment_id,
        "goal_id": contract.goal_id,
        "variants": variants,
        "variant_count": len(variants),
        "metric": contract.metric,
        "max_iterations": int(contract.max_iterations or 0),
        "max_runtime_minutes": int(contract.max_runtime_minutes or 0),
        "max_parallel_variants": int(contract.max_parallel_variants or 0),
        "exploration_factor": float(contract.exploration_factor or 0),
        "exploration_decay": float(contract.exploration_decay or 0),
        "min_exploration_floor": float(contract.min_exploration_floor or 0),
        "confidence_threshold": float(contract.confidence_threshold or 0),
        "premature_convergence_blocked": True,
        "bounded": bounded,
        "valid": bool(not validation_errors and bounded),
        "validation_errors": validation_errors,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

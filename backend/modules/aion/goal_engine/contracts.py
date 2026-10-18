from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RiskTier = Literal["low", "medium", "high"]
ApprovalPolicy = Literal["dry_run_only", "human_approval_required", "autonomous_allowed"]
GoalStatus = Literal["draft", "active", "paused", "completed", "failed", "cancelled"]
WinnerPolicy = Literal["manual", "automatic_bandit", "highest_score"]
LoserPolicy = Literal["keep_exploring", "pause_loser", "stop_loser"]
LoopMode = Literal["fixed_count", "until_goal_achieved", "until_failed", "while_improving"]
OutcomeStatus = Literal["unknown", "success", "partial", "failed"]


@dataclass(frozen=True)
class GoalNodeContract:
    goal_id: str
    goal_name: str
    target_metric: str
    target_value: float
    deadline: str | None = None
    budget_limit: dict[str, Any] | None = None
    allowed_channels: list[str] = field(default_factory=list)
    risk_tier: RiskTier = "low"
    success_threshold: float = 1.0
    failure_threshold: float = 0.0
    max_iterations: int = 1
    approval_policy: ApprovalPolicy = "dry_run_only"
    status: GoalStatus = "draft"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.goal_id:
            errors.append("goal_id is required")
        if not self.goal_name:
            errors.append("goal_name is required")
        if not self.target_metric:
            errors.append("target_metric is required")
        if self.target_value <= 0:
            errors.append("target_value must be positive")
        if self.max_iterations < 1:
            errors.append("max_iterations must be at least 1")
        if self.success_threshold <= self.failure_threshold:
            errors.append("success_threshold must be greater than failure_threshold")
        return errors


@dataclass(frozen=True)
class ExperimentNodeContract:
    experiment_id: str
    goal_id: str
    variants: list[str]
    metric: str
    sample_window: str | None = None
    min_sample_size: int = 1
    exploration_factor: float = 0.15
    exploration_decay: float = 0.98
    min_exploration_floor: float = 0.05
    confidence_threshold: float = 0.95
    winner_policy: WinnerPolicy = "manual"
    loser_policy: LoserPolicy = "keep_exploring"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.experiment_id:
            errors.append("experiment_id is required")
        if not self.goal_id:
            errors.append("goal_id is required")
        if len(self.variants) < 2:
            errors.append("experiment requires at least 2 variants")
        if not self.metric:
            errors.append("metric is required")
        if self.min_sample_size < 1:
            errors.append("min_sample_size must be at least 1")
        if not 0 <= self.exploration_factor <= 1:
            errors.append("exploration_factor must be between 0 and 1")
        if not 0 <= self.min_exploration_floor <= self.exploration_factor:
            errors.append("min_exploration_floor must be between 0 and exploration_factor")
        if not 0 < self.exploration_decay <= 1:
            errors.append("exploration_decay must be greater than 0 and no more than 1")
        if not 0 < self.confidence_threshold <= 1:
            errors.append("confidence_threshold must be greater than 0 and no more than 1")
        return errors


@dataclass(frozen=True)
class LoopNodeContract:
    loop_id: str
    goal_id: str | None = None
    loop_mode: LoopMode = "fixed_count"
    max_iterations: int = 1
    max_runtime_minutes: int = 10
    max_external_writes: int = 0
    max_spend: dict[str, Any] | None = None
    requires_human_approval: bool = True
    kill_switch_triggered: bool = False
    state_delta_strategy: Literal["isolate_increments"] = "isolate_increments"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.loop_id:
            errors.append("loop_id is required")
        if self.max_iterations < 1:
            errors.append("max_iterations must be at least 1")
        if self.max_runtime_minutes < 1:
            errors.append("max_runtime_minutes must be at least 1")
        if self.max_external_writes < 0:
            errors.append("max_external_writes cannot be negative")
        if self.loop_mode != "fixed_count" and self.goal_id is None:
            errors.append("goal_id is required for goal-aware loop modes")
        return errors


@dataclass(frozen=True)
class OutcomeEvaluationContract:
    outcome_id: str
    goal_id: str
    run_id: str
    status: OutcomeStatus = "unknown"
    quality_score: float = 0.0
    metric_actual: float | None = None
    metric_target: float | None = None
    cost: dict[str, Any] | None = None
    time_to_result_seconds: int | None = None
    confidence: float = 0.0
    reason: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.outcome_id:
            errors.append("outcome_id is required")
        if not self.goal_id:
            errors.append("goal_id is required")
        if not self.run_id:
            errors.append("run_id is required")
        if not 0 <= self.quality_score <= 1:
            errors.append("quality_score must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            errors.append("confidence must be between 0 and 1")
        return errors


@dataclass(frozen=True)
class ReflectionLearningContract:
    reflection_id: str
    source_run_id: str
    source_workflow_id: str
    source_glyph_code: str | None = None
    allow_learn: bool = False
    adr_active: bool = False
    winning_patterns: list[dict[str, Any]] = field(default_factory=list)
    failed_patterns: list[dict[str, Any]] = field(default_factory=list)
    advisory_only: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.reflection_id:
            errors.append("reflection_id is required")
        if not self.source_run_id:
            errors.append("source_run_id is required")
        if not self.source_workflow_id:
            errors.append("source_workflow_id is required")
        if self.adr_active:
            errors.append("learning blocked while adr_active=true")
        if not self.allow_learn:
            errors.append("learning requires allow_learn=true")
        if not self.advisory_only:
            errors.append("learned memory must remain advisory_only")
        return errors


@dataclass(frozen=True)
class StateDeltaAccumulatorContract:
    accumulator_id: str
    run_id: str
    checkpoint_id: str
    loop_context_snapshot: dict[str, Any] = field(default_factory=dict)
    deltas: list[dict[str, Any]] = field(default_factory=list)
    max_delta_count: int = 100
    max_snapshot_bytes: int = 32_000

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.accumulator_id:
            errors.append("accumulator_id is required")
        if not self.run_id:
            errors.append("run_id is required")
        if not self.checkpoint_id:
            errors.append("checkpoint_id is required")
        if self.max_delta_count < 1:
            errors.append("max_delta_count must be at least 1")
        if self.max_snapshot_bytes < 1024:
            errors.append("max_snapshot_bytes must be at least 1024")
        if len(self.deltas) > self.max_delta_count:
            errors.append("delta count exceeds max_delta_count")
        return errors


@dataclass(frozen=True)
class EnvironmentRevalidationContract:
    revalidation_id: str
    run_id: str
    checkpoint_id: str
    parent_goal_id: str | None = None
    approval_still_valid: bool = False
    vault_ready: bool = False
    connectors_ready: bool = False
    parent_goal_still_required: bool = False
    external_state_changed: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.revalidation_id:
            errors.append("revalidation_id is required")
        if not self.run_id:
            errors.append("run_id is required")
        if not self.checkpoint_id:
            errors.append("checkpoint_id is required")
        if not self.approval_still_valid:
            errors.append("approval must be revalidated before resume")
        if not self.vault_ready:
            errors.append("vault readiness must be revalidated before resume")
        if not self.connectors_ready:
            errors.append("connector readiness must be revalidated before resume")
        if not self.parent_goal_still_required:
            errors.append("parent goal must still be required before resume")
        if self.external_state_changed:
            errors.append("external state changed; resume must stop or re-plan")
        return errors

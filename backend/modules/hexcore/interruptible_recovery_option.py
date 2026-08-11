"""Governed, asymmetric switching for an interruptible recovery option.

The controller intentionally treats a false recovery hand-off as more costly
than a missed recovery.  It never grants an action chunk open-loop authority:
the caller must provide a new anomaly probability after every executed action.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryOptionConfig:
    enter_threshold: float
    exit_threshold: float
    sustained_observations: int = 2
    max_burst_actions: int = 3
    cooldown_actions: int = 2

    def __post_init__(self) -> None:
        if not 0.0 <= self.exit_threshold <= self.enter_threshold <= 1.0:
            raise ValueError("recovery_threshold_order_invalid")
        if self.sustained_observations < 1:
            raise ValueError("recovery_sustain_invalid")
        if not 1 <= self.max_burst_actions <= 3:
            raise ValueError("recovery_burst_must_be_one_to_three")
        if self.cooldown_actions < 0:
            raise ValueError("recovery_cooldown_invalid")


class InterruptibleRecoveryOption:
    """State machine that reconsiders recovery after every action."""

    def __init__(self, config: RecoveryOptionConfig):
        self.config = config
        self.reset()

    def reset(self) -> None:
        self.active = False
        self.high_streak = 0
        self.burst_actions = 0
        self.cooldown_remaining = 0

    def decide(self, anomaly_probability: float) -> tuple[bool, str]:
        probability = float(anomaly_probability)
        if not 0.0 <= probability <= 1.0:
            raise ValueError("recovery_probability_out_of_bounds")

        if self.active:
            if (
                probability < self.config.exit_threshold
                or self.burst_actions >= self.config.max_burst_actions
            ):
                self.active = False
                self.high_streak = 0
                self.burst_actions = 0
                self.cooldown_remaining = self.config.cooldown_actions
                return False, "recovery_exit_to_nominal"
            self.burst_actions += 1
            return True, "interruptible_recovery_continue"

        if self.cooldown_remaining:
            self.cooldown_remaining -= 1
            self.high_streak = 0
            return False, "recovery_cooldown_nominal"

        if probability >= self.config.enter_threshold:
            self.high_streak += 1
        else:
            self.high_streak = 0

        if self.high_streak >= self.config.sustained_observations:
            self.active = True
            self.high_streak = 0
            self.burst_actions = 1
            return True, "interruptible_recovery_enter"
        return False, "protected_nominal"


"""AION self-improvement modules."""

from .self_improvement_trial_loop import (
    AionSelfImprovementTrialLoop,
    TrialAttempt,
    TrialLoopResult,
    run_self_improvement_trial_loop,
)
from .persistent_self_improvement_memory import (
    AionPersistentSelfImprovementMemory,
    PersistentSelfImprovementMemoryRecord,
    PersistentSelfImprovementResult,
    run_persistent_self_improvement,
)

__all__ = [
    "AionSelfImprovementTrialLoop",
    "TrialAttempt",
    "TrialLoopResult",
    "run_self_improvement_trial_loop",
    "AionPersistentSelfImprovementMemory",
    "PersistentSelfImprovementMemoryRecord",
    "PersistentSelfImprovementResult",
    "run_persistent_self_improvement",
]

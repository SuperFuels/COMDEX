"""AION Phase 21L — Strategy Learning Kernel.

This module teaches AION what a strategy is before asking it to survive a world.

It models a tiny deterministic game where AION can choose between strategies:
- explore_unknown
- repeat_last_success
- avoid_last_failure

AION scores the outcome, adjusts trust in the selected strategy, persists the
ranked strategy profile, and proves whether strategy selection improved.

This is the missing layer between simple trial/error memory and survival games.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_STRATEGY_MEMORY_PATH = Path("data/aion_strategy/strategy_learning_memory.json")


@dataclass(frozen=True)
class StrategyAttempt:
    round_index: int
    strategy: str
    action: str
    reward: float
    success: bool
    strategy_trust_before: float
    strategy_trust_after: float
    observation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyLearningResult:
    kernel_version: str
    task_name: str
    rounds: int
    attempts: List[Dict[str, Any]]
    baseline_score: float
    final_score: float
    improvement_delta: float
    improved: bool
    best_strategy: str
    final_strategy_trust: Dict[str, float]
    memory_path: str
    memory_loaded: bool
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionStrategyLearningKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        max_rounds: int = 9,
        reward_door: str = "B",
        penalty_door: str = "C",
    ):
        self.memory_path = Path(memory_path or DEFAULT_STRATEGY_MEMORY_PATH)
        self.max_rounds = max_rounds
        self.reward_door = reward_door
        self.penalty_door = penalty_door
        self.actions = ["A", "B", "C"]
        self.strategies = ["explore_unknown", "repeat_last_success", "avoid_last_failure"]

        self.memory_loaded = False
        self.strategy_trust: Dict[str, float] = {
            "explore_unknown": 0.34,
            "repeat_last_success": 0.33,
            "avoid_last_failure": 0.33,
        }
        self.last_success_action: Optional[str] = None
        self.last_failure_action: Optional[str] = None
        self.tried_actions: List[str] = []

        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return

        trust = data.get("strategy_trust")
        if isinstance(trust, dict):
            for key in self.strategies:
                if key in trust:
                    self.strategy_trust[key] = float(trust[key])

        self.last_success_action = data.get("last_success_action")
        self.last_failure_action = data.get("last_failure_action")
        tried = data.get("tried_actions", [])
        if isinstance(tried, list):
            self.tried_actions = [str(x) for x in tried if str(x) in self.actions]
        self.memory_loaded = True

    def _save_memory(self, result: StrategyLearningResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": "phase21l_strategy_learning_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "strategy_trust": result.final_strategy_trust,
            "best_strategy": result.best_strategy,
            "last_success_action": self.last_success_action,
            "last_failure_action": self.last_failure_action,
            "tried_actions": self.tried_actions,
            "baseline_score": result.baseline_score,
            "final_score": result.final_score,
            "improvement_delta": result.improvement_delta,
            "run_count": int(result.evidence.get("previous_run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if isinstance(previous, dict):
            payload["run_count"] = int(previous.get("run_count", 0)) + 1
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _choose_strategy(self, round_index: int) -> str:
        # First three rounds deliberately sample strategy primitives.
        if round_index <= len(self.strategies) and not self.memory_loaded:
            return self.strategies[round_index - 1]

        return max(self.strategy_trust.items(), key=lambda kv: (kv[1], kv[0]))[0]

    def _choose_action(self, strategy: str, round_index: int) -> str:
        if strategy == "repeat_last_success" and self.last_success_action:
            return self.last_success_action

        if strategy == "avoid_last_failure":
            for action in self.actions:
                if action != self.last_failure_action:
                    if action not in self.tried_actions:
                        return action
            for action in self.actions:
                if action != self.last_failure_action:
                    return action

        # explore_unknown
        for action in self.actions:
            if action not in self.tried_actions:
                return action
        return self.actions[(round_index - 1) % len(self.actions)]

    def _score_action(self, action: str) -> float:
        if action == self.reward_door:
            return 1.0
        if action == self.penalty_door:
            return -1.0
        return 0.0

    def _update_trust(self, strategy: str, reward: float) -> None:
        before = self.strategy_trust[strategy]
        if reward > 0:
            self.strategy_trust[strategy] = min(1.0, before + 0.22)
        elif reward < 0:
            self.strategy_trust[strategy] = max(0.0, before - 0.18)
        else:
            self.strategy_trust[strategy] = max(0.0, before - 0.04)

        # Small normalization keeps the values interpretable.
        total = sum(self.strategy_trust.values()) or 1.0
        self.strategy_trust = {
            k: round(v / total, 6)
            for k, v in self.strategy_trust.items()
        }

    def run(self, *, task_name: str = "three_door_strategy_learning") -> StrategyLearningResult:
        attempts: List[StrategyAttempt] = []
        rewards: List[float] = []

        for round_index in range(1, self.max_rounds + 1):
            strategy = self._choose_strategy(round_index)
            action = self._choose_action(strategy, round_index)
            reward = self._score_action(action)

            before = float(self.strategy_trust[strategy])

            if action not in self.tried_actions:
                self.tried_actions.append(action)

            if reward > 0:
                self.last_success_action = action
            elif reward < 0:
                self.last_failure_action = action

            self._update_trust(strategy, reward)
            after = float(self.strategy_trust[strategy])

            if reward > 0:
                observation = "strategy produced reward; increase trust"
            elif reward < 0:
                observation = "strategy produced penalty; reduce trust"
            else:
                observation = "strategy produced neutral result; slightly reduce trust"

            attempts.append(
                StrategyAttempt(
                    round_index=round_index,
                    strategy=strategy,
                    action=action,
                    reward=reward,
                    success=reward > 0,
                    strategy_trust_before=round(before, 6),
                    strategy_trust_after=round(after, 6),
                    observation=observation,
                )
            )
            rewards.append(reward)

        baseline_score = sum(rewards[:3]) / max(1, min(3, len(rewards)))
        final_window = rewards[-3:] if len(rewards) >= 3 else rewards
        final_score = sum(final_window) / max(1, len(final_window))
        improvement_delta = final_score - baseline_score

        best_strategy = max(self.strategy_trust.items(), key=lambda kv: (kv[1], kv[0]))[0]

        evidence = {
            "uses_llm_shortcut": False,
            "uses_strategy_selection": True,
            "uses_reward_feedback": True,
            "uses_trust_update": True,
            "uses_persistent_memory": True,
            "memory_loaded": self.memory_loaded,
            "reward_trace": rewards,
            "actions_tried": list(self.tried_actions),
            "last_success_action": self.last_success_action,
            "last_failure_action": self.last_failure_action,
        }

        result = StrategyLearningResult(
            kernel_version="phase21l_strategy_learning_kernel_v1",
            task_name=task_name,
            rounds=len(attempts),
            attempts=[a.to_dict() for a in attempts],
            baseline_score=round(baseline_score, 6),
            final_score=round(final_score, 6),
            improvement_delta=round(improvement_delta, 6),
            improved=improvement_delta > 0,
            best_strategy=best_strategy,
            final_strategy_trust=dict(self.strategy_trust),
            memory_path=str(self.memory_path),
            memory_loaded=self.memory_loaded,
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational strategy learning: AION can select a strategy, "
                "score the outcome, adjust trust, and persist the ranked strategy profile. "
                "It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_strategy_learning_kernel(
    *,
    memory_path: Optional[Path] = None,
    max_rounds: int = 9,
    task_name: str = "three_door_strategy_learning",
) -> StrategyLearningResult:
    return AionStrategyLearningKernel(
        memory_path=memory_path,
        max_rounds=max_rounds,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_strategy_learning_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Strategy learning memory saved to: {result.memory_path}")

"""AION Phase 21M — Prediction Before Action Kernel.

Phase 21L taught AION strategy trust. Phase 21M adds prediction before action.

The kernel requires AION to:
1. choose a strategy,
2. predict the reward before acting,
3. act,
4. observe the actual reward,
5. calculate prediction error,
6. update strategy trust using both reward and prediction accuracy.

This is the next step before survival games.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.modules.aion_strategy.strategy_learning_kernel import DEFAULT_STRATEGY_MEMORY_PATH
except Exception:  # pragma: no cover
    DEFAULT_STRATEGY_MEMORY_PATH = Path("data/aion_strategy/strategy_learning_memory.json")


DEFAULT_PREDICTION_MEMORY_PATH = Path("data/aion_strategy/prediction_before_action_memory.json")


@dataclass(frozen=True)
class PredictionAttempt:
    round_index: int
    strategy: str
    action: str
    predicted_reward: float
    actual_reward: float
    prediction_error: float
    trust_before: float
    trust_after: float
    prediction_confidence_before: float
    prediction_confidence_after: float
    observation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PredictionBeforeActionResult:
    kernel_version: str
    task_name: str
    rounds: int
    attempts: List[Dict[str, Any]]
    baseline_prediction_error: float
    final_prediction_error: float
    prediction_error_delta: float
    prediction_improved: bool
    baseline_score: float
    final_score: float
    score_delta: float
    best_strategy: str
    final_strategy_trust: Dict[str, float]
    final_prediction_model: Dict[str, float]
    memory_loaded: bool
    memory_path: str
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionPredictionBeforeActionKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        strategy_memory_path: Optional[Path] = None,
        max_rounds: int = 9,
        reward_door: str = "B",
        penalty_door: str = "C",
    ):
        self.memory_path = Path(memory_path or DEFAULT_PREDICTION_MEMORY_PATH)
        self.strategy_memory_path = Path(strategy_memory_path or DEFAULT_STRATEGY_MEMORY_PATH)
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
        self.prediction_model: Dict[str, float] = {
            "A": 0.0,
            "B": 0.0,
            "C": 0.0,
        }
        self.prediction_confidence: Dict[str, float] = {
            "A": 0.10,
            "B": 0.10,
            "C": 0.10,
        }
        self.last_success_action: Optional[str] = None
        self.last_failure_action: Optional[str] = None
        self.tried_actions: List[str] = []

        self._load_strategy_memory()
        self._load_prediction_memory()

    def _load_strategy_memory(self) -> None:
        if not self.strategy_memory_path.exists():
            return
        try:
            data = json.loads(self.strategy_memory_path.read_text(encoding="utf-8"))
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

    def _load_prediction_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return

        model = data.get("prediction_model")
        if isinstance(model, dict):
            for action in self.actions:
                if action in model:
                    self.prediction_model[action] = float(model[action])

        conf = data.get("prediction_confidence")
        if isinstance(conf, dict):
            for action in self.actions:
                if action in conf:
                    self.prediction_confidence[action] = float(conf[action])

        trust = data.get("strategy_trust")
        if isinstance(trust, dict):
            for key in self.strategies:
                if key in trust:
                    self.strategy_trust[key] = float(trust[key])

        self.last_success_action = data.get("last_success_action", self.last_success_action)
        self.last_failure_action = data.get("last_failure_action", self.last_failure_action)
        tried = data.get("tried_actions", self.tried_actions)
        if isinstance(tried, list):
            self.tried_actions = [str(x) for x in tried if str(x) in self.actions]

        self.memory_loaded = True

    def _save_memory(self, result: PredictionBeforeActionResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21m_prediction_before_action_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "prediction_model": result.final_prediction_model,
            "prediction_confidence": dict(self.prediction_confidence),
            "strategy_trust": result.final_strategy_trust,
            "best_strategy": result.best_strategy,
            "last_success_action": self.last_success_action,
            "last_failure_action": self.last_failure_action,
            "tried_actions": self.tried_actions,
            "baseline_prediction_error": result.baseline_prediction_error,
            "final_prediction_error": result.final_prediction_error,
            "prediction_error_delta": result.prediction_error_delta,
            "prediction_improved": result.prediction_improved,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _choose_strategy(self, round_index: int) -> str:
        if round_index <= len(self.strategies) and not self.memory_loaded:
            return self.strategies[round_index - 1]
        return max(self.strategy_trust.items(), key=lambda kv: (kv[1], kv[0]))[0]

    def _choose_action(self, strategy: str, round_index: int) -> str:
        if strategy == "repeat_last_success" and self.last_success_action:
            return self.last_success_action

        if strategy == "avoid_last_failure":
            for action in self.actions:
                if action != self.last_failure_action and action not in self.tried_actions:
                    return action
            for action in self.actions:
                if action != self.last_failure_action:
                    return action

        # explore_unknown prefers low-confidence unknowns.
        unknown_sorted = sorted(
            self.actions,
            key=lambda a: (self.prediction_confidence.get(a, 0.0), self.actions.index(a)),
        )
        for action in unknown_sorted:
            if action not in self.tried_actions:
                return action
        return unknown_sorted[0]

    def _actual_reward(self, action: str) -> float:
        if action == self.reward_door:
            return 1.0
        if action == self.penalty_door:
            return -1.0
        return 0.0

    def _update_prediction_model(self, action: str, actual_reward: float) -> None:
        old = self.prediction_model.get(action, 0.0)
        confidence = self.prediction_confidence.get(action, 0.1)
        learning_rate = 0.55 if confidence < 0.5 else 0.30

        self.prediction_model[action] = round(old + learning_rate * (actual_reward - old), 6)
        self.prediction_confidence[action] = round(min(1.0, confidence + 0.25), 6)

    def _update_strategy_trust(self, strategy: str, actual_reward: float, prediction_error: float) -> None:
        before = self.strategy_trust[strategy]

        reward_term = 0.14 if actual_reward > 0 else (-0.12 if actual_reward < 0 else -0.03)
        prediction_term = 0.10 if prediction_error <= 0.25 else (-0.08 if prediction_error >= 0.75 else 0.0)

        self.strategy_trust[strategy] = max(0.0, min(1.0, before + reward_term + prediction_term))

        total = sum(self.strategy_trust.values()) or 1.0
        self.strategy_trust = {
            k: round(v / total, 6)
            for k, v in self.strategy_trust.items()
        }

    def run(self, *, task_name: str = "three_door_prediction_before_action") -> PredictionBeforeActionResult:
        attempts: List[PredictionAttempt] = []
        rewards: List[float] = []
        errors: List[float] = []

        for round_index in range(1, self.max_rounds + 1):
            strategy = self._choose_strategy(round_index)
            action = self._choose_action(strategy, round_index)

            predicted_reward = float(self.prediction_model.get(action, 0.0))
            prediction_conf_before = float(self.prediction_confidence.get(action, 0.0))
            trust_before = float(self.strategy_trust[strategy])

            actual_reward = self._actual_reward(action)
            prediction_error = abs(actual_reward - predicted_reward)

            if action not in self.tried_actions:
                self.tried_actions.append(action)

            if actual_reward > 0:
                self.last_success_action = action
            elif actual_reward < 0:
                self.last_failure_action = action

            self._update_prediction_model(action, actual_reward)
            self._update_strategy_trust(strategy, actual_reward, prediction_error)

            trust_after = float(self.strategy_trust[strategy])
            prediction_conf_after = float(self.prediction_confidence.get(action, 0.0))

            if prediction_error <= 0.25:
                observation = "prediction close; reinforce model and strategy"
            elif actual_reward > 0:
                observation = "prediction missed positive reward; update model toward reward"
            elif actual_reward < 0:
                observation = "prediction missed penalty; update model toward avoidance"
            else:
                observation = "neutral outcome; update model cautiously"

            attempts.append(
                PredictionAttempt(
                    round_index=round_index,
                    strategy=strategy,
                    action=action,
                    predicted_reward=round(predicted_reward, 6),
                    actual_reward=round(actual_reward, 6),
                    prediction_error=round(prediction_error, 6),
                    trust_before=round(trust_before, 6),
                    trust_after=round(trust_after, 6),
                    prediction_confidence_before=round(prediction_conf_before, 6),
                    prediction_confidence_after=round(prediction_conf_after, 6),
                    observation=observation,
                )
            )

            rewards.append(actual_reward)
            errors.append(prediction_error)

        baseline_errors = errors[:3] if len(errors) >= 3 else errors
        final_errors = errors[-3:] if len(errors) >= 3 else errors
        baseline_prediction_error = sum(baseline_errors) / max(1, len(baseline_errors))
        final_prediction_error = sum(final_errors) / max(1, len(final_errors))
        prediction_error_delta = baseline_prediction_error - final_prediction_error

        baseline_rewards = rewards[:3] if len(rewards) >= 3 else rewards
        final_rewards = rewards[-3:] if len(rewards) >= 3 else rewards
        baseline_score = sum(baseline_rewards) / max(1, len(baseline_rewards))
        final_score = sum(final_rewards) / max(1, len(final_rewards))
        score_delta = final_score - baseline_score

        best_strategy = max(self.strategy_trust.items(), key=lambda kv: (kv[1], kv[0]))[0]

        evidence = {
            "uses_llm_shortcut": False,
            "uses_prediction_before_action": True,
            "uses_prediction_error": True,
            "uses_strategy_trust_update": True,
            "uses_persistent_memory": True,
            "memory_loaded": self.memory_loaded,
            "reward_trace": rewards,
            "prediction_error_trace": [round(x, 6) for x in errors],
            "actions_tried": list(self.tried_actions),
            "last_success_action": self.last_success_action,
            "last_failure_action": self.last_failure_action,
        }

        result = PredictionBeforeActionResult(
            kernel_version="phase21m_prediction_before_action_kernel_v1",
            task_name=task_name,
            rounds=len(attempts),
            attempts=[a.to_dict() for a in attempts],
            baseline_prediction_error=round(baseline_prediction_error, 6),
            final_prediction_error=round(final_prediction_error, 6),
            prediction_error_delta=round(prediction_error_delta, 6),
            prediction_improved=prediction_error_delta > 0,
            baseline_score=round(baseline_score, 6),
            final_score=round(final_score, 6),
            score_delta=round(score_delta, 6),
            best_strategy=best_strategy,
            final_strategy_trust=dict(self.strategy_trust),
            final_prediction_model=dict(self.prediction_model),
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational prediction before action: AION can predict reward, act, "
                "measure prediction error, and update strategy trust from the result. "
                "It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_prediction_before_action_kernel(
    *,
    memory_path: Optional[Path] = None,
    strategy_memory_path: Optional[Path] = None,
    max_rounds: int = 9,
    task_name: str = "three_door_prediction_before_action",
) -> PredictionBeforeActionResult:
    return AionPredictionBeforeActionKernel(
        memory_path=memory_path,
        strategy_memory_path=strategy_memory_path,
        max_rounds=max_rounds,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_prediction_before_action_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Prediction-before-action memory saved to: {result.memory_path}")

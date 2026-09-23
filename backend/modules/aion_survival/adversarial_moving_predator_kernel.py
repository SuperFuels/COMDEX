"""AION Phase 21W — Adversarial Moving Hazard / Predator.

Phase 21W introduces a moving adversarial hazard.

Earlier phases:
- fixed hazard cells;
- multi-step lookahead;
- hazard semantics.

This phase tests whether AION can predict a moving danger's future position and
choose a route that avoids interception before impact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_PREDATOR_MEMORY_PATH = Path("data/aion_survival/adversarial_predator_memory.json")


@dataclass(frozen=True)
class PredatorFuture:
    first_action: str
    depth: int
    total_score: float
    predicted_intercepts: int
    predicted_goal_reached: bool
    simulated_steps: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PredatorExecutionStep:
    tick: int
    agent_before: Tuple[int, int]
    predator_before: Tuple[int, int]
    chosen_action: str
    agent_after: Tuple[int, int]
    predator_after: Tuple[int, int]
    predicted_intercepts_in_selected_future: int
    intercepted: bool
    reached_goal: bool
    avoided_predator_future: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["agent_before"] = list(self.agent_before)
        data["predator_before"] = list(self.predator_before)
        data["agent_after"] = list(self.agent_after)
        data["predator_after"] = list(self.predator_after)
        return data


@dataclass(frozen=True)
class AdversarialMovingPredatorResult:
    kernel_version: str
    task_name: str
    shallow_first_action: str
    deep_first_action: str
    lookahead_changed_action: bool
    predator_intercepts_predicted_for_shallow_action: int
    predator_intercepts_predicted_for_deep_action: int
    predator_intercepts_actual: int
    predator_avoided_before_impact: bool
    survived: bool
    goal_reached: bool
    ticks_run: int
    memory_loaded: bool
    memory_path: str
    shallow_candidates: List[Dict[str, Any]]
    deep_candidates: List[Dict[str, Any]]
    execution_trace: List[Dict[str, Any]]
    final_predator_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionAdversarialMovingPredatorKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        shallow_depth: int = 1,
        deep_depth: int = 4,
        max_ticks: int = 10,
    ):
        self.memory_path = Path(memory_path or DEFAULT_PREDATOR_MEMORY_PATH)
        self.shallow_depth = shallow_depth
        self.deep_depth = deep_depth
        self.max_ticks = max_ticks
        self.memory_loaded = False

        self.width = 5
        self.height = 3
        self.start = (0, 1)
        self.goal = (4, 1)
        self.predator_start = (3, 1)

        self.actions = ["right", "up", "down", "left", "wait"]
        self.action_vectors = {
            "right": (1, 0),
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "wait": (0, 0),
        }

        self.policy: Dict[str, Any] = {
            "predator_intercept_penalty": 10.0,
            "goal_bonus": 5.0,
            "safe_route_bonus": 1.0,
            "successful_predator_avoidances": 0,
            "best_first_action": None,
        }

        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            policy = data.get("predator_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: AdversarialMovingPredatorResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21w_adversarial_moving_predator_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "predator_policy": result.final_predator_policy,
            "last_predator_avoided_before_impact": result.predator_avoided_before_impact,
            "last_goal_reached": result.goal_reached,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _inside(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def _apply_action(self, position: Tuple[int, int], action: str) -> Tuple[int, int]:
        dx, dy = self.action_vectors[action]
        candidate = (position[0] + dx, position[1] + dy)
        return candidate if self._inside(candidate) else position

    def _distance_to_goal(self, position: Tuple[int, int]) -> int:
        return abs(self.goal[0] - position[0]) + abs(self.goal[1] - position[1])

    def _move_predator(self, predator: Tuple[int, int], agent: Tuple[int, int], step_index: int) -> Tuple[int, int]:
        # Predator moves every second step. This creates a delayed interception risk.
        if step_index % 2 != 0:
            return predator

        px, py = predator
        ax, ay = agent

        options = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)):
            cand = (px + dx, py + dy)
            if not self._inside(cand):
                continue
            dist = abs(cand[0] - ax) + abs(cand[1] - ay)
            options.append((dist, cand))
        options.sort(key=lambda x: x[0])
        return options[0][1]

    def _rollout_next_action(self, position: Tuple[int, int]) -> str:
        scored = []
        for action in self.actions:
            after = self._apply_action(position, action)
            before_dist = self._distance_to_goal(position)
            after_dist = self._distance_to_goal(after)
            score = 0.0
            if after_dist < before_dist:
                score += 2.0
            elif after_dist > before_dist:
                score -= 1.0
            if action == "wait":
                score -= 2.0
            scored.append((score, -self.actions.index(action), action))
        scored.sort(reverse=True)
        return scored[0][2]

    def _simulate_candidate(self, first_action: str, depth: int) -> PredatorFuture:
        agent = self.start
        predator = self.predator_start
        total_score = 0.0
        intercepts = 0
        goal_reached = False
        steps: List[Dict[str, Any]] = []

        for d in range(1, depth + 1):
            action = first_action if d == 1 else self._rollout_next_action(agent)
            agent_next = self._apply_action(agent, action)
            predator_next = self._move_predator(predator, agent_next, d)

            intercepted = agent_next == predator_next or agent_next == predator
            reached_goal = agent_next == self.goal

            if intercepted:
                intercepts += 1
            if reached_goal:
                goal_reached = True

            score = 0.0
            if reached_goal:
                score += float(self.policy.get("goal_bonus", 5.0))
            if intercepted:
                score -= float(self.policy.get("predator_intercept_penalty", 10.0))
            score -= 0.10 * self._distance_to_goal(agent_next)

            discount = 0.82 ** (d - 1)
            total_score += score * discount

            steps.append(
                {
                    "depth": d,
                    "action": action,
                    "agent_position": list(agent_next),
                    "predator_position": list(predator_next),
                    "intercepted": intercepted,
                    "reached_goal": reached_goal,
                }
            )

            agent = agent_next
            predator = predator_next

        return PredatorFuture(
            first_action=first_action,
            depth=depth,
            total_score=round(total_score, 6),
            predicted_intercepts=intercepts,
            predicted_goal_reached=goal_reached,
            simulated_steps=steps,
        )

    def _evaluate_candidates(self, depth: int) -> List[PredatorFuture]:
        candidates = [self._simulate_candidate(action, depth) for action in self.actions]
        candidates.sort(key=lambda c: (c.total_score, -self.actions.index(c.first_action)), reverse=True)
        return candidates

    def _execute(self, depth: int) -> Tuple[List[PredatorExecutionStep], int, bool, bool]:
        agent = self.start
        predator = self.predator_start
        trace: List[PredatorExecutionStep] = []
        actual_intercepts = 0
        survived = True
        goal_reached = False

        for tick in range(1, self.max_ticks + 1):
            candidates = self._evaluate_from_state(agent, predator, depth)
            selected = candidates[0]

            action = selected.first_action
            agent_before = agent
            predator_before = predator

            agent_after = self._apply_action(agent, action)
            predator_after = self._move_predator(predator, agent_after, tick)

            intercepted = agent_after == predator_after or agent_after == predator_before
            if intercepted:
                actual_intercepts += 1
                survived = False

            reached_goal = agent_after == self.goal
            if reached_goal:
                goal_reached = True

            avoided_future = selected.predicted_intercepts == 0 and any(c.predicted_intercepts > 0 for c in candidates[1:])

            trace.append(
                PredatorExecutionStep(
                    tick=tick,
                    agent_before=agent_before,
                    predator_before=predator_before,
                    chosen_action=action,
                    agent_after=agent_after,
                    predator_after=predator_after,
                    predicted_intercepts_in_selected_future=selected.predicted_intercepts,
                    intercepted=intercepted,
                    reached_goal=reached_goal,
                    avoided_predator_future=avoided_future,
                )
            )

            agent = agent_after
            predator = predator_after

            if not survived or goal_reached:
                break

        return trace, actual_intercepts, survived, goal_reached

    def _simulate_candidate_from_state(self, agent_start: Tuple[int, int], predator_start: Tuple[int, int], first_action: str, depth: int) -> PredatorFuture:
        agent = agent_start
        predator = predator_start
        total_score = 0.0
        intercepts = 0
        goal_reached = False
        steps: List[Dict[str, Any]] = []

        for d in range(1, depth + 1):
            action = first_action if d == 1 else self._rollout_next_action(agent)
            agent_next = self._apply_action(agent, action)
            predator_next = self._move_predator(predator, agent_next, d)

            intercepted = agent_next == predator_next or agent_next == predator
            reached_goal = agent_next == self.goal

            if intercepted:
                intercepts += 1
            if reached_goal:
                goal_reached = True

            score = 0.0
            if reached_goal:
                score += float(self.policy.get("goal_bonus", 5.0))
            if intercepted:
                score -= float(self.policy.get("predator_intercept_penalty", 10.0))
            score -= 0.10 * self._distance_to_goal(agent_next)
            total_score += score * (0.82 ** (d - 1))

            steps.append(
                {
                    "depth": d,
                    "action": action,
                    "agent_position": list(agent_next),
                    "predator_position": list(predator_next),
                    "intercepted": intercepted,
                    "reached_goal": reached_goal,
                }
            )

            agent = agent_next
            predator = predator_next

        return PredatorFuture(
            first_action=first_action,
            depth=depth,
            total_score=round(total_score, 6),
            predicted_intercepts=intercepts,
            predicted_goal_reached=goal_reached,
            simulated_steps=steps,
        )

    def _evaluate_from_state(self, agent: Tuple[int, int], predator: Tuple[int, int], depth: int) -> List[PredatorFuture]:
        candidates = [
            self._simulate_candidate_from_state(agent, predator, action, depth)
            for action in self.actions
        ]
        candidates.sort(key=lambda c: (c.total_score, -self.actions.index(c.first_action)), reverse=True)
        return candidates

    def run(self, *, task_name: str = "adversarial_moving_predator") -> AdversarialMovingPredatorResult:
        shallow_candidates = self._evaluate_candidates(self.shallow_depth)
        deep_candidates = self._evaluate_candidates(self.deep_depth)

        shallow_choice = shallow_candidates[0]
        deep_choice = deep_candidates[0]

        shallow_action_deep_view = next(c for c in deep_candidates if c.first_action == shallow_choice.first_action)

        trace, actual_intercepts, survived, goal_reached = self._execute(self.deep_depth)

        avoided_before_impact = (
            shallow_choice.first_action != deep_choice.first_action
            and shallow_action_deep_view.predicted_intercepts >= 1
            and deep_choice.predicted_intercepts == 0
            and actual_intercepts == 0
        )

        if avoided_before_impact:
            self.policy["successful_predator_avoidances"] = int(self.policy.get("successful_predator_avoidances", 0)) + 1
            self.policy["best_first_action"] = deep_choice.first_action

        evidence = {
            "uses_llm_shortcut": False,
            "uses_adversarial_moving_hazard": True,
            "uses_predator_future_prediction": True,
            "uses_multistep_lookahead": True,
            "uses_before_impact_avoidance": True,
            "uses_persistent_predator_memory": True,
            "memory_loaded": self.memory_loaded,
            "shallow_first_action": shallow_choice.first_action,
            "deep_first_action": deep_choice.first_action,
            "shallow_action_predicted_intercepts_in_deep_view": shallow_action_deep_view.predicted_intercepts,
            "deep_action_predicted_intercepts": deep_choice.predicted_intercepts,
        }

        result = AdversarialMovingPredatorResult(
            kernel_version="phase21w_adversarial_moving_predator_kernel_v1",
            task_name=task_name,
            shallow_first_action=shallow_choice.first_action,
            deep_first_action=deep_choice.first_action,
            lookahead_changed_action=shallow_choice.first_action != deep_choice.first_action,
            predator_intercepts_predicted_for_shallow_action=shallow_action_deep_view.predicted_intercepts,
            predator_intercepts_predicted_for_deep_action=deep_choice.predicted_intercepts,
            predator_intercepts_actual=actual_intercepts,
            predator_avoided_before_impact=avoided_before_impact,
            survived=survived,
            goal_reached=goal_reached,
            ticks_run=len(trace),
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            shallow_candidates=[c.to_dict() for c in shallow_candidates],
            deep_candidates=[c.to_dict() for c in deep_candidates],
            execution_trace=[t.to_dict() for t in trace],
            final_predator_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational adversarial lookahead: AION can predict a moving predator's "
                "future interception path and avoid it before impact. It does not prove general intelligence "
                "or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_adversarial_moving_predator_kernel(
    *,
    memory_path: Optional[Path] = None,
    shallow_depth: int = 1,
    deep_depth: int = 4,
    max_ticks: int = 10,
    task_name: str = "adversarial_moving_predator",
) -> AdversarialMovingPredatorResult:
    return AionAdversarialMovingPredatorKernel(
        memory_path=memory_path,
        shallow_depth=shallow_depth,
        deep_depth=deep_depth,
        max_ticks=max_ticks,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_adversarial_moving_predator_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Adversarial predator memory saved to: {result.memory_path}")

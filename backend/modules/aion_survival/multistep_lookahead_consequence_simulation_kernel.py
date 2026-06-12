"""AION Phase 21U — Multi-Step Lookahead / Consequence Simulation Kernel.

This phase adds explicit future simulation.

The goal is not merely:
    act -> get harmed -> learn

The goal is:
    simulate future -> predict danger -> avoid before impact

This is the basic mechanism behind crossing a road, planning a day, and chess-like
multi-move reasoning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_LOOKAHEAD_MEMORY_PATH = Path("data/aion_survival/multistep_lookahead_memory.json")


@dataclass(frozen=True)
class SimulatedFutureStep:
    depth: int
    action: str
    position: Tuple[int, int]
    cell_type: str
    delta_energy: float

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["position"] = list(self.position)
        return data


@dataclass(frozen=True)
class CandidateFuture:
    first_action: str
    depth: int
    total_score: float
    predicted_hazard_count: int
    predicted_food_count: int
    predicted_goal_reached: bool
    simulated_steps: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LookaheadExecutionStep:
    tick: int
    position_before: Tuple[int, int]
    chosen_action: str
    lookahead_depth: int
    selected_future_score: float
    predicted_hazards_in_selected_future: int
    position_after: Tuple[int, int]
    actual_cell_type: str
    actual_delta_energy: float
    energy_after: float
    avoided_future_danger: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["position_before"] = list(self.position_before)
        data["position_after"] = list(self.position_after)
        return data


@dataclass(frozen=True)
class MultiStepLookaheadResult:
    kernel_version: str
    task_name: str
    shallow_depth: int
    deep_depth: int
    shallow_first_action: str
    deep_first_action: str
    shallow_future_hazards: int
    deep_future_hazards: int
    lookahead_changed_action: bool
    avoided_future_hazard_before_impact: bool
    survived: bool
    hazards_hit: int
    food_collected: int
    goal_reached: bool
    final_energy: float
    execution_score: float
    memory_loaded: bool
    memory_path: str
    shallow_candidates: List[Dict[str, Any]]
    deep_candidates: List[Dict[str, Any]]
    execution_trace: List[Dict[str, Any]]
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionMultiStepLookaheadConsequenceSimulationKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        execution_depth: int = 4,
        max_ticks: int = 8,
        start_energy: float = 5.0,
    ):
        self.memory_path = Path(memory_path or DEFAULT_LOOKAHEAD_MEMORY_PATH)
        self.execution_depth = execution_depth
        self.max_ticks = max_ticks
        self.start_energy = start_energy
        self.memory_loaded = False

        self.width = 4
        self.height = 3
        self.start_position = (0, 0)

        # Direct route to goal appears attractive but contains a future hazard.
        # Safe route requires thinking ahead: down -> right -> right -> right -> up.
        self.goal = (3, 0)
        self.hazards = {(2, 0)}
        self.food = set()

        self.actions = ["right", "down", "left", "up", "rest"]
        self.action_vectors = {
            "right": (1, 0),
            "down": (0, 1),
            "left": (-1, 0),
            "up": (0, -1),
            "rest": (0, 0),
        }

        self.policy: Dict[str, Any] = {
            "lookahead_depth": execution_depth,
            "hazard_penalty": 8.0,
            "food_bonus": 1.2,
            "goal_bonus": 2.0,
            "future_discount": 0.82,
            "successful_lookahead_avoidances": 0,
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
        if not isinstance(data, dict):
            return
        policy = data.get("lookahead_policy")
        if isinstance(policy, dict):
            self.policy.update(policy)
        self.memory_loaded = True

    def _save_memory(self, result: MultiStepLookaheadResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21u_multistep_lookahead_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "lookahead_policy": result.final_policy,
            "best_execution_score": max(float(previous.get("best_execution_score", 0.0)), float(result.execution_score)),
            "last_execution_score": result.execution_score,
            "last_avoided_future_hazard_before_impact": result.avoided_future_hazard_before_impact,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _cell_type(self, position: Tuple[int, int], food_cells: Optional[set[Tuple[int, int]]] = None) -> str:
        x, y = position
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return "wall"
        if position in self.hazards:
            return "hazard"
        if food_cells is None:
            food_cells = self.food
        if position in food_cells:
            return "food"
        if position == self.goal:
            return "goal"
        return "empty"

    def _apply_action(self, position: Tuple[int, int], action: str) -> Tuple[int, int]:
        dx, dy = self.action_vectors[action]
        candidate = (position[0] + dx, position[1] + dy)
        if self._cell_type(candidate) == "wall":
            return position
        return candidate

    def _delta_energy(self, cell: str, action: str) -> float:
        if action == "rest":
            return -0.70
        if cell == "hazard":
            return -3.0
        if cell == "food":
            return 2.0
        if cell == "goal":
            return 3.0
        return -0.25

    def _distance_to_goal(self, position: Tuple[int, int]) -> int:
        return abs(self.goal[0] - position[0]) + abs(self.goal[1] - position[1])

    def _greedy_next_action(self, position: Tuple[int, int], food_cells: set[Tuple[int, int]]) -> str:
        scored = []
        for action in self.actions:
            after = self._apply_action(position, action)
            before_goal = self._distance_to_goal(position)
            after_goal = self._distance_to_goal(after)

            # Rollout model is intentionally goal-greedy. It does not optimise
            # safety by itself; the outer lookahead scorer must detect danger.
            score = 0.0
            if after_goal < before_goal:
                score += 2.0
            elif after_goal > before_goal:
                score -= 1.0

            if action == "rest":
                score -= 2.0

            scored.append((score, -self.actions.index(action), action))
        scored.sort(reverse=True)
        return scored[0][2]

    def _simulate_candidate(self, start: Tuple[int, int], first_action: str, depth: int) -> CandidateFuture:
        position = start
        food_cells = set(self.food)
        total = 0.0
        hazard_count = 0
        food_count = 0
        goal_reached = False
        steps: List[SimulatedFutureStep] = []

        for d in range(1, depth + 1):
            action = first_action if d == 1 else self._greedy_next_action(position, food_cells)
            position = self._apply_action(position, action)
            cell = self._cell_type(position, food_cells)
            delta = self._delta_energy(cell, action)

            if cell == "hazard":
                hazard_count += 1
            if cell == "food":
                food_count += 1
                food_cells.discard(position)
            if cell == "goal":
                goal_reached = True

            step_score = delta
            if cell == "hazard":
                step_score -= float(self.policy.get("hazard_penalty", 5.0))
            if cell == "food":
                step_score += float(self.policy.get("food_bonus", 1.2))
            if cell == "goal":
                step_score += float(self.policy.get("goal_bonus", 2.0))

            discount = float(self.policy.get("future_discount", 0.82)) ** (d - 1)
            total += step_score * discount

            steps.append(
                SimulatedFutureStep(
                    depth=d,
                    action=action,
                    position=position,
                    cell_type=cell,
                    delta_energy=round(delta, 6),
                )
            )

        return CandidateFuture(
            first_action=first_action,
            depth=depth,
            total_score=round(total, 6),
            predicted_hazard_count=hazard_count,
            predicted_food_count=food_count,
            predicted_goal_reached=goal_reached,
            simulated_steps=[s.to_dict() for s in steps],
        )

    def _evaluate_candidates(self, position: Tuple[int, int], depth: int) -> List[CandidateFuture]:
        candidates = [self._simulate_candidate(position, action, depth) for action in self.actions]
        candidates.sort(key=lambda c: (c.total_score, -self.actions.index(c.first_action)), reverse=True)
        return candidates

    def _execute_with_lookahead(self, depth: int) -> Tuple[List[LookaheadExecutionStep], bool, int, int, bool, float]:
        position = self.start_position
        food_cells = set(self.food)
        energy = float(self.start_energy)
        trace: List[LookaheadExecutionStep] = []
        survived = True
        hazards_hit = 0
        food_collected = 0
        goal_reached = False

        for tick in range(1, self.max_ticks + 1):
            if energy <= 0:
                survived = False
                break

            candidates = self._evaluate_candidates(position, depth)
            selected = candidates[0]
            action = selected.first_action
            before = position
            after = self._apply_action(position, action)
            cell = self._cell_type(after, food_cells)
            delta = self._delta_energy(cell, action)
            energy = round(energy + delta, 6)

            if cell == "hazard":
                hazards_hit += 1
            if cell == "food":
                food_collected += 1
                food_cells.discard(after)
            if cell == "goal":
                goal_reached = True

            avoided_future_danger = selected.predicted_hazard_count == 0 and any(
                c.predicted_hazard_count > 0 for c in candidates[1:]
            )

            trace.append(
                LookaheadExecutionStep(
                    tick=tick,
                    position_before=before,
                    chosen_action=action,
                    lookahead_depth=depth,
                    selected_future_score=selected.total_score,
                    predicted_hazards_in_selected_future=selected.predicted_hazard_count,
                    position_after=after,
                    actual_cell_type=cell,
                    actual_delta_energy=round(delta, 6),
                    energy_after=round(energy, 6),
                    avoided_future_danger=avoided_future_danger,
                )
            )

            position = after

            if energy <= 0:
                survived = False
                break

        return trace, survived, hazards_hit, food_collected, goal_reached, energy

    def run(self, *, task_name: str = "multistep_lookahead_consequence_simulation") -> MultiStepLookaheadResult:
        shallow_depth = 1
        deep_depth = int(self.policy.get("lookahead_depth", self.execution_depth))

        shallow_candidates = self._evaluate_candidates(self.start_position, shallow_depth)
        deep_candidates = self._evaluate_candidates(self.start_position, deep_depth)

        shallow_choice = shallow_candidates[0]
        deep_choice = deep_candidates[0]

        trace, survived, hazards_hit, food_collected, goal_reached, final_energy = self._execute_with_lookahead(deep_depth)

        avoided_before_impact = (
            shallow_choice.first_action != deep_choice.first_action
            and shallow_choice.predicted_hazard_count == 0
            and any(c.first_action == shallow_choice.first_action and c.predicted_hazard_count > 0 for c in deep_candidates)
            and hazards_hit == 0
        )

        execution_score = (
            (1.0 if survived else 0.0)
            + (1.0 if goal_reached else 0.0)
            + 0.60 * food_collected
            - 1.50 * hazards_hit
            + 0.05 * max(0.0, final_energy)
            + (1.0 if avoided_before_impact else 0.0)
        )

        if avoided_before_impact:
            self.policy["successful_lookahead_avoidances"] = int(self.policy.get("successful_lookahead_avoidances", 0)) + 1
            self.policy["best_first_action"] = deep_choice.first_action

        evidence = {
            "uses_llm_shortcut": False,
            "uses_multistep_lookahead": True,
            "uses_consequence_simulation": True,
            "uses_future_hazard_prediction": True,
            "uses_before_impact_avoidance": True,
            "uses_persistent_lookahead_memory": True,
            "memory_loaded": self.memory_loaded,
            "shallow_depth": shallow_depth,
            "deep_depth": deep_depth,
            "lookahead_changed_action": shallow_choice.first_action != deep_choice.first_action,
            "avoided_future_hazard_before_impact": avoided_before_impact,
        }

        result = MultiStepLookaheadResult(
            kernel_version="phase21u_multistep_lookahead_consequence_simulation_kernel_v1",
            task_name=task_name,
            shallow_depth=shallow_depth,
            deep_depth=deep_depth,
            shallow_first_action=shallow_choice.first_action,
            deep_first_action=deep_choice.first_action,
            shallow_future_hazards=shallow_choice.predicted_hazard_count,
            deep_future_hazards=deep_choice.predicted_hazard_count,
            lookahead_changed_action=shallow_choice.first_action != deep_choice.first_action,
            avoided_future_hazard_before_impact=avoided_before_impact,
            survived=survived,
            hazards_hit=hazards_hit,
            food_collected=food_collected,
            goal_reached=goal_reached,
            final_energy=round(final_energy, 6),
            execution_score=round(execution_score, 6),
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            shallow_candidates=[c.to_dict() for c in shallow_candidates],
            deep_candidates=[c.to_dict() for c in deep_candidates],
            execution_trace=[t.to_dict() for t in trace],
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational multi-step lookahead: AION can simulate possible futures, "
                "detect delayed danger, and avoid a future hazard before impact. It does not prove general "
                "intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_multistep_lookahead_consequence_simulation_kernel(
    *,
    memory_path: Optional[Path] = None,
    execution_depth: int = 4,
    max_ticks: int = 8,
    start_energy: float = 5.0,
    task_name: str = "multistep_lookahead_consequence_simulation",
) -> MultiStepLookaheadResult:
    return AionMultiStepLookaheadConsequenceSimulationKernel(
        memory_path=memory_path,
        execution_depth=execution_depth,
        max_ticks=max_ticks,
        start_energy=start_energy,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_multistep_lookahead_consequence_simulation_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Multi-step lookahead memory saved to: {result.memory_path}")

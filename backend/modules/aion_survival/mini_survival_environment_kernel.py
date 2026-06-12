"""AION Phase 21P — Mini Survival Environment Kernel.

This is AION's first tiny survival world.

The kernel gives AION:
- a small grid;
- energy;
- food;
- hazard;
- limited actions;
- prediction before movement;
- rule/prediction repair from outcome;
- persistent survival memory.

It is deliberately small. The point is not a complex game yet. The point is to
prove that AION can use strategy, prediction, rules, and repair inside a survival
loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_SURVIVAL_MEMORY_PATH = Path("data/aion_survival/mini_survival_memory.json")


@dataclass(frozen=True)
class SurvivalTick:
    tick: int
    position_before: Tuple[int, int]
    action: str
    predicted_delta_energy: float
    position_after: Tuple[int, int]
    cell_type: str
    actual_delta_energy: float
    prediction_error: float
    energy_after: float
    survived: bool
    observation: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["position_before"] = list(self.position_before)
        data["position_after"] = list(self.position_after)
        return data


@dataclass(frozen=True)
class SurvivalRunResult:
    kernel_version: str
    task_name: str
    ticks_run: int
    survived: bool
    survival_score: float
    final_energy: float
    food_collected: int
    hazards_hit: int
    baseline_prediction_error: float
    final_prediction_error: float
    prediction_error_delta: float
    prediction_improved: bool
    ticks: List[Dict[str, Any]]
    final_policy: Dict[str, Any]
    memory_loaded: bool
    memory_path: str
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionMiniSurvivalEnvironmentKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        max_ticks: int = 12,
        start_energy: float = 6.0,
    ):
        self.memory_path = Path(memory_path or DEFAULT_SURVIVAL_MEMORY_PATH)
        self.max_ticks = max_ticks
        self.start_energy = start_energy
        self.width = 5
        self.height = 5
        self.start_position = (0, 0)

        # Tiny deterministic world:
        # AION starts at top-left.
        # Food is reachable by moving right/right/down.
        # Hazard is reachable but should be avoided.
        self.food_cells = {(2, 1), (4, 2)}
        self.hazard_cells = {(1, 2), (3, 1)}
        self.goal_cells = {(4, 4)}

        self.actions = ["right", "down", "left", "up", "rest"]
        self.action_vectors = {
            "right": (1, 0),
            "down": (0, 1),
            "left": (-1, 0),
            "up": (0, -1),
            "rest": (0, 0),
        }

        self.memory_loaded = False
        self.prediction_model: Dict[str, float] = {
            "food": 2.0,
            "hazard": -3.0,
            "empty": -0.25,
            "wall": -1.0,
            "goal": 3.0,
            # Rest is safe but should not dominate exploration.
            "rest": -0.60,
        }
        self.policy: Dict[str, Any] = {
            "prefer_food": 0.50,
            "avoid_hazard": 0.50,
            "avoid_wall": 0.50,
            "conserve_energy": 0.25,
            "best_action_by_position": {},
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

        model = data.get("prediction_model")
        if isinstance(model, dict):
            for key, value in model.items():
                self.prediction_model[str(key)] = float(value)

        policy = data.get("policy")
        if isinstance(policy, dict):
            for key, value in policy.items():
                self.policy[key] = value

        self.memory_loaded = True

    def _save_memory(self, result: SurvivalRunResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21p_mini_survival_environment_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "prediction_model": dict(self.prediction_model),
            "policy": dict(self.policy),
            "best_survival_score": max(float(previous.get("best_survival_score", 0.0)), float(result.survival_score)),
            "last_survival_score": result.survival_score,
            "last_survived": result.survived,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _cell_type(self, position: Tuple[int, int]) -> str:
        x, y = position
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return "wall"
        if position in self.food_cells:
            return "food"
        if position in self.hazard_cells:
            return "hazard"
        if position in self.goal_cells:
            return "goal"
        return "empty"

    def _apply_action(self, position: Tuple[int, int], action: str) -> Tuple[int, int]:
        dx, dy = self.action_vectors[action]
        candidate = (position[0] + dx, position[1] + dy)
        if self._cell_type(candidate) == "wall":
            return position
        return candidate

    def _actual_delta_energy(self, cell_type: str, action: str) -> float:
        if action == "rest":
            return -0.60
        if cell_type == "food":
            return 2.0
        if cell_type == "hazard":
            return -3.0
        if cell_type == "goal":
            return 3.0
        return -0.25

    def _predict_action(self, position: Tuple[int, int], action: str) -> float:
        if action == "rest":
            return float(self.prediction_model.get("rest", -0.05))
        after = self._apply_action(position, action)
        cell = self._cell_type(after)
        return float(self.prediction_model.get(cell, -0.25))

    def _choose_action(self, position: Tuple[int, int], energy: float, tick: int) -> str:
        key = f"{position[0]},{position[1]}"
        best_known = self.policy.get("best_action_by_position", {}).get(key)
        if isinstance(best_known, str) and best_known in self.actions:
            return best_known

        # Choose action with highest predicted delta, with deterministic tie-break.
        scored = []
        for action in self.actions:
            predicted = self._predict_action(position, action)
            after = self._apply_action(position, action)
            cell = self._cell_type(after)

            # Survival bias: avoid predicted hazards and walls; prefer food/goal.
            if cell == "hazard":
                predicted -= float(self.policy.get("avoid_hazard", 0.5))
            if cell == "wall":
                predicted -= float(self.policy.get("avoid_wall", 0.5))
            if cell == "food":
                predicted += float(self.policy.get("prefer_food", 0.5))
            if energy <= 2 and action == "rest":
                predicted += float(self.policy.get("conserve_energy", 0.25))

            # Stagnation penalty: survival should require exploration, not idle resting.
            if action == "rest" and energy > 2:
                predicted -= 0.75

            # Small curiosity bonus for unvisited movement cells.
            pos_key = f"{after[0]},{after[1]}"
            known_positions = set(self.policy.get("visited_positions", []))
            if action != "rest" and pos_key not in known_positions:
                predicted += 0.35

            scored.append((predicted, -self.actions.index(action), action))

        scored.sort(reverse=True)
        return scored[0][2]

    def _update_from_outcome(
        self,
        *,
        position_before: Tuple[int, int],
        action: str,
        cell_type: str,
        predicted: float,
        actual: float,
    ) -> None:
        # Update prediction model toward actual cell outcome.
        key = "rest" if action == "rest" else cell_type
        old = float(self.prediction_model.get(key, 0.0))
        self.prediction_model[key] = round(old + 0.40 * (actual - old), 6)

        # Update policy memory for visited positions and successful local action.
        pos_key = f"{position_before[0]},{position_before[1]}"
        visited = set(self.policy.get("visited_positions", []))
        visited.add(pos_key)
        self.policy["visited_positions"] = sorted(visited)

        best_by_pos = dict(self.policy.get("best_action_by_position", {}))
        if actual > 0:
            best_by_pos[pos_key] = action
            self.policy["prefer_food"] = round(min(1.0, float(self.policy.get("prefer_food", 0.5)) + 0.08), 6)
        elif action == "rest":
            self.policy["conserve_energy"] = round(max(0.0, float(self.policy.get("conserve_energy", 0.25)) - 0.05), 6)
        elif cell_type == "hazard":
            self.policy["avoid_hazard"] = round(min(1.0, float(self.policy.get("avoid_hazard", 0.5)) + 0.08), 6)
        elif cell_type == "wall":
            self.policy["avoid_wall"] = round(min(1.0, float(self.policy.get("avoid_wall", 0.5)) + 0.08), 6)

        self.policy["best_action_by_position"] = best_by_pos

    def run(self, *, task_name: str = "mini_survival_environment") -> SurvivalRunResult:
        position = self.start_position
        energy = float(self.start_energy)
        ticks: List[SurvivalTick] = []
        errors: List[float] = []
        food_collected = 0
        hazards_hit = 0
        survived = True

        for tick in range(1, self.max_ticks + 1):
            if energy <= 0:
                survived = False
                break

            action = self._choose_action(position, energy, tick)
            predicted = self._predict_action(position, action)
            position_before = position
            position_after = self._apply_action(position, action)
            cell_type = self._cell_type(position_after)
            actual = self._actual_delta_energy(cell_type, action)
            error = abs(actual - predicted)

            energy = round(energy + actual, 6)

            if cell_type == "food":
                food_collected += 1
                # Food is consumed after collection.
                self.food_cells.discard(position_after)
            if cell_type == "hazard":
                hazards_hit += 1

            if energy <= 0:
                survived = False

            self._update_from_outcome(
                position_before=position_before,
                action=action,
                cell_type=cell_type,
                predicted=predicted,
                actual=actual,
            )

            if actual > 0:
                observation = "survival-positive action; reinforce local policy"
            elif cell_type == "hazard":
                observation = "hazard encountered; repair policy toward avoidance"
            elif action == "rest":
                observation = "rest action conserved loop but cost small energy"
            else:
                observation = "neutral movement cost; continue exploration"

            ticks.append(
                SurvivalTick(
                    tick=tick,
                    position_before=position_before,
                    action=action,
                    predicted_delta_energy=round(predicted, 6),
                    position_after=position_after,
                    cell_type=cell_type,
                    actual_delta_energy=round(actual, 6),
                    prediction_error=round(error, 6),
                    energy_after=round(energy, 6),
                    survived=survived,
                    observation=observation,
                )
            )
            errors.append(error)
            position = position_after

            if not survived:
                break

        baseline_errors = errors[:3] if len(errors) >= 3 else errors
        final_errors = errors[-3:] if len(errors) >= 3 else errors
        baseline_prediction_error = sum(baseline_errors) / max(1, len(baseline_errors))
        final_prediction_error = sum(final_errors) / max(1, len(final_errors))
        prediction_error_delta = baseline_prediction_error - final_prediction_error

        survival_score = (
            (1.0 if survived else 0.0)
            + 0.10 * len(ticks)
            + 0.50 * food_collected
            - 0.75 * hazards_hit
            + 0.05 * max(0.0, energy)
        )

        evidence = {
            "uses_llm_shortcut": False,
            "uses_survival_world": True,
            "uses_energy": True,
            "uses_prediction_before_action": True,
            "uses_policy_update": True,
            "uses_persistent_memory": True,
            "memory_loaded": self.memory_loaded,
            "food_collected": food_collected,
            "hazards_hit": hazards_hit,
            "ticks_run": len(ticks),
            "prediction_error_trace": [round(e, 6) for e in errors],
        }

        result = SurvivalRunResult(
            kernel_version="phase21p_mini_survival_environment_kernel_v1",
            task_name=task_name,
            ticks_run=len(ticks),
            survived=survived,
            survival_score=round(survival_score, 6),
            final_energy=round(energy, 6),
            food_collected=food_collected,
            hazards_hit=hazards_hit,
            baseline_prediction_error=round(baseline_prediction_error, 6),
            final_prediction_error=round(final_prediction_error, 6),
            prediction_error_delta=round(prediction_error_delta, 6),
            prediction_improved=prediction_error_delta > 0,
            ticks=[t.to_dict() for t in ticks],
            final_policy=dict(self.policy),
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates a minimal operational survival loop: AION can predict, act, "
                "manage energy, update policy, and persist survival memory. "
                "It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_mini_survival_environment_kernel(
    *,
    memory_path: Optional[Path] = None,
    max_ticks: int = 12,
    start_energy: float = 6.0,
    task_name: str = "mini_survival_environment",
) -> SurvivalRunResult:
    return AionMiniSurvivalEnvironmentKernel(
        memory_path=memory_path,
        max_ticks=max_ticks,
        start_energy=start_energy,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_mini_survival_environment_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Mini survival memory saved to: {result.memory_path}")

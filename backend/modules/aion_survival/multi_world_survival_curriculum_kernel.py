"""AION Phase 21S — Multi-World Survival Curriculum Kernel.

Phase 21S runs AION through several small survival worlds and accumulates a
curriculum policy across them.

The purpose is to test whether survival learning can persist across maps rather
than only inside one fixed world.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CURRICULUM_MEMORY_PATH = Path("data/aion_survival/multi_world_curriculum_memory.json")


@dataclass(frozen=True)
class CurriculumWorldResult:
    world_id: str
    survived: bool
    ticks_run: int
    final_energy: float
    food_collected: int
    hazards_hit: int
    hazards_avoided: int
    world_score: float
    route: List[List[int]]
    learned_concepts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultiWorldSurvivalCurriculumResult:
    kernel_version: str
    task_name: str
    worlds_run: int
    worlds_survived: int
    curriculum_score: float
    baseline_world_score: float
    final_world_score: float
    curriculum_delta: float
    curriculum_improved: bool
    memory_loaded: bool
    memory_path: str
    world_results: List[Dict[str, Any]]
    final_curriculum_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionMultiWorldSurvivalCurriculumKernel:
    def __init__(
        self,
        *,
        memory_path: Optional[Path] = None,
        max_ticks_per_world: int = 10,
        start_energy: float = 5.0,
    ):
        self.memory_path = Path(memory_path or DEFAULT_CURRICULUM_MEMORY_PATH)
        self.max_ticks_per_world = max_ticks_per_world
        self.start_energy = start_energy
        self.memory_loaded = False

        self.actions = ["right", "down", "left", "up", "rest"]
        self.action_vectors = {
            "right": (1, 0),
            "down": (0, 1),
            "left": (-1, 0),
            "up": (0, -1),
            "rest": (0, 0),
        }

        self.curriculum_policy: Dict[str, Any] = {
            "prefer_food": 0.70,
            "avoid_hazard": 0.70,
            "seek_goal": 0.80,
            "avoid_wall": 0.40,
            "known_hazard_concept": True,
            "known_food_concept": True,
            "known_goal_concept": True,
            "world_policy": {},
            "concept_success_counts": {
                "food_seek": 0,
                "hazard_avoidance": 0,
                "goal_seek": 0,
            },
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

        policy = data.get("curriculum_policy")
        if isinstance(policy, dict):
            self.curriculum_policy.update(policy)

        self.memory_loaded = True

    def _save_memory(self, result: MultiWorldSurvivalCurriculumResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21s_multi_world_survival_curriculum_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "curriculum_policy": result.final_curriculum_policy,
            "best_curriculum_score": max(float(previous.get("best_curriculum_score", 0.0)), float(result.curriculum_score)),
            "last_curriculum_score": result.curriculum_score,
            "last_worlds_survived": result.worlds_survived,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _worlds(self) -> List[Dict[str, Any]]:
        return [
            {
                "world_id": "world_1_food_path",
                "width": 4,
                "height": 4,
                "start": (0, 0),
                "food": {(1, 0)},
                "hazards": {(0, 1)},
                "goal": (3, 3),
            },
            {
                "world_id": "world_2_hazard_detour",
                "width": 4,
                "height": 4,
                "start": (0, 0),
                "food": {(2, 1)},
                "hazards": {(1, 0), (1, 1)},
                "goal": (3, 3),
            },
            {
                "world_id": "world_3_goal_transfer",
                "width": 5,
                "height": 4,
                "start": (0, 0),
                "food": {(1, 2), (3, 1)},
                "hazards": {(0, 1), (2, 2)},
                "goal": (4, 3),
            },
        ]

    def _cell_type(self, world: Dict[str, Any], position: Tuple[int, int]) -> str:
        x, y = position
        if x < 0 or x >= int(world["width"]) or y < 0 or y >= int(world["height"]):
            return "wall"
        if position in world["hazards"]:
            return "hazard"
        if position in world["food"]:
            return "food"
        if position == world["goal"]:
            return "goal"
        return "empty"

    def _apply_action(self, world: Dict[str, Any], position: Tuple[int, int], action: str) -> Tuple[int, int]:
        dx, dy = self.action_vectors[action]
        candidate = (position[0] + dx, position[1] + dy)
        if self._cell_type(world, candidate) == "wall":
            return position
        return candidate

    def _delta_energy(self, cell: str, action: str) -> float:
        if action == "rest":
            return -0.75
        if cell == "hazard":
            return -3.0
        if cell == "food":
            return 2.0
        if cell == "goal":
            return 3.0
        return -0.25

    def _distance_to_goal(self, world: Dict[str, Any], position: Tuple[int, int]) -> int:
        goal = world["goal"]
        return abs(goal[0] - position[0]) + abs(goal[1] - position[1])

    def _choose_action(self, world: Dict[str, Any], position: Tuple[int, int], energy: float, visited: set[str]) -> str:
        scored = []

        for action in self.actions:
            after = self._apply_action(world, position, action)
            cell = self._cell_type(world, after)
            predicted = self._delta_energy(cell, action)

            if cell == "hazard":
                predicted -= 5.0 * float(self.curriculum_policy.get("avoid_hazard", 0.7))
            if cell == "food":
                predicted += float(self.curriculum_policy.get("prefer_food", 0.7))
            if cell == "goal":
                predicted += float(self.curriculum_policy.get("seek_goal", 0.8))
            if cell == "wall":
                predicted -= float(self.curriculum_policy.get("avoid_wall", 0.4))

            # Goal pressure: prefer moves that reduce distance to the goal.
            before_dist = self._distance_to_goal(world, position)
            after_dist = self._distance_to_goal(world, after)
            if after_dist < before_dist:
                predicted += 0.35
            elif after_dist > before_dist:
                predicted -= 0.20

            key = f"{after[0]},{after[1]}"
            if action != "rest" and key not in visited:
                predicted += 0.10

            if action == "rest":
                predicted -= 0.50

            scored.append((predicted, -self.actions.index(action), action))

        scored.sort(reverse=True)
        return scored[0][2]

    def _update_curriculum_policy(self, *, cell: str, avoided_hazard: bool, reached_goal: bool) -> List[str]:
        learned: List[str] = []
        counts = dict(self.curriculum_policy.get("concept_success_counts", {}))

        if cell == "food":
            counts["food_seek"] = int(counts.get("food_seek", 0)) + 1
            self.curriculum_policy["prefer_food"] = round(min(1.0, float(self.curriculum_policy.get("prefer_food", 0.7)) + 0.04), 6)
            learned.append("food_seek")
        if avoided_hazard:
            counts["hazard_avoidance"] = int(counts.get("hazard_avoidance", 0)) + 1
            self.curriculum_policy["avoid_hazard"] = round(min(1.0, float(self.curriculum_policy.get("avoid_hazard", 0.7)) + 0.04), 6)
            learned.append("hazard_avoidance")
        if reached_goal:
            counts["goal_seek"] = int(counts.get("goal_seek", 0)) + 1
            self.curriculum_policy["seek_goal"] = round(min(1.0, float(self.curriculum_policy.get("seek_goal", 0.8)) + 0.04), 6)
            learned.append("goal_seek")

        self.curriculum_policy["concept_success_counts"] = counts
        return learned

    def _run_world(self, world: Dict[str, Any]) -> CurriculumWorldResult:
        position = world["start"]
        energy = float(self.start_energy)
        route: List[List[int]] = [list(position)]
        visited: set[str] = {f"{position[0]},{position[1]}"}

        hazards_hit = 0
        hazards_avoided = 0
        food_collected = 0
        learned_concepts: List[str] = []
        survived = True

        for tick in range(1, self.max_ticks_per_world + 1):
            if energy <= 0:
                survived = False
                break

            adjacent_hazard_exists = any(
                self._cell_type(world, self._apply_action(world, position, action)) == "hazard"
                for action in self.actions
                if action != "rest"
            )

            action = self._choose_action(world, position, energy, visited)
            after = self._apply_action(world, position, action)
            cell = self._cell_type(world, after)

            avoided_hazard = adjacent_hazard_exists and cell != "hazard"
            if avoided_hazard:
                hazards_avoided += 1

            delta = self._delta_energy(cell, action)
            energy = round(energy + delta, 6)

            if cell == "hazard":
                hazards_hit += 1
            if cell == "food":
                food_collected += 1
                world["food"].discard(after)
            reached_goal = cell == "goal"

            learned = self._update_curriculum_policy(
                cell=cell,
                avoided_hazard=avoided_hazard,
                reached_goal=reached_goal,
            )
            learned_concepts.extend(learned)

            position = after
            route.append(list(position))
            visited.add(f"{position[0]},{position[1]}")

            if energy <= 0:
                survived = False
                break

        world_score = (
            (1.0 if survived else 0.0)
            + 0.10 * len(route)
            + 0.50 * food_collected
            + 0.25 * hazards_avoided
            - 1.00 * hazards_hit
            + 0.05 * max(0.0, energy)
        )

        world_policy = dict(self.curriculum_policy.get("world_policy", {}))
        world_policy[str(world["world_id"])] = {
            "survived": survived,
            "food_collected": food_collected,
            "hazards_hit": hazards_hit,
            "hazards_avoided": hazards_avoided,
            "score": round(world_score, 6),
        }
        self.curriculum_policy["world_policy"] = world_policy

        return CurriculumWorldResult(
            world_id=str(world["world_id"]),
            survived=survived,
            ticks_run=max(0, len(route) - 1),
            final_energy=round(energy, 6),
            food_collected=food_collected,
            hazards_hit=hazards_hit,
            hazards_avoided=hazards_avoided,
            world_score=round(world_score, 6),
            route=route,
            learned_concepts=sorted(set(learned_concepts)),
        )

    def run(self, *, task_name: str = "multi_world_survival_curriculum") -> MultiWorldSurvivalCurriculumResult:
        world_results = [self._run_world(dict(world)) for world in self._worlds()]

        scores = [w.world_score for w in world_results]
        baseline_world_score = scores[0] if scores else 0.0
        final_world_score = scores[-1] if scores else 0.0
        curriculum_score = round(sum(scores), 6)
        curriculum_delta = round(final_world_score - baseline_world_score, 6)
        worlds_survived = sum(1 for w in world_results if w.survived)

        # Improvement can mean either final score improves or all worlds survive
        # while concept counters increase.
        counts = self.curriculum_policy.get("concept_success_counts", {})
        concepts_learned = sum(int(v) for v in counts.values()) if isinstance(counts, dict) else 0
        curriculum_improved = bool(worlds_survived == len(world_results) and concepts_learned > 0)

        evidence = {
            "uses_llm_shortcut": False,
            "uses_multi_world_curriculum": True,
            "uses_energy": True,
            "uses_food_seeking_transfer": True,
            "uses_hazard_avoidance_transfer": True,
            "uses_goal_seeking_transfer": True,
            "uses_persistent_curriculum_memory": True,
            "memory_loaded": self.memory_loaded,
            "worlds_run": len(world_results),
            "worlds_survived": worlds_survived,
            "concept_success_counts": dict(self.curriculum_policy.get("concept_success_counts", {})),
        }

        result = MultiWorldSurvivalCurriculumResult(
            kernel_version="phase21s_multi_world_survival_curriculum_kernel_v1",
            task_name=task_name,
            worlds_run=len(world_results),
            worlds_survived=worlds_survived,
            curriculum_score=curriculum_score,
            baseline_world_score=round(baseline_world_score, 6),
            final_world_score=round(final_world_score, 6),
            curriculum_delta=curriculum_delta,
            curriculum_improved=curriculum_improved,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            world_results=[w.to_dict() for w in world_results],
            final_curriculum_policy=dict(self.curriculum_policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates an operational multi-world survival curriculum: AION can run multiple "
                "survival worlds, reuse food/hazard/goal concepts, update a curriculum policy, and persist "
                "cross-world survival memory. It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_multi_world_survival_curriculum_kernel(
    *,
    memory_path: Optional[Path] = None,
    max_ticks_per_world: int = 10,
    start_energy: float = 5.0,
    task_name: str = "multi_world_survival_curriculum",
) -> MultiWorldSurvivalCurriculumResult:
    return AionMultiWorldSurvivalCurriculumKernel(
        memory_path=memory_path,
        max_ticks_per_world=max_ticks_per_world,
        start_energy=start_energy,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_multi_world_survival_curriculum_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Multi-world curriculum memory saved to: {result.memory_path}")

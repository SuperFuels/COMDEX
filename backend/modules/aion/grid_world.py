# backend/modules/aion/grid_world.py

import random
from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.strategy_planner import StrategyPlanner

# ── Setup
GRID_SIZE = 10
OBJECTS = ['bed', 'desk', 'coffee', 'window']
DANGERS = ['pit', 'spike']
MAX_STEPS = 100
VISION_RANGE = 2

memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()


class AIONAgent:
    def __init__(self):
        self.reset()

    def reset(self):
        self.position = [0, 0]
        self.visited = set()
        self.collected = set()
        self.steps = 0
        self.score = 0
        self.alive = True

    def move(self, direction):
        if not self.alive:
            return "☠️ AION is dead."

        dx, dy = {
            'up': (-1, 0), 'down': (1, 0),
            'left': (0, -1), 'right': (0, 1)
        }.get(direction, (0, 0))

        new_x = max(0, min(GRID_SIZE - 1, self.position[0] + dx))
        new_y = max(0, min(GRID_SIZE - 1, self.position[1] + dy))
        self.position = [new_x, new_y]
        self.steps += 1

        obj = world.get(tuple(self.position), None)
        self.visited.add(tuple(self.position))

        if obj in DANGERS:
            self.alive = False
            return f"💀 AION stepped on a {obj} and died."
        elif obj in OBJECTS and obj not in self.collected:
            self.collected.add(obj)
            self.score += 10
            return f"✅ AION collected {obj}."
        else:
            return f"➡️ Moved to {self.position}."

    def sense(self):
        x, y = self.position
        vision = {}
        for dx in range(-VISION_RANGE, VISION_RANGE + 1):
            for dy in range(-VISION_RANGE, VISION_RANGE + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    obj = world.get((nx, ny), None)
                    if obj:
                        vision[(nx, ny)] = obj
        return vision

    def game_over(self):
        return not self.alive or self.steps >= MAX_STEPS or self.collected == set(OBJECTS)

    def summary(self):
        return {
            "steps": self.steps,
            "score": self.score,
            "collected": list(self.collected),
            "status": "complete" if self.collected == set(OBJECTS) else "failed"
        }


def spawn_world():
    layout = {}
    positions = random.sample(
        [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)],
        len(OBJECTS) + len(DANGERS)
    )
    for i, obj in enumerate(OBJECTS + DANGERS):
        layout[positions[i]] = obj
    return layout

# ── Simulation Runner
def run_grid_simulation():
    global world
    world = spawn_world()
    aion = AIONAgent()
    log = []

    while not aion.game_over():
        vision = aion.sense()
        direction = random.choice(['up', 'down', 'left', 'right'])
        outcome = aion.move(direction)
        log.append(outcome)

    # Store memory
    summary = aion.summary()
    memory.store({
        "label": f"grid_world_run_{summary['status']}",
        "content": str(summary)
    })

    if summary['status'] == 'complete':
        tracker.record_milestone("Grid World Completed")
        tracker.export_summary()
        planner.generate()

    return summary, log
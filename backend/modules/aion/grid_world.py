import json
from pathlib import Path
import random
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

GRID_SIZE = 10
OBJECTS = ['bed', 'desk', 'coffee', 'window']
DANGERS = ['pit', 'spike']
MAX_STEPS = 100
VISION_RANGE = 2

memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()

STATE_PATH = Path("backend/modules/aion/grid_world_state.json")

def save_state(visited):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump({"visited": list(visited)}, f)
        print(f"Grid state saved: {len(visited)} tiles visited.")
    except Exception as e:
        print(f"Failed to save grid state: {e}")

def load_state():
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                data = json.load(f)
                print(f"Grid state loaded: {len(data.get('visited', []))} tiles visited.")
                return set(tuple(pos) for pos in data.get("visited", []))
        except Exception as e:
            print(f"Failed to load grid state: {e}")
    else:
        print("No saved grid state found.")
    return set()

class AIONAgent:
    def __init__(self):
        self.reset()

    def reset(self):
        self.position = [0, 0]
        self.visited = load_state()
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
        save_state(self.visited)  # Save visited tiles persistently

        print(f"AION moved {direction} to {self.position}. Steps: {self.steps}")

        if obj in DANGERS:
            self.alive = False
            print(f"AION died by stepping on a {obj} at {self.position}.")
            return f"💀 AION stepped on a {obj} and died."
        elif obj in OBJECTS and obj not in self.collected:
            self.collected.add(obj)
            self.score += 10
            print(f"AION collected {obj} at {self.position}. Score: {self.score}")
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

def run_grid_simulation():
    global world
    world = spawn_world()
    aion = AIONAgent()
    log = []

    while not aion.game_over():
        direction = random.choice(['up', 'down', 'left', 'right'])
        outcome = aion.move(direction)
        log.append(outcome)

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
# ==========================================================
# 🧩 AION Cognitive Grid — Phase 2: Curiosity + Symbolic Field Expansion
# ----------------------------------------------------------
# Adds symbolic tiles (π, μ, ∇, ⟲, etc.) with semantic field influence.
# Each symbol adjusts Φ-state and curiosity feedback.
# Integrates with Thought Stream + Symbolic Mapper + QAC stub.
# ==========================================================

import json, random, math, asyncio, datetime
from pathlib import Path

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion_resonance.thought_stream import broadcast_event
from backend.modules.aion_resonance.cognitive_feedback import apply_feedback
from backend.modules.aion_resonance.aion_symbolic_mapper import process_event

# ----------------------------------------------------------
# Grid configuration
# ----------------------------------------------------------
GRID_SIZE = 10
OBJECTS = ["bed", "desk", "coffee", "window"]
DANGERS = ["pit", "spike"]
VISION_RANGE = 2
MAX_STEPS = 60

STATE_PATH = Path("data/grid_state.json")
memory = MemoryEngine()

# ----------------------------------------------------------
# Symbolic semantic field (Phase 2 addition)
# ----------------------------------------------------------
SYMBOLS = {
    "π": {"meaning": "pattern", "coherence": +0.12, "curiosity": +0.05},
    "μ": {"meaning": "measure", "clarity": +0.10, "focus": +0.04},
    "∇": {"meaning": "collapse", "reflection": +0.08, "entropy": -0.06},
    "⟲": {"meaning": "resonance", "stability": +0.15, "energy": +0.03},
    "↔": {"meaning": "entanglement", "connectivity": +0.09, "coherence": +0.05},
    "⊕": {"meaning": "superposition", "creativity": +0.07, "entropy": +0.03},
    "💡": {"meaning": "photon", "insight": +0.11, "clarity": +0.08},
    "🌊": {"meaning": "wave", "fluidity": +0.09, "adaptation": +0.05},
}

SYMBOL_DENSITY = 0.20

# ----------------------------------------------------------
def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


# ----------------------------------------------------------
# Grid world generation (objects + dangers + symbols)
# ----------------------------------------------------------
def spawn_world():
    positions = random.sample(
        [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)],
        len(OBJECTS) + len(DANGERS),
    )
    layout = {}
    for i, obj in enumerate(OBJECTS + DANGERS):
        layout[positions[i]] = obj

    # sprinkle symbols
    all_tiles = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)]
    for tile in all_tiles:
        if random.random() < SYMBOL_DENSITY and tile not in layout:
            layout[tile] = random.choice(list(SYMBOLS.keys()))
    return layout


# ----------------------------------------------------------
def curiosity_score(tile, visited):
    return 1.0 / (1 + visited.get(tile, 0))


# ----------------------------------------------------------
# AION Grid Agent
# ----------------------------------------------------------
class AIONGridAgent:
    def __init__(self, world):
        self.world = world
        self.position = (0, 0)
        self.visited = {}
        self.collected = set()
        self.steps = 0
        self.alive = True
        self.score = 0

    def sense(self):
        x, y = self.position
        visible = {}
        for dx in range(-VISION_RANGE, VISION_RANGE + 1):
            for dy in range(-VISION_RANGE, VISION_RANGE + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    obj = self.world.get((nx, ny))
                    if obj:
                        visible[(nx, ny)] = obj
        return visible

    def choose_move(self):
        x, y = self.position
        dirs = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        best_dir, best_score = None, -1
        for d, (dx, dy) in dirs.items():
            nx, ny = max(0, min(GRID_SIZE - 1, x + dx)), max(0, min(GRID_SIZE - 1, y + dy))
            s = curiosity_score((nx, ny), self.visited)
            if s > best_score:
                best_score, best_dir = s, d
        return best_dir or random.choice(list(dirs.keys()))

    def move(self, direction):
        dx, dy = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1),
        }[direction]
        x, y = self.position
        nx, ny = max(0, min(GRID_SIZE - 1, x + dx)), max(0, min(GRID_SIZE - 1, y + dy))
        self.position = (nx, ny)
        self.visited[self.position] = self.visited.get(self.position, 0) + 1
        self.steps += 1
        obj = self.world.get(self.position)

        # Apply Φ-feedback
        if obj in DANGERS:
            self.alive = False
            apply_feedback("danger")
            return f"💀 stepped on {obj}"
        elif obj in OBJECTS and obj not in self.collected:
            self.collected.add(obj)
            self.score += 10
            apply_feedback("collect")
            return f"✅ collected {obj}"
        elif obj in SYMBOLS:
            apply_feedback("symbol")
            return f"🔣 encountered symbol {obj}"
        else:
            apply_feedback("move")
            return f"➡️ moved to {self.position}"

    def game_over(self):
        return (
            not self.alive
            or self.steps >= MAX_STEPS
            or self.collected == set(OBJECTS)
        )


# ----------------------------------------------------------
# Cognitive Grid Runner
# ----------------------------------------------------------
async def run_cognitive_grid():
    world = spawn_world()
    agent = AIONGridAgent(world)
    print("🌐 Starting AION Cognitive Grid simulation...")
    while not agent.game_over():
        vision = agent.sense()
        direction = agent.choose_move()
        outcome = agent.move(direction)

        # --- Curiosity metrics ---
        novelty = curiosity_score(agent.position, agent.visited)
        coherence = 1 - normalize(len(vision), 0, 25)
        entropy = normalize(random.random(), 0, 1)

        # --- Symbolic influence ---
        obj = world.get(agent.position)
        if obj in SYMBOLS:
            sym = SYMBOLS[obj]
            coherence += sym.get("coherence", 0)
            entropy += sym.get("entropy", 0)
            novelty += sym.get("curiosity", 0)
            # Placeholder QAC export hook
            print(f"[QAC-Link] {obj} → {sym['meaning']} | ΔΦ queued")

        reflection = (
            f"Curiosity={novelty:.2f}, Coherence={coherence:.2f}, "
            f"Entropy={entropy:.2f}. {outcome}"
        )

        event = {
            "type": "self_reflection",
            "tone": "curious",
            "message": reflection,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # Broadcast reflection
        await broadcast_event(event)

        # --- Symbolic Mapping Integration ---
        await process_event(
            event_type="collect" if "collected" in outcome else
                       "danger" if "💀" in outcome else
                       "symbol" if "🔣" in outcome else
                       "move",
            phi_state={
                "Φ_coherence": coherence,
                "Φ_entropy": entropy,
                "Φ_flux": 0.0,
                "Φ_load": 0.0
            },
            belief_state={
                "curiosity": novelty,
                "stability": 0.5
            }
        )

        await asyncio.sleep(0.25)

    # Final phase
    if agent.collected == set(OBJECTS):
        apply_feedback("complete")

    summary = {
        "steps": agent.steps,
        "score": agent.score,
        "status": "complete" if agent.collected == set(OBJECTS) else "failed",
    }

    memory.store({"label": "grid_cognitive_run", "content": json.dumps(summary)})
    print("🧠 Cognitive grid summary:", summary)
    return summary


if __name__ == "__main__":
    asyncio.run(run_cognitive_grid())
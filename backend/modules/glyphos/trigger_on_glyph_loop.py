# File: backend/modules/glyphos/trigger_on_glyph_loop.py

import threading
import time

from backend.modules.dna_chain.dc_handler import load_dimension_by_id
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ DNA Switch registration for tracking and mutation
DNA_SWITCH.register(__file__)  # DNA evolution enabled

# ✅ Glyphs that trigger Tessaris runtime actions
WATCHED_GLYPHS = {"🧠", "✧", "🪄"}

# ✅ Runtime registry of containers to monitor
GLYPH_TRIGGER_REGISTRY = set()


def register_container_for_glyph_triggers(container_id: str):
    """Register a container ID to be monitored for glyph-based triggers."""
    GLYPH_TRIGGER_REGISTRY.add(container_id)
    print(f"[🔗] Registered container for glyph triggers: {container_id}")


def glyph_behavior_loop(poll_interval: float = 2.0):
    """Watch live containers for glyphs that should trigger Tessaris logic."""
    print("🔁 Starting glyph behavior watcher...")
    while True:
        for container_id in list(GLYPH_TRIGGER_REGISTRY):
            try:
                container = load_dimension_by_id(container_id)
                cubes = container.get("cubes", [])

                for cube in cubes:
                    glyphs = cube.get("glyphs", [])
                    if any(glyph in WATCHED_GLYPHS for glyph in glyphs):
                        print(f"🚨 Glyph trigger detected in container {container_id}: {glyphs}")
                        # Launch a reaction via Tessaris
                        TessarisEngine.process_triggered_cube(cube, source=container_id)

            except Exception as e:
                print(f"⚠️ Glyph trigger check failed in container {container_id}: {e}")
        time.sleep(poll_interval)